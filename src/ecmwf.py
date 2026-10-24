"""Archived ECMWF rain forecasts for the three storms (task A15).

C9 runs Layer 2 on rain forecasts made 1, 2 and 3 days before each storm instead of
the rain that fell. This script gets those forecasts from Open-Meteo's Previous Runs
API (https://open-meteo.com/en/docs/previous-runs-api), model ECMWF IFS 0.25 degree
(config.FORECAST_MODEL), and checks which storms the archive covers (gate A).

What "previous day N" means: for every hour, Open-Meteo keeps the value from a model
run started at least 24 x N hours before that hour. It drops each run's first 24 x N
hours and joins the runs into one series. So precipitation_previous_day1 is the
forecast made about 1 day ahead, _day2 about 2 days ahead, and so on.
Open-Meteo began storing ECMWF IFS 0.25 runs in February 2024 (first hour: 3 Feb 2024
for day 1).

Why previous days 1 to 5 (config.FORECAST_PREVIOUS_DAYS): C9 forecasts an n-day rain
total (n = config.RAIN_ACCUM_DAYS = 3) 1, 2 and 3 days before the window's first day
(config.FORECAST_LEADS_DAYS). A forecast made L days before the window reaches day i of
the window (i = 0, 1, 2) L + i days ahead, so it is previous_day L on the first day,
L + 1 on the second and L + 2 on the third. For each hour of the day, those three values
come from the same run. Leads 1-3 with n = 3 need previous days 1-5. Taking
previous_day1 on all three days would mix in runs started during the storm.

Where: every 0.25 degree grid cell that overlaps the A7 catchments, with its share of
the catchment area as its weight (catchments.grid_cells). A14 uses the same cells for
ERA5, so C9 compares each forecast with ERA5's own return levels over the same area.

When: each storm's wettest UTC days, from config.STORMS (Carina first; A11 adds the
2025 and 2026 dates), plus the n - 1 days before the first of them. C3 and C8 take a
storm's wettest n-day window whose last day is one of its wettest days, so a window can
start up to n - 1 days early (fetch_span). A storm without dates is skipped and listed
as such.

Hours to UTC days: Open-Meteo labels each hourly total with the end of its hour (the
01:00 value is rain from 00:00 to 01:00 UTC). utc_day_totals moves every label back
1 hour, then adds up each day's 24 hours, so a day is 00:00-24:00 UTC, the same day as
IMERG (8 AM-8 AM Philippine time). This is why each request runs to the day after the
storm's last day: that day's 00:00 value is the last hour of the storm's last day.

Each storm's reply is saved unchanged in data/raw/ecmwf_previous_runs/, one JSON file
per storm named with the model and its dates. A file already there is not fetched
again (delete it to refresh).

Output: data/clean/forecasts_storms.csv, one row per storm, previous day N, UTC day and cell:
    storm, previous_day, date, lat, lon, weight, rain_mm
previous_day N holds Open-Meteo's precipitation_previous_dayN; C9 turns these into
lead-time totals. A storm and previous day are written only if the archive has every
hour of every day at every cell. The catchment rain for one storm, previous day and UTC
day is sum(weight x rain_mm).
The table is rewritten on every run, with only its header if no storm is covered, so a
table from an earlier run is never left behind. A storm Open-Meteo refuses (HTTP 400,
e.g. dates outside its archive) is reported as not covered; a download that still fails
after RETRIES tries is reported as not checked, and the run then exits with an error.

Run from the repository root (needs A7's catchments_qc.gpkg):
    python -m src.ecmwf
"""

import json
import time
from datetime import date, timedelta

import geopandas as gpd
import pandas as pd
import requests

import config
from src import catchments

PREVIOUS_RUNS_API = "https://previous-runs-api.open-meteo.com/v1/forecast"
TIMEOUT_S = 120
RETRIES = 3
RETRY_WAIT_S = 10
SAME_POINT_DEG = 0.001  # a reply's grid point must be the requested one to within this
COLUMNS = ["storm", "previous_day", "date", "lat", "lon", "weight", "rain_mm"]


class RequestRefused(Exception):
    """Open-Meteo answered HTTP 400 (dates outside its archive, or a bad parameter). Retrying will not help."""


def previous_day_variable(n):
    """Open-Meteo's name for the forecast made n days ahead of each hour, e.g. precipitation_previous_day1."""
    return f"precipitation_previous_day{n}"


def fetch_span(first, last):
    """The UTC days fetched for a storm whose wettest days are first..last.

    From n - 1 days before `first` (n = config.RAIN_ACCUM_DAYS), so an n-day window that
    ends on `first` is covered, to `last`.
    """
    return first - timedelta(days=config.RAIN_ACCUM_DAYS - 1), last


def leads_covered(covered):
    """The lead times C9 can use: lead L needs previous days L to L + n - 1, all covered.

    covered: coverage(table), True or False per previous day.
    """
    days = range(config.RAIN_ACCUM_DAYS)
    return [lead for lead in config.FORECAST_LEADS_DAYS
            if all(covered.get(lead + i, False) for i in days)]


def raw_path(storm, first, last):
    """Where one storm's reply is saved, e.g. data/raw/ecmwf_previous_runs/carina_2024_ecmwf_ifs025_20240721_20240725.json.

    first and last are the fetched days (fetch_span). The model is in the name, so
    changing config.FORECAST_MODEL fetches new replies instead of reading another model's.
    """
    return config.ECMWF_RAW / f"{storm}_{config.FORECAST_MODEL}_{first:%Y%m%d}_{last:%Y%m%d}.json"


def request_params(cells, first, last):
    """The Previous Runs request for one storm: every cell, every previous day, in UTC.

    end_date is the day after the storm's last day, for that day's 00:00 value (see the
    top of this file). cell_selection=nearest returns the grid point itself; Open-Meteo's
    default may move to a neighbouring land cell with a similar elevation.
    """
    return {
        "latitude": ",".join(str(v) for v in cells["lat"]),
        "longitude": ",".join(str(v) for v in cells["lon"]),
        "hourly": ",".join(previous_day_variable(n) for n in config.FORECAST_PREVIOUS_DAYS),
        "models": config.FORECAST_MODEL,
        "start_date": f"{first:%Y-%m-%d}",
        "end_date": f"{last + timedelta(days=1):%Y-%m-%d}",
        "timezone": "GMT",
        "cell_selection": "nearest",
    }


def fetch(cells, first, last, path):
    """Request one storm from Open-Meteo and save the reply at path, byte for byte as received.

    The file is written under a temporary name first, so a stopped run never leaves half
    a file that a rerun would read.
    """
    r = requests.get(PREVIOUS_RUNS_API, params=request_params(cells, first, last), timeout=TIMEOUT_S)
    if r.status_code == 400:
        raise RequestRefused(r.text[:300])  # Open-Meteo's reply names the reason
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    part.write_bytes(r.content)
    part.replace(path)


def fetch_retrying(cells, first, last, path):
    """fetch() with up to RETRIES tries, waiting a little longer after each failure; RequestRefused is raised at once."""
    for attempt in range(1, RETRIES + 1):
        try:
            fetch(cells, first, last, path)
            return
        except requests.RequestException:
            if attempt == RETRIES:
                raise
            time.sleep(RETRY_WAIT_S * attempt)


def download(storm, cells, first, last):
    """One storm's reply from Open-Meteo, as a list with one entry per cell.

    The reply is saved unchanged before it is read, and a saved reply is reused.
    The request is tried again on a failure (fetch_retrying).
    """
    path = raw_path(storm, first, last)
    if path.exists():
        print(f"{storm}: reading {path.name} (already on disk)")
    else:
        print(f"{storm}: requesting {first} to {last} from Open-Meteo Previous Runs")
        fetch_retrying(cells, first, last, path)

    replies = json.loads(path.read_text(encoding="utf-8"))
    return replies if isinstance(replies, list) else [replies]  # one cell comes back without a list


def check_reply(replies, cells, path):
    """Stop unless the reply holds the requested cells, in order, in UTC, in mm."""
    if len(replies) != len(cells):
        raise ValueError(f"{path.name}: {len(replies)} points, expected {len(cells)} (delete it to refresh)")
    for reply, cell in zip(replies, cells.itertuples()):
        if (abs(reply["latitude"] - cell.lat) > SAME_POINT_DEG
                or abs(reply["longitude"] - cell.lon) > SAME_POINT_DEG):
            raise ValueError(f"{path.name}: got point {reply['latitude']}, {reply['longitude']} "
                             f"for cell {cell.lat}, {cell.lon} (delete it to refresh)")
        if reply["utc_offset_seconds"] != 0:
            raise ValueError(f"{path.name}: times are not UTC")
        for n in config.FORECAST_PREVIOUS_DAYS:
            unit = reply["hourly_units"].get(previous_day_variable(n), "missing")
            if unit != "mm":
                raise ValueError(f"{path.name}: unit of {previous_day_variable(n)} is {unit}, expected mm "
                                 f"(delete it to refresh)")


def utc_day_totals(hourly):
    """Add hourly rain up into UTC days.

    hourly: table indexed by Open-Meteo's hour labels (UTC), one column per variable, mm.
    Each label is the end of its hour, so it moves back config.OPEN_METEO_HOUR_SHIFT (-1)
    hours to the hour's start; then each day is the sum of its 24 hours. A day with a
    missing hour, or with fewer than 24 hours in the table, gets NaN.
    """
    shifted = hourly.copy()
    shifted.index = shifted.index + pd.Timedelta(hours=config.OPEN_METEO_HOUR_SHIFT)
    return shifted.groupby(shifted.index.floor("D")).sum(min_count=24)


def storm_table(storm, replies, cells, first, last):
    """One storm's daily forecasts: storm, previous_day, date, lat, lon, weight, rain_mm.

    first..last are the fetched days (fetch_span). Days outside them are dropped (the
    request's extra day and the hour before the first day). rain_mm is NaN where the
    archive misses an hour.
    """
    days = pd.date_range(first, last, freq="D")
    rows = []
    for reply, cell in zip(replies, cells.itertuples()):
        hourly = pd.DataFrame(reply["hourly"]).set_index("time")
        hourly.index = pd.to_datetime(hourly.index)
        daily = utc_day_totals(hourly.astype(float)).reindex(days)
        for n in config.FORECAST_PREVIOUS_DAYS:
            for day, rain in daily[previous_day_variable(n)].items():
                rows.append({"storm": storm, "previous_day": n, "date": f"{day:%Y-%m-%d}",
                             "lat": cell.lat, "lon": cell.lon, "weight": round(cell.weight, 6),
                             "rain_mm": round(rain, 2)})  # hourly values have 2 decimals; drops float noise
    return pd.DataFrame(rows, columns=COLUMNS)


def coverage(table):
    """For each previous day N: True if every day at every cell has a forecast."""
    return table.groupby("previous_day")["rain_mm"].apply(lambda r: bool(r.notna().all()))


def catchment_rain(table):
    """Catchment rain per previous day N and UTC day: sum of weight x rain_mm over the cells (mm)."""
    weighted = table.assign(mm=table["weight"] * table["rain_mm"])
    return weighted.pivot_table(index="date", columns="previous_day", values="mm", aggfunc="sum").round(1)


def tracker_line(status):
    """The one line for the Request Tracker: which storms the archive covers."""
    leads = ", ".join(str(n) for n in config.FORECAST_LEADS_DAYS)
    storms = "; ".join(f"{storm} {text}" for storm, text in status.items())
    return (f"A15 ({date.today():%Y-%m-%d}): Open-Meteo Previous Runs, ECMWF IFS 0.25, "
            f"{config.RAIN_ACCUM_DAYS}-day totals at leads {leads} days: {storms}")


def main():
    shape = gpd.read_file(config.CATCHMENTS, layer="catchments")
    cells = catchments.grid_cells(shape, config.GRID_025_DEG)
    print(f"{len(cells)} cells of {config.GRID_025_DEG} degrees overlap the catchments:")
    print(cells.round({"km2": 1, "weight": 3}).to_string(index=False))
    print()

    tables, status, failed = [], {}, []
    for storm, facts in config.STORMS.items():  # Carina first
        if facts["wettest_days"] is None:
            status[storm] = "not checked: no dates yet (A11)"
            print(f"{storm}: skipped, no wettest days in config.STORMS yet (A11)")
            continue
        first, last = fetch_span(*facts["wettest_days"])
        try:
            replies = download(storm, cells, first, last)
        except RequestRefused as e:
            status[storm] = f"not covered ({first} to {last}): Open-Meteo refused the request: {e}"
            print(f"  {status[storm]}")
            continue
        except requests.RequestException as e:
            status[storm] = f"not checked ({first} to {last}): download failed after {RETRIES} tries"
            print(f"  {status[storm]}: {e}")
            failed.append(storm)
            continue
        check_reply(replies, cells, raw_path(storm, first, last))
        table = storm_table(storm, replies, cells, first, last)

        covered = coverage(table)
        days_in = [n for n in covered.index if covered[n]]
        leads_in = leads_covered(covered)
        if len(leads_in) == len(config.FORECAST_LEADS_DAYS):
            status[storm] = f"covered ({first} to {last})"
        elif leads_in:
            status[storm] = f"partly covered ({first} to {last}): leads {leads_in} only"
        else:
            status[storm] = f"not covered ({first} to {last})"
        print(f"  {status[storm]}")

        if days_in:
            table = table[table["previous_day"].isin(days_in)]
            print("  catchment rain, mm per UTC day (columns: previous day N):")
            print("  " + catchment_rain(table).to_string().replace("\n", "\n  "))
            tables.append(table)

    # Always rewritten, header only if nothing is covered, so C9 never reads an earlier run's table.
    out = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=COLUMNS)
    part = config.FORECASTS_STORMS.with_suffix(".part")
    out.to_csv(part, index=False)
    part.replace(config.FORECASTS_STORMS)
    if out.empty:
        print(f"\nno storm has archived forecasts: wrote {config.FORECASTS_STORMS} with no rows")
    else:
        print(f"\nwrote {config.FORECASTS_STORMS} ({len(out)} rows)")
    print("\nFor the Request Tracker:")
    print(tracker_line(status))
    if failed:
        raise SystemExit(f"\ndownload failed for {', '.join(failed)}; run again to retry (saved replies are reused)")


if __name__ == "__main__":
    main()

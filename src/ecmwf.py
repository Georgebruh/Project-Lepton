"""Archived ECMWF rain forecasts for the three storms (task A15).

C9 runs Layer 2 on rain forecasts made 1, 2 and 3 days before each storm instead of
the rain that fell. This script gets those forecasts from Open-Meteo's Previous Runs
API (https://open-meteo.com/en/docs/previous-runs-api), model ECMWF IFS 0.25 degree
(config.FORECAST_MODEL), and checks which storms the archive covers (gate A).

What "previous day N" means: for every hour, Open-Meteo keeps the value from a model
run started at least 24 x N hours before that hour. It drops each run's first 24 x N
hours and joins the runs into one series. So precipitation_previous_day1 is the
forecast made about 1 day ahead, _day2 about 2 days ahead, _day3 about 3 days ahead.
Open-Meteo began storing ECMWF IFS 0.25 runs in February 2024 (first hour: 3 Feb 2024
for day 1).

Where: every 0.25 degree grid cell that overlaps the A7 catchments, with its share of
the catchment area as its weight (catchments.grid_cells). A14 uses the same cells for
ERA5, so C9 compares each forecast with ERA5's own return levels over the same area.

When: each storm's wettest UTC days, from config.STORMS (Carina first; A11 adds the
2025 and 2026 dates). A storm without dates is skipped and listed as such.

Hours to UTC days: Open-Meteo labels each hourly total with the end of its hour (the
01:00 value is rain from 00:00 to 01:00 UTC). utc_day_totals moves every label back
1 hour, then adds up each day's 24 hours, so a day is 00:00-24:00 UTC, the same day as
IMERG (8 AM-8 AM Philippine time). This is why each request runs to the day after the
storm's last day: that day's 00:00 value is the last hour of the storm's last day.

Each storm's reply is saved unchanged in data/raw/ecmwf_previous_runs/, one JSON file
per storm named with its dates. A file already there is not fetched again (delete it
to refresh).

Output: data/clean/forecasts_storms.csv, one row per storm, lead time, UTC day and cell:
    storm, lead_days, date, lat, lon, weight, rain_mm
A storm and lead time are written only if the archive has every hour of every day at
every cell. The catchment rain for one storm, lead time and day is sum(weight x rain_mm).

Run from the repository root (needs A7's catchments_qc.gpkg):
    python -m src.ecmwf
"""

import json
from datetime import date, timedelta

import geopandas as gpd
import pandas as pd
import requests

import config
from src import catchments

PREVIOUS_RUNS_API = "https://previous-runs-api.open-meteo.com/v1/forecast"
TIMEOUT_S = 120
SAME_POINT_DEG = 0.001  # a reply's grid point must be the requested one to within this


def lead_variable(lead_days):
    """Open-Meteo's name for the forecast made lead_days days ahead, e.g. precipitation_previous_day1."""
    return f"precipitation_previous_day{lead_days}"


def raw_path(storm, first, last):
    """Where one storm's reply is saved, e.g. data/raw/ecmwf_previous_runs/carina_2024_20240723_20240725.json."""
    return config.ECMWF_RAW / f"{storm}_{first:%Y%m%d}_{last:%Y%m%d}.json"


def request_params(cells, first, last):
    """The Previous Runs request for one storm: every cell, every lead time, in UTC.

    end_date is the day after the storm's last day, for that day's 00:00 value (see the
    top of this file). cell_selection=nearest returns the grid point itself; Open-Meteo's
    default may move to a neighbouring land cell with a similar elevation.
    """
    return {
        "latitude": ",".join(str(v) for v in cells["lat"]),
        "longitude": ",".join(str(v) for v in cells["lon"]),
        "hourly": ",".join(lead_variable(n) for n in config.FORECAST_LEADS_DAYS),
        "models": config.FORECAST_MODEL,
        "start_date": f"{first:%Y-%m-%d}",
        "end_date": f"{last + timedelta(days=1):%Y-%m-%d}",
        "timezone": "GMT",
        "cell_selection": "nearest",
    }


def download(storm, cells, first, last):
    """One storm's reply from Open-Meteo, as a list with one entry per cell.

    The reply is saved unchanged before it is read, and a saved reply is reused.
    """
    path = raw_path(storm, first, last)
    if path.exists():
        print(f"{storm}: reading {path.name} (already on disk)")
    else:
        print(f"{storm}: requesting {first} to {last} from Open-Meteo Previous Runs")
        r = requests.get(PREVIOUS_RUNS_API, params=request_params(cells, first, last), timeout=TIMEOUT_S)
        if r.status_code != 200:
            raise SystemExit(f"Open-Meteo answered HTTP {r.status_code}: {r.text[:300]}")
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part")
        part.write_text(r.text, encoding="utf-8")
        part.replace(path)

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
        for n in config.FORECAST_LEADS_DAYS:
            unit = reply["hourly_units"][lead_variable(n)]
            if unit != "mm":
                raise ValueError(f"{path.name}: {lead_variable(n)} is in {unit}, expected mm")


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
    """One storm's daily forecasts: storm, lead_days, date, lat, lon, weight, rain_mm.

    Days outside first..last are dropped (the request's extra day and the hour before
    the first day). rain_mm is NaN where the archive misses an hour.
    """
    days = pd.date_range(first, last, freq="D")
    rows = []
    for reply, cell in zip(replies, cells.itertuples()):
        hourly = pd.DataFrame(reply["hourly"]).set_index("time")
        hourly.index = pd.to_datetime(hourly.index)
        daily = utc_day_totals(hourly.astype(float)).reindex(days)
        for n in config.FORECAST_LEADS_DAYS:
            for day, rain in daily[lead_variable(n)].items():
                rows.append({"storm": storm, "lead_days": n, "date": f"{day:%Y-%m-%d}",
                             "lat": cell.lat, "lon": cell.lon, "weight": round(cell.weight, 6),
                             "rain_mm": round(rain, 2)})  # hourly values have 2 decimals; drops float noise
    return pd.DataFrame(rows)


def coverage(table):
    """For each lead time: True if every day at every cell has a forecast."""
    return table.groupby("lead_days")["rain_mm"].apply(lambda r: bool(r.notna().all()))


def catchment_rain(table):
    """Catchment rain per lead time and day: sum of weight x rain_mm over the cells (mm)."""
    weighted = table.assign(mm=table["weight"] * table["rain_mm"])
    return weighted.pivot_table(index="date", columns="lead_days", values="mm", aggfunc="sum").round(1)


def tracker_line(status):
    """The one line for the Request Tracker: which storms the archive covers."""
    leads = ", ".join(str(n) for n in config.FORECAST_LEADS_DAYS)
    storms = "; ".join(f"{storm} {text}" for storm, text in status.items())
    return f"A15 ({date.today():%Y-%m-%d}): Open-Meteo Previous Runs, ECMWF IFS 0.25, leads {leads} days: {storms}"


def main():
    shape = gpd.read_file(config.CATCHMENTS, layer="catchments")
    cells = catchments.grid_cells(shape, config.GRID_025_DEG)
    print(f"{len(cells)} cells of {config.GRID_025_DEG} degrees overlap the catchments:")
    print(cells.round({"km2": 1, "weight": 3}).to_string(index=False))
    print()

    tables, status = [], {}
    for storm, facts in config.STORMS.items():  # Carina first
        if facts["wettest_days"] is None:
            status[storm] = "not checked: no dates yet (A11)"
            print(f"{storm}: skipped, no wettest days in config.STORMS yet (A11)")
            continue
        first, last = facts["wettest_days"]
        replies = download(storm, cells, first, last)
        check_reply(replies, cells, raw_path(storm, first, last))
        table = storm_table(storm, replies, cells, first, last)

        covered = coverage(table)
        leads_in = [n for n in covered.index if covered[n]]
        if len(leads_in) == len(covered):
            status[storm] = f"covered ({first} to {last})"
        elif leads_in:
            status[storm] = f"partly covered ({first} to {last}): leads {leads_in} only"
        else:
            status[storm] = f"not covered ({first} to {last})"
        print(f"  {status[storm]}")

        table = table[table["lead_days"].isin(leads_in)]
        if leads_in:
            print("  catchment rain, mm per UTC day (columns: lead in days):")
            print("  " + catchment_rain(table).to_string().replace("\n", "\n  "))
        tables.append(table)

    out = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    if out.empty:
        raise SystemExit("no storm has archived forecasts; forecasts_storms.csv not written")
    part = config.FORECASTS_STORMS.with_suffix(".part")
    out.to_csv(part, index=False)
    part.replace(config.FORECASTS_STORMS)
    print(f"\nwrote {config.FORECASTS_STORMS} ({len(out)} rows)")
    print("\nFor the Request Tracker:")
    print(tracker_line(status))


if __name__ == "__main__":
    main()

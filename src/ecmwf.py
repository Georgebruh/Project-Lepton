"""Archived ECMWF rain forecasts for the storms."""

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
    """Open-Meteo answered HTTP 400 (dates outside its archive, or a bad parameter)."""


def previous_day_variable(n):
    """Open-Meteo's name for the forecast made n days ahead of each hour, e.g. precipitation_previous_day1."""
    return f"precipitation_previous_day{n}"


def fetch_span(first, last):
    """The UTC days fetched for a storm whose wettest days are first..last."""
    return first - timedelta(days=config.RAIN_ACCUM_DAYS - 1), last


def leads_covered(covered):
    """The lead times the forecast run can use: lead L needs previous days L to L + n - 1."""
    days = range(config.RAIN_ACCUM_DAYS)
    return [lead for lead in config.FORECAST_LEADS_DAYS
            if all(covered.get(lead + i, False) for i in days)]


def raw_path(storm, first, last):
    """Where one storm's reply is saved, under data/raw/ecmwf_previous_runs/."""
    return config.ECMWF_RAW / f"{storm}_{config.FORECAST_MODEL}_{first:%Y%m%d}_{last:%Y%m%d}.json"


def request_params(cells, first, last):
    """The Previous Runs request for one storm: every cell, every previous day, in UTC."""
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
    """Request one storm from Open-Meteo and save the reply at path, byte for byte as received."""
    r = requests.get(PREVIOUS_RUNS_API, params=request_params(cells, first, last), timeout=TIMEOUT_S)
    if r.status_code == 400:
        raise RequestRefused(r.text[:300])  # Open-Meteo's reply names the reason
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    part.write_bytes(r.content)
    part.replace(path)


def download(storm, cells, first, last):
    """One storm's reply from Open-Meteo, as a list with one entry per cell."""
    path = raw_path(storm, first, last)
    if path.exists():
        print(f"{storm}: reading {path.name} (already on disk)")
    else:
        print(f"{storm}: requesting {first} to {last} from Open-Meteo Previous Runs")
        for attempt in range(1, RETRIES + 1):
            try:
                fetch(cells, first, last, path)
                break
            except requests.RequestException:
                if attempt == RETRIES:
                    raise
                time.sleep(RETRY_WAIT_S * attempt)

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
    """Add hourly rain up into UTC days."""
    shifted = hourly.copy()
    shifted.index = shifted.index + pd.Timedelta(hours=config.OPEN_METEO_HOUR_SHIFT)
    return shifted.groupby(shifted.index.floor("D")).sum(min_count=24)


def storm_table(storm, replies, cells, first, last):
    """One storm's daily forecasts: storm, previous_day, date, lat, lon, weight, rain_mm."""
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

    # Always rewritten, header only if nothing is covered, so no old table is read.
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

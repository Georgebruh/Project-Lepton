"""ERA5 hourly rain over the catchments, added up into UTC days."""

import json
import time
from datetime import date, timedelta

import geopandas as gpd
import pandas as pd
import requests

import config
from src import catchments, flood_exposure
from src.ecmwf import SAME_POINT_DEG, utc_day_totals

HISTORICAL_API = "https://archive-api.open-meteo.com/v1/archive"
VARIABLE = "precipitation"
TIMEOUT_S = 180
RETRIES = 3
RETRY_WAIT_S = 10
RATE_LIMIT_WAIT_S = 65   # after HTTP 429 (too many requests this minute), wait past the minute
PAUSE_S = 5              # between yearly requests, to stay under the per-minute limit
COLUMNS = ["date", "lat", "lon", "weight", "rain_mm"]


class RequestRefused(Exception):
    """Open-Meteo answered HTTP 400 (a bad date or parameter)."""


def year_span(year):
    """First and last UTC day fetched for one year: 1 Jan to 31 Dec, but never before config.ERA5_START."""
    return max(date(year, 1, 1), config.ERA5_START), date(year, 12, 31)


def raw_path(year):
    """Where one year's reply is saved, e.g. data/raw/era5_open_meteo/era5_2024.json."""
    return config.ERA5_RAW / f"{config.ERA5_MODEL}_{year}.json"


def request_params(cells, first, last):
    """The Historical Weather request for one year: every cell, hourly rain, in UTC."""
    return {
        "latitude": ",".join(str(v) for v in cells["lat"]),
        "longitude": ",".join(str(v) for v in cells["lon"]),
        "hourly": VARIABLE,
        "models": config.ERA5_MODEL,
        "start_date": f"{first:%Y-%m-%d}",
        "end_date": f"{last + timedelta(days=1):%Y-%m-%d}",
        "timezone": "GMT",
        "cell_selection": "nearest",
    }


def fetch(cells, first, last, path):
    """Request one year from Open-Meteo and save the reply at path, byte for byte as received."""
    r = requests.get(HISTORICAL_API, params=request_params(cells, first, last), timeout=TIMEOUT_S)
    if r.status_code == 400:
        raise RequestRefused(r.text[:300])  # Open-Meteo's reply names the reason
    if r.status_code == 429:
        print(f"  Open-Meteo asks to slow down; waiting {RATE_LIMIT_WAIT_S} s")
        time.sleep(RATE_LIMIT_WAIT_S)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    part.write_bytes(r.content)
    part.replace(path)


def download(year, cells):
    """One year's reply from Open-Meteo, as a list with one entry per cell."""
    path = raw_path(year)
    first, last = year_span(year)
    if path.exists():
        print(f"{year}: reading {path.name} (already on disk)")
    else:
        print(f"{year}: requesting {first} to {last} from Open-Meteo Historical Weather")
        for attempt in range(1, RETRIES + 1):
            try:
                fetch(cells, first, last, path)
                break
            except requests.RequestException:
                if attempt == RETRIES:
                    raise
                time.sleep(RETRY_WAIT_S * attempt)
        time.sleep(PAUSE_S)

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
        unit = reply["hourly_units"].get(VARIABLE, "missing")
        if unit != "mm":
            raise ValueError(f"{path.name}: unit of {VARIABLE} is {unit}, expected mm (delete it to refresh)")


def year_table(year, replies, cells):
    """One year's daily rain: date, lat, lon, weight, rain_mm."""
    first, last = year_span(year)
    days = pd.date_range(first, last, freq="D")
    rows = []
    for reply, cell in zip(replies, cells.itertuples()):
        hourly = pd.DataFrame(reply["hourly"]).set_index("time")
        hourly.index = pd.to_datetime(hourly.index)
        daily = utc_day_totals(hourly.astype(float)).reindex(days)
        for day, rain in daily[VARIABLE].items():
            rows.append({"date": f"{day:%Y-%m-%d}", "lat": cell.lat, "lon": cell.lon,
                         "weight": round(cell.weight, 6),
                         "rain_mm": round(rain, 2)})  # hourly values have 2 decimals; drops float noise
    return pd.DataFrame(rows, columns=COLUMNS)


def catchment_rain(table):
    """Catchment rain per UTC day: sum of weight x rain_mm over the cells (mm)."""
    weighted = table.assign(mm=table["weight"] * table["rain_mm"])
    return weighted.groupby("date")["mm"].sum()


def check_table(table, n_cells):
    """Stop unless every day from ERA5_START to the last year has every cell, with no gap and no negative rain."""
    first = config.ERA5_START
    last = date(config.ERA5_YEARS[1], 12, 31)
    expected_days = (last - first).days + 1
    if table["rain_mm"].isna().any():
        bad = sorted(table.loc[table["rain_mm"].isna(), "date"].unique())
        raise ValueError(f"{len(bad)} days miss an hour, first {bad[0]}: delete that year's reply and rerun")
    if (table["rain_mm"] < 0).any():
        raise ValueError("negative rain in the ERA5 replies")
    if len(table) != expected_days * n_cells or table.duplicated(["date", "lat", "lon"]).any():
        raise ValueError(f"{len(table)} rows, expected {expected_days} days x {n_cells} cells, no duplicates")


def main():
    shape = gpd.read_file(config.CATCHMENTS, layer="catchments")
    cells = catchments.grid_cells(shape, config.GRID_025_DEG)
    print(f"{len(cells)} cells of {config.GRID_025_DEG} degrees overlap the catchments:")
    print(cells.round({"km2": 1, "weight": 3}).to_string(index=False))
    print()

    tables = []
    for year in range(config.ERA5_START.year, config.ERA5_YEARS[1] + 1):
        replies = download(year, cells)
        check_reply(replies, cells, raw_path(year))
        tables.append(year_table(year, replies, cells))

    out = pd.concat(tables, ignore_index=True)
    check_table(out, len(cells))
    part = config.ERA5_DAILY.with_suffix(".part")
    out.to_csv(part, index=False)
    part.replace(config.ERA5_DAILY)
    print(f"\nwrote {config.ERA5_DAILY} ({len(out)} rows)")

    # A quick look: each year's wettest catchment n-day total.
    days = config.RAIN_ACCUM_DAYS
    rain = catchment_rain(out)
    rain.index = pd.to_datetime(rain.index)
    totals = flood_exposure.n_day_totals(rain, days)
    wettest = totals.groupby(totals.index.year).agg(["idxmax", "max"])
    wettest.columns = ["last UTC day", "catchment mm"]
    wettest["last UTC day"] = wettest["last UTC day"].dt.strftime("%Y-%m-%d")
    print(f"\nEach year's wettest {days}-day total over the catchments (ERA5), by its last UTC day:")
    print(wettest.round(1).to_string())


if __name__ == "__main__":
    main()

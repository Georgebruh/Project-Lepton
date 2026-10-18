"""Weekly rain and exposure features for Quezon City (task B4).

Formulas (task B4):
    R_d = sum_g(w_g * R_{g,d}) / sum_g(w_g)
    R(t) = sum_{d in t} R_d
    Rcum2(t) = R(t - 1) + R(t)
    EI2(t) = max(EI(t - 1), EI(t))

In plain words:
1. Each 0.1 x 0.1 degree IMERG cell is clipped to Quezon City in EPSG:32651
   and weighted by the WorldPop 2024 residents inside that QC part (from
   exactextract in EPSG:4326), so rain where people live counts more.
2. Each UTC day's rain over QC (R_d) is the population-weighted average across
   IMERG cells. Dimensions are matched by name ("lon", "lat", "time"), never by
   position (rule 8).
3. Weekly rain R(t) sums the 7 UTC days of morbidity week t. Incomplete weeks
   (< 7 UTC days) get NaN so missing inputs are never treated as 0 mm (rule 5).
4. Rcum2(t) adds the last two weeks of rain, R(t - 1) + R(t). Week -1 (the 7 UTC
   days before 2015 week 1) is summed from IMERG so 2015 week 1 has Rcum2(0).
5. EI(t) comes from task C3 (ei_weekly.csv), and EI2(t) = max(EI(t - 1), EI(t))
   is computed within each fit_year so return-level fits never leak across years
   (rule 2). For a 1-week forecast of target week T + 1, M4 reads Rcum2(T) and
   EI2(T).

Outputs:
    data/clean/imerg_weights_qc.csv  (config.IMERG_WEIGHTS_QC)
    data/clean/rain_weekly.csv       (config.RAIN_WEEKLY)
    data/clean/features_weekly.csv   (config.FEATURES_WEEKLY)

Run from the repository root:  python -m src.features
Needs A3, A4, A5, A6 and C3 first.
"""

import math

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box

import config
from src import rescale, weeks

SHOW_CELLS = 5
SHOW_DAYS = 5


def cell_weights(ds, barangays):
    """WorldPop counts and normalized weights inside QC for each IMERG grid cell (task B4).

    Builds the 0.1-degree box around each (lon, lat) centre in ds, clips it to QC
    in EPSG:32651, and extracts WorldPop counts in EPSG:4326 via rescale.worldpop_in.
    """
    if "lon" not in ds.coords or "lat" not in ds.coords:
        raise ValueError(f"expected 'lon' and 'lat' coordinates, got {list(ds.coords)}")

    lons = ds["lon"].to_numpy()
    lats = ds["lat"].to_numpy()
    half = config.IMERG_CELL_DEG / 2.0

    rows = [
        {
            "lon": float(lon),
            "lat": float(lat),
            "geometry": box(float(lon) - half, float(lat) - half, float(lon) + half, float(lat) + half),
        }
        for lon in lons
        for lat in lats
    ]
    cells = gpd.GeoDataFrame(rows, crs=config.CRS_LONLAT)

    # Reproject to EPSG:32651 for geometric overlay, then back to EPSG:4326 in worldpop_in
    cells = cells.set_geometry(
        cells.segmentize(config.IMERG_CELL_DEG / config.GRID_EDGE_POINTS)
    ).to_crs(config.CRS_OVERLAY)
    qc = barangays.to_crs(config.CRS_OVERLAY).union_all()
    clipped = cells.intersection(qc)

    area_km2 = clipped.area / 1e6
    qc_km2 = qc.area / 1e6
    if not math.isclose(area_km2.sum(), qc_km2, rel_tol=config.GRID_AREA_TOLERANCE):
        raise ValueError(
            f"IMERG cells cover {area_km2.sum():.2f} km2 of QC, expected {qc_km2:.2f} km2"
        )

    found = rescale.worldpop_in(cells.set_geometry(clipped))
    people = found["people"].to_numpy(dtype=float)
    pixels = found["pixels"].to_numpy(dtype=float)

    if np.isnan(people).any() or (people < 0).any():
        raise ValueError("missing or negative WorldPop counts in IMERG cells")
    total_people = people.sum()
    if total_people <= 0:
        raise ValueError("total WorldPop population inside QC across IMERG cells is zero")

    return pd.DataFrame({
        "lon": cells["lon"].to_numpy(),
        "lat": cells["lat"].to_numpy(),
        "area_km2": area_km2.to_numpy(),
        "worldpop_qc": people,
        "worldpop_pixels": pixels,
        "weight": people / total_people,
    })


def daily_qc_rain(ds, weights_table):
    """Population-weighted daily rain R_d over QC for every UTC day in ds (task B4).

    Formula: R_d = sum_g(w_g * R_{g,d}) / sum_g(w_g).
    Selects and reduces strictly by dimension name ("lon", "lat", "time"), never
    by position (rule 8).
    """
    rain_var = config.IMERG_VARIABLES[0]
    rain = ds[rain_var]
    if set(rain.dims) != {"time", "lon", "lat"}:
        raise ValueError(f"expected dimensions {{'time', 'lon', 'lat'}}, got {rain.dims}")

    if bool(rain.isnull().any()):
        raise ValueError("IMERG precipitation contains missing (NaN) values")
    if bool((rain < 0).any()):
        raise ValueError("IMERG precipitation contains negative values")

    w_sum = weights_table["weight"].sum()
    if not np.isfinite(w_sum) or w_sum <= 0:
        raise ValueError(f"invalid sum of cell weights: {w_sum}")

    lon_keys = np.round(ds["lon"].to_numpy(), 4)
    lat_keys = np.round(ds["lat"].to_numpy(), 4)
    pivoted = (
        weights_table.assign(
            lon_key=np.round(weights_table["lon"], 4),
            lat_key=np.round(weights_table["lat"], 4),
            norm_weight=weights_table["weight"] / w_sum,
        )
        .pivot(index="lon_key", columns="lat_key", values="norm_weight")
        .reindex(index=lon_keys, columns=lat_keys)
    )
    if pivoted.isna().any().any():
        raise ValueError("weights_table does not cover every (lon, lat) cell in ds")

    weights_da = xr.DataArray(
        pivoted.to_numpy(),
        coords={"lon": ds["lon"], "lat": ds["lat"]},
        dims=("lon", "lat"),
    )

    # xarray aligns dimensions by name regardless of axis order
    weighted_daily = (rain * weights_da).sum(dim=["lon", "lat"], skipna=False)
    dates = pd.to_datetime(weighted_daily["time"].to_numpy()).date
    values = weighted_daily.to_numpy(dtype=float)

    table = pd.DataFrame({"date": dates, "rain_mm": values})
    if table["date"].duplicated().any():
        raise ValueError("duplicate UTC dates in IMERG daily dataset")
    return table.sort_values("date").reset_index(drop=True)


def weekly_rain(daily, calendar=None):
    """Weekly rain R(t) and 2-week cumulative rain Rcum2(t) by morbidity week (task B4).

    Formula: R(t) = sum_{d in t} R_d, Rcum2(t) = R(t - 1) + R(t).
    Only complete weeks with all 7 UTC days receive a numeric R(t); incomplete
    weeks get NaN (rule 5). Week -1 is summed when present in daily so week 0
    (2015 week 1) has a complete Rcum2(0).
    """
    if calendar is None:
        calendar = (
            pd.read_csv(config.CALENDAR)
            if config.CALENDAR.exists()
            else weeks.build_calendar()
        )

    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"]).dt.date
    if daily["date"].duplicated().any():
        raise ValueError("daily rain table has duplicate dates")
    if daily["rain_mm"].isna().any() or (daily["rain_mm"] < 0).any():
        raise ValueError("daily rain table has missing or negative values")

    cal = calendar.copy()
    cal["date"] = pd.to_datetime(cal["date"]).dt.date
    cal["week_start"] = pd.to_datetime(cal["week_start"]).dt.date
    wk_table = (
        cal[["week_index", "year", "week", "week_start", "week_of_year"]]
        .drop_duplicates("week_index")
        .sort_values("week_index")
        .reset_index(drop=True)
    )

    min_wk = int(wk_table["week_index"].min()) - 1
    max_wk = int(wk_table["week_index"].max())

    daily["week_index"] = [weeks.week_index(d) for d in daily["date"]]
    in_range = daily[(daily["week_index"] >= min_wk) & (daily["week_index"] <= max_wk)]

    grouped = in_range.groupby("week_index")["rain_mm"].agg(rain_days="count", rain_sum="sum")
    if (grouped["rain_days"] > config.DAYS_PER_WEEK).any():
        raise ValueError(f"a week has more than {config.DAYS_PER_WEEK} UTC days")

    # Verify there are no internal gaps between the first and last complete weeks
    complete_wks = grouped.index[grouped["rain_days"] == config.DAYS_PER_WEEK]
    if len(complete_wks) >= 2:
        first_c, last_c = int(complete_wks.min()), int(complete_wks.max())
        expected_span = set(range(first_c, last_c + 1))
        missing_internal = sorted(expected_span - set(complete_wks))
        if missing_internal:
            raise ValueError(
                f"incomplete IMERG weeks inside the record at week_index {missing_internal[:10]}"
            )

    grouped["rain_mm"] = np.where(
        grouped["rain_days"] == config.DAYS_PER_WEEK, grouped["rain_sum"], np.nan
    )
    rain_by_wk = grouped["rain_mm"]
    days_by_wk = grouped["rain_days"]

    wk_table["rain_days"] = (
        days_by_wk.reindex(wk_table["week_index"]).fillna(0).astype(int).to_numpy()
    )
    wk_table["rain_mm"] = rain_by_wk.reindex(wk_table["week_index"]).to_numpy(dtype=float)
    prev_rain = rain_by_wk.reindex(wk_table["week_index"] - 1).to_numpy(dtype=float)
    wk_table["rcum2_mm"] = prev_rain + wk_table["rain_mm"].to_numpy(dtype=float)
    wk_table["rcum2_scaled"] = wk_table["rcum2_mm"] / config.RAIN_SCALE_MM
    return wk_table


def add_ei2(ei_table):
    """Add EI2(t) = max(EI(t - 1), EI(t)) within each fit_year (task B4).

    Matches t - 1 by exact week_index within the same fit_year so return-level
    fits never cross forecast years (rule 2). Missing values propagate as NaN
    (rule 5).
    """
    if not {"week_index", "ei"}.issubset(ei_table.columns):
        raise ValueError(f"ei_table must contain 'week_index' and 'ei', got {list(ei_table.columns)}")

    table = ei_table.copy()
    if "fit_year" in table.columns:
        if table.duplicated(subset=["fit_year", "week_index"]).any():
            raise ValueError("duplicate (fit_year, week_index) rows in ei_table")
        table = table.sort_values(["fit_year", "week_index"]).reset_index(drop=True)
        indexed = table.set_index(["fit_year", "week_index"])["ei"]
        prev_keys = pd.MultiIndex.from_arrays([table["fit_year"], table["week_index"] - 1])
        ei_prev = indexed.reindex(prev_keys).to_numpy(dtype=float)
    else:
        if table.duplicated(subset=["week_index"]).any():
            raise ValueError("duplicate week_index rows in ei_table")
        table = table.sort_values("week_index").reset_index(drop=True)
        indexed = table.set_index("week_index")["ei"]
        ei_prev = indexed.reindex(table["week_index"] - 1).to_numpy(dtype=float)

    table["ei2"] = np.maximum(ei_prev, table["ei"].to_numpy(dtype=float))
    return table


def combine_features(rain_table, ei_table):
    """Merge weekly rain features (R, Rcum2) with exposure features (EI, EI2) (task B4)."""
    with_ei2 = add_ei2(ei_table)

    if "rain_days" in with_ei2.columns:
        check = with_ei2[["week_index", "rain_days"]].drop_duplicates().merge(
            rain_table[["week_index", "rain_days"]], on="week_index", suffixes=("_ei", "_rain")
        )
        mismatch = check[check["rain_days_ei"] != check["rain_days_rain"]]
        if len(mismatch):
            raise ValueError(f"rain_days mismatch between B4 and C3:\n{mismatch.head()}")

    extra_cols = [
        c for c in ("fit_year", "week_index", "rmax_mm", "weekrmax_mm", "ei", "ei2")
        if c in with_ei2.columns
    ]
    merged = with_ei2[extra_cols].merge(
        rain_table, on="week_index", how="left", validate="many_to_one"
    )

    ordered_cols = [
        c for c in (
            "fit_year",
            "week_index",
            "year",
            "week",
            "week_start",
            "week_of_year",
            "rain_days",
            "rain_mm",
            "rcum2_mm",
            "rcum2_scaled",
            "rmax_mm",
            "weekrmax_mm",
            "ei",
            "ei2",
        )
        if c in merged.columns
    ]
    sort_cols = ["fit_year", "week_index"] if "fit_year" in merged.columns else ["week_index"]
    return merged[ordered_cols].sort_values(sort_cols).reset_index(drop=True)


def lagged_for_targets(features_table, fit_year=None, horizon=1):
    """M4 rain and exposure inputs aligned to each target week T + horizon (task B4, B5).

    For the 1-week forecast of target week s = T + 1 (horizon=1), M4 reads
    Rcum2(T) and EI2(T) from week T = s - 1. For B11's 2-week forecast of
    target week s = T + 2 (horizon=2), M4 reads Rcum2(T) and EI2(T) from s - 2.
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")

    sub = features_table.copy()
    if "fit_year" in sub.columns:
        if fit_year is None:
            raise ValueError("fit_year is required when features_table has a 'fit_year' column")
        sub = sub[sub["fit_year"] == fit_year].copy()
        if sub.empty:
            raise ValueError(f"no rows found for fit_year={fit_year}")

    indexed = sub.set_index("week_index")
    source_wk = sub["week_index"] - horizon
    out = sub[["week_index", "year", "week", "week_start", "week_of_year"]].copy()
    if "fit_year" in sub.columns:
        out.insert(0, "fit_year", fit_year)
    out["source_week_index"] = source_wk.to_numpy()
    out["rain_mm"] = indexed["rain_mm"].reindex(source_wk).to_numpy(dtype=float)
    out["rcum2_mm"] = indexed["rcum2_mm"].reindex(source_wk).to_numpy(dtype=float)
    out["rcum2_scaled"] = out["rcum2_mm"] / config.RAIN_SCALE_MM
    if "ei" in indexed.columns:
        out["ei"] = indexed["ei"].reindex(source_wk).to_numpy(dtype=float)
    if "ei2" in indexed.columns:
        out["ei2"] = indexed["ei2"].reindex(source_wk).to_numpy(dtype=float)
    return out.reset_index(drop=True)


def report(weights_table, daily_table, rain_table, features_table=None):
    """Print diagnostic summaries of cell weights, daily rain, weekly rain, and EI2."""
    in_qc = weights_table[weights_table["weight"] > 0]
    print(
        f"IMERG grid: {len(in_qc)} of {len(weights_table)} cells overlap QC; "
        f"total WorldPop in QC = {weights_table['worldpop_qc'].sum():,.0f} "
        f"across {weights_table['area_km2'].sum():.2f} km2"
    )
    top_cells = in_qc.sort_values("weight", ascending=False).head(SHOW_CELLS)
    print(f"\ntop {SHOW_CELLS} IMERG cells by QC population weight:")
    print(
        top_cells[["lon", "lat", "area_km2", "worldpop_qc", "weight"]]
        .round({"area_km2": 2, "worldpop_qc": 0, "weight": 4})
        .to_string(index=False)
    )

    print(f"\ndaily QC rain ({len(daily_table)} UTC days, {daily_table['date'].iloc[0]} to {daily_table['date'].iloc[-1]}):")
    wettest_days = daily_table.sort_values("rain_mm", ascending=False).head(SHOW_DAYS)
    print(wettest_days.round({"rain_mm": 2}).to_string(index=False))

    complete = rain_table[rain_table["rain_days"] == config.DAYS_PER_WEEK]
    print(
        f"\nweekly QC rain: {len(complete)} complete 7-day weeks of {len(rain_table)} calendar weeks; "
        f"max R(t) = {complete['rain_mm'].max():.1f} mm, "
        f"max Rcum2(t) = {complete['rcum2_mm'].max():.1f} mm"
    )

    if features_table is not None:
        valid = features_table.dropna(subset=["rcum2_mm", "ei2"])
        corr = valid["rcum2_mm"].corr(valid["ei2"])
        flag = "ABOVE" if abs(corr) > config.RAIN_EI_MAX_CORR else "below"
        print(
            f"\ncombined features ({len(features_table)} rows): "
            f"corr(Rcum2, EI2) = {corr:.3f} ({flag} {config.RAIN_EI_MAX_CORR} threshold for B5)"
        )


def main():
    barangays = gpd.read_file(
        config.BARANGAYS_QC, layer="barangays", columns=["psgc", "adm4_name", "pop_2024"]
    )
    if len(barangays) != config.QC_BARANGAYS:
        raise ValueError(
            f"{config.BARANGAYS_QC.name} has {len(barangays)} barangays, expected {config.QC_BARANGAYS}"
        )

    with xr.open_dataset(config.IMERG_DAILY) as ds:
        weights_table = cell_weights(ds, barangays)
        daily_table = daily_qc_rain(ds, weights_table)

    rain_table = weekly_rain(daily_table)

    config.IMERG_WEIGHTS_QC.parent.mkdir(parents=True, exist_ok=True)
    weights_table.to_csv(config.IMERG_WEIGHTS_QC, index=False)
    rain_table.to_csv(config.RAIN_WEEKLY, index=False)

    features_table = None
    if config.EI_WEEKLY.exists():
        ei_table = pd.read_csv(config.EI_WEEKLY)
        features_table = combine_features(rain_table, ei_table)
        features_table.to_csv(config.FEATURES_WEEKLY, index=False)

    report(weights_table, daily_table, rain_table, features_table)
    print(f"\nwrote {config.IMERG_WEIGHTS_QC} and {config.RAIN_WEEKLY}")
    if features_table is not None:
        print(f"wrote {config.FEATURES_WEEKLY} ({len(features_table)} rows)")
    else:
        print(f"note: {config.EI_WEEKLY} not found yet; run C3 then rerun python -m src.features")


if __name__ == "__main__":
    main()
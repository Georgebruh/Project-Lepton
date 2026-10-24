"""Rain return levels, graded exposure and the weekly exposure index."""

import argparse
import math

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats
from shapely.geometry import box

import config
from src import weeks

RETURN_PERIODS = config.NOAH_RETURN_PERIODS  # (5, 25, 100): one anchor per NOAH map
COLUMNS = ["fit_year", "rain_days", "week_index", "year", "week", "rmax_mm", "ei"]


def gumbel_level(mu, beta, period):
    """R(T) = mu - beta * ln(-ln(1 - 1/T)): the rain exceeded on average once every T years."""
    return mu - beta * math.log(-math.log(1 - 1 / period))


def imerg_cell_weights(lon, lat, catchments):
    """Each IMERG cell's share of the catchment area, for cells whose centres are lon x lat."""
    half = config.IMERG_CELL_DEG / 2
    cells = gpd.GeoDataFrame(
        {"lon": [x for x in lon for _ in lat], "lat": [y for _ in lon for y in lat]},
        geometry=[box(x - half, y - half, x + half, y + half) for x in lon for y in lat],
        crs=config.CRS_LONLAT,
    )
    # Extra points along each edge keep it on its latitude or longitude line after reprojecting.
    cells = cells.set_geometry(cells.segmentize(config.IMERG_CELL_DEG / config.GRID_EDGE_POINTS))
    cells = cells.to_crs(config.CRS_OVERLAY)
    shape = catchments.to_crs(config.CRS_OVERLAY).union_all()
    cells["km2"] = cells.intersection(shape).area / 1e6
    cells = cells[cells["km2"] > 0]

    total_km2 = shape.area / 1e6
    if not math.isclose(cells["km2"].sum(), total_km2, rel_tol=config.GRID_AREA_TOLERANCE):
        raise ValueError(f"the IMERG cells hold {cells['km2'].sum():.1f} km2 of the {total_km2:.1f} km2 catchments")
    cells["weight"] = cells["km2"] / cells["km2"].sum()
    return pd.DataFrame(cells.drop(columns="geometry")).reset_index(drop=True)


def catchment_rain():
    """R24 for every UTC day in imerg_daily.nc: area-weighted mean over the catchments (mm)."""
    catchments = gpd.read_file(config.CATCHMENTS, layer="catchments")
    with xr.open_dataset(config.IMERG_DAILY) as ds:
        rain = ds["precipitation"].load()
    cells = imerg_cell_weights(rain["lon"].values, rain["lat"].values, catchments)

    weights = xr.DataArray(
        cells["weight"].values, dims="cell",
        coords={"lon": ("cell", cells["lon"].values), "lat": ("cell", cells["lat"].values)},
    )
    picked = rain.sel(lon=weights["lon"], lat=weights["lat"])  # one column per catchment cell
    r24 = (picked * weights).sum(dim="cell").to_series()
    r24.index = pd.DatetimeIndex(r24.index).normalize()
    if r24.isna().any():
        raise ValueError(f"R24 is missing on {int(r24.isna().sum())} days: run check S2")
    return r24.rename("r24_mm")


def n_day_totals(daily, days=config.RAIN_ACCUM_DAYS):
    """Rain of the `days` UTC days ending on each day: Rn_d = R24_d + ... + R24_{d-days+1} (mm)."""
    index = pd.DatetimeIndex(daily.index)
    gaps = pd.date_range(index.min(), index.max(), freq="D").difference(index)
    if len(gaps) or not index.is_monotonic_increasing:
        raise ValueError(f"daily rain must have every day in order; {len(gaps)} days missing")
    return daily.rolling(days).sum().dropna()


def annual_maxima(totals, keep_2000=config.IMERG_KEEP_2000):
    """Each year's wettest n-day total (mm), for every complete calendar year in the record."""
    days_per_year = totals.groupby(totals.index.year).size()
    maxima = totals.groupby(totals.index.year).max()
    full = [y for y in maxima.index
            if days_per_year[y] == pd.Timestamp(year=y, month=12, day=31).dayofyear]  # 365 or 366
    if keep_2000 and config.IMERG_START.year in maxima.index:
        full = sorted(set(full) | {config.IMERG_START.year})
    return maxima.loc[full]


def fit_gumbel(maxima):
    """Gumbel mu and beta fitted by maximum likelihood to a list of annual maxima."""
    mu, beta = stats.gumbel_r.fit(np.asarray(maxima, dtype=float))
    return mu, beta


def return_levels(maxima, year):
    """R0, R(5), R(25), R(100) for a forecast or storm `year`, fitted on years before it only."""
    before = maxima[maxima.index < year]
    if len(before) < config.GUMBEL_MIN_YEARS:
        raise ValueError(f"{len(before)} years of maxima before {year}; the fit needs "
                         f"at least {config.GUMBEL_MIN_YEARS}")
    mu, beta = fit_gumbel(before)
    levels = {period: gumbel_level(mu, beta, period) for period in RETURN_PERIODS}
    return {"mu": mu, "beta": beta, "n_years": len(before),
            "r0": config.R0_FACTOR * levels[5], **levels}


def map_table(overlay):
    """The overlay as one row per barangay and level, one column per map: Pop_5, Pop_25, Pop_100."""
    table = overlay.pivot_table(index=["psgc", "var"], columns="return_period",
                                values="residents", aggfunc="sum")
    missing = set(RETURN_PERIODS) - set(table.columns)
    if missing:
        raise ValueError(f"the overlay has no {sorted(missing)}-year map")
    return table[list(RETURN_PERIODS)]


def map_weights(rain, levels):
    """How much of each map's residents an n-day total of `rain` mm counts: {5: w5, 25: w25, 100: w100}."""
    rains = [levels["r0"]] + [levels[p] for p in RETURN_PERIODS]
    if not all(a < b for a, b in zip(rains, rains[1:])):
        raise ValueError(f"the anchors must rise: R0, R(5), R(25), R(100) = {[round(r, 1) for r in rains]}")
    names = [None] + list(RETURN_PERIODS)  # the R0 anchor has no map: nobody is exposed there
    weights = {p: 0.0 for p in RETURN_PERIODS}
    if rain <= rains[0]:
        return weights
    if rain >= rains[-1]:
        weights[RETURN_PERIODS[-1]] = 1.0
        return weights
    i = next(n for n in range(len(rains) - 1) if rain <= rains[n + 1])  # rain lies in rains[i]..rains[i+1]
    share = (rain - rains[i]) / (rains[i + 1] - rains[i])
    if names[i] is not None:
        weights[names[i]] = 1 - share
    weights[names[i + 1]] = share
    return weights


def graded_exposure(rain, levels, overlay):
    """N_{b,k}: residents of each barangay and level that an n-day total of `rain` mm would flood."""
    pops = map_table(overlay)
    residents = sum(w * pops[p] for p, w in map_weights(rain, levels).items())
    return residents.rename("residents").reset_index()


def exposed_total(rain, levels, map_totals):
    """QC residents in zones an n-day total of `rain` mm would flood: sum of N_{b,k} over barangays and levels."""
    return sum(w * map_totals[p] for p, w in map_weights(rain, levels).items())


def map_totals(overlay):
    """Each map's QC residents in flood zones, all barangays and levels: {5: ..., 25: ..., 100: ...}."""
    return map_table(overlay).sum().to_dict()


def weekly_rmax(totals, calendar):
    """Each MMWR week's wettest n-day total ending in that week (mm), for weeks with all 7 days."""
    days = calendar[["date", "week_index", "year", "week"]].copy()
    days["date"] = pd.to_datetime(days["date"])
    days = days.merge(totals.rename("rain_mm"), left_on="date", right_index=True, how="inner")
    weekly = days.groupby(["week_index", "year", "week"])["rain_mm"].agg(["max", "size"]).reset_index()
    weekly = weekly[weekly["size"] == 7]
    return weekly.drop(columns="size").rename(columns={"max": "rmax_mm"})


def weekly_ei(rmax, levels, map_tot, qc_total_2024):
    """EI(t) = 100 * sum of N_{b,k}(Rmax_t) / QC's 2024 total, for every week in rmax."""
    ei = [100 * exposed_total(r, levels, map_tot) / qc_total_2024 for r in rmax["rmax_mm"]]
    return rmax.assign(ei=ei)


def storm_peak(totals, first, last):
    """A storm's wettest n-day total whose last day falls between first and last."""
    window = totals[pd.Timestamp(first):pd.Timestamp(last)]
    return float(window.max()), window.idxmax()


def storm_report(totals, maxima, overlay, qc_total_2024, days):
    """Where each storm's wettest n-day total falls against its own year's return levels."""
    map_tot = map_totals(overlay)
    rows = []
    for storm, facts in config.STORMS.items():
        peak, end = storm_peak(totals, facts["start_date"], facts["end_date"])
        levels = return_levels(maxima, facts["year"])
        start = end - pd.Timedelta(days=days - 1)
        rows.append({"storm": storm, "UTC days": f"{start:%Y-%m-%d} to {end:%Y-%m-%d}",
                     f"{days}-day mm": peak, "R0": levels["r0"], "R(5)": levels[5],
                     "R(25)": levels[25], "R(100)": levels[100],
                     "EI %": 100 * exposed_total(peak, levels, map_tot) / qc_total_2024})
    return pd.DataFrame(rows).set_index("storm")


def output_path(days, keep_2000=config.IMERG_KEEP_2000):
    """ei_weekly.csv for config's settings; a comparison run writes its own file."""
    parts = []
    if days != config.RAIN_ACCUM_DAYS:
        parts.append(f"{days}day")
    if keep_2000 != config.IMERG_KEEP_2000:
        parts.append("with2000" if keep_2000 else "no2000")
    if not parts:
        return config.EI_WEEKLY
    return config.EI_WEEKLY.with_name(f"{config.EI_WEEKLY.stem}_{'_'.join(parts)}.csv")


def parse_args():
    parser = argparse.ArgumentParser(description="C3: return levels, graded exposure and weekly EI")
    parser.add_argument("--days", type=int, default=config.RAIN_ACCUM_DAYS,
                        help=f"days in the trigger rain total (default {config.RAIN_ACCUM_DAYS}; "
                             f"{config.RAIN_ACCUM_DAYS_TEST} = the single-day comparison run)")
    parser.add_argument("--without-2000", action="store_true",
                        help="refit without the partial year 2000 (June-December), the plan's comparison run")
    return parser.parse_args()


def main():
    args = parse_args()
    days = args.days
    keep_2000 = config.IMERG_KEEP_2000 and not args.without_2000
    if days < 1:
        raise SystemExit("--days must be 1 or more")
    r24 = catchment_rain()
    totals = n_day_totals(r24, days)
    maxima = annual_maxima(totals, keep_2000)
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    census = pd.read_csv(config.CENSUS_QC, dtype={"psgc": str})
    qc_total_2024 = float(census["pop_2024"].sum())  # the census rescale fitted the map to these totals
    print(f"Trigger rain: {days}-day totals (config.RAIN_ACCUM_DAYS = {config.RAIN_ACCUM_DAYS}; "
          f"1 = the single wettest day); June-December 2000 {'kept' if keep_2000 else 'left out'}")
    print(f"R24 for {len(r24)} UTC days, {r24.index[0]:%Y-%m-%d} to {r24.index[-1]:%Y-%m-%d}; "
          f"annual maxima for {len(maxima)} years ({maxima.index[0]}-{maxima.index[-1]})")
    print(f"QC 2024 total (EI denominator): {qc_total_2024:,.0f}")

    calendar = weeks.build_calendar()
    rmax = weekly_rmax(totals, calendar)
    map_tot = map_totals(overlay)
    tables, fits = [], []
    for year in range(config.BACKTEST_FIRST_YEAR, config.BACKTEST_LAST_YEAR + 1):
        levels = return_levels(maxima, year)
        fits.append({"fit_year": year, "years": levels["n_years"], "mu": levels["mu"],
                     "beta": levels["beta"], "R0": levels["r0"], "R(5)": levels[5],
                     "R(25)": levels[25], "R(100)": levels[100]})
        tables.append(weekly_ei(rmax, levels, map_tot, qc_total_2024).assign(fit_year=year))

    out = pd.concat(tables, ignore_index=True).assign(rain_days=days)
    out = out[COLUMNS].round({"rmax_mm": 2, "ei": 4})
    path = output_path(days, keep_2000)
    part = path.with_suffix(".part")
    out.to_csv(part, index=False)
    part.replace(path)

    print(f"\nGumbel fits, one per forecast year (years before it only), mm per {days} UTC days:")
    print(pd.DataFrame(fits).set_index("fit_year").round(1).to_string())
    print(f"\nEach storm's wettest {days}-day total against its own year's fit (C8's first check):")
    print(storm_report(totals, maxima, overlay, qc_total_2024, days).round(1).to_string())
    last = out[out["fit_year"] == config.BACKTEST_LAST_YEAR]
    print(f"\nwrote {path} ({len(out)} rows: {out['fit_year'].nunique()} fit years x "
          f"{len(last)} weeks, {last['year'].iloc[0]} week {last['week'].iloc[0]} to "
          f"{last['year'].iloc[-1]} week {last['week'].iloc[-1]}); "
          f"EI above 0 in {(last['ei'] > 0).mean():.1%} of weeks ({config.BACKTEST_LAST_YEAR} fit)")
    print("Now run the checks (S9):  python -m src.checks")


if __name__ == "__main__":
    main()

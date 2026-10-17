"""Rain return levels, graded exposure and the weekly exposure index (task C3).

The trigger rain is an n-day total, n = config.RAIN_ACCUM_DAYS: 3 by default, 1 for the
plan's original single wettest day (the comparison run). The single day missed the long
habagat floods of 2025 and 2026 (D = 6 and 4 days, moderate rain each day) in a test
run of C9 on 2026-10-18, so C3 switched to 3-day totals; the paper reports both runs. Every step below uses
the same n, so the return levels and the storms are always on one scale.

Five steps, each one function below:

1. catchment_rain: R24 for every UTC day = IMERG's daily rain averaged over the A7
   catchments, each 0.1 degree cell weighted by its area inside them:
       R24_d = sum over cells g of w_g * R_{g,d},   w_g = (catchment km2 in g) / (catchment km2)

2. n_day_totals: Rn_d = R24_d + R24_{d-1} + ... + R24_{d-n+1}, the rain of the n UTC days
   ending on day d. With n = 1 it is R24 itself.

3. return_levels: fit a Gumbel curve to each year's wettest n-day total, using only years
   BEFORE the forecast or storm year (rule 2), at least config.GUMBEL_MIN_YEARS of them:
       R(T) = mu - beta * ln(-ln(1 - 1/T)),   R0 = 0.5 * R(5)
   In plain words: R(25) is the n-day rain IMERG sees about once in 25 years, on IMERG's
   own scale (rule 3: never compare it with ERA5 or ECMWF rain). The fit is maximum
   likelihood (scipy's gumbel_r.fit), the estimator check S9's pass values match.

4. graded_exposure: residents exposed by an n-day total of Rn mm, interpolated between
   NOAH's maps (C2's overlay), for each barangay b and hazard level k:
       N_{b,k} = Pop_a + (Rn - R_a) / (R_b - R_a) * (Pop_b - Pop_a)
   between the anchors (R0, 0), (R(5), Pop_5), (R(25), Pop_25), (R(100), Pop_100).
   Below R0 nobody; above R(100) the 100-year map's residents. A storm halfway between
   the 5- and 25-year rain counts halfway between the two maps' residents.

5. weekly_ei: EI(t) = 100 * sum over b, k of N_{b,k}(Rmax_t) / P_QC_2024
   Rmax_t is the wettest n-day total ending in week t (MMWR weeks, A3); with n = 3, a
   total ending on Sunday also holds the last 2 days of the week before. EI is the
   percentage of QC residents living in zones that rain would flood. The denominator is
   QC's 2024 total, the total C1 fitted the population map to, never that week's
   population (rule 7).

The return levels change with the forecast year, so ei_weekly.csv holds one EI series per
forecast year: B10 at a forecast day in year Y reads the rows with fit_year == Y. Those
rows cover every week 2015 onward, all scored with the levels fitted on years before Y.

Output: data/clean/ei_weekly.csv (config.EI_WEEKLY), one row per fit year and MMWR week:
    fit_year, rain_days, week_index, year, week, rmax_mm, ei
rain_days is the n the file was made with. Weeks run 2015 week 1 to the last week IMERG has
all 7 days of. The comparison runs write their own files beside it: --days 1 writes
ei_weekly_1day.csv, --without-2000 writes ei_weekly_no2000.csv.

C8 and C9 call n_day_totals, annual_maxima, return_levels and graded_exposure for each
storm, with the same config.RAIN_ACCUM_DAYS (C9 on ERA5 and the ECMWF forecasts);
graded_exposure returns the psgc, var, residents table C5's exposed_with_tiers takes.

Run from the repository root (needs A4's imerg_daily.nc, A7's catchments, A5's census and
C2's overlay_qc.csv):
    python -m src.flood_exposure                  # 3-day totals (config.RAIN_ACCUM_DAYS): ei_weekly.csv
    python -m src.flood_exposure --days 1         # single-day comparison run: ei_weekly_1day.csv
    python -m src.flood_exposure --without-2000   # refit without June-December 2000 (plan
                                                  # correction 7): ei_weekly_no2000.csv
Then run the checks (S9):  python -m src.checks
"""

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
    """Each IMERG cell's share of the catchment area, for cells whose centres are lon x lat.

    A cell is the 0.1 degree square around its centre. Areas are measured in EPSG:32651.
    Returns a table with lon, lat, km2 and weight (the weights add up to 1). Stops if the
    cells do not hold the whole catchment area, which would mean the IMERG box is too small.
    """
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
    """R24 for every UTC day in imerg_daily.nc: area-weighted mean over the catchments (mm).

    Returns a Series indexed by day. Cells are picked by their lon and lat names, never by
    position (rule 8).
    """
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
    """Rain of the `days` UTC days ending on each day: Rn_d = R24_d + ... + R24_{d-days+1} (mm).

    daily: one value per UTC day (catchment_rain, or ERA5's or a forecast's catchment
    rain). The first days-1 days have no full window and are dropped. With days = 1 this
    returns `daily` unchanged. Stops if a day is missing, which would make a window span
    more than `days` days.
    """
    index = pd.DatetimeIndex(daily.index)
    gaps = pd.date_range(index.min(), index.max(), freq="D").difference(index)
    if len(gaps) or not index.is_monotonic_increasing:
        raise ValueError(f"daily rain must have every day in order; {len(gaps)} days missing")
    return daily.rolling(days).sum().dropna()


def annual_maxima(totals, keep_2000=config.IMERG_KEEP_2000):
    """Each year's wettest n-day total (mm), for every complete calendar year in the record.

    totals: n_day_totals. Each total belongs to the year of its last day. A year counts
    only if every one of its days has a total. The exception is 2000, whose record starts
    on config.IMERG_START (1 June; ERA5 starts there too, config.ERA5_START): it is kept
    when keep_2000 (config.IMERG_KEEP_2000; June to December is the rainy season). The plan
    refits once without it (correction 7): python -m src.flood_exposure --without-2000.
    """
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
    """R0, R(5), R(25), R(100) for a forecast or storm `year`, fitted on years before it only.

    maxima: Series of annual maxima indexed by year (annual_maxima). Stops when fewer than
    config.GUMBEL_MIN_YEARS years come before `year`. Returns a dict with mu, beta, the
    number of years used, R0 and one entry per return period (5, 25, 100).
    """
    before = maxima[maxima.index < year]
    if len(before) < config.GUMBEL_MIN_YEARS:
        raise ValueError(f"{len(before)} years of maxima before {year}; the fit needs "
                         f"at least {config.GUMBEL_MIN_YEARS}")
    mu, beta = fit_gumbel(before)
    levels = {period: gumbel_level(mu, beta, period) for period in RETURN_PERIODS}
    return {"mu": mu, "beta": beta, "n_years": len(before),
            "r0": config.R0_FACTOR * levels[5], **levels}


def map_table(overlay):
    """C2's overlay as one row per barangay and level, one column per map: Pop_5, Pop_25, Pop_100."""
    table = overlay.pivot_table(index=["psgc", "var"], columns="return_period",
                                values="residents", aggfunc="sum")
    missing = set(RETURN_PERIODS) - set(table.columns)
    if missing:
        raise ValueError(f"the overlay has no {sorted(missing)}-year map")
    return table[list(RETURN_PERIODS)]


def map_weights(rain, levels):
    """How much of each map's residents an n-day total of `rain` mm counts: {5: w5, 25: w25, 100: w100}.

    The anchors are (R0, nobody), (R(5), Pop_5), (R(25), Pop_25), (R(100), Pop_100), joined
    by straight lines, so N = w5 * Pop_5 + w25 * Pop_25 + w100 * Pop_100. Examples:
    rain = R(5) gives w5 = 1; halfway between R(5) and R(25) gives w5 = w25 = 0.5; halfway
    between R0 and R(5) gives w5 = 0.5 (half of the 5-year residents); below R0 all are 0;
    above R(100), w100 = 1. `rain` and `levels` must use the same n and the same product.
    """
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
    """N_{b,k}: residents of each barangay and level that an n-day total of `rain` mm would flood.

    levels: from return_levels. overlay: C2's table (psgc, return_period, var, residents).
    Returns one row per barangay and level with columns psgc, var and residents: the
    table C5's exposed_with_tiers takes.
    """
    pops = map_table(overlay)
    residents = sum(w * pops[p] for p, w in map_weights(rain, levels).items())
    return residents.rename("residents").reset_index()


def exposed_total(rain, levels, map_totals):
    """QC residents in zones an n-day total of `rain` mm would flood: sum of N_{b,k} over barangays and levels.

    map_totals: each map's QC total, {5: Pop_5, 25: Pop_25, 100: Pop_100} (map_totals()).
    The same weights apply to every barangay, so the city total is the weighted city totals.
    """
    return sum(w * map_totals[p] for p, w in map_weights(rain, levels).items())


def map_totals(overlay):
    """Each map's QC residents in flood zones, all barangays and levels: {5: ..., 25: ..., 100: ...}."""
    return map_table(overlay).sum().to_dict()


def weekly_rmax(totals, calendar):
    """Each MMWR week's wettest n-day total ending in that week (mm), for weeks with all 7 days.

    totals: n_day_totals, labelled by each window's last day. calendar: A3's date -> week
    table. Returns a table with week_index, year, week, rmax_mm.
    """
    days = calendar[["date", "week_index", "year", "week"]].copy()
    days["date"] = pd.to_datetime(days["date"])
    days = days.merge(totals.rename("rain_mm"), left_on="date", right_index=True, how="inner")
    weekly = days.groupby(["week_index", "year", "week"])["rain_mm"].agg(["max", "size"]).reset_index()
    weekly = weekly[weekly["size"] == 7]
    return weekly.drop(columns="size").rename(columns={"max": "rmax_mm"})


def weekly_ei(rmax, levels, map_tot, qc_total_2024):
    """EI(t) = 100 * sum of N_{b,k}(Rmax_t) / QC's 2024 total, for every week in rmax (rule 7).

    map_tot: map_totals(overlay).
    """
    ei = [100 * exposed_total(r, levels, map_tot) / qc_total_2024 for r in rmax["rmax_mm"]]
    return rmax.assign(ei=ei)


def storm_peak(totals, first, last):
    """A storm's wettest n-day total whose last day falls on one of its wettest days, first..last.

    Returns (rain in mm, last day of that window). With n = 3 and a 3-day first..last
    (config.STORMS), the window can start up to 2 days before `first`.
    """
    window = totals[pd.Timestamp(first):pd.Timestamp(last)]
    return float(window.max()), window.idxmax()


def storm_report(totals, maxima, overlay, qc_total_2024, days):
    """Where each storm's wettest n-day total falls against its own year's return levels (C8's first check).

    totals and maxima must be made with the same `days`.
    """
    map_tot = map_totals(overlay)
    rows = []
    for storm, facts in config.STORMS.items():
        peak, end = storm_peak(totals, *facts["wettest_days"])
        levels = return_levels(maxima, facts["year"])
        start = end - pd.Timedelta(days=days - 1)
        rows.append({"storm": storm, "UTC days": f"{start:%Y-%m-%d} to {end:%Y-%m-%d}",
                     f"{days}-day mm": peak, "R0": levels["r0"], "R(5)": levels[5],
                     "R(25)": levels[25], "R(100)": levels[100],
                     "EI %": 100 * exposed_total(peak, levels, map_tot) / qc_total_2024})
    return pd.DataFrame(rows).set_index("storm")


def output_path(days, keep_2000=config.IMERG_KEEP_2000):
    """ei_weekly.csv for config's settings; a comparison run gets its own file, so it never
    replaces the main one: ei_weekly_1day.csv for another n, ei_weekly_no2000.csv without 2000."""
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
    qc_total_2024 = float(census["pop_2024"].sum())  # C1 fitted the map to these totals (S8)
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

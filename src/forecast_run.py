"""Layer 2 on archived rain forecasts: the forecast-driven storm run (task C9).

C8 runs the storms on the rain that fell (IMERG). C9 asks what a health office would have
stocked 1, 2 or 3 days before each storm, from the ECMWF forecast it had then (A15,
Open-Meteo Previous Runs). After the rain the chain is the same: C3's graded exposure,
C5's exposed people, C6's units, C7's need per health center.

Five steps, each one function below:

1. era5_maxima: ERA5's catchment rain per UTC day (A14), its n-day totals and each
   year's wettest (n = config.RAIN_ACCUM_DAYS = 3). The forecasts are matched on ERA5's
   return levels, fitted on years before the storm's year, never on IMERG's (rule 3):
   ERA5 comes from the same ECMWF model as the forecasts, so the two share one scale.

2. forecast_daily: each forecast's catchment rain per UTC day, the sum of weight x rain_mm
   over A15's 4 cells, for each previous day N.

3. lead_total and forecast_peak: the n-day total forecast L days before the window,
       R_L = sum over i = 0 .. n-1 of previous_day (L + i) on the window's day i
   (data/raw/ecmwf_previous_runs.md says why), and each lead's wettest window ending on
   one of the storm's wettest days (config.STORMS' wettest_days): "each lead time's
   wettest forecast" in the plan. The same lead's total over C8's window (the IMERG peak,
   flood_exposure.storm_peak over start_date to end_date) is reported beside it.

4. flagged and flag_scores: a barangay is flagged when at least a share X of its 2024
   residents live in zones the rain floods (config.FLAG_EXPOSED_SHARES, an assumption;
   every barangay has some residents in the 5-year zones, so "anyone" would flag all 142).
   Reported for each X: the share of flagged barangays A11 lists as flooded, and the share
   of listed barangays that were flagged.

5. run_tables: C5 to C7 at that rain, for a short flood (D = 1, at each w) and a long one
   (D = 7), because the flood's length is not known 1-3 days ahead (config.FORECAST_RUN_D,
   exposed.scenarios). The observed run (IMERG rain on IMERG's levels, A11's D), done
   here the same way C8 does it, sits beside the forecasts.

Outputs in results/ (no case data):
    c9_forecast_runs.csv       one row per storm, run, D and w: the window, rain, return
                               levels, where the rain falls, EI, flag shares, and QC's
                               exposed people and units
    c9_forecast_barangays.csv  the same runs, one row per barangay
    c9_forecast_centers.csv    the same runs, need per health center and pool, by tier
Every unit figure is stock planning, not a prescription (rule 10).

Run from the repository root (needs A4's imerg_daily.nc, A7, A14's era5_daily.csv, A15's
forecasts_storms.csv, A5's census_qc.csv, C2's overlay_qc.csv, C4's shares_qc.csv and
C7's center_shares_qc.csv); a few seconds:
    python -m src.forecast_run
"""

import pandas as pd

import config
from src import allocation, doses, era5, exposed, flood_exposure

N_DAYS = config.RAIN_ACCUM_DAYS
OBSERVED = "observed"
KEYS = ["storm", "run", "flood", "D", "w"]   # one run of C5-C7; the key of every output row
UNIT_COLUMNS = ["exposed", *doses.UNITS]     # exposed people, then doxy100, courses, amox500


def era5_maxima():
    """Each year's wettest n-day ERA5 total over the catchments (mm), from A14's table.

    Stops if a value is missing: a missing cell would make that day's sum too small.
    """
    table = pd.read_csv(config.ERA5_DAILY)
    if table["rain_mm"].isna().any():
        raise ValueError("era5_daily.csv has missing rain: rerun python -m src.era5")
    rain = era5.catchment_rain(table)
    rain.index = pd.to_datetime(rain.index)
    return flood_exposure.annual_maxima(flood_exposure.n_day_totals(rain, N_DAYS))


def forecast_daily(table):
    """Catchment rain of each forecast per UTC day: sum of weight x rain_mm over the cells (mm).

    table: A15's forecasts_storms.csv. Returns a Series indexed by storm, previous_day and
    date (a Timestamp), not rounded. Stops if a value is missing or a day lacks a cell.
    """
    if table["rain_mm"].isna().any():
        raise ValueError("forecasts_storms.csv has missing rain: rerun python -m src.ecmwf")
    n_cells = table[["lat", "lon"]].drop_duplicates().shape[0]
    cells_per_day = table.groupby(["storm", "previous_day", "date"]).size()
    if (cells_per_day != n_cells).any():
        raise ValueError(f"some forecast days do not have all {n_cells} cells: rerun python -m src.ecmwf")
    weighted = table.assign(mm=table["weight"] * table["rain_mm"], date=pd.to_datetime(table["date"]))
    return weighted.groupby(["storm", "previous_day", "date"])["mm"].sum()


def lead_total(daily, storm, lead, end):
    """R_L: the n-day total ending on `end`, forecast `lead` days before the window's first day.

    Day i of the window (i = 0 .. n-1) comes from previous_day lead + i. Stops if A15 did
    not fetch one of them.
    """
    start = pd.Timestamp(end) - pd.Timedelta(days=N_DAYS - 1)
    total = 0.0
    for i in range(N_DAYS):
        day = start + pd.Timedelta(days=i)
        key = (storm, lead + i, day)
        if key not in daily.index:
            raise ValueError(f"{storm}: no previous_day {lead + i} forecast for {day:%Y-%m-%d} "
                             f"(run python -m src.ecmwf)")
        total += daily[key]
    return total


def forecast_peak(daily, storm, lead, first, last):
    """A lead's wettest n-day forecast total among windows ending first..last: (mm, last day)."""
    ends = pd.date_range(first, last, freq="D")
    totals = pd.Series([lead_total(daily, storm, lead, end) for end in ends], index=ends)
    return float(totals.max()), totals.idxmax()


def position(rain, levels):
    """Where an n-day total falls against R0, R(5), R(25) and R(100), in words, e.g. "R(5) to R(25)"."""
    anchors = [("R0", levels["r0"])] + [(f"R({p})", levels[p]) for p in flood_exposure.RETURN_PERIODS]
    if rain < anchors[0][1]:
        return "below R0"
    for (low, _), (high, r_high) in zip(anchors, anchors[1:]):
        if rain < r_high:
            return f"{low} to {high}"
    return "above R(100)"


def flagged(residents, shares, share):
    """Barangays (psgc) with at least `share` of their 2024 residents in zones the rain floods.

    residents: C3's graded exposure (psgc, var, residents); the levels are added up.
    """
    per_barangay = residents.groupby("psgc")["residents"].sum()
    pop = shares["pop_2024"].reindex(per_barangay.index)
    if pop.isna().any() or len(per_barangay) != config.QC_BARANGAYS:
        raise ValueError(f"need the 2024 population of all {config.QC_BARANGAYS} barangays")
    return set(per_barangay.index[per_barangay >= share * pop])


def flag_scores(flagged_psgc, flooded_psgc):
    """The two shares C8 and C9 report, for one flag rule.

    flagged_and_listed / flagged: of the barangays flagged, the share A11 lists as flooded.
    flagged_and_listed / listed: of the barangays A11 lists, the share that were flagged.
    The first is left empty (None) when nothing is flagged: no share can be computed.
    """
    both = len(flagged_psgc & set(flooded_psgc))
    return {"flagged": len(flagged_psgc), "flagged_and_listed": both,
            "share_flagged_listed": both / len(flagged_psgc) if flagged_psgc else None,
            "share_listed_flagged": both / len(flooded_psgc)}


def rain_columns(storm, run, product, lead, window_end, rain, rain_c8_window, levels,
                 residents, shares, qc_total, flooded):
    """The columns of a run that do not depend on D or w: the window, rain, levels, EI and flags."""
    start = window_end - pd.Timedelta(days=N_DAYS - 1)
    row = {"storm": storm, "run": run, "product": product, "lead_days": lead,
           "window": f"{start:%Y-%m-%d} to {window_end:%Y-%m-%d}",
           "rain_mm": rain, "rain_c8_window_mm": rain_c8_window,
           "levels_years": levels["n_years"], "r0": levels["r0"], "r5": levels[5],
           "r25": levels[25], "r100": levels[100], "position": position(rain, levels),
           "ei_pct": 100 * residents["residents"].sum() / qc_total,
           "listed_flooded": len(flooded)}
    for share in config.FLAG_EXPOSED_SHARES:
        tag = f"{100 * share:.0f}"
        scores = flag_scores(flagged(residents, shares, share), flooded)
        row.update({f"{name}_{tag}": value for name, value in scores.items()})
    return row


def observed_scenarios(flood_days):
    """(label, D, w) for the observed run: A11's D; w matters only below the cut-off (C5)."""
    if flood_days >= config.CONTINUOUS_EXPOSURE_DAYS:
        return [(f"D = {flood_days} (any w)", flood_days, config.WOUND_SHARE_W[0])]
    return [(f"D = {flood_days}, w = {w:g}", flood_days, w) for w in config.WOUND_SHARE_W]


def run_tables(rain_row, residents, shares, center_table, scenarios):
    """C5 to C7 at one rain for each (label, D, w): the run rows, barangay rows and center rows."""
    runs, barangays, centers = [], [], []
    per_barangay = residents.groupby("psgc")["residents"].sum().rename("residents")
    for label, days, w in scenarios:
        keys = {"storm": rain_row["storm"], "run": rain_row["run"], "flood": label, "D": days, "w": w}
        stock = doses.barangay_doses(residents, shares, days, w)
        runs.append({**rain_row, **keys, **stock[UNIT_COLUMNS].sum().to_dict(), "label": doses.LABEL})
        barangays.append(stock[UNIT_COLUMNS].join(per_barangay).reset_index().assign(**keys))
        for pool, need in allocation.center_needs(residents, shares, center_table, days, w).items():
            centers.append(need.reset_index().assign(pool=pool, **keys))
    return runs, barangays, centers


def storm_runs(storm, facts, imerg, era5_max, daily, overlay, shares, center_table, qc_total):
    """Every run of one storm: observed (IMERG) first, then each lead (ECMWF)."""
    imerg_totals, imerg_max = imerg
    flooded = facts["flooded_psgc"]
    out = ([], [], [])

    rain, end = flood_exposure.storm_peak(imerg_totals, facts["start_date"], facts["end_date"])
    levels = flood_exposure.return_levels(imerg_max, facts["year"])
    residents = flood_exposure.graded_exposure(rain, levels, overlay)
    row = rain_columns(storm, OBSERVED, "IMERG Late", "", end, rain, rain, levels,
                       residents, shares, qc_total, flooded)
    for part, rows in zip(out, run_tables(row, residents, shares, center_table, observed_scenarios(facts["D"]))):
        part.extend(rows)
    c8_end = end

    levels = flood_exposure.return_levels(era5_max, facts["year"])  # ERA5's own scale (rule 3)
    for lead in config.FORECAST_LEADS_DAYS:
        rain, end = forecast_peak(daily, storm, lead, *facts["wettest_days"])
        rain_c8 = lead_total(daily, storm, lead, c8_end)
        residents = flood_exposure.graded_exposure(rain, levels, overlay)
        row = rain_columns(storm, f"lead {lead}", "ECMWF IFS 0.25", lead, end, rain, rain_c8, levels,
                           residents, shares, qc_total, flooded)
        for part, rows in zip(out, run_tables(row, residents, shares, center_table, exposed.scenarios())):
            part.extend(rows)
    return out


def write(table, path):
    """Write a results table via a .part file, so a stopped run never leaves half a file."""
    part = path.with_suffix(".part")
    table.to_csv(part, index=False)
    part.replace(path)


def report(runs):
    """Print each storm's rain against its levels, the flag shares, and QC's stock per run."""
    rain_cols = ["run", "window", "rain_mm", "rain_c8_window_mm", "r0", "r5", "r25", "r100",
                 "position", "ei_pct"]
    flag_cols = [f"{name}_{100 * s:.0f}" for s in config.FLAG_EXPOSED_SHARES
                 for name in ("flagged", "share_flagged_listed", "share_listed_flagged")]
    for storm, rows in runs.groupby("storm", sort=False):
        by_run = rows.drop_duplicates("run")
        print(f"\n{storm} ({config.STORMS[storm]['start_date']} to {config.STORMS[storm]['end_date']}, "
              f"D = {config.STORMS[storm]['D']}, {by_run['listed_flooded'].iloc[0]} barangays listed flooded):")
        print("  " + by_run[rain_cols].round(1).to_string(index=False).replace("\n", "\n  "))
        print("  flagged barangays (share of residents in flood zones at least 25% / 50%):")
        print("  " + by_run[["run", *flag_cols]].round(2).to_string(index=False).replace("\n", "\n  "))
        print("  QC stock, units (stock planning, not prescriptions):")
        units = rows[["run", "flood", *doses.UNITS]]
        print("  " + units.to_string(index=False, float_format="{:,.0f}".format).replace("\n", "\n  "))
    print(f"\n{doses.LABEL}")


def main():
    forecasts = pd.read_csv(config.FORECASTS_STORMS)
    daily = forecast_daily(forecasts)
    era5_max = era5_maxima()
    imerg_totals = flood_exposure.n_day_totals(flood_exposure.catchment_rain(), N_DAYS)
    imerg = (imerg_totals, flood_exposure.annual_maxima(imerg_totals))
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    shares = exposed.load_shares()
    center_table = allocation.load_center_shares()
    census = pd.read_csv(config.CENSUS_QC, dtype={"psgc": str})
    qc_total = float(census["pop_2024"].sum())  # EI over QC's 2024 total from the same maps (rule 7)
    print(f"C9 on {N_DAYS}-day totals: ECMWF forecasts on ERA5's return levels, beside IMERG's observed run")

    tables = ([], [], [])
    for storm, facts in config.STORMS.items():
        if storm not in set(forecasts["storm"]):
            print(f"{storm}: no archived forecasts in forecasts_storms.csv (A15), skipped")
            continue
        for part, rows in zip(tables, storm_runs(storm, facts, imerg, era5_max, daily, overlay,
                                                 shares, center_table, qc_total)):
            part.extend(rows)

    runs = pd.DataFrame(tables[0])
    barangays = pd.concat(tables[1], ignore_index=True)[[*KEYS, "psgc", "residents", *UNIT_COLUMNS]]
    centers = pd.concat(tables[2], ignore_index=True)[[*KEYS, "pool", "facility_code", *exposed.TIERS]]
    report(runs)
    write(runs.round(4), config.C9_RUNS)
    write(barangays.round(2), config.C9_BARANGAYS)
    write(centers.round(2), config.C9_CENTERS)
    print(f"\nwrote {config.C9_RUNS} ({len(runs)} rows), {config.C9_BARANGAYS} ({len(barangays)} rows), "
          f"{config.C9_CENTERS} ({len(centers)} rows)")


if __name__ == "__main__":
    main()

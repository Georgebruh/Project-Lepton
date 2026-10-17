"""Sanity checks S1-S11 (task A2; specs in the plan's "Sanity checks" table).

Run from the repository root:  python -m src.checks
A check that is not built yet, or whose data file is not on this computer, is
reported as SKIP. Any FAIL stops work: the script exits with code 1.
A check may return a short text, printed after PASS.
"""

import sys
from datetime import date

import numpy as np
import pandas as pd
import xarray as xr
from epiweeks import Week, Year

import config
from src import forecast_range, thresholds, weeks


class NotBuilt(Exception):
    """Raised by a check whose task has not been done yet."""


def need_file(path, task):
    """Raise NotBuilt if a task's output file is not on this computer."""
    if not path.exists():
        raise NotBuilt(f"{path.name} not found: run task {task} or copy the file from the team drive")


def s1_calendar():
    """S1 (A3): CDC/MMWR weeks.

    9 Aug 2026 is 2026 week 32 (9-15 Aug); 2020 and 2025 have 53 weeks;
    2015 week 1 starts 4 Jan 2015. Then the same on the A3 calendar table,
    plus: every week index covers 7 days with no gaps, and week 53 maps to 52.
    """
    wk = Week.fromdate(date(2026, 8, 9))
    assert (wk.year, wk.week) == (2026, 32), f"got {wk}"
    assert wk.startdate() == date(2026, 8, 9), wk.startdate()
    assert wk.enddate() == date(2026, 8, 15), wk.enddate()
    for year in (2020, 2025):
        assert Year(year).totalweeks() == 53, f"{year} has {Year(year).totalweeks()} weeks"
    assert Week(2015, 1).startdate() == config.FIRST_WEEK_START

    # The A3 table: the same answers, plus a gap-free week index.
    table = weeks.build_calendar()
    row = table.set_index("date").loc[date(2026, 8, 9)]
    assert (row["year"], row["week"]) == (2026, 32), f"got {row['year']} week {row['week']}"
    assert table["date"].iloc[0] == config.FIRST_WEEK_START
    assert table["week_index"].iloc[0] == 0
    per_week = table.groupby("week_index").size()
    assert (per_week == 7).all(), "every week index must cover exactly 7 days"
    assert (per_week.index == range(len(per_week))).all(), "week index has a gap"
    for year in (2020, 2025):
        n = table.loc[table["year"] == year, "week"].nunique()
        assert n == 53, f"{year} has {n} weeks in the table"
        wk53 = table[(table["year"] == year) & (table["week"] == 53)]
        assert (wk53["week_of_year"] == 52).all(), f"{year} week 53 not mapped to 52"
    assert table["week_of_year"].max() == config.MAX_WEEK


def s3_census():
    """S3 (A5): boundaries, 2024 totals and 2020 age tables joined on PSGC.

    142 QC barangays, each code once, matched in all three sources (a shape, a
    2020 total and a 2024 total); barangay totals add up to QC's 2020 and 2024
    census totals; the 2020 single ages add up to each barangay's 2020 total.
    """
    import geopandas as gpd

    if not config.BARANGAYS_QC.exists():
        raise NotBuilt("needs task A5 (run python -m src.census)")
    brgy = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "pop_2020", "pop_2024"])
    age = pd.read_csv(config.AGE_SEX_2020_QC, dtype={"psgc": str})

    assert len(brgy) == config.QC_BARANGAYS, f"{len(brgy)} barangays"
    assert brgy["psgc"].is_unique, "duplicate psgc"
    assert brgy["psgc"].str.fullmatch(config.QC_PSGC_PREFIX + r"\d{5}").all(), "psgc not a 10-digit QC code"
    assert brgy.geometry.notna().all() and not brgy.geometry.is_empty.any(), "barangay without a shape"
    assert brgy[["pop_2020", "pop_2024"]].notna().all().all(), "barangay without a census total"
    for year in (2020, 2024):
        total = int(brgy[f"pop_{year}"].sum())
        assert total == config.CENSUS_POP_QC[year], f"{year}: {total} != {config.CENSUS_POP_QC[year]}"

    assert set(age["psgc"]) == set(brgy["psgc"]), "age table and boundaries hold different barangays"
    assert len(age) == config.QC_BARANGAYS * 2 * 81, f"age table has {len(age)} rows, expected 142 x 2 sexes x 81 ages"
    by_brgy = age.groupby("psgc")["pop"].sum()
    assert (by_brgy == brgy.set_index("psgc")["pop_2020"]).all(), "single ages do not add up to pop_2020"


def s2_rain_file():
    """S2 (A4): scan imerg_daily.nc in the A4 box.

    Passes when: the cells are exactly the A4 box; there is one value per UTC day from
    IMERG_START with no day missing; no value is a fill value (stored as missing) or
    negative; and big storms show up as wet days, which proves the dates and the place
    are right. Days are ranked by the plain average over the box's cells (1 = wettest):
    Carina's wettest day (23-25 July 2024) must be in 2024's wettest 5% of days, and
    each of S2_KNOWN_STORMS must have a day in the whole record's wettest 1%.
    (IMERG ranks Carina only #10 of 2024: satellites under-read long monsoon rain.)
    """
    need_file(config.IMERG_DAILY, "A4 (python -m src.imerg)")
    with xr.open_dataset(config.IMERG_DAILY) as ds:
        rain = ds["precipitation"].load()

    # The box: cell centres run from half a cell inside one edge to half a cell inside the other.
    # Rule 8: lon and lat are always picked by name.
    lon_min, lat_min, lon_max, lat_max = config.IMERG_BOX
    half = config.IMERG_CELL_DEG / 2
    for name, low, high in (("lon", lon_min, lon_max), ("lat", lat_min, lat_max)):
        centres = rain[name].values
        expected = round((high - low) / config.IMERG_CELL_DEG)
        assert len(centres) == expected, f"{len(centres)} {name} cells, expected {expected}"
        assert np.isclose(centres.min(), low + half, atol=1e-3), f"{name} starts at {centres.min()}"
        assert np.isclose(centres.max(), high - half, atol=1e-3), f"{name} ends at {centres.max()}"

    days = pd.DatetimeIndex(rain["time"].values)
    assert days.is_unique, "a day appears twice"
    assert days[0] == pd.Timestamp(config.IMERG_START), f"first day is {days[0]:%Y-%m-%d}"
    missing = pd.date_range(days[0], days[-1], freq="D").difference(days)
    assert len(missing) == 0, f"{len(missing)} days missing, first {missing[0]:%Y-%m-%d}"

    fill_days = days[rain.isnull().any(dim=["lon", "lat"]).values]  # fill values are read in as missing
    assert len(fill_days) == 0, f"fill values on {len(fill_days)} days, first {fill_days[0]:%Y-%m-%d}"
    assert float(rain.min()) >= 0, f"negative rain: {float(rain.min())} mm"

    box_mean = rain.mean(dim=["lon", "lat"]).to_series()

    carina = config.STORMS["carina_2024"]
    first, last = carina["wettest_days"]
    year = box_mean[box_mean.index.year == carina["year"]]
    year_rank = year.rank(ascending=False, method="min").astype(int)
    carina_best = year_rank[pd.Timestamp(first):pd.Timestamp(last)].min()
    carina_text = f"Carina #{carina_best} of {len(year)} days in {carina['year']}"
    assert carina_best <= config.S2_CARINA_TOP_SHARE * len(year), carina_text

    record_rank = box_mean.rank(ascending=False, method="min").astype(int)
    storm_text = []
    for name, (first, last) in config.S2_KNOWN_STORMS.items():
        best = record_rank[pd.Timestamp(first):pd.Timestamp(last)].min()
        storm_text.append(f"{name} #{best}")
        assert best <= config.S2_KNOWN_STORMS_TOP_SHARE * len(box_mean), (
            f"{name}'s wettest day is #{best} of {len(box_mean)} days")
    return (f"{len(days)} days {days[0]:%Y-%m-%d} to {days[-1]:%Y-%m-%d}; {carina_text}; "
            f"{', '.join(storm_text)} of {len(box_mean)} days")


def toy_cases(last_year):
    """Made-up weekly counts from 2015 to `last_year` for S7: 10 x (year - 2014) + week.

    COVID years get 10,000 in every week, so a threshold that wrongly used them
    would be far off.
    """
    rows = []
    for year in range(config.FIRST_WEEK_START.year, last_year + 1):
        for wk in Year(year).iterweeks():
            count = 10_000 if year in config.COVID_YEARS else 10 * (year - 2014) + wk.week
            rows.append({"week_index": weeks.week_index(wk.startdate()), "year": year,
                         "week": wk.week, "cases": count})
    return pd.DataFrame(rows)


def s7_breach():
    """S7, first part (B6's forecast_dist, B7): breach probability and thresholds.

    From the plan: forecast_dist(20, 5) with threshold 12.4 gives sf(12) = 0.758
    = P(Y >= 13); threshold 200 gives about 0. A count equal to the threshold is
    not a breach, in the forecast and in the scored outcome alike.
    Then thresholds on made-up counts (toy_cases), worked by hand:
      - 2019 week 1, cutoff 2018 week 50: 2018 is not complete yet, so the years
        are 2015-2017, with week-1 counts 11, 21, 31: mean 21, SD 10, T = 41.
      - every count after the cutoff overwritten with -999 (as S11 does): still 41.
      - 2025: the 5 most recent non-COVID years are 2018, 2019, 2022-2024, and
        week 53 gets week 52's threshold. With 2023 missing a week, 2017 replaces it.
      - 2017 has only 2 years before it, so it stops.
    The second part, "S7 scores" (wis, episodes and the exact interval), waits for D1 and D3.
    """
    dist = forecast_range.forecast_dist(20, 5)
    p = thresholds.breach_probability(dist, 12.4)
    assert round(p, 3) == 0.758, f"Pr(breach) at 12.4 = {p}"
    assert np.isclose(p, 1 - dist.cdf(12)), "Pr(breach) at 12.4 must be P(Y >= 13)"
    assert thresholds.breach_probability(dist, 200) < 1e-9, "Pr(breach) at 200 must be about 0"
    assert thresholds.breach_probability(dist, 12.0) == p, "at 12.0 a breach is also Y >= 13"
    assert thresholds.breached(13, 12.4) and not thresholds.breached(12, 12.4)
    assert not thresholds.breached(12, 12.0), "a count equal to the threshold is not a breach"

    cases = toy_cases(2024)
    cutoff = weeks.week_index(Week(2018, 50).startdate())
    t = thresholds.epidemic_threshold(2019, 1, cases, cutoff)
    assert np.isclose(t, 41), f"2019 week 1 threshold is {t}, expected 41"
    hidden = cases.copy()
    hidden.loc[hidden["week_index"] > cutoff, "cases"] = -999
    assert thresholds.epidemic_threshold(2019, 1, hidden, cutoff) == t, "the threshold used a count after the cutoff"

    end_2024 = weeks.week_index(Year(2024).enddate())
    years = thresholds.reference_years(2025, cases, end_2024)
    assert years == [2018, 2019, 2022, 2023, 2024], f"2025 reference years {years}"
    t_52 = thresholds.epidemic_threshold(2025, 52, cases, end_2024)
    assert thresholds.epidemic_threshold(2025, 53, cases, end_2024) == t_52, "week 53 must use week 52"
    gap = cases.copy()
    gap.loc[(gap["year"] == 2023) & (gap["week"] == 20), "cases"] = np.nan
    years = thresholds.reference_years(2025, gap, end_2024)
    assert years == [2017, 2018, 2019, 2022, 2024], f"with 2023 incomplete: {years}"

    try:
        thresholds.epidemic_threshold(2017, 1, cases, end_2024)
    except ValueError:
        pass
    else:
        raise AssertionError("2017 has only 2 reference years and must stop")
    return f"Pr(Y > 12.4) = {p:.3f}; toy 2019 week 1 threshold {t:g}"


def s8_census_fit():
    """S8, first part (C1): each barangay's rescaled pixels add up to its 2024 census total.

    Counts every barangay's census-fitted residents again, from the WorldPop grid and the
    barangay shapes, with rescale.rescaled_residents (the function C2 uses for the hazard
    levels), and passes when each is within 0.1% (config.S8_CENSUS_TOLERANCE) of its
    pop_2024. That also catches a scale file left over from an older grid or older shapes.
    The scale file must hold one positive factor for each of A5's 142 barangays.
    The second and third parts (exposed residents, C2) are s8_overlay.
    """
    # Files first: without them the check is a SKIP, even where exactextract is not installed.
    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.WORLDPOP_SCALE_QC, "C1 (python -m src.rescale)")

    import geopandas as gpd

    from src import rescale

    brgy = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "pop_2024"])
    scale = pd.read_csv(config.WORLDPOP_SCALE_QC, dtype={"psgc": str})

    assert len(scale) == config.QC_BARANGAYS and scale["psgc"].is_unique, (
        f"scale file has {len(scale)} rows, {scale['psgc'].nunique()} barangays")
    assert set(scale["psgc"]) == set(brgy["psgc"]), "scale file and A5's barangays hold different barangays"
    assert np.isfinite(scale["scale"]).all() and (scale["scale"] > 0).all(), "a scale factor is missing, 0 or negative"

    fitted = rescale.rescaled_residents(brgy)
    gap = (fitted / brgy["pop_2024"] - 1).abs()
    worst = gap.idxmax()
    assert gap[worst] <= config.S8_CENSUS_TOLERANCE, (
        f"{brgy.loc[worst, 'psgc']}: rescaled pixels add up to {fitted[worst]:,.1f}, "
        f"census {brgy.loc[worst, 'pop_2024']:,}")
    return (f"{len(brgy)} barangays, largest gap {gap[worst]:.1e}; "
            f"QC {fitted.sum():,.0f} vs census {brgy['pop_2024'].sum():,}")


def s8_overlay():
    """S8, second and third parts (C2): the overlay table, and the barangays to inspect.

    overlay_qc.csv holds one row for each of the 142 barangays x 3 maps x 3 hazard levels,
    with no missing or negative area or residents. In each map, the residents of the three
    levels never exceed the barangay's 2024 census total (with the first part's 0.1%).
    Then lists the barangays whose exposed residents fall from the 5-year map to the 25-
    or 100-year map, to inspect: NOAH modelled each map separately, so this is not a
    failure (python -m src.overlay prints their numbers).
    """
    # Files first: without them the check is a SKIP, even where exactextract is not installed.
    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.OVERLAY, "C2 (python -m src.overlay)")

    import geopandas as gpd

    from src import overlay

    brgy = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "adm4_name", "pop_2024"])
    table = pd.read_csv(config.OVERLAY, dtype={"psgc": str})

    expected = config.QC_BARANGAYS * len(config.NOAH_RETURN_PERIODS) * len(config.NOAH_HAZARD_LEVELS)
    assert len(table) == expected, f"{len(table)} rows, expected {expected} (barangays x maps x levels)"
    assert not table.duplicated(overlay.KEYS).any(), "a barangay, map and level appears twice"
    assert set(table["psgc"]) == set(brgy["psgc"]), "overlay and A5's barangays hold different barangays"
    assert set(table["return_period"]) == set(config.NOAH_RETURN_PERIODS), "unexpected maps"
    assert set(table["var"]) == set(config.NOAH_HAZARD_LEVELS), "unexpected hazard levels"
    for col in ("area_km2", "residents"):
        assert table[col].notna().all() and (table[col] >= 0).all(), f"missing or negative {col}"

    exposed = overlay.exposed_by_map(table)
    pop = brgy.set_index("psgc")["pop_2024"]
    over = exposed.gt(pop * (1 + config.S8_CENSUS_TOLERANCE), axis=0).any(axis=1)
    assert not over.any(), f"exposed residents exceed the census total in {list(exposed.index[over])}"

    falls = overlay.falls_with_rarer_map(table)
    names = ", ".join(brgy.set_index("psgc").loc[falls.index, "adm4_name"])
    return (f"at most {exposed.div(pop, axis=0).max().max():.1%} of a barangay exposed; "
            f"{len(falls)} barangays fall in a rarer map, inspect: {names}")


def not_built(task):
    """Make a placeholder check for a task that has not been done yet."""
    def check():
        raise NotBuilt(f"needs task {task}")
    return check


CHECKS = {
    "S1 calendar": s1_calendar,
    "S2 rain file": s2_rain_file,
    "S3 census join": s3_census,
    "S4 cases file": not_built("A13"),
    "S5 M4 simulation": not_built("B5"),
    "S6 theta": not_built("B6"),
    "S7 breach": s7_breach,
    "S7 scores": not_built("D1, D3"),
    "S8 census fit": s8_census_fit,
    "S8 overlay": s8_overlay,
    "S9 return levels": not_built("C3"),
    "S10 shares and doses": not_built("C4, C6"),
    "S11 leakage": not_built("B10"),
}


def main():
    """Run every check, print PASS / SKIP / FAIL, and return the exit code."""
    failed = 0
    for name, check in CHECKS.items():
        try:
            detail = check()
            print(f"PASS  {name}" + (f" ({detail})" if detail else ""))
        except NotBuilt as e:
            print(f"SKIP  {name} ({e})")
        except Exception as e:
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

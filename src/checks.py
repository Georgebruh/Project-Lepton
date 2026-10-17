"""Sanity checks S1-S11 (task A2; specs in the plan's "Sanity checks" table).

Also runs two checks with no S number: A11's storm facts and B8's hand check of
M0 and M1.

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
from src import baselines, forecast_range, thresholds, weeks


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


def a11_storms():
    """A11 (no S number): the storm facts in config.STORMS that C8 and C9 read.

    For each storm: flooding starts on or before the day it ends, and D (days flooded) is
    the days from start_date to end_date, both counted. The wettest UTC days lie in the
    storm's year, in order, and hold at least config.RAIN_ACCUM_DAYS days, so C3 and C9
    have a whole n-day total there (A15 fetches the forecasts for those days). The flooded
    barangays are 10-digit QC PSGC codes, none listed twice. Then, with A5's census table:
    every code is one of QC's 142 barangays. A wrong code would quietly lower C8's share of
    flooded barangays that were flagged. Last, with A4's IMERG file: IMERG's wettest n-day
    window ending during the flood (start_date to end_date) ends on one of the wettest days,
    so C8 takes the storm's real peak and A15 fetches the forecasts for it.
    """
    for storm, facts in config.STORMS.items():
        start, end = facts["start_date"], facts["end_date"]
        assert start <= end, f"{storm}: flooding ends ({end}) before it starts ({start})"
        days = (end - start).days + 1
        assert facts["D"] == days, f"{storm}: D = {facts['D']}, but {start} to {end} is {days} days"
        first, last = facts["wettest_days"]
        assert first.year == last.year == facts["year"], f"{storm}: wettest days {first} to {last} not in {facts['year']}"
        assert (last - first).days + 1 >= config.RAIN_ACCUM_DAYS, (
            f"{storm}: wettest days {first} to {last} are fewer than {config.RAIN_ACCUM_DAYS} (config.RAIN_ACCUM_DAYS)")
        codes = facts["flooded_psgc"]
        assert len(codes) == len(set(codes)), f"{storm}: a flooded barangay is listed twice"
        bad = [c for c in codes if not (len(c) == 10 and c.isdigit() and c.startswith(config.QC_PSGC_PREFIX))]
        assert not bad, f"{storm}: not 10-digit QC PSGC codes: {bad}"

    need_file(config.CENSUS_QC, "A5 (python -m src.census)")
    known = set(pd.read_csv(config.CENSUS_QC, dtype={"psgc": str})["psgc"])
    for storm, facts in config.STORMS.items():
        unknown = sorted(set(facts["flooded_psgc"]) - known)
        assert not unknown, f"{storm}: flooded barangays not among A5's {len(known)}: {unknown}"

    need_file(config.IMERG_DAILY, "A4 (python -m src.imerg)")
    from src import flood_exposure as fe

    totals = fe.n_day_totals(fe.catchment_rain(), config.RAIN_ACCUM_DAYS)
    peaks = []
    for storm, facts in config.STORMS.items():
        peak_mm, peak_end = fe.storm_peak(totals, facts["start_date"], facts["end_date"])
        first, last = facts["wettest_days"]
        assert first <= peak_end.date() <= last, (
            f"{storm}: IMERG's wettest {config.RAIN_ACCUM_DAYS}-day window during the flood ends on "
            f"{peak_end:%Y-%m-%d}, outside the wettest days {first} to {last}")
        peaks.append(f"{storm} D = {facts['D']}, {len(facts['flooded_psgc'])} flooded barangays, "
                     f"peak {peak_mm:.0f} mm ending {peak_end:%d %b}")
    return "; ".join(peaks)


def toy_cases(last_year, first_year=config.FIRST_WEEK_START.year):
    """Made-up weekly counts from `first_year` to `last_year` for S7 and B8: 10 x (year - 2014) + week.

    COVID years get 10,000 in every week, so a threshold or M1 that wrongly
    used them would be far off.
    """
    rows = []
    for year in range(first_year, last_year + 1):
        for wk in Year(year).iterweeks():
            count = 10_000 if year in config.COVID_YEARS else 10 * (year - 2014) + wk.week
            rows.append({"week_index": weeks.week_index(wk.startdate()), "year": year,
                         "week": wk.week, "cases": count})
    return pd.DataFrame(rows)


def hide_after(cases, cutoff):
    """Copy of `cases` with every count after week index `cutoff` overwritten, as S11 does (rule 1)."""
    hidden = cases.copy()
    hidden.loc[hidden["week_index"] > cutoff, "cases"] = config.S11_HIDDEN_COUNT
    return hidden


def stops_with(text, func, *args):
    """True when func(*args) stops with a ValueError whose message holds `text`.

    Matching the message makes sure the guard under test fired, not some other error.
    """
    try:
        func(*args)
    except ValueError as e:
        return text in str(e)
    return False


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
    cutoff = weeks.week_index_of(2018, 50)
    t = thresholds.epidemic_threshold(2019, 1, cases, cutoff)
    assert np.isclose(t, 41), f"2019 week 1 threshold is {t}, expected 41"
    hidden = hide_after(cases, cutoff)
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

    assert stops_with("reference years", thresholds.epidemic_threshold, 2017, 1, cases, end_2024), (
        "2017 has only 2 reference years and must stop")
    return f"Pr(Y > 12.4) = {p:.3f}; toy 2019 week 1 threshold {t:g}"


def b8_baselines():
    """B8 (no S number): M0 and M1 on made-up counts, worked by hand.

    toy_cases from 2021 to 2026: 10 x (year - 2014) + week, so 2022 week 10 = 90
    and 2025 week 53 = 163; COVID year 2021 is 10,000 in every week. Each
    forecast is rerun with every count after its cutoff hidden (hide_after, as
    S11 does) and must not change; every cutoff hides some counts. Option B
    cutoffs are the week before the target; the last M1 row is option C, g = 2.
    """
    cases = toy_cases(2026, first_year=2021)
    models = {"M0": baselines.m0_forecast, "M1": baselines.m1_forecast}
    worked = [
        # model, target (year, week), cutoff (year, week), answer by hand
        ("M0", (2022, 10), (2022, 9), 10_000),  # 2021 week 10: COVID years are not skipped
        ("M0", (2025, 10), (2025, 9), 110),     # 2024 week 10 = 100 + 10
        ("M0", (2025, 53), (2025, 52), 111),    # 52 weeks back stays in 2025: week 1
        ("M0", (2026, 1), (2025, 53), 112),     # after a 53-week year: 2025 week 2
        ("M1", (2025, 10), (2025, 9), 100),     # 2022-2024, COVID 2021 skipped: (90 + 100 + 110) / 3
        ("M1", (2025, 53), (2025, 52), 142),    # week 52's counts: (132 + 142 + 152) / 3
        ("M1", (2026, 1), (2025, 53), 96),      # 2022-2025: (81 + 91 + 101 + 111) / 4
        ("M1", (2026, 2), (2025, 52), 92),      # 2025 week 53 hidden, so 2022-2024: (82 + 92 + 102) / 3
    ]
    for name, (year, week), (cut_year, cut_week), answer in worked:
        model = models[name]
        cutoff = weeks.week_index_of(cut_year, cut_week)
        label = f"{name} {year} week {week}, cutoff {cut_year} week {cut_week}"
        got = model(year, week, cases, cutoff)
        assert np.isclose(got, answer), f"{label}: {got}, by hand {answer}"
        assert model(year, week, hide_after(cases, cutoff), cutoff) == got, f"{label}: used a count after the cutoff"
        assert model(float(year), float(week), cases, cutoff) == got, f"{label}: fails on float year and week"

    m0, m1 = baselines.m0_forecast, baselines.m1_forecast
    missing = cases.copy()
    missing.loc[(missing["year"] == 2024) & (missing["week"] == 10), "cases"] = np.nan
    twice = pd.concat([cases, cases[(cases["year"] == 2023) & (cases["week"] == 10)]])
    assert stops_with("after the cutoff", m0, 2025, 10, cases, weeks.week_index_of(2024, 9)), (
        "M0 must stop when 52 weeks back is after the cutoff")
    assert stops_with("missing count", m0, 2025, 10, missing, weeks.week_index_of(2025, 9)), (
        "M0 must stop when the count 52 weeks back is missing")
    assert stops_with("0 rows", m0, 2021, 10, cases, weeks.week_index_of(2021, 9)), (
        "M0 must stop when 52 weeks back is before the data")
    assert stops_with("reference years", m1, 2024, 10, cases, weeks.week_index_of(2024, 9)), (
        "M1 must stop with 2 reference years (2022, 2023; 2021 is COVID)")
    assert stops_with("expected one week-10 count", m1, 2025, 10, twice, weeks.week_index_of(2025, 9)), (
        "M1 must stop when a reference year has two week-10 rows")
    for model in (m0, m1):
        assert stops_with("Week must be in", model, 2026, 53, cases, weeks.week_index_of(2026, 52)), (
            "M0 and M1 must stop on 2026 week 53, which does not exist")
    return f"{len(worked)} forecasts match the hand answers; leaks, gaps, duplicates and bad weeks stop"


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


def toy_overlay():
    """Made-up C2 table for S9: 2 barangays x 3 maps x 3 levels, residents worked by hand.

    Barangay "B" has fewer residents in the 25-year map than in the 5-year one (S8 lists
    real barangays like it), so the interpolation must also work going down.
    """
    pops = {  # (psgc, var): (Pop_5, Pop_25, Pop_100)
        ("A", 1): (100, 200, 400), ("A", 2): (10, 50, 90), ("A", 3): (0, 0, 30),
        ("B", 1): (80, 60, 70), ("B", 2): (0, 20, 20), ("B", 3): (0, 0, 0),
    }
    rows = [{"psgc": b, "var": k, "return_period": t, "residents": float(n)}
            for (b, k), values in pops.items() for t, n in zip(config.NOAH_RETURN_PERIODS, values)]
    return pd.DataFrame(rows)


def s9_return_levels():
    """S9 (C3): Gumbel return levels, the fit, and graded exposure.

    From the plan: a Gumbel curve with mu = 100, beta = 30 has R(5), R(25), R(100) =
    145.0, 196.0, 238.0. Fitting 500 samples of 25 maxima gives a median R(25) of about
    191, with 90% of fits between 164 and 224 (within S9_FIT_TOLERANCE_MM here; the
    random seed moves them a little). Graded exposure on toy_overlay: 0 at or below R0,
    exactly Pop_5 at R(5), Pop_100 above R(100), halfway between Pop_5 and Pop_25 at the
    rain halfway between. Rule 2: the fit for a year uses only years before it, so
    changing that year's maxima or later ones changes nothing; under 10 years stops.
    n-day totals (config.RAIN_ACCUM_DAYS): daily rain 10, 20, 30, 0, 5 gives 3-day totals
    60, 50, 35 on days 3-5; 1 day returns the rain unchanged; a missing day stops.
    """
    from scipy import stats

    from src import flood_exposure as fe

    true = [round(fe.gumbel_level(100, 30, t), 1) for t in config.NOAH_RETURN_PERIODS]
    assert true == [145.0, 196.0, 238.0], f"true R(5), R(25), R(100) = {true}"

    rng = np.random.default_rng(config.RANDOM_SEED)
    fitted = []
    for _ in range(config.S9_SAMPLES):
        sample = stats.gumbel_r.rvs(loc=100, scale=30, size=config.S9_SAMPLE_YEARS, random_state=rng)
        mu, beta = fe.fit_gumbel(sample)
        fitted.append(fe.gumbel_level(mu, beta, 25))
    median, low, high = np.median(fitted), *np.percentile(fitted, [5, 95])
    tol = config.S9_FIT_TOLERANCE_MM
    assert abs(median - 191) <= tol, f"median fitted R(25) = {median:.1f}, expected about 191"
    assert abs(low - 164) <= tol and abs(high - 224) <= tol, f"90% of fits in {low:.0f}-{high:.0f}, expected 164-224"

    levels = {"r0": 50.0, 5: 100.0, 25: 150.0, 100: 200.0}
    overlay = toy_overlay()
    pops = fe.map_table(overlay)

    def exposure(rain):
        table = fe.graded_exposure(rain, levels, overlay)
        assert list(table.columns) == ["psgc", "var", "residents"], f"columns {list(table.columns)} (C5 takes psgc, var, residents)"
        return table.set_index(["psgc", "var"])["residents"]

    assert (exposure(50.0) == 0).all() and (exposure(10.0) == 0).all(), "exposure at or below R0 must be 0"
    assert np.allclose(exposure(75.0), pops[5] / 2), "halfway between R0 and R(5) must be half of Pop_5"
    assert np.allclose(exposure(100.0), pops[5]), "exposure at R(5) must be Pop_5 exactly"
    assert np.allclose(exposure(125.0), (pops[5] + pops[25]) / 2), "halfway between R(5) and R(25) must be halfway"
    assert np.allclose(exposure(200.0), pops[100]) and np.allclose(exposure(500.0), pops[100]), (
        "exposure at and above R(100) must be Pop_100")
    totals = fe.map_totals(overlay)
    assert np.isclose(fe.exposed_total(125.0, levels, totals), exposure(125.0).sum()), "city total != sum of barangays"

    maxima = pd.Series(stats.gumbel_r.rvs(loc=100, scale=30, size=20, random_state=rng), index=range(2000, 2020))
    before = fe.return_levels(maxima, 2015)
    changed = maxima.copy()
    changed[changed.index >= 2015] = 999.0
    assert fe.return_levels(changed, 2015) == before, "the 2015 fit used 2015 or a later year (rule 2)"
    assert before["n_years"] == 15, f"the 2015 fit used {before['n_years']} years, expected 2000-2014"
    assert stops_with("at least", fe.return_levels, maxima, 2009), "a fit on 9 years must stop"

    daily = pd.Series([10.0, 20.0, 30.0, 0.0, 5.0], index=pd.date_range("2024-07-21", periods=5, freq="D"))
    three = fe.n_day_totals(daily, 3)
    assert three.tolist() == [60.0, 50.0, 35.0], f"3-day totals {three.tolist()}, by hand 60, 50, 35"
    assert three.index[0] == pd.Timestamp("2024-07-23"), "a total must be labelled with its last day"
    assert fe.n_day_totals(daily, 1).equals(daily), "1-day totals must be the daily rain unchanged"
    assert stops_with("every day", fe.n_day_totals, daily.drop(daily.index[2]), 3), "a missing day must stop"
    return (f"median fitted R(25) {median:.1f}, 90% of fits {low:.0f}-{high:.0f}; toy exposure and "
            f"n-day totals match by hand")


def s9_exposure_index():
    """S9, real data (C3): ei_weekly.csv.

    Made with config.RAIN_ACCUM_DAYS (the rain_days column), so a file from an older run
    or another n is caught. One row per fit year and week, every fit year from
    BACKTEST_FIRST_YEAR to BACKTEST_LAST_YEAR, weeks from 2015 week 1 with no gap; EI
    between 0 and 100, never missing; the wettest week of each fit year has the highest
    EI or ties it (EI only grows with rain).
    """
    need_file(config.EI_WEEKLY, "C3 (python -m src.flood_exposure)")
    ei = pd.read_csv(config.EI_WEEKLY)
    assert "rain_days" in ei.columns, "ei_weekly.csv has no rain_days column: rerun python -m src.flood_exposure"
    made_with = sorted(ei["rain_days"].unique())
    assert made_with == [config.RAIN_ACCUM_DAYS], (
        f"ei_weekly.csv was made with {made_with}-day totals, config says {config.RAIN_ACCUM_DAYS}: rerun C3")
    fit_years = list(range(config.BACKTEST_FIRST_YEAR, config.BACKTEST_LAST_YEAR + 1))
    assert sorted(ei["fit_year"].unique()) == fit_years, f"fit years {sorted(ei['fit_year'].unique())}"
    assert not ei.duplicated(["fit_year", "week_index"]).any(), "a fit year and week appear twice"
    assert ei[["rmax_mm", "ei"]].notna().all().all(), "missing rain or EI"
    assert ei["ei"].between(0, 100).all(), f"EI outside 0-100: {ei['ei'].min()} to {ei['ei'].max()}"
    for year, rows in ei.groupby("fit_year"):
        index = rows["week_index"].to_numpy()
        assert index[0] == 0 and (np.diff(index) == 1).all(), f"fit {year}: weeks do not run from 0 without a gap"
        assert rows.loc[rows["rmax_mm"].idxmax(), "ei"] == rows["ei"].max(), f"fit {year}: EI does not grow with rain"
    last = ei[ei["fit_year"] == config.BACKTEST_LAST_YEAR]
    return (f"{config.RAIN_ACCUM_DAYS}-day totals; {len(fit_years)} fit years x {len(last)} weeks; "
            f"EI above 0 in {(last['ei'] > 0).mean():.1%} "
            f"of weeks, highest {last['ei'].max():.1f}% ({config.BACKTEST_LAST_YEAR} fit)")


def s10_shares():
    """S10, first part (C4): child, pregnant and adult shares.

    First a made-up city whose answers are worked out by hand, which tests the formulas
    themselves. Then shares_qc.csv: one row for each of A5's 142 barangays; no share
    missing or negative; the three shares add to 1 in every barangay; the pregnant counts
    add up to QC's (A12's births x 0.75), which stay below the 3.5% upper bound; and the
    file matches a fresh run of src.shares, which catches a file left over from older
    inputs. The upper-bound test (3.5% of QC pregnant) must give shares that add to 1,
    none negative, too.
    The second part (doses and allocate) is C6 and C7.
    """
    from src import shares

    # Made-up city of two barangays, worked by hand, with 100 pregnant women in all.
    # a: 1,000 people in 2020, 300 under 18, 250 women 15-49 of whom 25 are 15-17; 1,250 in 2024.
    # b: 2,000 people in 2020, 500 under 18, 750 women 15-49 of whom 50 are 15-17; 2,500 in 2024.
    #   a: preg = 100 x 250/1000 = 25, s_preg = 25/1250 = 0.02, s_child = 300/1000 - 0.02 x 25/250 = 0.298
    #   b: preg = 100 x 750/1000 = 75, s_preg = 75/2500 = 0.03, s_child = 500/2000 - 0.03 x 50/750 = 0.248
    toy = pd.DataFrame({"pop_2020": [1000, 2000], "pop_2024": [1250, 2500], "children": [300, 500],
                        "women_15_49": [250, 750], "women_15_17": [25, 50]}, index=["a", "b"])
    got = shares.group_shares(toy, 100)
    for col, expected in (("preg", [25, 75]), ("s_preg", [0.02, 0.03]),
                          ("s_child", [0.298, 0.248]), ("s_adult", [0.682, 0.722])):
        assert np.allclose(got[col], expected), f"made-up city: {col} = {list(got[col])}, expected {expected}"

    need_file(config.CENSUS_QC, "A5 (python -m src.census)")
    need_file(config.BIRTHS_2024, "A12 (copy psa_births_2024.csv from the team drive)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    table = pd.read_csv(config.SHARES_QC, dtype={"psgc": str}).set_index("psgc")
    counts = shares.barangay_counts()

    assert len(table) == config.QC_BARANGAYS and table.index.is_unique, (
        f"shares file has {len(table)} rows, {table.index.nunique()} barangays")
    assert set(table.index) == set(counts.index), "shares file and A5's barangays hold different barangays"
    preg_qc = shares.pregnant_from_births(shares.qc_births())
    upper_qc = shares.upper_bound_pregnant(counts)
    assert preg_qc < upper_qc, f"{preg_qc:,.0f} pregnant women is above the 3.5% upper bound ({upper_qc:,.0f})"
    upper = shares.group_shares(counts, upper_qc)
    for label, t in (("shares file", table), ("upper bound", upper)):
        s = t[shares.SHARES]
        assert s.notna().all().all(), f"{label}: a share is missing"
        assert (s >= 0).all().all(), f"{label}: negative share in {list(s.index[(s < 0).any(axis=1)])}"
        off = (s.sum(axis=1) - 1).abs()
        assert off.max() <= config.S10_SHARE_TOLERANCE, f"{label}: shares add to {s.sum(axis=1)[off.idxmax()]} in {off.idxmax()}"
    assert np.isclose(table["preg"].sum(), preg_qc), f"pregnant counts add up to {table['preg'].sum():,.1f}, QC has {preg_qc:,.1f}"

    fresh = shares.group_shares(counts, preg_qc).loc[table.index]
    cols = ["pop_2020", "pop_2024", "children", "women_15_49", "women_15_17", "preg", *shares.SHARES]
    assert np.allclose(table[cols], fresh[cols]), "shares file differs from a fresh run: rerun python -m src.shares"
    return (f"QC child {(table['s_child'] * table['pop_2024']).sum() / table['pop_2024'].sum():.1%}, "
            f"pregnant {preg_qc:,.0f}, smallest adult share {table['s_adult'].min():.3f} "
            f"({upper['s_adult'].min():.3f} at the 3.5% upper bound)")


def s10_exposed():
    """S10, C5 part: exposed people per group, and the adult risk tiers.

    First a made-up city whose answers are worked out by hand, with q and r_k away from 1
    so both are tested. Then S10's dose input, 100 exposed adults with w = 0.5, split into
    tiers at D = 1, 3 and 10 (C6 turns them into 600, 200 and 400 capsules), plus the
    bounds of w and the 1- and 3-day cut-off tests. Input that would give wrong counts
    without an error must stop the run (rule 5): a barangay missing, or two maps' rows
    passed together. Then the real tables, at each map's own rain (C2's map x C4's
    shares): one row per barangay, nothing missing or negative; with q = r_k = 1 everyone
    exposed equals the map's residents; the groups add up to everyone exposed; and the
    tiers add up to the exposed adults in every preview scenario.
    """
    from src import exposed

    # Made-up city of two barangays, q = 0.5, r_k = 0.5 at level 1 and 1 at levels 2 and 3.
    # a: N = 100, 200, 300 -> 0.5 x (0.5 x 100 + 200 + 300) = 275; shares 0.30 / 0.02 / 0.68 -> 82.5, 5.5, 187
    # b: N =   0,  50,   0 -> 0.5 x 50 = 25;                       shares 0.25 / 0.03 / 0.72 -> 6.25, 0.75, 18
    toy_shares = pd.DataFrame({"s_child": [0.30, 0.25], "s_preg": [0.02, 0.03], "s_adult": [0.68, 0.72]},
                              index=pd.Index(["a", "b"], name="psgc"))
    toy = pd.DataFrame({"psgc": ["a"] * 3 + ["b"] * 3, "var": [1, 2, 3] * 2,
                        "residents": [100, 200, 300, 0, 50, 0]})
    got = exposed.exposed_people(toy, toy_shares, q=0.5, contact={1: 0.5, 2: 1.0, 3: 1.0})
    for col, expected in (("exposed", [275, 25]), ("e_child", [82.5, 6.25]),
                          ("e_preg", [5.5, 0.75]), ("e_adult", [187, 18])):
        assert np.allclose(got[col], expected), f"made-up city: {col} = {list(got[col])}, expected {expected}"

    # S10's input: 100 exposed adults. (D, cut-off, w) -> (high, moderate, low)
    adults = pd.Series([100.0])
    for days, cutoff, w, expected in (
        (1, 2, 0.5, (0, 50, 50)),     # short flood, split by w; C6: 2 x 50 + 10 x 50 = 600 capsules
        (3, 2, 0.5, (100, 0, 0)),     # 2 days or more, all high; C6: 2 x ceil(3/7) x 100 = 200
        (10, 2, 0.5, (100, 0, 0)),    # C6: 2 x ceil(10/7) x 100 = 400
        (1, 2, 0.0, (0, 0, 100)),     # the bounds of w
        (1, 2, 1.0, (0, 100, 0)),
        (2, 3, 0.5, (0, 50, 50)),     # cut-off tests (C8): 2 days is short under a 3-day cut-off
        (1, 1, 0.5, (100, 0, 0)),     # and every flood is long under a 1-day cut-off
    ):
        tiers = tuple(exposed.adult_tiers(adults, days, w, cutoff).iloc[0][exposed.TIERS])
        assert np.allclose(tiers, expected), (
            f"D = {days}, cut-off {cutoff}, w = {w}: (high, moderate, low) = {tiers}, expected {expected}")

    for label, bad in (("barangay b missing", toy[toy["psgc"] == "a"]), ("two maps mixed", pd.concat([toy, toy]))):
        try:
            exposed.exposed_people(bad, toy_shares)
        except ValueError:
            continue
        raise AssertionError(f"{label}: exposed_people did not stop")

    need_file(config.OVERLAY, "C2 (python -m src.overlay)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    table = exposed.load_shares()
    full_contact = {k: 1.0 for k in config.NOAH_HAZARD_LEVELS}
    parts = []
    for period in config.NOAH_RETURN_PERIODS:
        residents = exposed.map_residents(overlay, period)
        people = exposed.exposed_people(residents, table)
        assert len(people) == config.QC_BARANGAYS, f"{period}-year map: {len(people)} barangays"
        assert people.notna().all().all() and (people >= 0).all().all(), f"{period}-year map: missing or negative counts"
        flooded = residents.groupby("psgc")["residents"].sum().loc[people.index]
        everyone = exposed.exposed_people(residents, table, q=1.0, contact=full_contact)["exposed"]
        assert np.allclose(everyone, flooded), f"{period}-year map: with q = r_k = 1, exposed differs from the map's residents"
        assert np.allclose(people[list(exposed.GROUPS)].sum(axis=1), people["exposed"]), (
            f"{period}-year map: the groups do not add up to everyone exposed")
        for label, days, w in exposed.scenarios():
            tiers = exposed.adult_tiers(people["e_adult"], days, w)
            assert np.allclose(tiers.sum(axis=1), people["e_adult"]), f"{period}-year map, {label}: tiers do not add up"
        parts.append(f"R({period}) {people['exposed'].sum():,.0f}")
    return f"QC exposed at {', '.join(parts)}; groups and tiers add up"


def s10_doses():
    """S10, C6 part: drug units per barangay.

    S10's input, 100 exposed adults with w = 0.5 and u = 1, split into tiers by C5 and
    turned into capsules: 600 at D = 1 (50 moderate x 10 + 50 low x 2), 200 at D = 3
    (100 high x 2 x 1 week) and 400 at D = 10 (2 weeks). Then made-up children and
    pregnant women worked by hand: 10 children need 10 courses at D = 1 and at D = 7, 20 at
    D = 8 (a part week counts whole) and 30 at D = 15; 5 pregnant women need 30 tablets;
    u = 0.5 halves every figure. Input that would give wrong stock without an error must
    stop the run (rule 5): u above 1, a missing count. Then the real tables at each map's
    own rain, in every preview flood: one row per barangay, no unit missing or negative,
    and the doxycycline tiers add up to the total.
    The allocation part (allocate) is C7.
    """
    from src import doses, exposed

    def made_up(adults=0, children=0, pregnant=0, days=1):
        """One made-up barangay's C5 table, with S10's w = 0.5 and the plan's 2-day cut-off."""
        tiers = exposed.adult_tiers(pd.Series([float(adults)]), days, w=0.5, cutoff=2)
        return tiers.assign(e_child=float(children), e_preg=float(pregnant))

    for days, expected in ((1, 600), (3, 200), (10, 400)):
        got = doses.doses(made_up(adults=100, days=days), days, u=1.0)["doxy100"].iloc[0]
        assert np.isclose(got, expected), f"100 adults, D = {days}: {got} capsules, expected {expected}"
    for days, expected in ((1, 10), (7, 10), (8, 20), (15, 30)):
        got = doses.doses(made_up(children=10, days=days), days, u=1.0)["courses"].iloc[0]
        assert np.isclose(got, expected), f"10 children, D = {days}: {got} courses, expected {expected}"
    got = doses.doses(made_up(pregnant=5), 1, u=1.0)["amox500"].iloc[0]
    assert np.isclose(got, 30), f"5 pregnant women: {got} tablets, expected 30"
    half = doses.doses(made_up(adults=100, children=10, pregnant=5), 1, u=0.5).iloc[0]
    for col, expected in (("doxy100", 300), ("courses", 5), ("amox500", 15)):
        assert np.isclose(half[col], expected), f"u = 0.5: {col} = {half[col]}, expected {expected}"

    for label, call in (("u = 1.5", lambda: doses.doses(made_up(adults=100), 1, u=1.5)),
                        ("a missing count", lambda: doses.doses(made_up(adults=100).assign(e_child=np.nan), 1))):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError(f"{label}: doses did not stop")

    need_file(config.OVERLAY, "C2 (python -m src.overlay)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    table = exposed.load_shares()
    shown = []
    for period in config.NOAH_RETURN_PERIODS:
        residents = exposed.map_residents(overlay, period)
        for label, days, w in exposed.scenarios():
            stock = doses.barangay_doses(residents, table, days, w)
            units = stock[[*doses.DOXY_BY_TIER, *doses.UNITS]]
            assert len(stock) == config.QC_BARANGAYS, f"R({period}), {label}: {len(stock)} barangays"
            assert units.notna().all().all() and (units >= 0).all().all(), f"R({period}), {label}: missing or negative units"
            assert np.allclose(stock[doses.DOXY_BY_TIER].sum(axis=1), stock["doxy100"]), (
                f"R({period}), {label}: the doxycycline tiers do not add up to the total")
            if period == exposed.PREVIEW_MAP:
                shown.append(f"{label}: {stock['doxy100'].sum():,.0f}")
    return (f"QC doxycycline capsules at R({exposed.PREVIEW_MAP}), {'; '.join(shown)} "
            f"(stock planning, not prescriptions)")


def s10_allocate():
    """S10, C7 part: allocate, and how the barangays' need reaches the health centers.

    S10's input: need high [100, 50], moderate [40, 60], low [20, 0] with stock 180 must
    give high 100 and 50 (in full), moderate 12 and 18 (the 30 left, shared 40 : 60), low
    0, total 180. Also: with stock for everyone, each center gets exactly its need; with
    none, nobody gets anything; negative stock or a missing need stops the run (rule 5).
    Then center_shares_qc.csv: every barangay sends need, its shares add to 1; every center
    named can be placed; a barangay with its own centers sends need only to them, one
    without to a single nearest center; and the file matches a fresh run (which catches
    a file left over from older inputs). Last, at R(25) in every preview flood, the
    health centers' need adds up to the barangays' need, pool by pool and tier by tier.
    """
    from src import allocation, doses, exposed

    need = pd.DataFrame({"high": [100, 50], "moderate": [40, 60], "low": [20, 0]}, index=["a", "b"])
    for stock, expected in ((180, [[100, 12, 0], [50, 18, 0]]),   # S10
                            (1000, need.to_numpy()),               # enough for everyone: exactly the need
                            (0, [[0, 0, 0], [0, 0, 0]]),
                            (120, [[80, 0, 0], [40, 0, 0]])):      # short in the high tier: shared 100 : 50
        got = allocation.allocate(need, stock)
        assert np.allclose(got.to_numpy(), expected), f"stock {stock}: got {got.to_numpy().tolist()}, expected {np.asarray(expected).tolist()}"
    for label, call in (("negative stock", lambda: allocation.allocate(need, -1)),
                        ("a missing need", lambda: allocation.allocate(need.astype(float).where(need > 0), 10))):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError(f"{label}: allocate did not stop")

    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.FACILITIES_QC, "A10 (python -m src.facilities)")
    need_file(config.WORLDPOP_SCALE_QC, "C1 (python -m src.rescale)")
    need_file(config.CENTER_SHARES, "C7 (python -m src.allocation)")
    table = allocation.load_center_shares()
    barangays = allocation.load_barangays()
    centers, _ = allocation.load_centers(barangays)

    assert set(table["psgc"]) == set(barangays["psgc"]), "the shares file and A5's barangays hold different barangays"
    assert not table.duplicated(["psgc", "facility_code"]).any(), "a barangay and health center appear twice"
    total = table.groupby("psgc")["share"].sum()
    assert np.allclose(total, 1), f"shares do not add to 1 in {list(total.index[~np.isclose(total, 1)])}"
    assert (table["share"] > 0).all(), "a share is 0 or negative"
    assert set(table["facility_code"]) <= set(centers["facility_code"]), "a health center in the file cannot be placed"
    home = centers.groupby("psgc")["facility_code"].apply(set)
    centroid = barangays.set_index("psgc").geometry.centroid
    for psgc, rows in table.groupby("psgc"):
        if psgc in home.index:
            assert set(rows["facility_code"]) == home[psgc], f"{psgc} does not send its need to its own health centers"
        else:
            assert len(rows) == 1 and (rows["rule"] == "nearest").all(), f"{psgc} has no center but is not sent to one nearest"
            distance = centers.set_index("facility_code").distance(centroid[psgc])
            assert np.isclose(distance[rows["facility_code"].iloc[0]], distance.min()), f"{psgc} is not sent to its nearest center"
    fresh = allocation.center_shares(barangays, centers)
    keys = ["psgc", "facility_code"]
    merged = table.merge(fresh, on=keys, how="outer", suffixes=("", "_fresh"), indicator=True)
    assert (merged["_merge"] == "both").all() and np.allclose(merged["share"], merged["share_fresh"]), (
        "shares file differs from a fresh run: rerun python -m src.allocation")

    need_file(config.OVERLAY, "C2 (python -m src.overlay)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    residents = exposed.map_residents(pd.read_csv(config.OVERLAY, dtype={"psgc": str}), exposed.PREVIEW_MAP)
    group_shares = exposed.load_shares()
    for label, days, w in exposed.scenarios():
        stock = doses.barangay_doses(residents, group_shares, days, w)
        by_barangay = allocation.pool_needs(stock, days, w)
        by_center = allocation.center_needs(residents, group_shares, table, days, w)
        for pool in allocation.POOLS:
            assert np.allclose(by_center[pool].sum(), by_barangay[pool].sum()), (
                f"R({exposed.PREVIEW_MAP}), {label}, {pool}: the health centers' need does not add up to the barangays'")
            assert np.isclose(by_barangay[pool].to_numpy().sum(), stock[pool].sum()), f"{label}, {pool}: tiers do not add up"
    rules = table.drop_duplicates("psgc")["rule"].value_counts()
    return (f"{table['facility_code'].nunique()} health centers; barangays own {rules.get('own', 0)}, "
            f"split {rules.get('split', 0)}, nearest {rules.get('nearest', 0)} "
            f"(farthest {table['distance_km'].max():.2f} km); need adds up")


def not_built(task):
    """Make a placeholder check for a task that has not been done yet."""
    def check():
        raise NotBuilt(f"needs task {task}")
    return check


CHECKS = {
    "S1 calendar": s1_calendar,
    "S2 rain file": s2_rain_file,
    "S3 census join": s3_census,
    "A11 storm facts": a11_storms,
    "S4 cases file": not_built("A13"),
    "S5 M4 simulation": not_built("B5"),
    "S6 theta": not_built("B6"),
    "S7 breach": s7_breach,
    "S7 scores": not_built("D1, D3"),
    "B8 M0 and M1": b8_baselines,
    "S8 census fit": s8_census_fit,
    "S8 overlay": s8_overlay,
    "S9 return levels": s9_return_levels,
    "S9 exposure index": s9_exposure_index,
    "S10 shares": s10_shares,
    "S10 exposed": s10_exposed,
    "S10 doses": s10_doses,
    "S10 allocate": s10_allocate,
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

"""Sanity checks S1-S11 (task A2; specs in the plan's "Sanity checks" table).

Also runs B8's hand check of M0 and M1, which has no S number.

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


def s10_shares():
    """S10, first part (C4): child, pregnant and adult shares.

    First a made-up city whose answers are worked out by hand, which tests the formulas
    themselves. Then shares_qc.csv: one row for each of A5's 142 barangays; no share
    missing or negative; the three shares add to 1 in every barangay; the pregnant counts
    add up to QC's (A12's births x 0.75); and the file matches a fresh run of src.shares,
    which catches a file left over from older inputs. The upper-bound test (3.5% of QC
    pregnant) must give shares that add to 1, none negative, too.
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
    upper = shares.group_shares(counts, shares.upper_bound_pregnant(counts))
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
    "B8 M0 and M1": b8_baselines,
    "S8 census fit": s8_census_fit,
    "S8 overlay": s8_overlay,
    "S9 return levels": not_built("C3"),
    "S10 shares": s10_shares,
    "S10 doses": not_built("C6, C7"),
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

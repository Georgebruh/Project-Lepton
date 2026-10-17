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
from src import weeks


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


def s8_census_fit():
    """S8, first part (C1): each barangay's rescaled pixels add up to its 2024 census total.

    Counts every barangay's census-fitted residents again, from the WorldPop grid and the
    barangay shapes, with rescale.rescaled_residents (the function C2 uses for the hazard
    levels), and passes when each is within 0.1% (config.S8_CENSUS_TOLERANCE) of its
    pop_2024. That also catches a scale file left over from an older grid or older shapes.
    The scale file must hold one positive factor for each of A5's 142 barangays.
    The second and third parts (exposed residents, C2) are s8_overlay.
    """
    import geopandas as gpd

    from src import rescale

    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.WORLDPOP_SCALE_QC, "C1 (python -m src.rescale)")
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
    import geopandas as gpd

    from src import overlay

    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.OVERLAY, "C2 (python -m src.overlay)")
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
    "S7 breach and scores": not_built("B7"),
    "S8 census fit": s8_census_fit,
    "S8 overlay": s8_overlay,
    "S9 return levels": not_built("C3"),
    "S10 shares": s10_shares,
    "S10 exposed": s10_exposed,
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

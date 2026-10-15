"""Sanity checks S1-S11 (task A2; specs in the plan's "Sanity checks" table).

Run from the repository root:  python -m src.checks
A check that is not built yet is reported as SKIP. Any FAIL stops work:
the script exits with code 1.
"""

import sys
from datetime import date

from epiweeks import Week, Year

import config


class NotBuilt(Exception):
    """Raised by a check whose task has not been done yet."""


def s1_calendar():
    """S1 (A3): CDC/MMWR weeks.

    9 Aug 2026 is 2026 week 32 (9-15 Aug); 2020 and 2025 have 53 weeks;
    2015 week 1 starts 4 Jan 2015.
    """
    wk = Week.fromdate(date(2026, 8, 9))
    assert (wk.year, wk.week) == (2026, 32), f"got {wk}"
    assert wk.startdate() == date(2026, 8, 9), wk.startdate()
    assert wk.enddate() == date(2026, 8, 15), wk.enddate()
    for year in (2020, 2025):
        assert Year(year).totalweeks() == 53, f"{year} has {Year(year).totalweeks()} weeks"
    assert Week(2015, 1).startdate() == config.FIRST_WEEK_START


def s3_census():
    """S3 (A5): boundaries, 2024 totals and 2020 age tables joined on PSGC.

    142 QC barangays, each code once, matched in all three sources (a shape, a
    2020 total and a 2024 total); barangay totals add up to QC's 2020 and 2024
    census totals; the 2020 single ages add up to each barangay's 2020 total.
    """
    import geopandas as gpd
    import pandas as pd

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


def not_built(task):
    """Make a placeholder check for a task that has not been done yet."""
    def check():
        raise NotBuilt(f"needs task {task}")
    return check


CHECKS = {
    "S1 calendar": s1_calendar,
    "S2 rain file": not_built("A4"),
    "S3 census join": s3_census,
    "S4 cases file": not_built("A13"),
    "S5 M4 simulation": not_built("B5"),
    "S6 theta": not_built("B6"),
    "S7 breach and scores": not_built("B7"),
    "S8 overlay": not_built("C1, C2"),
    "S9 return levels": not_built("C3"),
    "S10 shares and doses": not_built("C4, C6"),
    "S11 leakage": not_built("B10"),
}


def main():
    """Run every check, print PASS / SKIP / FAIL, and return the exit code."""
    failed = 0
    for name, check in CHECKS.items():
        try:
            check()
            print(f"PASS  {name}")
        except NotBuilt as e:
            print(f"SKIP  {name} ({e})")
        except Exception as e:
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

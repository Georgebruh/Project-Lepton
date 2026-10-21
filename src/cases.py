"""Quezon City weekly cases from QCESD's case list (task A13).

QCESD sent a case list (config.QCESD_CASES_RAW; note in data/raw/qcesd.md): one sheet per
year, 2015 to October 2026, one row per case, with the date of onset, a morbidity week, the
date of admission, the district and the barangay. It holds no names, but it is a case-level
record: it stays in data/raw/qcesd/ (kept out of git) and is never committed or shared
(rule 11). The adviser approved aggregating it to weekly counts (E2). This script reads
only the two dates and writes the weekly table the models read:

    week_index, year, week, cases      (config.CASES_WEEKLY)

Decision-tree row (A13, 2026-10-20): the list has onset dates but no report dates, so the
row is "QC weekly counts by onset week": option C, the delay guard g = 2
(config.DATA_OPTION). Admission dates are not report dates (the health office learns of
a case after admission), so option B does not apply.

A case's week is the MMWR week holding its date of onset (A3). The file's own
Morbidity_week column is not used, because its meaning changes from year to year (checked
2026-10-20 on all 4,953 rows): it is the onset week in 2024-2026, the admission week in
2018, 2020, 2022 and 2023, and the month of admission (1-12) in 2015-2017, 2019 and 2021.

Every row counts as one case, as given:
  - 136 rows repeat another row in all six columns. They are kept: with them the list
    gives QCESD's published 2025 totals (check S4), so they are separate cases.
  - 27 cases were admitted before their onset or over 30 days after it, likely a typo in
    one of the dates (often day and month swapped). Their onset is kept as given; main()
    prints how many.

Zero or missing (check S4): the list covers every week from 2015 week 1, so a week with no
case in it has 0 cases. Its last weeks are still filling in, because cases reach hospital
days after onset. So a week is final only once config.CASES_COMPLETE_DAYS (17) days have
passed between its last day and the data date, the latest date in the list: 99% of cases
were admitted within 17 days of onset. The weeks after it, up to the week of the data date,
are rows with a missing count, never 0.

Run from the repository root:  python -m src.cases
Check: python -m src.checks (S4 cases file).
"""

import warnings
from datetime import timedelta

import numpy as np
import pandas as pd

import config
from src import view, weeks


def read_case_list(path=config.QCESD_CASES_RAW):
    """The onset and admission date of every case, from every sheet of QCESD's file.

    Returns one row per case with two columns, onset and admission (a missing admission
    stays NaT). Stops on a sheet whose columns differ from config.QCESD_COLUMNS, or on a
    case without a date of onset.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: copy QCESD's case list from the team drive (data/raw/qcesd.md)")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Unknown extension")   # openpyxl, about Excel formatting only
        sheets = pd.read_excel(path, sheet_name=None)
    parts = []
    for name, sheet in sheets.items():
        if list(sheet.columns) != list(config.QCESD_COLUMNS):
            raise ValueError(f"sheet {name!r} has columns {list(sheet.columns)}, expected {list(config.QCESD_COLUMNS)}")
        parts.append(sheet[[config.QCESD_ONSET, config.QCESD_ADMISSION]])
    table = pd.concat(parts, ignore_index=True)
    cases = pd.DataFrame({"onset": pd.to_datetime(table[config.QCESD_ONSET], errors="coerce"),
                          "admission": pd.to_datetime(table[config.QCESD_ADMISSION], errors="coerce")})
    if cases["onset"].isna().any():
        raise ValueError(f"{cases['onset'].isna().sum()} cases have no date of onset (or one that is not a date)")
    return cases


def data_date(cases):
    """The latest date of onset or admission in the list: the list holds no case after it."""
    return max(cases["onset"].max(), cases["admission"].max()).date()


def delay_days(cases):
    """Days from onset to admission for each case; NaN where the admission date is missing."""
    return (cases["admission"] - cases["onset"]).dt.days


def onset_weeks(cases):
    """Continuous week index (A3) of the MMWR week holding each case's onset."""
    return cases["onset"].map(lambda day: weeks.week_index(day.date()))


def last_complete_week(as_of):
    """Week index of the last week whose count is final on day `as_of`.

    In plain words: the last week that ended at least config.CASES_COMPLETE_DAYS days
    before `as_of`. With the list's data date 18 Oct 2026, that is the week ending 26 Sep
    (2026 week 38): 26 Sep + 17 days = 13 Oct, while week 39 ends 3 Oct + 17 = 20 Oct.
    """
    latest_end = as_of - timedelta(days=config.CASES_COMPLETE_DAYS)
    index = weeks.week_index(latest_end)
    if weeks.week_start(index) + timedelta(days=6) > latest_end:   # that week ends after latest_end
        index -= 1
    return index


def weekly_counts(cases):
    """One row per MMWR week (week_index, year, week, cases), 2015 week 1 to the week of the data date.

    cases = the number of cases whose onset falls in that week, 0 if none, and missing
    after the last complete week (last_complete_week). Stops on an onset before 2015 week 1.
    """
    index = onset_weeks(cases)
    if (index < 0).any():
        raise ValueError(f"{(index < 0).sum()} cases have their onset before 2015 week 1 ({config.FIRST_WEEK_START})")
    as_of = data_date(cases)
    counts = index.value_counts().reindex(range(weeks.week_index(as_of) + 1), fill_value=0).sort_index()
    year_week = [weeks.year_week(i) for i in counts.index]
    table = pd.DataFrame({"week_index": counts.index, "year": [yw[0] for yw in year_week],
                          "week": [yw[1] for yw in year_week], "cases": counts.to_numpy(dtype=float)})
    table.loc[table["week_index"] > last_complete_week(as_of), "cases"] = np.nan
    return table[view.COLUMNS]


def published_totals(cases):
    """Each of QCESD's published totals (config.CASES_PUBLISHED) beside the list's count of the same days.

    The list is counted by onset date (as the weekly table is) and, for comparison, by
    admission date. One row per published total.
    """
    rows = []
    for pub in config.CASES_PUBLISHED:
        start, end = pd.Timestamp(pub["start"]), pd.Timestamp(pub["end"])
        rows.append({"start": pub["start"], "end": pub["end"], "published": pub["cases"],
                     "by_onset": int(cases["onset"].between(start, end).sum()),
                     "by_admission": int(cases["admission"].between(start, end).sum())})
    table = pd.DataFrame(rows)
    table["gap"] = table["by_onset"] / table["published"] - 1
    return table


def main():
    """Build the weekly table, save it and print what to look at. Prints totals only, never a case."""
    cases = read_case_list()
    table = weekly_counts(cases)
    config.CASES_WEEKLY.parent.mkdir(parents=True, exist_ok=True)
    table.astype({"cases": "Int64"}).to_csv(config.CASES_WEEKLY, index=False)   # whole numbers; missing stays empty

    as_of = data_date(cases)
    complete = last_complete_week(as_of)
    missing = table[table["cases"].isna()]
    print(f"{len(cases):,} cases, onset {cases['onset'].min():%Y-%m-%d} to {cases['onset'].max():%Y-%m-%d}; "
          f"data date {as_of} (latest onset or admission)")
    print(f"Saved {config.CASES_WEEKLY} ({len(table)} weeks): final to {weeks.year_week(complete)} (year, week); "
          f"{len(missing)} later weeks missing, {weeks.year_week(missing['week_index'].min())} to "
          f"{weeks.year_week(missing['week_index'].max())}, holding {onset_weeks(cases).gt(complete).sum()} cases so far")
    print(f"Decision tree: onset weeks, no report dates -> option {config.DATA_OPTION}, g = {config.DELAY_GUARD_G}")

    delay = delay_days(cases).dropna()
    odd = ((delay < 0) | (delay > config.CASES_DELAY_FLAG_DAYS)).sum()
    print(f"\nOnset to admission ({len(delay):,} cases with both dates): median {delay.median():.0f} days, "
          f"95% within {delay.quantile(0.95):.0f}, 99% within {delay.quantile(0.99):.0f}; "
          f"{(delay <= config.CASES_COMPLETE_DAYS).mean():.1%} within config.CASES_COMPLETE_DAYS = {config.CASES_COMPLETE_DAYS}")
    print(f"Likely date typos, kept as given: {odd} cases admitted before onset or over {config.CASES_DELAY_FLAG_DAYS} days after; "
          f"{cases['admission'].isna().sum()} cases without an admission date")

    print("\nQCESD's published totals beside the list:")
    print(published_totals(cases).to_string(index=False, formatters={"gap": "{:+.1%}".format}))
    print("\nCases per MMWR year (final weeks only):")
    print(table.groupby("year")["cases"].agg(["count", "sum"]).rename(columns={"count": "final weeks"})
          .astype(int).to_string())


if __name__ == "__main__":
    main()

"""Quezon City weekly cases from QCESD's case list."""

import warnings
from datetime import timedelta

import numpy as np
import pandas as pd

import config
from src import view, weeks


def read_case_list(path=config.QCESD_CASES_RAW):
    """The onset and admission date of every case, from every sheet of QCESD's file."""
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
    """Continuous week index of the MMWR week holding each case's onset."""
    return cases["onset"].map(lambda day: weeks.week_index(day.date()))


def last_complete_week(as_of):
    """Week index of the last week whose count is final on day `as_of`."""
    latest_end = as_of - timedelta(days=config.CASES_COMPLETE_DAYS)
    index = weeks.week_index(latest_end)
    if weeks.week_start(index) + timedelta(days=6) > latest_end:   # that week ends after latest_end
        index -= 1
    return index


def weekly_counts(cases):
    """One row per MMWR week (week_index, year, week, cases), 2015 week 1 to the week of the data date."""
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
    """Each of QCESD's published totals (config.CASES_PUBLISHED) beside the list's count of the same days."""
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
    """Build the weekly table, save it and print what to look at."""
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

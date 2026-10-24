"""M0 and M1, the two seasonal baselines."""

import pandas as pd

import config
from src import thresholds, weeks


def m0_forecast(target_year, target_week, cases, cutoff):
    """M0: the count exactly 52 weeks before the target week."""
    index = weeks.week_index_of(target_year, target_week) - config.M0_LAG_WEEKS
    where = f"{target_year} week {target_week}: week index {index}, {config.M0_LAG_WEEKS} weeks back,"
    if index > cutoff:
        raise ValueError(f"{where} is after the cutoff {cutoff}")
    count = cases.loc[cases["week_index"] == index, "cases"]
    if len(count) != 1:
        raise ValueError(f"{where} has {len(count)} rows in the cases table, expected 1")
    if pd.isna(count.iloc[0]):
        raise ValueError(f"{where} has a missing count")
    return float(count.iloc[0])


def m1_forecast(target_year, target_week, cases, cutoff):
    """M1: mean of the target's week of year over the threshold reference years."""
    weeks.week_index_of(target_year, target_week)  # stops on a week the year does not have
    counts = thresholds.reference_counts(int(target_year), int(target_week), cases, cutoff)
    return float(counts.mean())

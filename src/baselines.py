"""M0 and M1, the two seasonal baselines (task B8).

Both forecast a target week's expected cases (the forecast mean mu) from past
counts alone; B6 turns mu into a forecast range, NB(mu, theta).

  M0  the count exactly 52 weeks before the target week. In plain words: next
      week looks like the same week last year. "52 weeks" counts week indexes,
      not week numbers, so after a 53-week year the match moves by one week:
      2026 week 1 uses 2025 week 2, and 2025 week 53 uses 2025 week 1. That
      keeps the two weeks 364 days apart; matching week numbers would put
      them 371 days apart. COVID years are not skipped, so 2021 and 2022
      targets read 2020 and 2021.
  M1  the mean of the target's week of year (53 mapped to 52) over the B7
      reference years: up to the 5 most recent complete non-COVID years before
      the target year, at least 3. These are the threshold's own counts
      (thresholds.reference_counts), so M1 is the mean in T_w = mean + 2 SD.

Both read only counts at or before `cutoff`, the last week the model may see
on the forecast day (T in option B, T - g in option C; B2), so overwriting the
other counts with -999 leaves them unchanged (rule 1, check S11). Both stop
instead of returning NaN (rule 5), and both stop on a target week the year
does not have (2026 week 53).

Check: python -m src.checks ("B8 M0 and M1": made-up counts worked by hand).
"""

import pandas as pd

import config
from src import thresholds, weeks


def m0_forecast(target_year, target_week, cases, cutoff):
    """M0 (B8): the count exactly 52 weeks before the target week.

    In plain words: the target's week index minus 52 (config.M0_LAG_WEEKS),
    looked up in the weekly table (week_index, year, week, cases; A13). Stops
    if that week is after the cutoff (reading it would be a leak), is not in
    the table exactly once, or has a missing count.
    """
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
    """M1 (B8): mean of the target's week of year over the B7 reference years.

    In plain words: the average count of this week (53 mapped to 52) in up to
    the 5 most recent complete non-COVID years before the target year. Stops
    with fewer than 3 such years (thresholds.reference_counts), and on a week
    the target year does not have.
    """
    weeks.week_index_of(target_year, target_week)  # stops on a week the year does not have
    counts = thresholds.reference_counts(int(target_year), int(target_week), cases, cutoff)
    return float(counts.mean())

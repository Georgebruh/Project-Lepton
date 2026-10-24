"""Epidemic thresholds and breach probability."""

import numpy as np
import pandas as pd
from epiweeks import Year

import config
from src import weeks


def complete_years(cases, cutoff):
    """Years in which every MMWR week has a count at or before week index `cutoff`."""
    seen = cases[(cases["week_index"] <= cutoff) & cases["cases"].notna()]
    weeks_seen = seen.groupby("year")["week"].nunique()
    return [int(year) for year, n in weeks_seen.items() if n == Year(int(year)).totalweeks()]


def reference_years(target_year, cases, cutoff):
    """Up to the 5 most recent complete non-COVID years before `target_year`, oldest first."""
    years = [year for year in complete_years(cases, cutoff)
             if year < target_year and year not in config.COVID_YEARS]
    return sorted(years)[-config.THRESHOLD_MAX_YEARS:]


def reference_counts(target_year, target_week, cases, cutoff):
    """Week w's count in each reference year, where w is the target week with 53 mapped to 52."""
    years = reference_years(target_year, cases, cutoff)
    if len(years) < config.THRESHOLD_MIN_YEARS:
        raise ValueError(f"{target_year} week {target_week}: {len(years)} reference years {years}, "
                         f"need at least {config.THRESHOLD_MIN_YEARS}")
    w = weeks.week_of_year(target_week)
    rows = cases[cases["year"].isin(years) & (cases["week"] == w)]
    counts = rows.set_index("year")["cases"].sort_index()
    if list(counts.index) != years:
        raise ValueError(f"expected one week-{w} count for each of {years}, got {list(counts.index)}")
    return counts


def epidemic_threshold(target_year, target_week, cases, cutoff):
    """T_w = mean + 2 SD of week w's counts over the reference years."""
    counts = reference_counts(target_year, target_week, cases, cutoff)
    return counts.mean() + config.THRESHOLD_SD * counts.std(ddof=1)


def breach_probability(dist, t_w):
    """Pr(breach) = Pr(Y > T_w) = 1 - F(floor(T_w)) = dist.sf(floor(T_w))."""
    return dist.sf(np.floor(t_w))


def breached(count, t_w):
    """True when the final count is strictly greater than T_w."""
    if np.any(pd.isna(count)):
        raise ValueError("a final count is missing; a missing week cannot be scored")
    return count > t_w

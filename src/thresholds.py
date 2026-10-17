"""Epidemic thresholds and breach probability (task B7).

The epidemic threshold of a target week is the usual count for that week of the
year plus two standard deviations:

    T_w = mean_w + 2 * sd_w

where mean_w and sd_w are the mean and the sample standard deviation (divided by
n - 1) of week w's counts over the reference years: up to the 5 most recent
complete non-COVID years before the target year, and at least 3
(config.THRESHOLD_*). Week 53 uses week 52's threshold. A reference year's own
week 53 is not used, so each reference year gives exactly one count.

"Complete" means every week of the year has a count the model may see on the
forecast day, that is up to its cutoff: T in option B, T - g in option C (B2).
In plain words, a year whose last weeks are still hidden by the delay guard is
not a reference year yet. So in option C the first g target weeks of a year
use the years before last year, and last year joins from week g + 1. This keeps
counts the model cannot see out of the threshold (rule 1, check S11). M1 (B8) is
the mean over the same years, so it uses reference_counts too.

A week is breached when its final count is strictly greater than T_w (rule 6).
Counts are whole numbers, so for a forecast distribution F:

    Pr(breach) = Pr(Y > T_w) = 1 - F(floor(T_w)) = dist.sf(floor(T_w))

The scored outcome (D3) uses the same strict rule and the same T_w: the one
stored with the forecast.

The method is an assumption until QCESD confirms theirs (A1).

Check: python -m src.checks (S7).
"""

import numpy as np
import pandas as pd
from epiweeks import Year

import config
from src import weeks


def complete_years(cases, cutoff):
    """Years in which every MMWR week has a count at or before week index `cutoff`.

    `cases` is the weekly table (week_index, year, week, cases; A13). Missing
    counts are NaN (check S4), so a year with a missing week is not complete.
    """
    seen = cases[(cases["week_index"] <= cutoff) & cases["cases"].notna()]
    weeks_seen = seen.groupby("year")["week"].nunique()
    return [int(year) for year, n in weeks_seen.items() if n == Year(int(year)).totalweeks()]


def reference_years(target_year, cases, cutoff):
    """Up to the 5 most recent complete non-COVID years before `target_year`, oldest first (B7)."""
    years = [year for year in complete_years(cases, cutoff)
             if year < target_year and year not in config.COVID_YEARS]
    return sorted(years)[-config.THRESHOLD_MAX_YEARS:]


def reference_counts(target_year, target_week, cases, cutoff):
    """Week w's count in each reference year, where w is the target week with 53 mapped to 52.

    Returns one count per reference year, indexed by year. Stops when fewer than
    3 years (config.THRESHOLD_MIN_YEARS) are complete before the target year, or
    when a year has more than one week-w row (a duplicate would count twice).
    M1 (B8) is the mean of these counts.
    """
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
    """T_w = mean + 2 SD of week w's counts over the reference years (B7)."""
    counts = reference_counts(target_year, target_week, cases, cutoff)
    return counts.mean() + config.THRESHOLD_SD * counts.std(ddof=1)


def breach_probability(dist, t_w):
    """Pr(breach) = Pr(Y > T_w) = 1 - F(floor(T_w)) = dist.sf(floor(T_w)) (B7, rule 6).

    In plain words: the chance of a whole-number count above T_w. For T_w = 12.4
    that is Pr(Y >= 13) = dist.sf(12).
    """
    return dist.sf(np.floor(t_w))


def breached(count, t_w):
    """True when the final count is strictly greater than T_w (rule 6; scored in D3).

    A count equal to T_w is not a breach. Stops on a missing count, which would
    otherwise be scored as "not breached".
    """
    if np.any(pd.isna(count)):
        raise ValueError("a final count is missing; a missing week cannot be scored")
    return count > t_w

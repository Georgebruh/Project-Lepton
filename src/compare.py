"""Comparing two models week by week: the primary endpoint (task D5), the flood and practical tests (D6).

For each scored target week t, the loss difference of model a against model b is

    d_t = |y_t - mu_a,t| - |y_t - mu_b,t|

so mean(d) = MAE_a - MAE_b. Below 0, model a misses less on average.

How sure is that mean? Misses come in runs (an outbreak lasts several weeks), so the weeks
are not independent and resampling single weeks would give too narrow an interval. The
moving-block bootstrap (Kunsch 1989) resamples whole runs of weeks instead:

  1. every run of L consecutive weeks of d is a block (L = 8, config.BOOT_BLOCK_WEEKS);
  2. pick ceil(n / L) blocks at random, with replacement, put them end to end and keep the
     first n weeks;
  3. take the mean; repeat 2,000 times (config.BOOT_RESAMPLES; seed config.RANDOM_SEED, so
     every run gives the same interval);
  4. the 95% interval runs from the 2.5% point to the 97.5% point of those means.

Wholly below 0: model a misses less. Wholly above 0: model b misses less. Across 0: these
weeks cannot tell the two apart. The weeks are in time order with the COVID years left
out, so a block can join 2019's last weeks to 2022's first; that join happens once in
about 350 weeks, a small effect the paper mentions. Reruns with 4- and 13-week blocks
(config.BOOT_BLOCK_WEEKS_TESTS) show whether the answer hangs on L.

The Diebold-Mariano test (h = 1), reported beside it, asks the same question with a
formula: DM = mean(d) / (sd(d) / sqrt(n)), two-sided p-value from a t distribution with
n - 1 degrees of freedom (with h = 1 this is a paired t test on the misses). It treats
the weeks as independent, so when misses come in runs its p-value can be too small; that
is why the block-bootstrap interval is the headline and DM only sits beside it. B3's
m3.dm_test is the paper's one-sided version of the same statistic. Implementation Plan
v2's block_bootstrap and dm_test are not in the repository or on the team drive, so both
are written here from the plan's description.

D5, the primary endpoint: M4 against M3 (config.PRIMARY_COMPARISON) over the MAE window
(config.MAE_YEARS: 2018-2019 and 2022-2026). M5 (stretch task B12) is not built; if it
is, the plan adds M5 against M3 and Holm-corrects the two.

D6, with the same bootstrap and window:
  - the flood test, M4 against M4 without EI2 (config.FLOOD_TEST): does the flood exposure
    index make the city forecast more accurate? On most forecast days the two models are
    nested (M4 without EI2 is M4 minus one term), and for nested models DM's p-value is
    not valid: when the extra term adds nothing, the two forecasts nearly coincide (Clark
    & McCracken 2001). So this test has no DM, as the plan says. On days when rain and
    EI2 correlate above 0.8, M4 leaves rain out and keeps EI2 while M4 without EI2 keeps
    rain (src/m4.py), so there the test compares the flood index with rain. B10 should
    record those days (fit_m4's corr_rain_ei) so the paper can say how many there were.
    flood_finding states the answer in one sentence; if EI2 adds nothing, it says so
    plainly: the flood maps then earn their place in Layer 2, not Layer 1.
  - the practical test, M4 against M1 (config.PRACTICAL_TEST): does M4 beat the same-week
    average health offices use now? Not nested, so DM is reported.

Checks: python -m src.checks ("D5 primary endpoint" and "D6 flood test": made-up misses
worked by hand).
"""

import numpy as np
import pandas as pd
from scipy import stats

import config
from src import scores


def loss_differences(table, model_a, model_b, years):
    """d_t = |y_t - mu_a| - |y_t - mu_b| for each target week in `years`, oldest first.

    table: B10's forecasts, one row per model and target week (model, week_index, year,
    y, mu). Returns week_index, year and d. Stops unless both models have one forecast
    for exactly the same weeks (scores.check_same_weeks) against the same count y, and
    on a missing value (rule 5).
    """
    rows = table[table["model"].isin([model_a, model_b]) & table["year"].isin(years)]
    if set(rows["model"]) != {model_a, model_b}:
        raise ValueError(f"need forecasts of both {model_a} and {model_b} in {years}")
    scores.check_same_weeks(rows)
    a = rows[rows["model"] == model_a].sort_values("week_index")
    b = rows[rows["model"] == model_b].sort_values("week_index")
    y, mu_a = scores.check_pairs(a["y"], a["mu"])
    y_b, mu_b = scores.check_pairs(b["y"], b["mu"])
    if not np.array_equal(y, y_b):
        raise ValueError(f"{model_a} and {model_b} are scored against different counts in some week")
    return pd.DataFrame({"week_index": a["week_index"].to_numpy(), "year": a["year"].to_numpy(),
                         "d": np.abs(y - mu_a) - np.abs(y - mu_b)})


def block_bootstrap(d, block=config.BOOT_BLOCK_WEEKS, resamples=config.BOOT_RESAMPLES, seed=config.RANDOM_SEED):
    """Moving-block bootstrap of mean(d): the mean and its 95% interval, low and high (D5).

    d: the loss differences in time order. See the module docstring for the four steps.
    Stops on a missing value and on fewer values than one block.
    """
    d = np.asarray(d, dtype=float)
    n = len(d)
    if np.isnan(d).any():
        raise ValueError("a loss difference is missing (NaN)")
    if n < block:
        raise ValueError(f"{n} weeks, fewer than one {block}-week block")
    rng = np.random.default_rng(seed)
    blocks = -(-n // block)   # ceil(n / block)
    means = np.empty(resamples)
    for i in range(resamples):
        starts = rng.integers(0, n - block + 1, size=blocks)   # any run of `block` weeks can be picked
        means[i] = np.concatenate([d[s:s + block] for s in starts])[:n].mean()
    tail = 100 * (1 - config.BOOT_INTERVAL) / 2
    low, high = np.percentile(means, [tail, 100 - tail])
    return {"mean": float(d.mean()), "low": float(low), "high": float(high)}


def dm_test(d):
    """Diebold-Mariano (h = 1) on loss differences d: DM = mean / (sd / sqrt(n)), two-sided p (D5).

    Stops on a missing value, on fewer than 2 values, and when every d is the same (sd = 0:
    DM is undefined).
    """
    d = np.asarray(d, dtype=float)
    n = len(d)
    if np.isnan(d).any():
        raise ValueError("a loss difference is missing (NaN)")
    if n < 2 or np.ptp(d) == 0:   # ptp = largest - smallest; an sd near 1e-17 would not be exactly 0
        raise ValueError(f"DM is undefined for {n} loss differences that are all the same")
    stat = d.mean() / (d.std(ddof=1) / np.sqrt(n))
    return {"dm_stat": float(stat), "dm_p": float(2 * stats.t.sf(abs(stat), df=n - 1))}


def verdict(low, high, model_a, model_b):
    """The interval in plain words: which model misses less, or that these weeks cannot tell."""
    if high < 0:
        return f"{model_a} misses less"
    if low > 0:
        return f"{model_b} misses less"
    return "no clear difference"


def compare(table, model_a, model_b, years=config.MAE_YEARS, dm=True):
    """Model a against model b: mean of d and its interval for 8-week blocks, then 4 and 13 (D5).

    Returns one row per block length: comparison, block_weeks, weeks, mean_diff, low,
    high, verdict, and with dm=True the Diebold-Mariano dm_stat and dm_p.
    """
    d = loss_differences(table, model_a, model_b, years)["d"]
    test = dm_test(d) if dm else {}
    rows = []
    for block in (config.BOOT_BLOCK_WEEKS, *config.BOOT_BLOCK_WEEKS_TESTS):
        boot = block_bootstrap(d, block)
        rows.append({"comparison": f"{model_a} vs {model_b}", "block_weeks": block, "weeks": len(d),
                     "mean_diff": boot["mean"], "low": boot["low"], "high": boot["high"],
                     "verdict": verdict(boot["low"], boot["high"], model_a, model_b), **test})
    return pd.DataFrame(rows)


def primary_endpoint(table, years=config.MAE_YEARS):
    """D5: M4 against M3 over the MAE window, with the Diebold-Mariano test beside it.

    The first row (8-week blocks) is the headline: mean of |error M4| - |error M3| and its
    95% interval; below 0 means M4 misses less. The 4- and 13-week rows are the checks.
    years: the MAE window; pass 2018-2026 for the all-years check (COVID years included).
    """
    return compare(table, *config.PRIMARY_COMPARISON, years=years)


def flood_and_practical_tests(table, years=config.MAE_YEARS):
    """D6: M4 against M4 without EI2 (no DM: nested models), then M4 against M1.

    years: the MAE window; pass 2018-2026 for the all-years check. Same columns as
    compare; the flood test's dm_stat and dm_p are empty (NaN).
    """
    flood = compare(table, *config.FLOOD_TEST, years=years, dm=False)
    practical = compare(table, *config.PRACTICAL_TEST, years=years)
    return pd.concat([flood, practical], ignore_index=True)


def flood_finding(result):
    """The flood test in one plain sentence (D6), from flood_and_practical_tests' result.

    The sentence comes from the 8-week row; it ends by saying whether the 4- and 13-week
    checks reach the same verdict.
    """
    with_ei, without_ei = config.FLOOD_TEST
    rows = result[result["comparison"] == f"{with_ei} vs {without_ei}"].set_index("block_weeks")
    row = rows.loc[config.BOOT_BLOCK_WEEKS]
    interval = (f"mean difference {row['mean_diff']:+.2f} cases a week, "
                f"95% interval {row['low']:+.2f} to {row['high']:+.2f}")
    effect = {f"{with_ei} misses less": "makes M4 more accurate",
              f"{without_ei} misses less": "makes M4 less accurate"}.get(row["verdict"], "adds no clear accuracy to M4")
    sentence = f"The flood exposure index {effect} ({interval})"
    if effect != "makes M4 more accurate":
        sentence += ": the flood maps earn their place in Layer 2, not Layer 1"
    tests = " and ".join(str(block) for block in config.BOOT_BLOCK_WEEKS_TESTS)
    if (rows["verdict"] == row["verdict"]).all():
        return f"{sentence}; the {tests}-week blocks agree."
    return f"{sentence}; the {tests}-week blocks do not all agree, so this result depends on the block length."

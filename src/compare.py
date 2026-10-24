"""Comparing two models week by week: the primary endpoint, the flood and practical tests."""

import numpy as np
import pandas as pd
from scipy import stats

import config
from src import scores


def loss_differences(table, model_a, model_b, years):
    """d_t = |y_t - mu_a| - |y_t - mu_b| for each target week in `years`, oldest first."""
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
    """Moving-block bootstrap of mean(d): the mean and its 95% interval, low and high."""
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
    """Diebold-Mariano (h = 1) on loss differences d: DM = mean / (sd / sqrt(n)), two-sided p."""
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
    """Model a against model b: mean of d and its interval for 8-week blocks, then 4 and 13."""
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
    """M4 against M3 over the MAE window, with the Diebold-Mariano test beside it."""
    return compare(table, *config.PRIMARY_COMPARISON, years=years)


def flood_and_practical_tests(table, years=config.MAE_YEARS):
    """M4 against M4 without EI2 (no DM: nested models), then M4 against M1."""
    flood = compare(table, *config.FLOOD_TEST, years=years, dm=False)
    practical = compare(table, *config.PRACTICAL_TEST, years=years)
    return pd.concat([flood, practical], ignore_index=True)


def flood_finding(result):
    """The flood test in one plain sentence, from flood_and_practical_tests' result."""
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

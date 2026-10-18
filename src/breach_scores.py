"""Breach scores: Brier, Brier skill, reliability, alarms and outbreak episodes (task D3).

B7 gives each forecast a breach probability p = Pr(Y > T_w). The scored outcome is o = 1
when the final count is strictly above the same T_w, else 0 (rule 6; thresholds.breached).

    BS  = mean (p_t - o_t)^2                     Brier score: 0 is perfect
    BSS = 1 - BS / mean (obar_t - o_t)^2         above 0 beats always quoting the usual rate

obar_t, the usual breach rate at forecast day T, is the share of non-COVID weeks from 2018
up to the cutoff (T in option B, T - g in option C) that breached (correction 12): only
weeks the model could have seen.

Reliability (CORP; Dimitriadis, Gneiting & Jordan 2021): sort the forecasts by p, then fit
the best step curve that never goes down to their outcomes (pool-adjacent-violators). Each
step is a range of p with the breach rate actually seen there and how many forecasts it
holds. A reliable forecast's steps sit on the diagonal.

Alarms: an alarm is raised when p >= p*. p* is the threshold with the best F1 on the first
half of the forecast days; precision and sensitivity are then reported on the second half:
    precision = alarms that breached / alarms;  sensitivity = breaches alarmed / breaches
    F1 = 2 * precision * sensitivity / (precision + sensitivity)

Outbreak episodes: runs of breach weeks, where a breach week at most
config.EPISODE_GAP_WEEKS after the previous one joins its episode (S7: weeks 3, 4, 6, 10,
11 give [3, 4, 6] and [10, 11]). "k of n episodes caught" gets an exact 95% interval
(Clopper-Pearson: proportion_confint(k, n, method="beta")).

Check: python -m src.checks ("S7 scores").
"""

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

import config


def check_probabilities(p, o):
    """p and o as float arrays; stops on missing values, p outside 0-1, o not 0 or 1, or lengths that differ."""
    p = np.asarray(p, dtype=float)
    o = np.asarray(o, dtype=float)
    if p.shape != o.shape or p.size == 0:
        raise ValueError(f"{p.size} probabilities and {o.size} outcomes: need the same number, at least 1")
    if np.isnan(p).any() or np.isnan(o).any():
        raise ValueError("a breach probability or an outcome is missing (NaN)")
    if (p < 0).any() or (p > 1).any() or not np.isin(o, (0, 1)).all():
        raise ValueError("probabilities must lie in 0-1 and outcomes be 0 or 1")
    return p, o


def brier(p, o):
    """BS = mean (p - o)^2: the mean squared error of the breach probabilities (D3)."""
    p, o = check_probabilities(p, o)
    return np.mean((p - o) ** 2)


def base_rate(outcomes, cutoff):
    """obar at one forecast day: the share of non-COVID weeks from 2018 to week index `cutoff` that breached.

    outcomes: one row per week with week_index, year and breached (True or False, B7's rule).
    Stops when no such week exists yet (the rate would be undefined).
    """
    seen = outcomes[(outcomes["week_index"] <= cutoff)
                    & (outcomes["year"] >= config.BACKTEST_FIRST_YEAR)
                    & ~outcomes["year"].isin(config.COVID_YEARS)]
    if seen.empty:
        raise ValueError(f"no non-COVID week from {config.BACKTEST_FIRST_YEAR} up to week index {cutoff}")
    return seen["breached"].astype(float).mean()


def brier_skill_score(p, o, obar):
    """BSS = 1 - BS / mean (obar - o)^2 (D3). obar: the usual breach rate at each forecast day (base_rate)."""
    p, o = check_probabilities(p, o)
    obar, _ = check_probabilities(obar, o)
    reference = np.mean((obar - o) ** 2)
    if reference == 0:
        raise ValueError("the usual-rate forecast is perfect on these weeks: BSS is undefined")
    return 1 - brier(p, o) / reference


def reliability(p, o):
    """CORP reliability steps: p_low, p_high, observed (breach rate) and forecasts (how many), lowest p first.

    Forecasts with the same p are pooled first; then neighbouring groups are pooled while
    an observed rate is above the next one (pool-adjacent-violators).
    """
    p, o = check_probabilities(p, o)
    groups = pd.DataFrame({"p": p, "o": o}).groupby("p")["o"].agg(["sum", "count"]).reset_index()
    steps = []   # each step: [p_low, p_high, breaches, forecasts]
    for row in groups.itertuples():
        steps.append([row.p, row.p, row.sum, row.count])
        while len(steps) > 1 and steps[-2][2] / steps[-2][3] > steps[-1][2] / steps[-1][3]:
            low, high, k, n = steps.pop()
            steps[-1][1] = high
            steps[-1][2] += k
            steps[-1][3] += n
    return pd.DataFrame([{"p_low": a, "p_high": b, "observed": k / n, "forecasts": n} for a, b, k, n in steps])


def alarm_scores(p, o, p_star):
    """Precision, sensitivity and F1 of alarms raised when p >= p_star.

    Precision is None when no alarm is raised and sensitivity None when nothing breached:
    neither can be computed then.
    """
    p, o = check_probabilities(p, o)
    alarm = p >= p_star
    hits = int((alarm & (o == 1)).sum())
    precision = hits / alarm.sum() if alarm.any() else None
    sensitivity = hits / (o == 1).sum() if (o == 1).any() else None
    f1 = 0.0
    if precision and sensitivity:
        f1 = 2 * precision * sensitivity / (precision + sensitivity)
    return {"p_star": p_star, "alarms": int(alarm.sum()), "breaches": int((o == 1).sum()),
            "precision": precision, "sensitivity": sensitivity, "f1": f1}


def best_p_star(p, o):
    """The threshold among the forecasts' own probabilities with the best F1 (ties: the lowest)."""
    p, o = check_probabilities(p, o)
    if not (o == 1).any():
        raise ValueError("no breach among these forecasts: p* cannot be chosen")
    scores = [alarm_scores(p, o, t) for t in np.unique(p)]
    return max(scores, key=lambda s: (s["f1"], -s["p_star"]))["p_star"]


def alarm_test(p, o):
    """p* from the first half of the forecast days (in order), scored on the second half (D3)."""
    p, o = check_probabilities(p, o)
    half = len(p) // 2
    p_star = best_p_star(p[:half], o[:half])
    return {"first_half": alarm_scores(p[:half], o[:half], p_star),
            "second_half": alarm_scores(p[half:], o[half:], p_star)}


def episodes(breach_weeks, gap=config.EPISODE_GAP_WEEKS):
    """Group breach weeks into outbreak episodes: a week at most `gap` after the last one joins it.

    breach_weeks: week indexes of breached weeks, in any order. episodes([]) is [] (v2's
    version crashed on an empty list).
    """
    if not breach_weeks:
        return []
    out = [[]]
    for week in sorted(breach_weeks):
        if out[-1] and week - out[-1][-1] > gap:
            out.append([])
        out[-1].append(week)
    return out


def caught_share(k, n):
    """k of n episodes caught: the share and its exact 95% interval (Clopper-Pearson)."""
    if n == 0 or not 0 <= k <= n:
        raise ValueError(f"need 0 <= k <= n and n > 0, got k = {k}, n = {n}")
    low, high = proportion_confint(k, n, method=config.EPISODE_CI_METHOD)
    return {"k": k, "n": n, "share": k / n, "low": low, "high": high}

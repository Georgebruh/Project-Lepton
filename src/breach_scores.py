"""Breach scores: Brier, Brier skill, reliability, alarms and outbreak episodes, lead time."""

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

import config
from src import view


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
    """BS = mean (p - o)^2: the mean squared error of the breach probabilities."""
    p, o = check_probabilities(p, o)
    return np.mean((p - o) ** 2)


def base_rate(outcomes, cutoff):
    """obar at one forecast day: the share of non-COVID weeks from 2018 to week index `cutoff` that breached."""
    seen = outcomes[(outcomes["week_index"] <= cutoff)
                    & (outcomes["year"] >= config.BACKTEST_FIRST_YEAR)
                    & ~outcomes["year"].isin(config.COVID_YEARS)]
    if seen.empty:
        raise ValueError(f"no non-COVID week from {config.BACKTEST_FIRST_YEAR} up to week index {cutoff}")
    return seen["breached"].astype(float).mean()


def brier_skill_score(p, o, obar):
    """BSS = 1 - BS / mean (obar - o)^2. obar: the usual breach rate at each forecast day (base_rate)."""
    p, o = check_probabilities(p, o)
    obar, _ = check_probabilities(obar, o)
    reference = np.mean((obar - o) ** 2)
    if reference == 0:
        raise ValueError("the usual-rate forecast is perfect on these weeks: BSS is undefined")
    return 1 - brier(p, o) / reference


def reliability(p, o):
    """CORP reliability steps: p_low, p_high, observed (breach rate) and forecasts (how many), lowest p first."""
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
    """Precision, sensitivity and F1 of alarms raised when p >= p_star."""
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
    """p* from the first half of the forecast days (in order), scored on the second half."""
    p, o = check_probabilities(p, o)
    half = len(p) // 2
    p_star = best_p_star(p[:half], o[:half])
    return {"first_half": alarm_scores(p[:half], o[:half], p_star),
            "second_half": alarm_scores(p[half:], o[half:], p_star)}


def episodes(breach_weeks, gap=config.EPISODE_GAP_WEEKS):
    """Group breach weeks into outbreak episodes: a week at most `gap` after the last one joins it."""
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


def lead_times(forecasts, p_star, option=config.DATA_OPTION, g=config.DELAY_GUARD_G,
               horizon=config.FORECAST_HORIZON_WEEKS, years=config.PROB_SCORE_YEARS):
    """Lead time of each outbreak episode, for one model's forecasts."""
    if not 0 <= p_star <= 1:   # also stops on NaN
        raise ValueError(f"the alarm cut-off p* is {p_star}: it must lie in 0-1")
    forecasts = forecasts[forecasts["year"].isin(years)]
    if forecasts["week_index"].duplicated().any():
        raise ValueError("two forecasts for the same target week")
    p, o = check_probabilities(forecasts["p"], forecasts["breached"])
    target = forecasts["week_index"].to_numpy()
    delay = view.guard_weeks(option, g)   # 0 in option B, g in option C
    rows = []
    for episode in episodes(list(target[o == 1])):
        first, last = episode[0], episode[-1]
        alarms = target[(p >= p_star) & np.isin(target, episode)]   # alarms for its breach weeks only
        alarm_day = alarms.min() - horizon if alarms.size else np.nan
        lead = first + delay - alarm_day
        rows.append({"first_week": first, "last_week": last, "shown_week": first + delay,
                     "first_alarm_day": alarm_day, "lead_weeks": lead,
                     "in_advance": bool(lead >= config.LEAD_TIME_IN_ADVANCE_WEEKS)})
    return pd.DataFrame(rows, columns=["first_week", "last_week", "shown_week", "first_alarm_day",
                                       "lead_weeks", "in_advance"])


def caught_in_advance(lead_table):
    """k of n episodes caught in advance (caught_share, exact 95% interval) and the median lead time."""
    if lead_table.empty:
        raise ValueError("no outbreak episode in these forecasts: lead time cannot be scored")
    alarmed = lead_table["lead_weeks"].dropna()
    return {**caught_share(int(lead_table["in_advance"].sum()), len(lead_table)),
            "alarmed": len(alarmed), "median_lead_weeks": alarmed.median()}

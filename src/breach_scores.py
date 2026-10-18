"""Breach scores: Brier, Brier skill, reliability, alarms and outbreak episodes (task D3), lead time (D4).

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

Lead time (D4), per outbreak episode:

    lead time = the week surveillance shows the breach - the forecast day of the first alarm

The breach shows when the episode's first breach week has ended (option B), or g weeks
later in option C, when its count clears the delay guard (view.guard_weeks; an
assumption, matching the guard). The first alarm is the earliest forecast with p >= p*
whose target is one of the episode's breach weeks; its forecast day is the target week
minus config.FORECAST_HORIZON_WEEKS. An alarm for a week that did not breach (before the
episode, or a quiet week inside it) was wrong about its own week and does not count
(assumption). An episode is caught in advance if its lead time is at least 1 week
(config.LEAD_TIME_IN_ADVANCE_WEEKS). In plain words: did the model raise the alarm before
surveillance could have shown the outbreak, and by how many weeks?

With 1-week forecasts the earliest alarm for a breach week comes 1 week before that week
ends, so in option B a lead time is at most 1 week, and in option C at most 1 + g. Lead
times of 0 or less (the alarm came no earlier than surveillance) are kept and reported.
Episodes are scored over config.PROB_SCORE_YEARS (2022-2026), as the breach scores are;
pass the forecast days not used to choose p* (alarm_test's second half).

Checks: python -m src.checks ("S7 scores"; "D4 lead time": worked by hand).
"""

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


def lead_times(forecasts, p_star, option=config.DATA_OPTION, g=config.DELAY_GUARD_G,
               horizon=config.FORECAST_HORIZON_WEEKS, years=config.PROB_SCORE_YEARS):
    """Lead time of each outbreak episode, for one model's forecasts (D4).

    forecasts: one row per target week with week_index, year, p (the breach probability)
    and breached (the outcome, 0 or 1); only target weeks in `years` are scored. p_star:
    the alarm cut-off (alarm_test's p*). horizon: weeks from forecast day to target week
    (2 for the B11 stretch).
    Returns one row per episode: first_week and last_week (its breach weeks), shown_week
    (when surveillance shows the breach), first_alarm_day (the forecast day of the first
    alarm for one of its breach weeks; NaN if none), lead_weeks (shown_week -
    first_alarm_day; NaN if no alarm) and in_advance (lead time of at least 1 week).
    Stops on a p* outside 0-1, two forecasts for one target week, and missing or
    impossible p or outcomes.
    """
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
    """k of n episodes caught in advance (caught_share, exact 95% interval) and the median lead time (D4).

    lead_table: lead_times' result. alarmed: episodes with any alarm for their breach weeks;
    the median lead time is over those, early or late (NaN if none). Stops when there is
    no episode to score.
    """
    if lead_table.empty:
        raise ValueError("no outbreak episode in these forecasts: lead time cannot be scored")
    alarmed = lead_table["lead_weeks"].dropna()
    return {**caught_share(int(lead_table["in_advance"].sum()), len(lead_table)),
            "alarmed": len(alarmed), "median_lead_weeks": alarmed.median()}

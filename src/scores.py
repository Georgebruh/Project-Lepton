"""Count and range scores for every model (tasks D1 and D2).

Every forecast is a negative binomial with mean mu and spread theta (B6's
forecast_range.forecast_dist). D1 scores the forecast mean and the forecast range
against the final count y:

    MAE  = mean |y - mu|            the average miss (the primary endpoint, D5)
    RMSE = sqrt(mean (y - mu)^2)    big misses count more
    Bias = mean (mu - y)            + means the forecasts lean high, - low
    Coverage_90 = share of weeks with q_0.05 <= y <= q_0.95; a well-sized 90% range
                  holds the truth about 9 weeks in 10 (the same for 50%)

WIS, the weighted interval score (Bracher et al. 2021), scores the whole range at once:

    WIS = [ 0.5 * |y - median| + sum over alpha of (alpha / 2) * IS_alpha ] / (K + 0.5)
    IS_alpha = (u - l) + (2 / alpha) * (l - y, if y < l) + (2 / alpha) * (y - u, if y > u)

where l and u are the alpha/2 and 1 - alpha/2 quantiles (the central 1 - alpha range)
and K = 11 is the number of alphas (config.WIS_ALPHAS). In plain words: the width of each
range, plus a penalty when the truth falls outside it, averaged over the ranges. It is in
cases, lower is better, and 0 for a forecast that puts all its weight on the truth.

score_models scores a table of forecasts, one row per model and target week, and stops
unless every model has a forecast on exactly the same weeks (rule 5, check S11).

MASE, the mean absolute scaled error (D2), puts MAE on a scale with no units:

    MASE = MAE / ( (1/104) * sum over target weeks t in 2016-2017 of |y_t - y_(t-52)| )

The denominator is the average miss of "same week last year" (M0's guess) over the
burn-in target weeks 2016-2017, looking back into 2015. It is fixed once, from the final
counts, and every model is divided by the same number (correction 11), so MASE ranks the
models exactly as MAE does. In plain words: below 1, the model misses less than that lazy
guess did in the burn-in years. The denominator uses only burn-in weeks, before the first
forecast day (2018), and feeds no forecast, so it leaks nothing.

Checks: python -m src.checks ("S7 scores": WIS of forecast_dist(20, 5) is 2.12 at y = 20
and 32.0 at y = 60; "D2 MASE": the denominator worked by hand).
"""

import numpy as np
import pandas as pd
from epiweeks import Year

import config
from src import baselines, forecast_range, weeks


def check_pairs(y, mu):
    """y and mu as float arrays; stops on missing values or lengths that differ (rule 5)."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if y.shape != mu.shape or y.size == 0:
        raise ValueError(f"{y.size} counts and {mu.size} forecasts: need the same number, at least 1")
    if np.isnan(y).any() or np.isnan(mu).any():
        raise ValueError("a count or a forecast is missing (NaN): every model must be scored on the same weeks")
    return y, mu


def point_scores(y, mu):
    """MAE, RMSE and bias of the forecast means mu against the counts y (D1)."""
    y, mu = check_pairs(y, mu)
    miss = mu - y
    return {"mae": np.mean(np.abs(miss)), "rmse": np.sqrt(np.mean(miss ** 2)), "bias": np.mean(miss)}


def interval_score(y, lower, upper, alpha):
    """IS_alpha = (u - l) + (2/alpha)(l - y if y < l) + (2/alpha)(y - u if y > u): one range's score."""
    return (upper - lower) + (2 / alpha) * max(lower - y, 0) + (2 / alpha) * max(y - upper, 0)


def wis(y, dist, alphas=config.WIS_ALPHAS):
    """The weighted interval score of one forecast distribution `dist` for the count y (D1)."""
    total = 0.5 * abs(y - dist.ppf(0.5))
    for alpha in alphas:
        total += (alpha / 2) * interval_score(y, dist.ppf(alpha / 2), dist.ppf(1 - alpha / 2), alpha)
    return total / (len(alphas) + 0.5)


def covered(y, dist, level):
    """True when y lies in the forecast's central `level` range, e.g. 0.9: q_0.05 <= y <= q_0.95."""
    tail = (1 - level) / 2
    return bool(dist.ppf(tail) <= y <= dist.ppf(1 - tail))


def check_same_weeks(table):
    """Stop unless every model has exactly one forecast for exactly the same target weeks (rule 5)."""
    if table.duplicated(["model", "week_index"]).any():
        raise ValueError("a model has two forecasts for the same target week")
    weeks_per_model = table.groupby("model")["week_index"].apply(frozenset)
    if weeks_per_model.nunique() != 1:
        counts = table.groupby("model").size().to_dict()
        raise ValueError(f"models are not scored on the same weeks: forecasts per model {counts}")


def score_models(table, years):
    """MAE, RMSE, bias, mean WIS and 50% / 90% coverage per model, over target weeks in `years`.

    table: one row per model and target week, with columns model, week_index, year (of the
    target week), y (the final count), mu and theta (the forecast, forecast_dist). years:
    the scoring window, e.g. config.MAE_YEARS or config.PROB_SCORE_YEARS. Returns one row
    per model.
    """
    rows = table[table["year"].isin(years)]
    if rows.empty:
        raise ValueError(f"no forecasts with target weeks in {years}")
    check_same_weeks(rows)
    out = []
    for model, group in rows.groupby("model"):
        scores = point_scores(group["y"], group["mu"])
        dists = [forecast_range.forecast_dist(mu, theta) for mu, theta in zip(group["mu"], group["theta"])]
        scores["wis"] = np.mean([wis(y, d) for y, d in zip(group["y"], dists)])
        for level in config.COVERAGE_LEVELS:
            scores[f"coverage_{100 * level:.0f}"] = np.mean([covered(y, d, level) for y, d in zip(group["y"], dists)])
        out.append({"model": model, "weeks": len(group), **scores})
    return pd.DataFrame(out).set_index("model")


def mase_denominator(cases, years=config.MASE_DENOM_YEARS):
    """MASE's fixed denominator (D2): M0's MAE over the target weeks in `years`.

    In plain words: the mean of |y_t - y_(t-52)|, where y_(t-52) is M0's forecast
    (baselines.m0_forecast), the count 52 week indexes back, so 2016 week 1 looks back
    to 2015 week 1. 2016 and 2017 have 52 weeks each: 104 target weeks.
    cases: the weekly table (week_index, year, week, cases; A13).
    Stops if a year in `years` does not have each of its weeks exactly once; if a row
    used has a week index that its year and week do not give; if a count used (in
    `years` or 52 weeks before) is missing or negative; if `years` is empty; or if the
    denominator is 0 (MASE would be infinite).
    """
    targets = cases[cases["year"].isin(years)]
    for year in years:
        found = targets.loc[targets["year"] == year, "week"].astype(int).tolist()
        n = Year(int(year)).totalweeks()
        missing = sorted(set(range(1, n + 1)) - set(found))
        repeated = sorted({week for week in found if found.count(week) > 1})
        extra = sorted(set(found) - set(range(1, n + 1)))
        if missing or repeated or extra:
            raise ValueError(f"MASE denominator: {year} must have each of its {n} weeks once; "
                             f"missing {missing}, repeated {repeated}, not in {year} {extra}")
    back = cases[cases["week_index"].isin(targets["week_index"] - config.M0_LAG_WEEKS)]
    used = pd.concat([targets, back])
    if [weeks.week_index_of(year, week) for year, week in zip(used["year"], used["week"])] != used["week_index"].tolist():
        raise ValueError("MASE denominator: a row's week index is not the one its year and week give")
    if used["cases"].isna().any():
        raise ValueError(f"MASE denominator: a count in {years}, or 52 weeks before one, is missing")
    if (used["cases"] < 0).any():
        raise ValueError(f"MASE denominator: a count in {years}, or 52 weeks before one, is negative")
    last_year = [baselines.m0_forecast(year, week, cases, index - 1)
                 for index, year, week in targets[["week_index", "year", "week"]].itertuples(index=False)]
    denominator = float(point_scores(targets["cases"], last_year)["mae"])   # stops on an empty `years`
    if denominator <= 0:
        raise ValueError(f"MASE denominator is {denominator}: every count in {years} equals last year's")
    return denominator


def add_mase(by_model, denominator):
    """score_models' table with a mase column: each model's MAE / the fixed denominator (D2)."""
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError(f"MASE denominator is {denominator}: it must be a positive number")
    return by_model.assign(mase=by_model["mae"] / denominator)

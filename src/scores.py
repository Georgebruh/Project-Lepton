"""Count and range scores for every model."""

import numpy as np
import pandas as pd
from epiweeks import Year

import config
from src import baselines, forecast_range, weeks


def check_pairs(y, mu):
    """y and mu as float arrays; stops on missing values or lengths that differ."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if y.shape != mu.shape or y.size == 0:
        raise ValueError(f"{y.size} counts and {mu.size} forecasts: need the same number, at least 1")
    if np.isnan(y).any() or np.isnan(mu).any():
        raise ValueError("a count or a forecast is missing (NaN): every model must be scored on the same weeks")
    return y, mu


def point_scores(y, mu):
    """MAE, RMSE and bias of the forecast means mu against the counts y."""
    y, mu = check_pairs(y, mu)
    miss = mu - y
    return {"mae": np.mean(np.abs(miss)), "rmse": np.sqrt(np.mean(miss ** 2)), "bias": np.mean(miss)}


def interval_score(y, lower, upper, alpha):
    """IS_alpha = (u - l) + (2/alpha)(l - y if y < l) + (2/alpha)(y - u if y > u): one range's score."""
    return (upper - lower) + (2 / alpha) * max(lower - y, 0) + (2 / alpha) * max(y - upper, 0)


def wis(y, dist, alphas=config.WIS_ALPHAS):
    """The weighted interval score of one forecast distribution `dist` for the count y."""
    total = 0.5 * abs(y - dist.ppf(0.5))
    for alpha in alphas:
        total += (alpha / 2) * interval_score(y, dist.ppf(alpha / 2), dist.ppf(1 - alpha / 2), alpha)
    return total / (len(alphas) + 0.5)


def covered(y, dist, level):
    """True when y lies in the forecast's central `level` range, e.g. 0.9: q_0.05 <= y <= q_0.95."""
    tail = (1 - level) / 2
    return bool(dist.ppf(tail) <= y <= dist.ppf(1 - tail))


def check_same_weeks(table):
    """Stop unless every model has exactly one forecast for exactly the same target weeks."""
    if table.duplicated(["model", "week_index"]).any():
        raise ValueError("a model has two forecasts for the same target week")
    weeks_per_model = table.groupby("model")["week_index"].apply(frozenset)
    if weeks_per_model.nunique() != 1:
        counts = table.groupby("model").size().to_dict()
        raise ValueError(f"models are not scored on the same weeks: forecasts per model {counts}")


def score_models(table, years):
    """MAE, RMSE, bias, mean WIS and 50% / 90% coverage per model, over target weeks in `years`."""
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
    """MASE's fixed denominator: M0's MAE over the target weeks in `years`."""
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
    """score_models' table with a mase column: each model's MAE / the fixed denominator."""
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError(f"MASE denominator is {denominator}: it must be a positive number")
    return by_model.assign(mase=by_model["mae"] / denominator)

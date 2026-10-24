"""Forecast range for every model."""

import numpy as np
from scipy import stats

import config


def forecast_dist(mu, theta):
    """The forecast: negative binomial with mean mu and spread theta."""
    if not np.isfinite(mu) or mu < 0:
        raise ValueError(f"forecast mean is {mu}: a model input is missing or wrong")
    if np.isnan(theta) or theta <= 0:
        raise ValueError(f"theta is {theta}: it must be positive or infinity")
    if np.isinf(theta):
        return stats.poisson(mu)
    return stats.nbinom(theta, theta / (theta + mu))


def range_90(dist):
    """The 90% forecast range: from the 5% point to the 95% point of the forecast."""
    return dist.ppf(config.RANGE_LOW_Q), dist.ppf(config.RANGE_HIGH_Q)


def estimate_theta(y, mu):
    """theta = sum(mu^2) / sum((y - mu)^2 - mu): the spread that matches the past misses."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if y.shape != mu.shape or y.size == 0:
        raise ValueError(f"y has {y.size} values and mu {mu.size}: need the same number, at least 1")
    if np.isnan(y).any() or np.isnan(mu).any():
        raise ValueError("a count or a forecast is missing: theta cannot be estimated")
    denominator = np.sum((y - mu) ** 2 - mu)
    if denominator <= 0:
        return np.inf
    return np.sum(mu ** 2) / denominator


def scored_past(past, cases, cutoff):
    """The past forecasts theta_for may use at this forecast day, with the count each one gets."""
    if past["week_index"].duplicated().any():
        raise ValueError("two past forecasts for the same target week")
    if past["mu"].isna().any():
        raise ValueError("a past forecast is missing (NaN)")
    seen = cases.loc[(cases["week_index"] <= cutoff) & cases["cases"].notna(),
                     ["week_index", "year", "cases"]]
    rows = past[["week_index", "mu"]].merge(seen, on="week_index", how="inner")
    rows = rows[~rows["year"].isin(config.COVID_YEARS)].sort_values("week_index")
    return rows.rename(columns={"cases": "y"}).tail(config.THETA_WINDOW).reset_index(drop=True)


def theta_for(past, cases, cutoff, fit_theta):
    """theta for a model's forecast at this forecast day."""
    rows = scored_past(past, cases, cutoff)
    if len(rows) < config.THETA_MIN_FORECASTS:
        return fit_theta
    return estimate_theta(rows["y"], rows["mu"])

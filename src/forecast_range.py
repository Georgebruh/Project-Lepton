"""Forecast range for every model (task B6; forecast_dist written early for B7).

Every forecast is a negative binomial distribution with mean mu and spread theta:

    variance = mu + mu**2 / theta

so a smaller theta gives a wider range. scipy's nbinom takes n = theta and
p = theta / (theta + mu), which gives exactly that mean and variance. When theta
is infinite (the past misses were no wider than a Poisson's, so estimate_theta
found no positive theta), the forecast is Poisson(mu).

theta comes from each model's own past misses (estimate_theta):

    theta = sum(mu_t^2) / sum((y_t - mu_t)^2 - mu_t)

In plain words: theta is set so the forecast ranges are as wide as the model's past
misses. A negative binomial's variance is mu + mu^2 / theta, so the squared misses
minus mu are what the mu^2 / theta part has to explain. If the misses are no bigger
than a Poisson's (denominator 0 or below), theta is infinity and the forecast is
Poisson.

theta_for picks the past forecasts at forecast day T: the model's last 104 forecasts
(config.THETA_WINDOW) whose target week is outside the COVID years and at or before
the cutoff (T in option B, T - g in option C; B2), each compared with the count the
model may see now. In option C the last g weeks' counts are still hidden, so their
forecasts cannot be scored yet (correction 10; rule 1, check S11). With fewer than
26 such forecasts (config.THETA_MIN_FORECASTS), the training fit's own theta is used
instead (M4: 1/alpha from smf.negativebinomial; M0, M1 and M3: estimate_theta on
their in-sample fits).

B7 needs forecast_dist to turn a forecast into a breach probability; B10 calls
theta_for at every forecast day, for every model.

Checks: python -m src.checks (S6 for theta, S7 for the breach probability).
"""

import numpy as np
from scipy import stats

import config


def forecast_dist(mu, theta):
    """The forecast: negative binomial with mean mu and spread theta (B6).

    In plain words: variance = mu + mu^2 / theta. theta = infinity gives
    Poisson(mu), the fallback when the past misses give no positive theta.
    Stops on a missing or negative mean, or a theta that is missing or not
    positive (rule 5: a missing input gives NaN without an error).
    """
    if not np.isfinite(mu) or mu < 0:
        raise ValueError(f"forecast mean is {mu}: a model input is missing or wrong")
    if np.isnan(theta) or theta <= 0:
        raise ValueError(f"theta is {theta}: it must be positive or infinity")
    if np.isinf(theta):
        return stats.poisson(mu)
    return stats.nbinom(theta, theta / (theta + mu))


def range_90(dist):
    """The 90% forecast range: from the 5% point to the 95% point of the forecast (B7)."""
    return dist.ppf(config.RANGE_LOW_Q), dist.ppf(config.RANGE_HIGH_Q)


def estimate_theta(y, mu):
    """theta = sum(mu^2) / sum((y - mu)^2 - mu): the spread that matches the past misses (B6).

    y: the counts; mu: the forecasts (or fitted means) made for them, in the same order.
    Returns infinity when the denominator is 0 or below: the misses were no wider than
    a Poisson's, and forecast_dist then gives Poisson(mu). Stops on missing values or
    on y and mu of different lengths.
    """
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
    """The past forecasts theta_for may use at this forecast day, with the count each one gets.

    past: the model's earlier forecasts, one row per target week (week_index, mu).
    cases: the weekly table (week_index, year, week, cases; A13).
    cutoff: the last week index the model may see (T in option B, T - g in option C).
    Keeps target weeks at or before the cutoff, outside config.COVID_YEARS, whose count is
    known (a missing count cannot be compared yet); then the last config.THETA_WINDOW of
    them. Returns week_index, year, mu and y, oldest first. Stops on a duplicate target
    week or a missing forecast (rule 5).
    """
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
    """theta for a model's forecast at this forecast day (B6).

    estimate_theta on the model's last 104 non-COVID past forecasts that the cutoff lets
    it score (scored_past). With fewer than config.THETA_MIN_FORECASTS (26) of them,
    returns fit_theta, the training fit's own theta. May return infinity (Poisson).
    """
    rows = scored_past(past, cases, cutoff)
    if len(rows) < config.THETA_MIN_FORECASTS:
        return fit_theta
    return estimate_theta(rows["y"], rows["mu"])

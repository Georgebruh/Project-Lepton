"""Forecast range for every model (task B6; forecast_dist written early for B7).

Every forecast is a negative binomial distribution with mean mu and spread theta:

    variance = mu + mu**2 / theta

so a smaller theta gives a wider range. scipy's nbinom takes n = theta and
p = theta / (theta + mu), which gives exactly that mean and variance. When theta
is infinite (the past misses were no wider than a Poisson's, so estimate_theta
found no positive theta), the forecast is Poisson(mu).

B7 needs this to turn a forecast into a breach probability; B6 adds
estimate_theta and theta_for here (theta from each model's last 104 non-COVID
past forecasts).

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

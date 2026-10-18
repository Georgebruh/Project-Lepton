"""M3, the Prophet + XGBoost benchmark, at one forecast day of the backtest (task B9).

B3 checked our copy of Latigay & Gonzaga's (2026) hybrid on their national data
(src/m3.py, results/m3_reproduction.md). Here the same model runs inside LEPTON's
weekly backtest (B10): at each forecast day it is refitted on the counts it may see
and forecasts one target week. The settings are B3's main run (config.M3_*):

  1. Gap filling. mu_w = mean count of week w over the seen years except 2020. A
     missing week in a COVID-19 lockdown gets 0.5 x mu_w; one in June-November gets
     1.0 x mu_w; what is still missing gets a straight line between its neighbours.
  2. Prophet on the filled series: multiplicative seasonality, changepoint prior
     scale 0.55, weekly and yearly seasonality on, no holidays.
  3. XGBoost learns Prophet's in-sample error r = y - yhat from two features,
     Prophet's yhat and the ISO week number (xgboost defaults, 100 rounds).
  4. Forecast = max(0, yhat + r_hat), clipped at zero.

What changes from B3 (the plan's B9; Notes.md section 4):
  - Training weeks: from the first week with a count in the weekly table (A13) to the
    cutoff, the last week the model may see (T in option B, T - g in option C; B2).
    Nothing after the cutoff is read, so overwriting those counts with -999 leaves
    the forecast unchanged (rule 1, check S11).
  - Gap filling uses only those weeks. B3 filled the whole series once, so its mu_w
    and its straight lines used later weeks: fine for reproducing the paper, a leak in
    a backtest. Here a gap at the end of the seen weeks has no later neighbour, so the
    straight line becomes the last filled value.
  - Weeks are MMWR (A3), not ISO. mu_w is the mean of MMWR week w (1-52); a year's
    week 53 is not used, and a missing week 53 borrows week 52's mean (as B3 and B7).
  - Target weeks are named by date. Prophet's ds is the Sunday that starts each MMWR
    week (weeks.week_start), and the target's ds comes from its own week index, so it
    is exact after a 53-week year. B3 counted rows instead.
  - The week feature is the ISO week number, as in the paper: the ISO week that holds
    the MMWR week's Monday to Saturday. It follows the calendar date, so in years that
    start on a Thursday (2015, 2026) it is the MMWR week number + 1.
  - The forecast is (target - cutoff) weeks past the last seen week: 1 in option B,
    g + 1 in option C. Prophet forecasts the target's date; XGBoost corrects it with
    the target's own features.

B10 calls m3_forecast at every forecast day and turns its mean into a forecast range
with B6 (forecast_range.theta_for), using fit_theta while M3 has fewer than 26 past
forecasts to judge itself by. fit_theta comes from Prophet's in-sample fit, not the
hybrid's: XGBoost is trained on those very weeks' errors and nearly repeats them, so
the hybrid's in-sample misses are tiny and its theta comes out infinite (a Poisson
range, far too narrow). On simulated counts with theta 5, Prophet's in-sample theta
was 4.0-4.5 and the hybrid's infinite every time.

Check: python -m src.checks ("B9 M3": made-up counts with gaps, worked by hand).
"""

import numpy as np
import pandas as pd
import xgboost as xgb

import config
from src import forecast_range, m3, weeks


def seen_weeks(cases, cutoff):
    """The weeks M3 may train on: week_index, year, week, ds (the week's Sunday) and cases.

    In plain words: the rows of the weekly table (A13) from the first week with a
    count to week index `cutoff`, oldest first. Missing counts stay NaN for
    fill_gaps. Stops if the table has no row for the cutoff, has two rows for a
    week, or has no count at all; and, from the first count on, if it skips a week,
    labels a row with a year and week that are not the MMWR week of its week index
    (mu_w groups by the labels, Prophet's dates come from the index), or holds a
    negative count.
    """
    seen = cases[cases["week_index"] <= cutoff].sort_values("week_index").reset_index(drop=True)
    if seen.empty or seen["week_index"].iloc[-1] != cutoff:
        raise ValueError(f"the cases table has no row for the cutoff, week index {cutoff}")
    if seen["week_index"].duplicated().any():
        raise ValueError("a week has two rows in the cases table")
    counted = seen["cases"].notna().to_numpy()
    if not counted.any():
        raise ValueError(f"no counts up to the cutoff, week index {cutoff}")
    seen = seen.iloc[counted.argmax():].reset_index(drop=True)   # from the first week with a count
    if len(seen) != cutoff - seen["week_index"].iloc[0] + 1:
        raise ValueError("the cases table skips a week before the cutoff; a missing count needs a row with no count")
    labelled = [weeks.week_index_of(year, week) for year, week in zip(seen["year"], seen["week"])]
    if labelled != seen["week_index"].tolist():
        raise ValueError("a row's year and week are not the MMWR week of its week index")
    if (seen["cases"] < 0).any():
        raise ValueError("a count up to the cutoff is negative")
    seen["ds"] = pd.Timestamp(config.FIRST_WEEK_START) + pd.to_timedelta(7 * seen["week_index"], unit="D")
    return seen[["week_index", "year", "week", "ds", "cases"]]


def seasonal_baseline(seen):
    """mu_w = mean count of MMWR week w (1-52) over the seen years except 2020, as {w: mu_w}.

    Week 53 borrows week 52's mean, as in B3. A week with no seen count outside 2020
    has no mean; fill_gaps then draws a straight line instead.
    """
    usual = seen[(seen["year"] != m3.COVID_YEAR) & (seen["week"] <= config.MAX_WEEK)]
    mu = usual.groupby("week")["cases"].mean()
    mu[53] = mu.get(52, np.nan)
    return mu


def fill_gaps(seen, lockdowns=config.M3_LOCKDOWNS):
    """Add y (the filled series) and fill_rule (how each week got its value): B3's three steps.

    For each missing week, judged by its Thursday (the Sunday ds + 4 days):
      in a lockdown         -> 0.5 x mu_w
      else June-November    -> 1.0 x mu_w
      else                  -> straight line between the nearest filled neighbours;
                               after the last count, the last filled value
    mu_w comes from seasonal_baseline(seen), so only seen weeks are used. The first
    two rules are B3's own (m3.gap_rule), so the two cannot drift apart.
    """
    mu = seasonal_baseline(seen)
    out = seen.copy()
    out["y"] = out["cases"].astype(float)
    out["fill_rule"] = np.where(out["cases"].notna(), "observed", "")
    for i in out.index[out["cases"].isna()]:
        thursday = (out.at[i, "ds"] + pd.Timedelta(days=4)).date()
        out.at[i, "y"], out.at[i, "fill_rule"] = m3.gap_rule(thursday, mu.get(out.at[i, "week"], np.nan), lockdowns)
    rest = out["y"].isna()
    out["y"] = out["y"].interpolate(method="linear")
    out.loc[rest, "fill_rule"] = "interpolated"
    if out["y"].isna().any():
        raise ValueError("a week is still empty after gap filling")
    return out


def iso_weeks(ds):
    """ISO week number of each MMWR week starting on the Sundays `ds`: the ISO week of its Monday."""
    return (pd.Series(pd.to_datetime(ds)) + pd.Timedelta(days=1)).dt.isocalendar().week.to_numpy(dtype=float)


def m3_forecast(target_year, target_week, cases, cutoff, xgb_params=config.M3_XGB_PARAMS):
    """M3 (B9): refit Prophet + XGBoost on the seen weeks and forecast one target week.

    Returns a dict:
      target_date  the Sunday that starts the target week (Prophet's ds for it)
      mu           the forecast, max(0, yhat + r_hat); the mean of the forecast range (B6)
      prophet      Prophet's yhat for the target week
      residual     XGBoost's correction r_hat
      fit_theta    estimate_theta on Prophet's in-sample fit (clipped at zero), over the
                   seen weeks with a count: the training fit's theta, which B6 uses
                   before 26 past forecasts (module docstring: why not the hybrid's)
      weeks_seen, weeks_filled   training weeks, and how many of them were gaps
    Stops on a target week at or before the cutoff (its count would be in the
    training data), on a week the year does not have (2026 week 53), and on a
    forecast that is not a number (rule 5).
    """
    target = weeks.week_index_of(target_year, target_week)   # stops on a week the year does not have
    if target <= cutoff:
        raise ValueError(f"{target_year} week {target_week} (week index {target}) is not after the cutoff {cutoff}")
    train = fill_gaps(seen_weeks(cases, cutoff))
    target_date = weeks.week_start(target)

    prophet = m3.fit_prophet(train)
    days = pd.concat([train["ds"], pd.Series([pd.Timestamp(target_date)])], ignore_index=True)
    yhat_all = prophet.predict(pd.DataFrame({"ds": days}))["yhat"].to_numpy()
    yhat_train, yhat = yhat_all[:-1], yhat_all[-1]   # the training weeks, then the target week

    features = np.column_stack([yhat_train, iso_weeks(train["ds"])])
    booster = m3.fit_xgboost(features, train["y"].to_numpy() - yhat_train, xgb_params)
    r_hat = float(booster.predict(xgb.DMatrix(np.array([[yhat, iso_weeks([target_date])[0]]])))[0])
    if not np.isfinite(yhat + r_hat):   # before clipping: Python's max(0.0, nan) is 0.0
        raise ValueError(f"M3's forecast for {target_year} week {target_week} is {yhat + r_hat}: an input is missing")
    mu = float(max(0.0, yhat + r_hat))

    counted = (train["fill_rule"] == "observed").to_numpy()
    fitted = np.maximum(0.0, yhat_train[counted])
    return {
        "target_date": target_date, "mu": mu, "prophet": float(yhat), "residual": r_hat,
        "fit_theta": forecast_range.estimate_theta(train["y"][counted], fitted),
        "weeks_seen": len(train), "weeks_filled": int((~counted).sum()),
    }

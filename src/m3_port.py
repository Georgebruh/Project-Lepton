"""M3, the Prophet + XGBoost benchmark, at one forecast day of the backtest."""

import numpy as np
import pandas as pd
import xgboost as xgb

import config
from src import forecast_range, m3, weeks


def seen_weeks(cases, cutoff):
    """The weeks M3 may train on: week_index, year, week, ds (the week's Sunday) and cases."""
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
    """mu_w = mean count of MMWR week w (1-52) over the seen years except 2020, as {w: mu_w}."""
    usual = seen[(seen["year"] != m3.COVID_YEAR) & (seen["week"] <= config.MAX_WEEK)]
    mu = usual.groupby("week")["cases"].mean()
    mu[53] = mu.get(52, np.nan)
    return mu


def fill_gaps(seen, lockdowns=config.M3_LOCKDOWNS):
    """Add y (the filled series) and fill_rule (how each week got its value): the three steps."""
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
    """M3: refit Prophet + XGBoost on the seen weeks and forecast one target week."""
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

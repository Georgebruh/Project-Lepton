"""Reproduce M3, the Prophet + XGBoost benchmark, on the paper's own data."""

import itertools
import json
import logging
import sys
from datetime import timedelta

import numpy as np
import pandas as pd
import xgboost as xgb
from prophet import Prophet
from scipy import stats

import config

logging.getLogger("cmdstanpy").disabled = True   # Prophet's fitter prints two lines per fit
logging.getLogger("prophet").setLevel(logging.WARNING)

COVID_YEAR = 2020   # left out of the seasonal baseline (the paper's rule)
MODELS = ("hybrid", "prophet", "snaive")


# 1. Data and gap filling

def load_series(drop_week_53=config.M3_DROP_WEEK_53):
    """The national series: ds (the ISO Monday), iso_year, iso_week, cases (empty if missing)."""
    df = pd.read_csv(config.PARRENO_WEEKLY, parse_dates=["week_start"])
    df = df.rename(columns={"week_start": "ds"})
    if drop_week_53:
        week_53 = df["iso_week"] == 53
        if df.loc[week_53, "cases"].notna().any():
            raise ValueError("an ISO week 53 has a count; it cannot be dropped")
        df = df[~week_53]
    return df.reset_index(drop=True)


def seasonal_baseline(df):
    """mu_w = mean count of ISO week w over every year except 2020, as {w: mu_w}."""
    mu = df[df["iso_year"] != COVID_YEAR].groupby("iso_week")["cases"].mean()
    mu[53] = mu[52]
    return mu


def in_windows(day, windows):
    """True if `day` falls inside any (first, last) date window, ends included."""
    return any(first <= day <= last for first, last in windows)


def gap_rule(thursday, mu_w, lockdowns):
    """The first two gap rules for one missing week, judged by its Thursday: (value, rule)."""
    if in_windows(thursday, lockdowns):
        return config.M3_COVID_GAP_FACTOR * mu_w, "lockdown"
    first_month, last_month = config.M3_RAINY_MONTHS
    if first_month <= thursday.month <= last_month:
        return config.M3_RAINY_GAP_FACTOR * mu_w, "monsoon"
    return np.nan, ""


def fill_gaps(df, lockdowns=config.M3_LOCKDOWNS):
    """Add y (the filled series) and fill_rule (how each week got its value)."""
    mu = seasonal_baseline(df)
    out = df.copy()
    out["y"] = out["cases"]
    out["fill_rule"] = np.where(out["cases"].notna(), "observed", "")
    for i in out.index[out["cases"].isna()]:
        thursday = (out.at[i, "ds"] + timedelta(days=3)).date()
        out.at[i, "y"], out.at[i, "fill_rule"] = gap_rule(thursday, mu[out.at[i, "iso_week"]], lockdowns)
    rest = out["y"].isna()
    out["y"] = out["y"].interpolate(method="linear")
    out.loc[rest, "fill_rule"] = "interpolated"
    if out["y"].isna().any():
        raise ValueError("a week is still empty after gap filling")
    return out


# 2-3. Prophet and XGBoost

def fit_prophet(train):
    """Prophet with the paper's settings, fitted on columns ds and y."""
    model = Prophet(
        growth="linear",
        seasonality_mode=config.M3_SEASONALITY_MODE,
        changepoint_prior_scale=config.M3_CHANGEPOINT_PRIOR,
        weekly_seasonality=True,
        yearly_seasonality=True,
        daily_seasonality=False,
        uncertainty_samples=0,   # only yhat is used; this skips the random range draws
    )
    model.fit(train[["ds", "y"]])
    return model


def fit_xgboost(features, target, xgb_params, rounds=config.M3_XGB_ROUNDS):
    """XGBoost regression trees (squared error) with `rounds` boosting rounds."""
    return xgb.train(dict(xgb_params), xgb.DMatrix(features, label=target), num_boost_round=rounds)


def xgb_settings(xgb_params):
    """The tree settings xgboost actually used, read back from a fitted model (for the record)."""
    booster = fit_xgboost(np.array([[0.0, 1.0], [1.0, 2.0]]), np.array([0.0, 1.0]), xgb_params)
    learner = json.loads(booster.save_config())["learner"]
    tree = learner["gradient_booster"]["tree_train_param"]
    keep = ("eta", "max_depth", "min_child_weight", "subsample", "colsample_bytree", "lambda", "alpha", "gamma")
    return {"objective": learner["objective"]["name"], "rounds": config.M3_XGB_ROUNDS,
            **{key: tree[key] for key in keep if key in tree}}


# 4-5. Rolling origin and the hybrid forecast

def fold_rows():
    """[(training rows, forecast rows)] for the 9 folds, as row positions."""
    folds = []
    for k in range(config.M3_FOLDS):
        origin = config.M3_FIRST_WINDOW + config.M3_STEP * k
        folds.append((range(0, origin), range(origin, origin + config.M3_HORIZON)))
    return folds


def prophet_folds(series):
    """Fit Prophet once per fold; keep train, test and Prophet's yhat on both."""
    folds = []
    for k, (train_rows, test_rows) in enumerate(fold_rows()):
        train, test = series.iloc[train_rows], series.iloc[test_rows]
        if (test["fill_rule"] != "observed").any():
            raise ValueError(f"fold {k + 1} would score a gap-filled week")
        prophet = fit_prophet(train)
        folds.append({
            "fold": k + 1, "train": train, "test": test,
            "yhat_train": prophet.predict(train[["ds"]])["yhat"].to_numpy(),
            "yhat_test": prophet.predict(test[["ds"]])["yhat"].to_numpy(),
            "snaive": series["y"].to_numpy()[np.array(test_rows) - config.M3_SEASONAL_PERIOD],
        })
    return folds


def hybrid_forecast(fold, xgb_params, rounds=config.M3_XGB_ROUNDS, leak=False):
    """max(0, yhat + r_hat) for the fold's forecast weeks."""
    train, test = fold["train"], fold["test"]
    features = np.column_stack([fold["yhat_train"], train["iso_week"]])
    target = train["y"].to_numpy() - fold["yhat_train"]
    features_test = np.column_stack([fold["yhat_test"], test["iso_week"]])
    if leak:
        features = np.vstack([features, features_test])
        target = np.concatenate([target, test["y"].to_numpy() - fold["yhat_test"]])
    booster = fit_xgboost(features, target, xgb_params, rounds)
    r_hat = booster.predict(xgb.DMatrix(features_test))
    return np.maximum(0.0, fold["yhat_test"] + r_hat)


def forecasts_table(folds, xgb_params):
    """One row per forecast week: fold, ds, iso_year, iso_week, actual, hybrid, prophet, snaive."""
    rows = []
    for fold in folds:
        test = fold["test"]
        rows.append(pd.DataFrame({
            "fold": fold["fold"], "ds": test["ds"].dt.date, "iso_year": test["iso_year"],
            "iso_week": test["iso_week"], "actual": test["y"],
            "hybrid": hybrid_forecast(fold, xgb_params), "prophet": fold["yhat_test"],
            "snaive": fold["snaive"],
        }))
    return pd.concat(rows, ignore_index=True)


# 6. Scores

def scores(actual, forecast):
    """MAE, RMSE, SMAPE (0-200 scale) and bias = mean(forecast - actual)."""
    actual, forecast = np.asarray(actual, float), np.asarray(forecast, float)
    error = forecast - actual
    return {
        "mae": np.mean(np.abs(error)),
        "rmse": np.sqrt(np.mean(error ** 2)),
        "smape": 100 * np.mean(2 * np.abs(error) / (np.abs(actual) + np.abs(forecast))),
        "bias": np.mean(error),
    }


def dm_test(actual, forecast_a, forecast_b):
    """Diebold-Mariano test, absolute errors, h = 1: is model a's error smaller than b's?"""
    d = np.abs(np.asarray(forecast_a) - actual) - np.abs(np.asarray(forecast_b) - actual)
    n = len(d)
    stat = d.mean() / (d.std(ddof=1) / np.sqrt(n))
    return stat, stats.t.cdf(stat, df=n - 1)


def score_table(forecasts):
    """Scores of each model beside the paper: Table I (all weeks) and Table II (peak weeks)."""
    peak = forecasts["actual"] > config.M3_PEAK_CASES
    rows = []
    for table, weeks, paper in (("I", forecasts.index == forecasts.index, config.M3_TABLE_I),
                                ("II", peak, config.M3_TABLE_II)):
        for model in MODELS:
            row = {"table": table, "weeks": int(weeks.sum()), "model": model,
                   **scores(forecasts.loc[weeks, "actual"], forecasts.loc[weeks, model])}
            row.update({f"paper_{key}": value for key, value in paper[model].items()})
            row["mae_gap_pct"] = 100 * (row["mae"] - row["paper_mae"]) / row["paper_mae"]
            rows.append(row)
    return pd.DataFrame(rows)


# Runs

def runs():
    """The runs to make: name -> (drop_week_53, lockdowns, xgb_params)."""
    drop = config.M3_DROP_WEEK_53
    return {
        "main": (drop, config.M3_LOCKDOWNS, config.M3_XGB_PARAMS),
        "max_depth_2": (drop, config.M3_LOCKDOWNS, config.M3_XGB_PARAMS_TEST),
        "other_week_53": (not drop, config.M3_LOCKDOWNS, config.M3_XGB_PARAMS),
        "lockdown_all_2020": (drop, config.M3_LOCKDOWNS_TEST, config.M3_XGB_PARAMS),
    }


def print_run(name, series, forecasts, table, dm):
    """Print one run's setup, gap filling and scores beside the paper."""
    first, last = forecasts.iloc[0], forecasts.iloc[-1]
    print(f"=== {name}: {len(series)} weeks; scored {first.iso_year}-W{first.iso_week:02d} "
          f"to {last.iso_year}-W{last.iso_week:02d}")
    print("    gaps filled:", series["fill_rule"].value_counts().drop("observed").to_dict())
    print(table[["table", "weeks", "model", "mae", "paper_mae", "mae_gap_pct", "rmse", "paper_rmse",
                 "smape", "paper_smape", "bias", "paper_bias"]].round(2).to_string(index=False))
    print(f"    Table III, DM hybrid vs prophet: {dm[0]:.4f}, p = {dm[1]:.4f} "
          f"(paper {config.M3_TABLE_III_DM['stat']}, p = {config.M3_TABLE_III_DM['p']})\n")


def main():
    """Run every variant, print each beside the paper, save the scores and forecasts."""
    print(f"xgboost {xgb.__version__}, default settings: {xgb_settings(config.M3_XGB_PARAMS)}\n")
    all_scores, all_forecasts = [], []
    for name, (drop_week_53, lockdowns, xgb_params) in runs().items():
        series = fill_gaps(load_series(drop_week_53), lockdowns)
        forecasts = forecasts_table(prophet_folds(series), xgb_params)
        table = score_table(forecasts)
        dm = dm_test(forecasts["actual"], forecasts["hybrid"], forecasts["prophet"])
        print_run(f"{name} (drop_week_53={drop_week_53}, xgb={xgb_params or 'defaults'})",
                  series, forecasts, table, dm)
        all_scores.append(table.assign(run=name, dm_stat=dm[0], dm_p=dm[1]))
        all_forecasts.append(forecasts.assign(run=name))

    main_table = all_scores[0].query("table == 'I'").set_index("model")
    for model in ("hybrid", "prophet"):
        gap = main_table.at[model, "mae_gap_pct"]
        verdict = "PASS" if abs(gap) <= 100 * config.M3_TOLERANCE else "OUTSIDE"
        print(f"{verdict}  {model} MAE {main_table.at[model, 'mae']:.2f} vs paper "
              f"{config.M3_TABLE_I[model]['mae']} ({gap:+.1f}%, tolerance {100 * config.M3_TOLERANCE:.0f}%)")

    config.M3_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(all_scores).round(4).to_csv(config.M3_RESULTS, index=False)
    pd.concat(all_forecasts).round(4).to_csv(config.M3_FORECASTS, index=False)
    print(f"\nwrote {config.M3_RESULTS} and {config.M3_FORECASTS}")


def diagnose():
    """Why the hybrid misses: every XGBoost setting in the config grid, then a leakage check."""
    series = fill_gaps(load_series(config.M3_DROP_WEEK_53), config.M3_LOCKDOWNS)
    folds = prophet_folds(series)
    actual = np.concatenate([fold["test"]["y"].to_numpy() for fold in folds])
    prophet = np.concatenate([fold["yhat_test"] for fold in folds])

    rows = []
    for leak in (False, True):
        for depth, rounds, eta in itertools.product(config.M3_DIAG_MAX_DEPTH, config.M3_DIAG_ROUNDS,
                                                    config.M3_DIAG_ETA):
            params = {"max_depth": depth, "eta": eta}
            hybrid = np.concatenate([hybrid_forecast(fold, params, rounds, leak) for fold in folds])
            dm = dm_test(actual, hybrid, prophet)
            rows.append({"leak": leak, "max_depth": depth, "rounds": rounds, "eta": eta,
                         **scores(actual, hybrid), "dm_stat": dm[0], "dm_p": dm[1]})
    grid = pd.DataFrame(rows)

    target = config.M3_TABLE_I["hybrid"]["mae"]
    print(f"Prophet alone: MAE {scores(actual, prophet)['mae']:.2f}; paper's hybrid: {target}")
    for leak, part in grid.groupby("leak"):
        label = "LEAK (XGBoost also sees the forecast weeks' errors)" if leak else "honest"
        near = (part["mae"] - target).abs() <= config.M3_TOLERANCE * target
        print(f"\n{label}: {len(part)} settings, hybrid MAE min {part['mae'].min():.2f}, "
              f"median {part['mae'].median():.2f}, max {part['mae'].max():.2f}; "
              f"within 10% of {target}: {int(near.sum())}")
        print(part.nsmallest(5, "mae")[["max_depth", "rounds", "eta", "mae", "rmse", "smape", "bias",
                                         "dm_stat", "dm_p"]].round(3).to_string(index=False))
    grid.round(4).to_csv(config.M3_DIAGNOSTICS, index=False)
    print(f"\nwrote {config.M3_DIAGNOSTICS}")


if __name__ == "__main__":
    diagnose() if "--diagnose" in sys.argv else main()

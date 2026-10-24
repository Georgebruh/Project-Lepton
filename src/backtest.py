"""The backtest loop."""

import argparse
import time

import numpy as np
from epiweeks import Year
import pandas as pd

import config
from src import baselines, forecast_range, m4, population, scores, thresholds, view, weeks

M4_NO_EI2 = config.FLOOD_TEST[1]   # "M4_no_EI2", M4 without EI2: the name the comparisons, figures and app read
MODELS = ("M0", "M1", "M3", "M4", M4_NO_EI2)
# The quantiles behind WIS's 11 central ranges, plus the median: 0.01, 0.025, ..., 0.5, ..., 0.99
QUANTILES = sorted({0.5} | {round(a / 2, 4) for a in config.WIS_ALPHAS} | {round(1 - a / 2, 4) for a in config.WIS_ALPHAS})
QUANTILE_COLUMNS = [f"q{q:.3f}" for q in QUANTILES]
PROGRESS_EVERY = 26   # print a line every half year of forecast days


# Inputs

def load_cases(path=config.CASES_WEEKLY):
    """The weekly table (week_index, year, week, cases)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run task A13, or test with --simulate")
    return pd.read_csv(path)[view.COLUMNS]


def load_features(path=config.FEATURES_WEEKLY):
    """The weekly rain and exposure: fit_year, week_index, rcum2 (mm) and ei2 (%), for M4."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run python -m src.features (B4)")
    table = pd.read_csv(path)
    return table[["fit_year", "week_index", "rcum2_mm", "ei2"]].rename(columns={"rcum2_mm": "rcum2"})


def load_population(path=config.POP_WEEKLY):
    """The weekly population (week_index, pop); rebuilt with population.weekly_population if absent."""
    table = pd.read_csv(path) if path.exists() else population.weekly_population()
    return table[["week_index", "pop"]]


def features_for(features, fit_year):
    """The rain and exposure rows of one fit year: return levels fitted on the years before it."""
    rows = features[features["fit_year"] == fit_year]
    if rows.empty:
        raise ValueError(f"features_weekly.csv has no rows with fit_year {fit_year}: rerun C3 and B4")
    return rows[["week_index", "rcum2", "ei2"]]


def simulated_cases(features, pop, seed=config.RANDOM_SEED):
    """Made-up QC-shaped weekly counts, 2015 week 1 to the last week with rain, for testing."""
    rng = np.random.default_rng(seed)
    true, base, theta = config.S5_TRUE, config.S5_BASE, config.S5_THETA
    rain = features_for(features, features["fit_year"].max()).set_index("week_index")
    t = np.arange(0, int(rain.index.max()) + 1)
    rcum2 = rain["rcum2"].reindex(t).to_numpy()
    ei2 = rain["ei2"].reindex(t).fillna(0).to_numpy()   # EI2 of week 0 needs week -1: 0
    P = pop.set_index("week_index")["pop"].reindex(t).to_numpy()
    year = np.array([weeks.year_week(i)[0] for i in t])
    season = m4.season_terms(t)
    covid = np.isin(year, config.COVID_YEARS)

    y = np.zeros(len(t))
    start = config.S5_SIM["start_cases"]
    y[:2] = rng.negative_binomial(theta, theta / (theta + start), 2)
    for s in range(2, len(t)):
        log_mu = (np.log(P[s - 1]) + base["Intercept"]
                  + sum(base[col] * season.at[s, col] for col in m4.SEASON)
                  + true["rho"] * np.log1p(y[s - 1] + y[s - 2])
                  + true["beta1"] * rcum2[s - 1] / config.RAIN_SCALE_MM + true["beta2"] * ei2[s - 1]
                  + true["delta"] * covid[s])
        mu = np.exp(log_mu)
        y[s] = rng.negative_binomial(theta, theta / (theta + mu))
    year_week = [weeks.year_week(i) for i in t]
    return pd.DataFrame({"week_index": t, "year": [yw[0] for yw in year_week],
                         "week": [yw[1] for yw in year_week], "cases": y})


# The training fit's theta for M0 and M1

def m0_fit_theta(cases, cut):
    """M0's training-fit theta: estimate_theta of y(s) against y(s - 52) over the weeks it can see."""
    seen = cases[(cases["week_index"] <= cut) & cases["cases"].notna()]
    counts = seen.set_index("week_index")["cases"]
    pairs = pd.DataFrame({"year": seen["year"].to_numpy(), "y": counts.to_numpy(),
                          "mu": counts.reindex(counts.index - config.M0_LAG_WEEKS).to_numpy()})
    pairs = pairs[~pairs["year"].isin(config.COVID_YEARS)].dropna().tail(config.THETA_WINDOW)
    return forecast_range.estimate_theta(pairs["y"], pairs["mu"])


def m1_fit_theta(target_year, cases, cut):
    """M1's training-fit theta: estimate_theta of the reference years' counts against their week means."""
    years = thresholds.reference_years(target_year, cases, cut)
    rows = cases[cases["year"].isin(years) & (cases["week"] <= config.MAX_WEEK)]
    means = rows.groupby("week")["cases"].transform("mean")
    return forecast_range.estimate_theta(rows["cases"], means)


# One forecast day

def model_means(T, cases, features, pop, option, g, models=MODELS):
    """Each model's forecast mean for target week T + h: {model: (mu, fit_theta, detail)}."""
    cut = view.cutoff(T, option, g)
    year, week = weeks.year_week(T + config.FORECAST_HORIZON_WEEKS)
    out = {}
    if "M0" in models:
        out["M0"] = (baselines.m0_forecast(year, week, cases, cut), m0_fit_theta(cases, cut), "")
    if "M1" in models:
        out["M1"] = (baselines.m1_forecast(year, week, cases, cut), m1_fit_theta(year, cases, cut), "")
    if "M3" in models:
        from src import m3_port   # imports Prophet and xgboost; only M3 needs them
        got = m3_port.m3_forecast(year, week, cases, cut)
        out["M3"] = (got["mu"], got["fit_theta"],
                     f"prophet {got['prophet']:.2f}, residual {got['residual']:.2f}, {got['weeks_filled']} weeks filled")
    wanted = [(name, with_ei) for name, with_ei in (("M4", True), (M4_NO_EI2, False)) if name in models]
    if wanted:
        rain = features_for(features, weeks.year_week(T)[0])
        train = m4.model_rows(view.training_rows(cases, T, option, g), rain, pop)
        target = m4.model_rows(view.prediction_row(cases, T, option, g), rain, pop)
        for name, with_ei in wanted:
            fit = m4.fit_m4(train, with_ei=with_ei)
            left_out = [term for term in m4.ALL_TERMS if term not in fit["terms"] and (with_ei or term != m4.EI)]
            detail = f"{fit['rows']} rows, {fit['method']}" + (f", left out {' '.join(left_out)}" if left_out else "")
            out[name] = (float(m4.predict_m4(fit, target)[0]), fit["theta"], detail)
    return out


def forecast_day(T, cases, features, pop, past, option, g, models=MODELS):
    """Every model's forecast at forecast day T: one row per model."""
    h = config.FORECAST_HORIZON_WEEKS
    cut = view.cutoff(T, option, g)
    year, week = weeks.year_week(T + h)
    t_w = thresholds.epidemic_threshold(year, week, cases, cut)
    rows = []
    for model, (mu, fit_theta, detail) in model_means(T, cases, features, pop, option, g, models).items():
        scored = len(forecast_range.scored_past(past[model], cases, cut))
        theta = forecast_range.theta_for(past[model], cases, cut, fit_theta)
        dist = forecast_range.forecast_dist(mu, theta)
        row = {"model": model, "forecast_week": T, "cutoff": cut, "fit_year": weeks.year_week(T)[0],
               "week_index": T + h, "year": year, "week": week, "mu": mu, "theta": theta,
               "theta_from": "past" if scored >= config.THETA_MIN_FORECASTS else "fit",
               "past_scored": scored, "threshold": t_w, "p_breach": float(thresholds.breach_probability(dist, t_w))}
        row.update({col: float(dist.ppf(q)) for col, q in zip(QUANTILE_COLUMNS, QUANTILES)})
        row["detail"] = detail
        rows.append(row)
    table = pd.DataFrame(rows)
    check_numbers(table)
    return table


def check_numbers(table):
    """Stop on a NaN in any number column; theta may be infinity (a Poisson range)."""
    numbers = table.select_dtypes("number")
    bad = numbers.columns[numbers.isna().any()].tolist()
    finite = numbers.drop(columns=["theta"])
    bad += finite.columns[~np.isfinite(finite).all()].tolist()
    if bad:
        raise ValueError(f"forecast days {sorted(table['forecast_week'].unique())[:5]}: "
                         f"NaN or infinite values in {sorted(set(bad))}")


# The loop

def forecast_days(cases, features, option, g):
    """The forecast days T (week indexes), first to last."""
    h = config.FORECAST_HORIZON_WEEKS
    first = weeks.week_index_of(config.BACKTEST_FIRST_YEAR, 1)
    last_count = int(cases.loc[cases["cases"].notna(), "week_index"].max())
    last_year_end = weeks.week_index_of(config.BACKTEST_LAST_YEAR, 1) + Year(config.BACKTEST_LAST_YEAR).totalweeks() - 1
    last = min(last_count - h, int(features["week_index"].max()), last_year_end)
    planned = first
    while len(thresholds.reference_years(weeks.year_week(first + h)[0], cases, view.cutoff(first, option, g))) \
            < config.THRESHOLD_MIN_YEARS:
        first += 1
        if first > last:
            raise ValueError(f"no forecast day has {config.THRESHOLD_MIN_YEARS} complete reference years")
    if first != planned:
        print(f"option {option}, g = {g}: first forecast day moved from {weeks.year_week(planned)} to "
              f"{weeks.year_week(first)} (year, week): fewer than {config.THRESHOLD_MIN_YEARS} complete "
              f"reference years before it")
    if last < first:
        raise ValueError(f"the data end at week index {last_count}: no forecast day from {weeks.year_week(first)}")
    return list(range(first, last + 1))


def run_backtest(cases, features, pop, option, g=config.DELAY_GUARD_G, models=MODELS, days=None):
    """The whole loop: every forecast day's forecasts, then each row's outcome (y, breached)."""
    view.guard_weeks(option, g)   # stops on an option not set (None) or not built (A)
    plan = forecast_days(cases, features, option, g)[:days]
    past = {model: pd.DataFrame({"week_index": pd.Series(dtype=int), "mu": pd.Series(dtype=float)}) for model in models}
    tables, start = [], time.time()
    print(f"{len(plan)} forecast days, {weeks.year_week(plan[0])} to {weeks.year_week(plan[-1])} (year, week); "
          f"option {option}" + (f", g = {g}" if option == "C" else "") + f"; models {', '.join(models)}")
    for n, T in enumerate(plan, 1):
        day = forecast_day(T, cases, features, pop, past, option, g, models)
        for model, group in day.groupby("model"):
            past[model] = pd.concat([past[model], group[["week_index", "mu"]]], ignore_index=True)
        tables.append(day)
        if n % PROGRESS_EVERY == 0 or n == len(plan):
            print(f"  {n}/{len(plan)} forecast days, {time.time() - start:.0f} s")
    table = pd.concat(tables, ignore_index=True)
    table.insert(0, "option", option)
    table.insert(1, "g", g if option == "C" else 0)
    return add_outcomes(table, cases)


def add_outcomes(table, cases):
    """Each row's final count y and breached = y > the row's own T_w."""
    counts = cases.set_index("week_index")["cases"]
    out = table.copy()
    out["y"] = counts.reindex(out["week_index"]).to_numpy()
    if out["y"].isna().any():
        missing = sorted(out.loc[out["y"].isna(), "week_index"].unique())
        raise ValueError(f"target weeks {missing[:5]} have no count: they cannot be scored")
    out["breached"] = thresholds.breached(out["y"], out["threshold"])
    scores.check_same_weeks(out)   # every model on exactly the same target weeks
    return out


def output_path(simulate, option, g, partial):
    """forecasts.csv for the real run; the simulated (per option), guard (g) and partial runs get their own names."""
    name = "forecasts"
    if simulate:
        name += f"_simulated_{option}"
    if option == "C" and g != config.DELAY_GUARD_G:
        name += f"_g{g}"
    if partial:
        name += "_partial"
    return config.FORECASTS.with_name(f"{name}.csv")


def write(table, path):
    """Save via a .part file, so a stopped run never leaves half a table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    table.round(4).to_csv(part, index=False)
    part.replace(path)


def summary(table):
    """Each model's scores over the MAE years the run holds: a first look, not the D results."""
    years = [year for year in config.MAE_YEARS if year in set(table["year"])]
    if not years:
        return "no target week in the MAE years yet"
    by_model = scores.score_models(table, years)
    by_model["brier"] = table[table["year"].isin(years)].groupby("model").apply(
        lambda group: np.mean((group["p_breach"] - group["breached"]) ** 2))
    return f"target years {years}:\n" + by_model.round(3).to_string()


def main():
    parser = argparse.ArgumentParser(description="B10: the weekly backtest loop")
    parser.add_argument("--simulate", action="store_true", help="made-up QC-shaped counts instead of A13's file")
    parser.add_argument("--option", choices=("B", "C"), default=config.DATA_OPTION,
                        help="decision-tree row (default config.DATA_OPTION)")
    parser.add_argument("--g", type=int, default=config.DELAY_GUARD_G, help="delay guard in weeks, option C")
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--days", type=int, help="run only the first N forecast days (a quick test)")
    args = parser.parse_args()

    features, pop = load_features(), load_population()
    cases = simulated_cases(features, pop) if args.simulate else load_cases()
    if args.simulate:
        print("made-up counts (simulated_cases), not QC data")
    models = [model for model in MODELS if model in args.models]
    table = run_backtest(cases, features, pop, args.option, args.g, models, args.days)
    path = output_path(args.simulate, args.option, args.g, partial=args.days is not None or models != list(MODELS))
    write(table, path)
    print(f"\n{summary(table)}\n\nwrote {path} ({len(table)} rows)")


if __name__ == "__main__":
    main()

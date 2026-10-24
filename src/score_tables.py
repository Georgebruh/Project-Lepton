"""Every score the paper's results quote, from the forecasts."""

import numpy as np
import pandas as pd

import config
from src import backtest, breach_scores, compare, forecast_run, observed_run, scores
from src.paper_figures import figure2_table, load_forecasts, ordered_models

WINDOWS = {"MAE years": config.MAE_YEARS, "prob years": config.PROB_SCORE_YEARS, "all years": config.ALL_YEARS}
SCORE_COLUMNS = ["window", "model", "weeks", "mae", "rmse", "bias", "mase", "wis", "coverage_50", "coverage_90",
                 "breaches", "brier", "bss", "bss_weeks"]
# Columns these tables read beyond the ones the loader checks.
RUN_COLUMNS = ["cutoff", "option", "g"]


# 1. Scores per window

def week_outcomes(table):
    """One row per target week: week_index, year and breached, which every model shares."""
    weeks = table[["week_index", "year", "breached"]].drop_duplicates()
    if weeks["week_index"].duplicated().any():
        raise ValueError("models disagree on whether a week breached: T_w must not depend on the model")
    return weeks.sort_values("week_index")


def usual_rates(cutoffs, outcomes):
    """obar at each forecast day (breach_scores.base_rate), NaN where no week from 2018 is visible yet."""
    counted = outcomes[(outcomes["year"] >= config.BACKTEST_FIRST_YEAR) & ~outcomes["year"].isin(config.COVID_YEARS)]
    first = counted["week_index"].min()
    return np.array([breach_scores.base_rate(outcomes, cut) if cut >= first else np.nan for cut in cutoffs])


def breach_window_scores(group, outcomes):
    """Breaches, Brier score and Brier skill score of one model's forecasts in one window."""
    group = group.sort_values("week_index")
    p = group["p_breach"].to_numpy(dtype=float)
    o = group["breached"].to_numpy(dtype=float)
    obar = usual_rates(group["cutoff"], outcomes)
    known = ~np.isnan(obar)
    return {"breaches": int(o.sum()), "brier": breach_scores.brier(p, o),
            "bss": breach_scores.brier_skill_score(p[known], o[known], obar[known]), "bss_weeks": int(known.sum())}


def window_scores(table, years, window, denominator, outcomes):
    """Every model's scores, MASE and breach scores over the target weeks in `years`."""
    by_model = scores.add_mase(scores.score_models(table, years), denominator)
    rows = table[table["year"].isin(years)]
    breach = pd.DataFrame.from_dict({model: breach_window_scores(group, outcomes)
                                     for model, group in rows.groupby("model")}, orient="index")
    out = by_model.join(breach).loc[ordered_models(by_model.index)].reset_index()
    out.insert(0, "window", window)
    return out


def score_table(table, cases):
    """d1_scores.csv: one row per window and model, the model order within each window."""
    denominator = scores.mase_denominator(cases)
    outcomes = week_outcomes(table)
    parts = [window_scores(table, years, window, denominator, outcomes) for window, years in WINDOWS.items()]
    return pd.concat(parts, ignore_index=True)[SCORE_COLUMNS]


def mae_by_year(table):
    """d1_mae_by_year.csv: each model's MAE in each target year, one row per year."""
    scores.check_same_weeks(table)
    table = table.assign(miss=(table["y"] - table["mu"]).abs())
    out = table.pivot_table(index="year", columns="model", values="miss", aggfunc="mean")
    out = out[ordered_models(out.columns)]
    out.insert(0, "weeks", table.groupby("year")["week_index"].nunique())
    out.insert(1, "in_headline", out.index.isin(config.MAE_YEARS))
    return out.reset_index()


# 2. Alarms, episodes and lead time

def alarm_row(group, option, g):
    """One model's alarm test and, on the second half, its episodes and lead time."""
    group = group.sort_values("week_index")
    test = breach_scores.alarm_test(group["p_breach"], group["breached"].astype(float))
    p_star = test["first_half"]["p_star"]
    second = group.iloc[len(group) // 2:].rename(columns={"p_breach": "p"})
    leads = breach_scores.lead_times(second[["week_index", "year", "p", "breached"]], p_star, option=option, g=g)
    advance = breach_scores.caught_in_advance(leads)
    alarmed = breach_scores.caught_share(advance["alarmed"], advance["n"])
    row = {"model": group["model"].iloc[0], "p_star": p_star}
    for half in ("first_half", "second_half"):
        for key in ("alarms", "breaches", "precision", "sensitivity", "f1"):
            row[f"{half}_{key}"] = test[half][key]
    row["second_half_weeks"] = len(second)
    row["second_half_from"] = int(second["week_index"].min())
    row.update({"episodes": advance["n"], "alarmed": alarmed["k"], "alarmed_low": alarmed["low"],
                "alarmed_high": alarmed["high"], "in_advance": advance["k"], "in_advance_low": advance["low"],
                "in_advance_high": advance["high"], "median_lead_weeks": advance["median_lead_weeks"]})
    return row


def alarm_table(table, years=config.PROB_SCORE_YEARS):
    """d3_alarms.csv: one row per model over `years` (2022-2026)."""
    rows = table[table["year"].isin(years)]
    option, g = str(table["option"].iloc[0]), int(table["g"].iloc[0])
    return pd.DataFrame([alarm_row(rows[rows["model"] == model], option, g)
                         for model in ordered_models(rows["model"].unique())])


def precision_recall(table, years=config.PROB_SCORE_YEARS):
    """d3_precision_recall.csv: per model, alarms, precision, sensitivity and F1 at every cut-off it uses."""
    rows = table[table["year"].isin(years)]
    parts = []
    for model in ordered_models(rows["model"].unique()):
        group = rows[rows["model"] == model]
        p, o = group["p_breach"].to_numpy(dtype=float), group["breached"].to_numpy(dtype=float)
        curve = pd.DataFrame([breach_scores.alarm_scores(p, o, cut) for cut in np.unique(p)])
        parts.append(curve.rename(columns={"p_star": "cutoff"}).assign(model=model, forecasts=len(group)))
    out = pd.concat(parts, ignore_index=True)
    return out[["model", "forecasts", "cutoff", "alarms", "breaches", "precision", "sensitivity", "f1"]]


# 3. The all-years check and the guard reruns

def all_years_tests(table):
    """d5_d6_all_years.csv: the comparisons over 2018-2026, every block length."""
    return pd.concat([compare.primary_endpoint(table, config.ALL_YEARS),
                      compare.flood_and_practical_tests(table, config.ALL_YEARS)], ignore_index=True)


def guard_paths():
    """The forecasts for g = 2 and each guard rerun that is on disk: {g: path}; prints any rerun missing."""
    paths = {config.DELAY_GUARD_G: config.FORECASTS}
    for g in config.DELAY_GUARD_G_TESTS:
        path = backtest.output_path(False, "C", g, False)
        if path.exists():
            paths[g] = path
        else:
            print(f"no guard rerun for g = {g} ({path.name}): python -m src.backtest --g {g}")
    return dict(sorted(paths.items()))


def guard_table(paths):
    """d5_guard_reruns.csv: the figure 2 numbers (8-week blocks) for each g, None with no rerun on disk."""
    if len(paths) == 1:
        return None
    parts = []
    for g, path in paths.items():
        fig2 = figure2_table(load_forecasts(path))
        parts.append(fig2[fig2["block_weeks"] == config.BOOT_BLOCK_WEEKS].assign(g=g, source=path.name))
    out = pd.concat(parts, ignore_index=True)
    return out[["g", "source", *[col for col in out.columns if col not in ("g", "source")]]]


# Running it

def load_run(path):
    """The forecasts, checked as the figures check them, then the three columns only these tables read."""
    table = load_forecasts(path)
    absent = [col for col in RUN_COLUMNS if col not in table]
    if absent:
        raise ValueError(f"{path.name} has no columns {absent}: is it B10's forecasts table?")
    if table[RUN_COLUMNS].isna().any().any():
        raise ValueError(f"{path.name} has missing values in {RUN_COLUMNS}: rerun B10 (rule 5)")
    return table


def report(tables):
    """Print every table written, rounded for the eye (the files keep 4 decimals)."""
    for path, table in tables.items():
        print(f"\n{path.name}:")
        observed_run.print_table(table, float_format="{:.3f}".format, na_rep="")


def main():
    table = load_run(config.FORECASTS)
    if str(table["option"].iloc[0]) != config.DATA_OPTION or int(table["g"].iloc[0]) != config.DELAY_GUARD_G:
        raise ValueError(f"{config.FORECASTS.name} is option {table['option'].iloc[0]}, g = {table['g'].iloc[0]}; "
                         f"config says {config.DATA_OPTION}, g = {config.DELAY_GUARD_G}: rerun python -m src.backtest")
    cases = backtest.load_cases()

    # Every table is built and checked before any file is written.
    tables = {config.D_SCORES: score_table(table, cases), config.D_MAE_BY_YEAR: mae_by_year(table),
              config.D_ALARMS: alarm_table(table), config.D_PRECISION_RECALL: precision_recall(table),
              config.D_TESTS_ALL_YEARS: all_years_tests(table)}
    guard = guard_table(guard_paths())
    if guard is not None:
        tables[config.D_GUARD_RERUNS] = guard

    for path, out in tables.items():
        forecast_run.write(out.round(4), path)
    report({path: out for path, out in tables.items() if path != config.D_PRECISION_RECALL})
    print("\nwrote:\n  " + "\n  ".join(f"results/{path.name}" for path in tables))


if __name__ == "__main__":
    main()

"""Every score the paper's results quote, from B10's forecasts (D1-D4, D5-D6's checks; for E6).

D1-D6 are functions in src/scores.py, src/breach_scores.py and src/compare.py. This file
applies them to B10's results/forecasts.csv and writes the tables E6 quotes, so every number
in the paper's results traces to a file in results/. It adds no new method. D8's figure 2
table (results/d8_fig2_mae.csv) already holds the headline MAEs and D5's and D6's tests.

1. d1_scores.csv: each model's scores in three windows (lepton-plan.md, Workstream D's table):
     MAE years   2018-2019 and 2022-2026 (config.MAE_YEARS): MAE, RMSE, bias and MASE are
                 headline here; they need no forecast spread, so the spread's warm-up counts
     prob years  2022-2026 (config.PROB_SCORE_YEARS): WIS, 50% and 90% coverage, the Brier
                 score and the Brier skill score are headline here, after the warm-up
     all years   2018-2026 (config.ALL_YEARS): every score, COVID years included, a check
   Each window's row holds every score; read each score from its headline window.
       Brier skill score = 1 - BS / mean (obar_t - o_t)^2, where obar_t is the share of
       non-COVID weeks from 2018 up to forecast t's cutoff that breached (D3). The first
       forecast days of 2018 see no such week yet, so they have no obar_t; the all-years
       BSS leaves them out, and bss_weeks counts the forecasts it uses.
2. d1_mae_by_year.csv: each model's MAE in each target year (D1), to show which years drive
   the differences. The COVID years are listed but are not in any headline score.
3. d3_alarms.csv: per model, the alarm test (D3) and lead time (D4) over 2022-2026:
       p* = the cut-off with the best F1 on the first half of the forecast days (in time
       order); precision, sensitivity and F1 on both halves. Then the second half's outbreak
       episodes (breach weeks at most config.EPISODE_GAP_WEEKS apart): how many had an alarm
       for one of their breach weeks, and how many were caught in advance (lead time at
       least 1 week, D4), each "k of n" with an exact 95% interval, and the median lead time.
4. d3_precision_recall.csv: the full precision-recall curve behind p* (the assumptions
   table's test of it): per model, for every cut-off among its own 2022-2026 breach
   probabilities, the alarms, precision, sensitivity and F1 over those forecasts.
5. d5_d6_all_years.csv: D5's and D6's comparisons again over 2018-2026, COVID years in.
6. d5_guard_reruns.csv, when B10's guard reruns are on disk (python -m src.backtest --g 1 and
   --g 3): for g = 1, 2 and 3 (config.DELAY_GUARD_G_TESTS), D8's figure 2 numbers (each
   model's MAE over the MAE years, then D5's and D6's comparisons, 8-week blocks), each run
   on its own forecast days.

Rule 5: every table is built from forecasts that D8's loader has checked (every model on the
same weeks, nothing missing), and every table is built before any file is written.

Run from the repository root, after B10 (and, if wanted, its guard reruns); seconds:
    python -m src.score_tables
"""

import numpy as np
import pandas as pd

import config
from src import backtest, breach_scores, compare, forecast_run, observed_run, scores
from src.paper_figures import figure2_table, load_forecasts, ordered_models

WINDOWS = {"MAE years": config.MAE_YEARS, "prob years": config.PROB_SCORE_YEARS, "all years": config.ALL_YEARS}
SCORE_COLUMNS = ["window", "model", "weeks", "mae", "rmse", "bias", "mase", "wis", "coverage_50", "coverage_90",
                 "breaches", "brier", "bss", "bss_weeks"]


# ---------------------------------------------------------------------------
# 1. Scores per window (D1, D2, D3)
# ---------------------------------------------------------------------------

def week_outcomes(table):
    """One row per target week: week_index, year and breached, which every model shares.

    The threshold T_w comes from the counts alone (B7), so every model's row for a week
    has the same outcome; stops if they do not.
    """
    weeks = table[["week_index", "year", "breached"]].drop_duplicates()
    if weeks["week_index"].duplicated().any():
        raise ValueError("models disagree on whether a week breached: T_w must not depend on the model")
    return weeks.sort_values("week_index")


def usual_rates(cutoffs, outcomes):
    """obar at each forecast day (breach_scores.base_rate), NaN where no week from 2018 is visible yet.

    In plain words: the usual breach rate is the share of non-COVID weeks from 2018 up to
    the forecast's cutoff that breached; before the first such week is visible it is undefined.
    """
    counted = outcomes[(outcomes["year"] >= config.BACKTEST_FIRST_YEAR) & ~outcomes["year"].isin(config.COVID_YEARS)]
    first = counted["week_index"].min()
    return np.array([breach_scores.base_rate(outcomes, cut) if cut >= first else np.nan for cut in cutoffs])


def breach_window_scores(group, outcomes):
    """Breaches, Brier score and Brier skill score of one model's forecasts in one window (D3)."""
    group = group.sort_values("week_index")
    p = group["p_breach"].to_numpy(dtype=float)
    o = group["breached"].to_numpy(dtype=float)
    obar = usual_rates(group["cutoff"], outcomes)
    known = ~np.isnan(obar)
    return {"breaches": int(o.sum()), "brier": breach_scores.brier(p, o),
            "bss": breach_scores.brier_skill_score(p[known], o[known], obar[known]), "bss_weeks": int(known.sum())}


def window_scores(table, years, window, denominator, outcomes):
    """Every model's D1 scores, MASE (D2) and breach scores (D3) over the target weeks in `years`."""
    by_model = scores.add_mase(scores.score_models(table, years), denominator)
    rows = table[table["year"].isin(years)]
    breach = pd.DataFrame.from_dict({model: breach_window_scores(group, outcomes)
                                     for model, group in rows.groupby("model")}, orient="index")
    out = by_model.join(breach).loc[ordered_models(by_model.index)].reset_index()
    out.insert(0, "window", window)
    return out


def score_table(table, cases):
    """d1_scores.csv: one row per window and model, D8's model order within each window."""
    denominator = scores.mase_denominator(cases)
    outcomes = week_outcomes(table)
    parts = [window_scores(table, years, window, denominator, outcomes) for window, years in WINDOWS.items()]
    return pd.concat(parts, ignore_index=True)[SCORE_COLUMNS]


def mae_by_year(table):
    """d1_mae_by_year.csv: each model's MAE in each target year, one row per year (D1)."""
    scores.check_same_weeks(table)
    table = table.assign(miss=(table["y"] - table["mu"]).abs())
    out = table.pivot_table(index="year", columns="model", values="miss", aggfunc="mean")
    out = out[ordered_models(out.columns)]
    out.insert(0, "weeks", table.groupby("year")["week_index"].nunique())
    out.insert(1, "in_headline", out.index.isin(config.MAE_YEARS))
    return out.reset_index()


# ---------------------------------------------------------------------------
# 2. Alarms, episodes and lead time (D3, D4)
# ---------------------------------------------------------------------------

def alarm_row(group, option, g):
    """One model's alarm test (D3) and, on the second half, its episodes and lead time (D4)."""
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


# ---------------------------------------------------------------------------
# 3. The all-years check and the guard reruns (D5, D6)
# ---------------------------------------------------------------------------

def all_years_tests(table):
    """d5_d6_all_years.csv: D5's and D6's comparisons over 2018-2026, every block length."""
    return pd.concat([compare.primary_endpoint(table, config.ALL_YEARS),
                      compare.flood_and_practical_tests(table, config.ALL_YEARS)], ignore_index=True)


def guard_paths():
    """B10's forecasts for g = 2 and each guard rerun that is on disk: {g: path}; prints any rerun missing."""
    paths = {config.DELAY_GUARD_G: config.FORECASTS}
    for g in config.DELAY_GUARD_G_TESTS:
        path = backtest.output_path(False, "C", g, False)
        if path.exists():
            paths[g] = path
        else:
            print(f"no guard rerun for g = {g} ({path.name}): python -m src.backtest --g {g}")
    return dict(sorted(paths.items()))


def guard_table(paths):
    """d5_guard_reruns.csv: D8's figure 2 numbers (8-week blocks) for each g, None with no rerun on disk."""
    if len(paths) == 1:
        return None
    parts = []
    for g, path in paths.items():
        fig2 = figure2_table(load_forecasts(path))
        parts.append(fig2[fig2["block_weeks"] == config.BOOT_BLOCK_WEEKS].assign(g=g, source=path.name))
    out = pd.concat(parts, ignore_index=True)
    return out[["g", "source", *[col for col in out.columns if col not in ("g", "source")]]]


# ---------------------------------------------------------------------------
# Running it
# ---------------------------------------------------------------------------

def report(tables):
    """Print every table written, rounded for the eye (the files keep 4 decimals)."""
    for path, table in tables.items():
        print(f"\n{path.name}:")
        observed_run.print_table(table, float_format="{:.3f}".format, na_rep="")


def main():
    table = load_forecasts(config.FORECASTS)
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

"""The paper's figures (task D8). Dose figures are stock planning, not prescriptions.

The plan's five figures, one function each. Every figure is drawn by this file from the
results files of earlier tasks, never by hand, so rerunning it after a result changes
redraws the paper's figures. D8 computes no new result: figures 1-3 apply D1's, D3's and
D5/D6's functions to B10's forecasts, and figures 4-5 read C8's storm runs.

1. forecast_figure: QC's weekly cases with M4's and M3's 1-week-ahead forecasts and M4's
   90% forecast range, every forecast day of B10's backtest (2018-2026). The range runs
   from the 5% to the 95% point of the forecast NB(mu, theta) (forecast_range.range_90),
   the same range D1 scores. The COVID years 2020-2021 are shaded: forecast, but left out
   of the headline scores.

2. mae_figure, two panels over the MAE window (config.MAE_YEARS: 2018-2019 and 2022-2026).
   Left: each model's MAE with a 95% interval. The interval is D5's moving-block bootstrap
   (compare.block_bootstrap: 8-week blocks, 2,000 resamples, fixed seed) on the model's own
   weekly misses |y - mu|, whose mean is the MAE.
   Right: the comparisons the paper tests, mean of |error M4| - |error other| with the same
   bootstrap's interval: D5's primary endpoint (M4 vs M3), D6's flood test (M4 vs M4
   without EI2) and practical test (M4 vs M1). Below 0, M4 misses less. The right panel is
   not in the plan's list; it is there because the left one cannot answer D5's question.
   Every model misses most in the same outbreak weeks, so two MAE intervals can overlap
   even when one model misses less almost every week; the paired difference is the test.

3. reliability_figure: D3's CORP reliability curve (breach_scores.reliability) of M4's and
   M3's breach probabilities over D3's window (config.D8_RELIABILITY_YEARS, 2022-2026), with
   the number of forecasts in each step below it, as the plan asks. A reliable forecast's
   steps sit on the diagonal: of the weeks given a 30% chance of a breach, about 30% breached.

4. exposure_map: residents in zones the storm's observed rain floods (C8's main run, C3's
   graded exposure), as a share of each barangay's 2024 residents: the measure D7 maps and
   C8 flags with, in D7's classes and colours (config.D7_MAP_SHARE_BREAKS). A11's flooded
   barangays are outlined. One panel per storm in config.D8_MAP_STORMS: Carina, as the plan
   asks, and Kristine on the same scale (an assumption; config.py says why).

5. doses_table: QC's stock on observed rain, one row per storm (and per w in a short flood):
   the 3-day rain and where it falls against IMERG's return levels, the EI, exposed people
   and the three units (C8's main run). Units are rounded up to whole units, the level stock
   is ordered at (allocation.round_up); exposed people are rounded to whole people. Written
   as a CSV for the paper's table and as a picture; both carry the stock-planning label
   (rule 10).

Each chart has a CSV beside it with the numbers it shows (config.D8_FIG*_TABLE), so the
paper's text can quote them and E11 can check them. Figure 1's numbers are B10's
forecasts.csv itself, and figure 4's are C8's c8_observed_barangays.csv.

Inputs. Figures 1-3 need B10's results/forecasts.csv, which needs A13's case data; until it
exists the default run stops and says so. Two flags:
    --layer2          figures 4 and 5 only (C8's files and A5's shapes; ready now)
    --preview FILE    figures 1-3 from another B10 file, such as its made-up-count run
                      (python -m src.backtest --simulate --option C writes
                      results/forecasts_simulated_C.csv). The files are named d8_preview_*,
                      say "Preview" across the top and are not for the paper; .gitignore
                      keeps them out of git.
Figures 1-3 stop unless B10's file has the models config.PRIMARY_COMPARISON, FLOOD_TEST and
PRACTICAL_TEST name, every model has a forecast on exactly the same weeks and no number is
missing (rule 5).

Outputs in results/ (weekly city counts only, nothing case-level):
    d8_fig1_forecasts.png
    d8_fig2_mae.png          d8_fig2_mae.csv
    d8_fig3_reliability.png  d8_fig3_reliability.csv
    d8_fig4_exposure_map.png
    d8_fig5_doses.png        d8_fig5_doses.csv

Run from the repository root; a few seconds:
    python -m src.paper_figures             # all five; needs B10's forecasts.csv
    python -m src.paper_figures --layer2    # figures 4 and 5
"""

import argparse
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")    # draw into files only; no window opens
import geopandas as gpd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import config
from src import (allocation, breach_scores, compare, doses, forecast_range, forecast_run, layer2_results,
                 observed_run, scores, weeks)

L2 = layer2_results                   # D7: map helpers, storm names, colours and save_png
BAND_MODEL, OTHER_MODEL = config.PRIMARY_COMPARISON     # M4 (with its range in figure 1) and M3
NEEDED_MODELS = sorted({*config.PRIMARY_COMPARISON, *config.FLOOD_TEST, *config.PRACTICAL_TEST})
FORECAST_COLUMNS = ["model", "week_index", "year", "y", "mu", "theta", "p_breach", "breached"]   # what D8 reads from B10
MODEL_NAMES = {                       # figure labels; figure 2's rows run in this order
    "M0": "M0, same week last year",
    "M1": "M1, same-week average",
    "M3": "M3, Prophet + XGBoost",
    "M4": "M4, negative binomial",
    config.FLOOD_TEST[1]: "M4 without EI2",
}
TEST_NAMES = {                        # figure 2's right panel: D5's and D6's comparisons
    " vs ".join(config.PRIMARY_COMPARISON): "M4 vs M3 (primary endpoint, D5)",
    " vs ".join(config.FLOOD_TEST): "M4 vs M4 without EI2 (flood test, D6)",
    " vs ".join(config.PRACTICAL_TEST): "M4 vs M1 (practical test, D6)",
}
INPUTS_LAYER2 = {                     # the files figures 4 and 5 read, and the task that makes each
    config.C8_RUNS: "C8: python -m src.observed_run",
    config.C8_BARANGAYS: "C8: python -m src.observed_run",
    config.BARANGAYS_QC: "A5: python -m src.census",
}

# Chart style, from the team's chart palette (D7 uses the same ink, surface and blue ramp).
INK, INK_2, SURFACE = L2.INK, L2.INK_2, L2.SURFACE
MUTED, GRID, BASELINE, SHADE = "#898781", "#e1e0d9", "#c3c2b7", "#f0efec"
SERIES = {BAND_MODEL: "#2a78d6", OTHER_MODEL: "#eb6834"}   # palette slots 1 and 2 (validated); other models muted
BAND_ALPHA = 0.15                     # M4's 90% range: a wash of its line colour
MIN_STEP_WIDTH = 0.01                 # figure 3: a reliability step holding one probability is drawn this wide


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def check_inputs(paths):
    """Stop with one clear message that lists every input file not on this computer."""
    missing = [f"  {path}  ({task})" for path, task in paths.items() if not Path(path).exists()]
    if missing:
        raise SystemExit("D8 needs these files; run their task or copy them from the team drive:\n"
                         + "\n".join(missing))


def check_forecasts_exist(path, preview):
    """Stop when B10's forecasts are missing, saying how to draw what can be drawn now."""
    if Path(path).exists():
        return
    if preview:
        raise SystemExit(f"--preview: {path} not found")
    raise SystemExit(
        f"D8's figures 1-3 need {path} (B10: python -m src.backtest, which needs A13's case data).\n"
        f"  Figures 4 and 5 now:   python -m src.paper_figures --layer2\n"
        f"  Figures 1-3 on B10's made-up counts:   python -m src.backtest --simulate --option C\n"
        f"    then   python -m src.paper_figures --preview results/forecasts_simulated_C.csv")


def load_forecasts(path):
    """B10's forecasts, checked: the columns D8 reads, the models it compares, nothing missing, the same weeks.

    One row per model and target week (model, week_index, year, y, mu, theta, p_breach,
    breached). theta may be infinity (a Poisson range, B6). Stops on a missing column or
    model, a missing number, or models forecast on different weeks (rule 5).
    """
    table = pd.read_csv(path)
    missing = [col for col in FORECAST_COLUMNS if col not in table]
    if missing:
        raise ValueError(f"{Path(path).name} has no columns {missing}: is it B10's forecasts table?")
    absent = [model for model in NEEDED_MODELS if model not in set(table["model"])]
    if absent:
        raise ValueError(f"{Path(path).name} has no forecasts for {absent} (it has {sorted(set(table['model']))}): "
                         f"B10's model names must match config.PRIMARY_COMPARISON, FLOOD_TEST and PRACTICAL_TEST")
    if table[FORECAST_COLUMNS].isna().any().any():
        raise ValueError(f"{Path(path).name} has missing values: rerun B10 (rule 5)")
    scores.check_same_weeks(table)
    return table


def ordered_models(models):
    """Models in MODEL_NAMES' order; any model not listed there goes last, by name."""
    order = list(MODEL_NAMES)
    return sorted(models, key=lambda model: (order.index(model) if model in order else len(order), model))


def model_name(model):
    return MODEL_NAMES.get(model, model)


def model_color(model):
    """M4 and M3 keep their colour in every figure; the other models are muted."""
    return SERIES.get(model, MUTED)


def years_words(years):
    """Years as runs: (2018, 2019, 2022, 2023) becomes "2018-2019 and 2022-2023"."""
    runs = []
    for year in sorted(years):
        if runs and year == runs[-1][-1] + 1:
            runs[-1].append(year)
        else:
            runs.append([year])
    words = [str(run[0]) if len(run) == 1 else f"{run[0]}–{run[-1]}" for run in runs]
    return ", ".join(words[:-1]) + " and " + words[-1] if len(words) > 1 else words[0]


def shown(path):
    """A path relative to the repository root when it is inside it, for printing."""
    path = Path(path).resolve()
    return path.relative_to(config.ROOT) if path.is_relative_to(config.ROOT) else path


def output(path, preview):
    """Where a figure goes: its own name, or d8_preview_... for a --preview run."""
    return path.with_name(config.D8_PREVIEW_PREFIX + path.name.removeprefix("d8_")) if preview else path


# ---------------------------------------------------------------------------
# Chart chrome shared by the figures
# ---------------------------------------------------------------------------

def style_axes(ax, grid_axis="y"):
    """Recessive chrome: no top or right spine, hairline grid on one axis, secondary-ink ticks."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
    ax.tick_params(colors=INK_2, labelsize=8, length=3, color=BASELINE)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor(SURFACE)


def header(fig, title, subtitle, preview=None, width=150):
    """Title and subtitle at the top left; a --preview run says so above them."""
    if preview:
        fig.text(0.01, 1.0, f"PREVIEW on {preview}: not the paper's results", fontsize=10, weight="bold",
                 color=INK, va="bottom")
    fig.text(0.01, 0.985, title, fontsize=13, weight="bold", color=INK, va="top")
    fig.text(0.01, 0.93, textwrap.fill(subtitle, width), fontsize=8.5, color=INK_2, va="top")


def footer(fig, text, width=170):
    fig.text(0.01, 0.005, textwrap.fill(text, width), fontsize=7.5, color=INK_2, va="bottom")


# ---------------------------------------------------------------------------
# Figure 1: weekly cases with M4's and M3's forecasts and M4's 90% range
# ---------------------------------------------------------------------------

def forecast_series(table, model):
    """One model's forecasts, oldest first: week_index, year, date (the week's Sunday), y, mu and its 90% range."""
    rows = table[table["model"] == model].sort_values("week_index")
    ranges = np.array([forecast_range.range_90(forecast_range.forecast_dist(mu, theta))
                       for mu, theta in zip(rows["mu"], rows["theta"])])
    out = rows[["week_index", "year", "y", "mu"]].reset_index(drop=True)
    out["low"], out["high"] = ranges[:, 0], ranges[:, 1]
    out["date"] = pd.to_datetime([weeks.week_start(index) for index in out["week_index"]])
    return out


def coverage_words(table):
    """D1's 90% coverage of M4's range over the probability-score window, in words ("" if no such week)."""
    years = [year for year in config.PROB_SCORE_YEARS if year in set(table["year"])]
    if not years:
        return ""
    row = scores.score_models(table[table["model"] == BAND_MODEL], years).loc[BAND_MODEL]
    return (f" Over {years_words(years)} it held the count in {row['coverage_90']:.0%} of "
            f"{row['weeks']:.0f} weeks (D1; 90% if well sized).")


def forecast_figure(table, path, source, preview=None):
    """Draw figure 1: QC's weekly cases, M4's and M3's forecasts, M4's 90% range, COVID years shaded."""
    band, other = forecast_series(table, BAND_MODEL), forecast_series(table, OTHER_MODEL)
    if not band["week_index"].equals(other["week_index"]):
        raise ValueError(f"{BAND_MODEL} and {OTHER_MODEL} are forecast on different weeks (rule 5)")
    fig, ax = plt.subplots(figsize=(11, 4.8), facecolor=SURFACE)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.76, bottom=0.16)
    style_axes(ax)

    for year in config.COVID_YEARS:
        in_year = band[band["year"] == year]
        if len(in_year):
            start, end = in_year["date"].min(), in_year["date"].max() + pd.Timedelta(days=config.DAYS_PER_WEEK)
            ax.axvspan(start, end, color=SHADE, linewidth=0, zorder=0)
    covid = band[band["year"].isin(config.COVID_YEARS)]
    if len(covid):
        middle = covid["date"].min() + (covid["date"].max() - covid["date"].min()) / 2
        ax.text(middle, 0.97, "COVID years:\nforecast, not scored", transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=7.5, color=INK_2)

    ax.fill_between(band["date"], band["low"], band["high"], color=model_color(BAND_MODEL), alpha=BAND_ALPHA,
                    linewidth=0, label=f"{BAND_MODEL}'s 90% range")
    ax.plot(other["date"], other["mu"], color=model_color(OTHER_MODEL), linewidth=1.3,
            label=f"{model_name(OTHER_MODEL)} forecast")
    ax.plot(band["date"], band["mu"], color=model_color(BAND_MODEL), linewidth=1.3,
            label=f"{model_name(BAND_MODEL)} forecast")
    ax.scatter(band["date"], band["y"], s=7, color=INK, linewidths=0, zorder=3, label="Cases (final weekly count)")

    ax.set_ylim(bottom=0)
    ax.set_xlim(band["date"].min(), band["date"].max() + pd.Timedelta(days=config.DAYS_PER_WEEK))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylabel("Cases per week", fontsize=9, color=INK_2)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=4, frameon=False, fontsize=8, labelcolor=INK)

    first, last = band["date"].min(), band["date"].max()
    option = table["option"].iloc[0] if "option" in table else None
    guard = f", g = {table['g'].iloc[0]:.0f}" if option == "C" and "g" in table else ""
    view = f" Decision-tree option {option}{guard}." if option else ""
    header(fig, "Quezon City weekly leptospirosis cases and 1-week-ahead forecasts",
           f"{len(band)} target weeks, the week of {first:%d %b %Y} to the week of {last:%d %b %Y}.{view} "
           f"{BAND_MODEL}'s 90% range runs from the 5% to the 95% point of its forecast, NB(mu, theta)."
           f"{coverage_words(table)}", preview)
    footer(fig, f"Source: {source} (B10's backtest), drawn by src/paper_figures.py (D8). Weekly city counts only.")
    L2.save_png(fig, path)


# ---------------------------------------------------------------------------
# Figure 2: MAE by model with intervals, and D5's and D6's comparisons
# ---------------------------------------------------------------------------

def mae_by_model(table, years=config.MAE_YEARS):
    """Each model's MAE over `years` with its 95% moving-block bootstrap interval (D1's MAE, D5's bootstrap).

    The bootstrap runs on the model's weekly misses |y - mu| in time order; their mean is
    the MAE, which scores.point_scores computes too, so the two are checked against each other.
    """
    rows = table[table["year"].isin(years)]
    if rows.empty:
        raise ValueError(f"no forecasts with target weeks in {years}")
    scores.check_same_weeks(rows)
    out = []
    for model in ordered_models(rows["model"].unique()):
        group = rows[rows["model"] == model].sort_values("week_index")
        y, mu = scores.check_pairs(group["y"], group["mu"])
        boot = compare.block_bootstrap(np.abs(y - mu))
        mae = scores.point_scores(y, mu)["mae"]
        if not np.isclose(boot["mean"], mae):
            raise ValueError(f"{model}: the bootstrap's mean miss {boot['mean']} is not D1's MAE {mae}")
        out.append({"part": "MAE by model", "name": model, "block_weeks": config.BOOT_BLOCK_WEEKS,
                    "weeks": len(group), "value": mae, "low": boot["low"], "high": boot["high"]})
    return pd.DataFrame(out)


def model_tests(table, years=config.MAE_YEARS):
    """D5's primary endpoint and D6's two tests, every block length (compare.py), in figure 2's columns."""
    tests = pd.concat([compare.primary_endpoint(table, years), compare.flood_and_practical_tests(table, years)],
                      ignore_index=True)
    return tests.rename(columns={"comparison": "name", "mean_diff": "value"}).assign(
        part="mean |error a| - |error b|")


def figure2_table(table, years=config.MAE_YEARS):
    """Figure 2's numbers: the MAE rows, then the comparison rows (8-week blocks first, then 4 and 13)."""
    columns = ["part", "name", "block_weeks", "weeks", "value", "low", "high", "verdict", "dm_stat", "dm_p"]
    return pd.concat([mae_by_model(table, years), model_tests(table, years)], ignore_index=True).reindex(columns=columns)


def interval_panel(ax, rows, names, colors, label):
    """Dots with their 95% intervals, top row first, each value written right of its interval (and of 0)."""
    y = np.arange(len(rows))[::-1]
    span = max(rows["high"].max(), 0) - min(rows["low"].min(), 0)
    for yi, (_, row), color in zip(y, rows.iterrows(), colors):
        ax.hlines(yi, row["low"], row["high"], color=color, linewidth=2, capstyle="round")
        ax.scatter(row["value"], yi, s=42, color=color, edgecolors=SURFACE, linewidths=1.5, zorder=3)
        ax.text(max(row["high"], 0) + 0.03 * span, yi, label(row), va="center", fontsize=8, color=INK)
    ax.set_yticks(y, names, fontsize=8.5, color=INK)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(min(rows["low"].min(), 0) - 0.05 * span, max(rows["high"].max(), 0) + 0.45 * span)
    style_axes(ax, grid_axis="x")
    ax.tick_params(axis="y", length=0)


def mae_figure(fig2, path, source, years=config.MAE_YEARS, preview=None):
    """Draw figure 2: left each model's MAE with its interval, right D5's and D6's differences (8-week blocks)."""
    by_model = fig2[fig2["part"] == "MAE by model"]
    tests = fig2[(fig2["part"] != "MAE by model") & (fig2["block_weeks"] == config.BOOT_BLOCK_WEEKS)]
    fig, (left, right) = plt.subplots(1, 2, figsize=(11.5, 4.4), facecolor=SURFACE,
                                      gridspec_kw={"width_ratios": [1, 1.15]})
    fig.subplots_adjust(left=0.15, right=0.99, top=0.76, bottom=0.17, wspace=0.75)

    interval_panel(left, by_model, [model_name(m) for m in by_model["name"]],
                   [model_color(m) for m in by_model["name"]], lambda row: f"{row['value']:.1f}")
    left.set_xlabel("Mean absolute error, cases a week", fontsize=8.5, color=INK_2)
    left.set_title("MAE by model, with 95% interval", loc="left", fontsize=10, color=INK)

    right.axvline(0, color=INK_2, linewidth=0.8)
    interval_panel(right, tests, [TEST_NAMES.get(n, n) for n in tests["name"]], [model_color(BAND_MODEL)] * len(tests),
                   lambda row: f"{row['value']:+.2f}  {row['verdict']}")
    right.set_xlabel("Mean of |error M4| − |error other model|, cases a week (below 0: M4 misses less)",
                     fontsize=8.5, color=INK_2)
    right.set_title("M4 against each model, week by week", loc="left", fontsize=10, color=INK)

    header(fig, "How far the 1-week-ahead forecasts miss",
           f"{by_model['weeks'].iloc[0]:.0f} target weeks in {years_words(years)} (COVID years left out). "
           f"95% moving-block bootstrap intervals: {config.BOOT_BLOCK_WEEKS}-week blocks, "
           f"{config.BOOT_RESAMPLES:,} resamples. The 4- and 13-week checks and the Diebold–Mariano tests are in "
           f"results/{config.D8_FIG2_TABLE.name}.", preview)
    footer(fig, f"Source: {source} (B10), scored with src/scores.py (D1) and src/compare.py (D5, D6); "
                f"drawn by src/paper_figures.py (D8).")
    L2.save_png(fig, path)


# ---------------------------------------------------------------------------
# Figure 3: reliability of the breach probabilities
# ---------------------------------------------------------------------------

def join_equal_steps(steps):
    """Neighbouring reliability steps with the same breach rate joined into one, their forecasts added up.

    D3's pool-adjacent-violators pools two steps only when the first rate is higher, so
    steps with equal rates stay apart (M4 on made-up counts: 49 steps at rate 0). Joining
    them draws the same curve, with one bar per rate in the panel below.
    """
    run = (steps["observed"] != steps["observed"].shift()).cumsum()
    return steps.groupby(run).agg(p_low=("p_low", "min"), p_high=("p_high", "max"), observed=("observed", "first"),
                                  forecasts=("forecasts", "sum")).reset_index(drop=True)


def reliability_table(table, models=config.PRIMARY_COMPARISON, years=config.D8_RELIABILITY_YEARS):
    """D3's CORP reliability steps for each model over `years`: model, p_low, p_high, observed, forecasts.

    Steps with the same rate next to each other are joined (join_equal_steps). Also each
    model's forecasts, breaches and Brier score (D3), repeated on its rows.
    """
    rows = table[table["year"].isin(years)]
    if rows.empty:
        raise ValueError(f"no forecasts with target weeks in {years}")
    scores.check_same_weeks(rows)
    parts = []
    for model in models:
        group = rows[rows["model"] == model].sort_values("week_index")
        p, o = group["p_breach"], group["breached"].astype(float)
        steps = join_equal_steps(breach_scores.reliability(p, o))
        if steps["forecasts"].sum() != len(group):
            raise ValueError(f"{model}: the reliability steps hold {steps['forecasts'].sum()} of {len(group)} forecasts")
        steps.insert(0, "model", model)
        parts.append(steps.assign(model_forecasts=len(group), model_breaches=int(o.sum()),
                                  brier=breach_scores.brier(p, o)))
    return pd.concat(parts, ignore_index=True)


def reliability_figure(steps, path, source, years=config.D8_RELIABILITY_YEARS, preview=None):
    """Draw figure 3: one column per model, the CORP curve against the diagonal above, forecasts per step below."""
    models = list(dict.fromkeys(steps["model"]))
    fig, axes = plt.subplots(2, len(models), figsize=(5.2 * len(models), 6.6), facecolor=SURFACE, squeeze=False,
                             sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    fig.subplots_adjust(left=0.08, right=0.98, top=0.80, bottom=0.12, wspace=0.25, hspace=0.12)
    for col, model in enumerate(models):
        top, bottom = axes[0, col], axes[1, col]
        rows = steps[steps["model"] == model]
        first = rows.iloc[0]
        style_axes(top, grid_axis="both")
        top.plot([0, 1], [0, 1], color=BASELINE, linewidth=1, label="Reliable: the steps sit on this line")
        x = np.ravel(np.column_stack([rows["p_low"], rows["p_high"]]))
        y = np.repeat(rows["observed"].to_numpy(), 2)
        top.plot(x, y, color=model_color(model), linewidth=2, solid_capstyle="round", solid_joinstyle="round",
                 label="Share that breached (CORP steps)")
        top.set_xlim(0, 1)
        top.set_ylim(0, 1)
        top.set_ylabel("Share of weeks that breached", fontsize=8.5, color=INK_2)
        top.set_title(f"{model_name(model)}: {first['model_forecasts']:.0f} forecasts, "
                      f"{first['model_breaches']:.0f} breaches, Brier {first['brier']:.3f}",
                      loc="left", fontsize=9.5, color=INK)
        style_axes(bottom)
        bottom.bar(rows["p_low"], rows["forecasts"], width=np.maximum(rows["p_high"] - rows["p_low"], MIN_STEP_WIDTH),
                   align="edge", color=model_color(model), edgecolor=SURFACE, linewidth=1)
        bottom.set_ylabel("Forecasts\nper step", fontsize=8.5, color=INK_2)
        bottom.set_xlabel("Forecast probability of a breach, Pr(Y > T_w)", fontsize=8.5, color=INK_2)
    axes[0, 0].legend(loc="upper left", frameon=False, fontsize=8, labelcolor=INK)

    header(fig, "Are the breach probabilities reliable?",
           f"Target weeks in {years_words(years)}. A breach is a final count strictly above the epidemic threshold "
           f"T_w (B7). Each step pools forecasts of similar probability (CORP, D3); a reliable forecast's steps sit "
           f"on the diagonal.", preview, width=115)
    footer(fig, f"Source: {source} (B10), steps from src/breach_scores.py (D3); drawn by src/paper_figures.py (D8). "
                f"Steps and counts: results/{config.D8_FIG3_TABLE.name}.", width=140)
    L2.save_png(fig, path)


# ---------------------------------------------------------------------------
# Figure 4: the exposure map
# ---------------------------------------------------------------------------

def map_tables(c8_runs, c8_barangays, shapes, storms=config.D8_MAP_STORMS):
    """For each storm to map, C8's main-run row and A5's shapes joined to its barangays (D7's map_run and map_table)."""
    unknown = [storm for storm in storms if storm not in config.STORMS]
    if unknown or not storms:
        raise ValueError(f"config.D8_MAP_STORMS must name storms in config.STORMS; unknown: {unknown}")
    return [(run, L2.map_table(shapes, c8_barangays, run)) for run in (L2.map_run(c8_runs, s) for s in storms)]


def exposure_map(maps, path):
    """Draw figure 4: per storm, the share of each barangay's residents in zones the observed rain floods."""
    breaks = config.D7_MAP_SHARE_BREAKS
    colors = L2.class_colors(L2.SHARE_CMAP, len(breaks) + 1)
    flag_tag, flag_share = L2.FLAG_TAGS[0], config.FLAG_EXPOSED_SHARES[0]
    fig, axes = plt.subplots(1, len(maps), figsize=(5.4 * len(maps), 7.0), facecolor=SURFACE, squeeze=False)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.74, bottom=0.17, wspace=0.05)
    for ax, (run, table) in zip(axes[0], maps):
        table.plot(ax=ax, color=[colors[c] for c in table["share_class"]], edgecolor=SURFACE, linewidth=0.4)
        gpd.GeoSeries([table.union_all()], crs=table.crs).boundary.plot(ax=ax, color=INK_2, linewidth=0.6)
        listed = table[table["listed_flooded"]]
        if len(listed):
            listed.boundary.plot(ax=ax, color=INK, linewidth=1.4)
        ax.set_axis_off()
        ax.set_title(L2.STORM_NAMES.get(run["storm"], run["storm"]), loc="left", fontsize=11, color=INK, pad=44)
        ax.text(0.0, 1.01, textwrap.fill(
            f"{run['rain_mm']:.1f} mm in {config.RAIN_ACCUM_DAYS} days ({L2.window_words(run['window'])}), "
            f"{L2.position_words(run['position'])}. EI {run['ei_pct']:.2f}% of QC's residents. "
            f"{int(run[f'flagged_{flag_tag}'])} barangays at {flag_share:.0%} or more; "
            f"{int(run['listed_flooded'])} named flooded (outlined).", 62),
            transform=ax.transAxes, va="bottom", fontsize=8, color=INK_2)

    labels = L2.class_labels(breaks, lambda b: f"{100 * b:g}%")
    handles = [Patch(facecolor=color, edgecolor="none", label=label) for color, label in zip(colors, labels)]
    handles.append(Line2D([], [], color=INK, linewidth=1.4, label="named flooded in A11's sources"))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.01, 0.06), ncol=4, frameon=False, fontsize=8,
               title="Share of the barangay's 2024 residents in zones the rain floods", title_fontsize=8.5,
               alignment="left", labelcolor=INK)
    header(fig, "Residents in zones the observed rain floods",
           f"C8's run on IMERG's wettest {config.RAIN_ACCUM_DAYS}-day total during each flood, placed on IMERG's "
           f"return levels fitted on the years before the storm. Same classes in every panel; from "
           f"{flag_share:.0%} up are the barangays C8 flags.", width=60 * len(maps))
    footer(fig, f"Source: results/{config.C8_BARANGAYS.name} (C8) and A5's barangay shapes; drawn by "
                f"src/paper_figures.py (D8). Doses per barangay: D7's maps (results/d7_map_<storm>.png).",
           width=65 * len(maps))
    L2.save_png(fig, path)


# ---------------------------------------------------------------------------
# Figure 5: the doses table
# ---------------------------------------------------------------------------

def doses_table(c8_runs):
    """QC's stock on observed rain, one row per storm (and w in a short flood), from C8's main run.

    rain_mm to 1 decimal, return_period to 1, ei_pct to 2; exposed to whole people; units
    rounded up to whole units. w is empty when D is at or above the cut-off: every exposed
    adult is then high risk and w changes nothing (C5). Stops unless C8 ran every storm.
    """
    runs = L2.main_runs(c8_runs)
    missing = sorted(set(config.STORMS) - set(runs["storm"]))
    if missing:
        raise ValueError(f"C8's main run has no rows for {missing}: rerun python -m src.observed_run")
    runs = L2.in_order(runs, by=["w"])
    out = runs[["storm", "window", "rain_mm", "position", "return_period", "ei_pct", "flood", "D"]].copy()
    out.insert(1, "storm_name", out["storm"].map(lambda storm: L2.STORM_NAMES.get(storm, storm)))
    out["rain_mm"] = out["rain_mm"].round(1)
    out["return_period"] = out["return_period"].round(1)
    out["ei_pct"] = out["ei_pct"].round(2)
    out["w"] = runs["w"].where(runs["D"] < runs["cutoff"])
    out["exposed"] = runs["exposed"].round().astype(int)
    out[L2.UNITS] = allocation.round_up(runs[L2.UNITS]).astype(int)
    out["label"] = doses.LABEL
    return out


def doses_figure(table, path):
    """Draw figure 5: the doses table as a picture, with the stock-planning label under its title."""
    columns = ["Storm", f"Wettest {config.RAIN_ACCUM_DAYS}-day rain", "Where it falls (IMERG)", "EI", "Flood",
               "Exposed\npeople", "Doxycycline 100 mg\ncapsules, adults", "Children's\ncourses",
               "Amoxicillin 500 mg\ntablets, pregnant"]
    cells = [[textwrap.fill(row["storm_name"], 26), f"{row['rain_mm']:.1f} mm\n{L2.window_words(row['window'])}",
              f"{L2.position_words(row['position'])}\n(about a {row['return_period']:.1f}-year rain)",
              f"{row['ei_pct']:.2f}%", row["flood"], f"{row['exposed']:,}", f"{row['doxy100']:,}",
              f"{row['courses']:,}", f"{row['amox500']:,}"] for _, row in table.iterrows()]
    fig, ax = plt.subplots(figsize=(12, 1.9 + 0.48 * len(cells)), facecolor=SURFACE)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.80, bottom=0.14)
    ax.set_axis_off()
    grid = ax.table(cellText=cells, colLabels=columns, loc="upper left", cellLoc="left", colLoc="left")
    grid.auto_set_font_size(False)
    grid.set_fontsize(8)
    grid.scale(1, 2.6)
    grid.auto_set_column_width(list(range(len(columns))))
    for (row, _), cell in grid.get_celld().items():
        cell.visible_edges = "B"
        cell.set_edgecolor(BASELINE if row == 0 else GRID)
        cell.set_facecolor(SURFACE)
        cell.get_text().set_color(INK)
        if row == 0:
            cell.get_text().set_weight("bold")
    header(fig, "Prophylaxis stock for Quezon City on the observed rain of each storm",
           f"{doses.LABEL} QC totals from C8's main run at full coverage (q = u = 1), rounded up to whole units. "
           f"A flood of {config.CONTINUOUS_EXPOSURE_DAYS} days or more makes every exposed adult high risk; a shorter "
           f"one is given at each w, the share of exposed adults with a wound or mucosal exposure.", width=175)
    footer(fig, f"Source: results/{config.C8_RUNS.name} (C8); the table: results/{config.D8_FIG5_TABLE.name}; per "
                f"health center: results/{config.D7_CENTERS.name} (D7). Drawn by src/paper_figures.py (D8). "
                f"{doses.LABEL}", width=175)
    L2.save_png(fig, path)


# ---------------------------------------------------------------------------
# Running it
# ---------------------------------------------------------------------------

def report(fig2, steps, doses_rows, written):
    """Print the numbers in figures 2, 3 and 5 (labelled where they hold doses) and every file written."""
    print_table = observed_run.print_table
    if fig2 is not None:
        print("\nFigure 2: MAE by model, and M4 against each model (mean of |error M4| - |error other|), "
              "95% bootstrap intervals:")
        print_table(fig2.drop(columns=["part"]), float_format="{:.3f}".format, na_rep="")
    if steps is not None:
        print("\nFigure 3: reliability steps (share that breached, forecasts per step):")
        print_table(steps, float_format="{:.3f}".format)
    if doses_rows is not None:
        print(f"\nFigure 5: QC's stock on observed rain (whole units, rounded up). {doses.LABEL}")
        cols = ["storm", "rain_mm", "position", "ei_pct", "flood", "exposed", *L2.UNITS]
        print_table(doses_rows[cols], formatters={col: "{:,}".format for col in ["exposed", *L2.UNITS]})
        print(f"\n{doses.LABEL}")
    print("\nwrote:\n  " + "\n  ".join(str(shown(path)) for path in written))


def main():
    parser = argparse.ArgumentParser(description="D8: the paper's five figures, from results/")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--layer2", action="store_true", help="figures 4 and 5 only (C8's files)")
    which.add_argument("--preview", metavar="FILE", help="figures 1-3 from another B10 file, named d8_preview_*")
    args = parser.parse_args()

    preview = Path(args.preview) if args.preview else None
    forecasts_path = preview or config.FORECASTS
    layer1, layer2 = not args.layer2, preview is None
    if layer1:
        check_forecasts_exist(forecasts_path, preview is not None)
    if layer2:
        check_inputs(INPUTS_LAYER2)

    # Every table is built and checked before any file is written.
    fig2 = steps = doses_rows = None
    if layer1:
        table = load_forecasts(forecasts_path)
        fig2 = figure2_table(table)
        steps = reliability_table(table)
    if layer2:
        c8_runs = pd.read_csv(config.C8_RUNS)
        c8_barangays = pd.read_csv(config.C8_BARANGAYS, dtype={"psgc": str})
        maps = map_tables(c8_runs, c8_barangays, allocation.load_barangays())
        doses_rows = doses_table(c8_runs)

    written = []
    if layer1:
        source = forecasts_path.name
        note = forecasts_path.name if preview else None
        paths = {key: output(path, preview is not None) for key, path in [
            ("fig1", config.D8_FIG1_FORECASTS), ("fig2", config.D8_FIG2_MAE), ("fig2_csv", config.D8_FIG2_TABLE),
            ("fig3", config.D8_FIG3_RELIABILITY), ("fig3_csv", config.D8_FIG3_TABLE)]}
        forecast_figure(table, paths["fig1"], source, note)
        mae_figure(fig2, paths["fig2"], source, preview=note)
        forecast_run.write(fig2.round(4), paths["fig2_csv"])
        reliability_figure(steps, paths["fig3"], source, preview=note)
        forecast_run.write(steps.round(4), paths["fig3_csv"])
        written += list(paths.values())
    if layer2:
        exposure_map(maps, config.D8_FIG4_MAP)
        doses_figure(doses_rows, config.D8_FIG5_DOSES)
        forecast_run.write(doses_rows, config.D8_FIG5_TABLE)
        written += [config.D8_FIG4_MAP, config.D8_FIG5_DOSES, config.D8_FIG5_TABLE]
    report(fig2, steps, doses_rows, written)


if __name__ == "__main__":
    main()

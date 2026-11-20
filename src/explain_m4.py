"""Explainer figures: how M4 (task B5) turns its inputs into a forecast, and how it is tested.

For teaching and slides, not results; the paper's results figures are src/paper_figures.py (D8).
Every number comes from the functions the backtest itself uses (src/m4.py, src/view.py,
src/forecast_range.py, src/thresholds.py, src/compare.py), and each figure checks that it
gets the backtest's own numbers back, so a picture cannot drift from the code it explains.

Run: python -m src.explain_m4   (needs results/forecasts.csv from B10 and the data/clean files)
Writes twelve figures, m4_01_... to m4_12_..., to results/explain/.
"""

import textwrap
import time
from datetime import date

import matplotlib

matplotlib.use("Agg")    # draw into files only; no window opens
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter, NullFormatter
from scipy import stats

import config
from src import backtest, compare, forecast_range, m4, paper_figures, thresholds, view, weeks

PF = paper_figures
INK, INK_2, SURFACE = PF.INK, PF.INK_2, PF.SURFACE
MUTED, GRID, BASELINE, SHADE = PF.MUTED, PF.GRID, PF.BASELINE, PF.SHADE
M4_BLUE, M3_ORANGE = PF.model_color("M4"), PF.model_color("M3")   # palette slots 1 and 2 (validated)
NO_EI2_GREY = PF.model_color(config.FLOOD_TEST[1])                # muted, as in the paper
# Steps of the palette's blue ramp: 100 and 150 for fills; 250, 350 and 450 (M4_BLUE) for an ordered build-up.
BLUE_100, BLUE_150, BLUE_250, BLUE_350 = "#cde2fb", "#b7d3f6", "#86b6ef", "#5598e7"
NICE_MULTIPLIERS = (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 0.8, 1, 1.25, 2, 5, 10, 20, 50, 100,
                    200, 500, 1000)          # the ticks a multiplier axis may show
X_EXTENT_Q = 0.99                            # the count plots' x axes run to this point of the forecast
BACKTEST_ROWS = 6                            # forecast days drawn in the rolling-origin figure
NOTE = "An explainer drawn by src/explain_m4.py, not a result. Weekly city counts only."


# Inputs

def load():
    """What every figure reads: cases, M4's inputs, B10's forecasts and the run's data option and guard."""
    if not config.FORECASTS.exists():
        raise FileNotFoundError(f"{config.FORECASTS} not found: run B10 first (python -m src.backtest)")
    table = pd.read_csv(config.FORECASTS)
    run = table[["option", "g"]].drop_duplicates()
    if len(run) != 1:
        raise ValueError(f"{config.FORECASTS.name} holds more than one data option or guard: one run per file")
    return {"cases": backtest.load_cases(), "features": backtest.load_features(),
            "pop": backtest.load_population(), "table": table,
            "option": run["option"].iloc[0], "g": int(run["g"].iloc[0])}


def fit_at(data, T, with_ei=True):
    """M4 exactly as the backtest fits it at forecast day T: the fit, and the rows it was fitted on."""
    rain = backtest.features_for(data["features"], weeks.year_week(T)[0])
    rows = m4.model_rows(view.training_rows(data["cases"], T, data["option"], data["g"]), rain, data["pop"])
    return m4.fit_m4(rows, with_ei=with_ei), m4.complete_rows(rows)


def dates(week_index):
    """The Sunday that starts each week index, as pandas dates."""
    return pd.to_datetime([weeks.week_start(int(i)) for i in week_index])


def model_rows(table, model):
    """One model's forecasts from B10, oldest first, with the date each target week starts."""
    rows = table[table["model"] == model].sort_values("week_index").reset_index(drop=True)
    rows["date"] = dates(rows["week_index"])
    return rows


def forecast_row(table, model, year, week):
    """The one forecast `model` made for target week (year, week)."""
    rows = table[(table["model"] == model) & (table["year"] == year) & (table["week"] == week)]
    if len(rows) != 1:
        raise ValueError(f"{model}: {len(rows)} forecasts for {year} week {week} in forecasts.csv, expected 1")
    return rows.iloc[0]


def last_fit(data):
    """M4's fit at the backtest's last forecast day, the one m4.main checks."""
    T = int(data["table"]["forecast_week"].max())
    fit, train = fit_at(data, T)
    return {"T": T, "fit": fit, "train": train, "train_dates": dates(train["week_index"])}


# Chart chrome

def header(fig, title, subtitle, width=140):
    """Title and subtitle at the top left, placed in inches; returns where the plots may start (a fraction)."""
    height = fig.get_figheight()
    fig.text(0.01, 1 - 0.08 / height, title, fontsize=13, weight="bold", color=INK, va="top")
    text = textwrap.fill(subtitle, width)
    fig.text(0.01, 1 - 0.40 / height, text, fontsize=8.5, color=INK_2, va="top", linespacing=1.35)
    return 1 - (0.40 + 0.18 * (text.count("\n") + 1) + 0.30) / height


def footer(fig, source):
    PF.footer(fig, f"Source: {source}. {NOTE}")


def save(fig, name):
    """Save one figure into results/explain/ and return its path."""
    config.EXPLAIN_DIR.mkdir(parents=True, exist_ok=True)
    path = config.EXPLAIN_DIR / name
    PF.L2.save_png(fig, path)
    return path


def shade_covid(ax, label=False, label_y=0.96):
    """Grey bands over the COVID years: forecast, but not scored."""
    for year in config.COVID_YEARS:
        ax.axvspan(pd.Timestamp(year, 1, 1), pd.Timestamp(year + 1, 1, 1), color=SHADE, linewidth=0, zorder=0)
    if label:
        middle = pd.Timestamp(config.COVID_YEARS[-1], 1, 1)
        ax.text(middle, label_y, "COVID years", transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=7.5, color=INK_2)


def year_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def times(value):
    """A multiplier written for people: 0.5 becomes '×0.5', 2 becomes '×2'."""
    return f"×{value:g}"


def multiplier_axis(ax, values):
    """A log y axis for a multiplier, ticks written ×0.5, ×1, ×2, and a dashed line at ×1 (no effect)."""
    values = np.asarray(values, dtype=float)
    low = min(np.nanmin(values), 1 / 1.3) / 1.15
    high = max(np.nanmax(values), 1.3) * 1.15
    ax.set_yscale("log")
    ax.set_ylim(low, high)
    ticks = [v for v in NICE_MULTIPLIERS if low <= v <= high]
    if high / low > 4:                       # a wide range: keep the 1-2-5 ticks only, or ×0.8 and ×1.25 crowd ×1
        ticks = [v for v in ticks if v not in (0.8, 1.25)]
    ax.set_yticks(ticks)
    ax.set_yticklabels([times(v) for v in ticks])
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.minorticks_off()
    ax.axhline(1, color=INK_2, linewidth=0.8, linestyle=(0, (3, 2)), zorder=1)


def panel_title(ax, text):
    ax.set_title(text, loc="left", fontsize=8.5, color=INK, pad=4)


def date_num(day):
    return mdates.date2num(pd.Timestamp(day))


# Figure 1: the data

def data_figure(ctx):
    """1. What M4 forecasts and what it reads: weekly cases, weekly rain and the flood exposure index."""
    data = ctx["data"]
    cases = data["cases"].dropna(subset=["cases"]).copy()
    cases["date"] = dates(cases["week_index"])
    feats = pd.read_csv(config.FEATURES_WEEKLY)
    feats = feats[(feats["fit_year"] == config.BACKTEST_LAST_YEAR) & (feats["week_index"] <= cases["week_index"].max())]
    feats = feats.assign(date=dates(feats["week_index"]))
    backtest_start = pd.Timestamp(weeks.week_start(weeks.week_index_of(config.BACKTEST_FIRST_YEAR, 1)))
    end = cases["date"].max() + pd.Timedelta(days=config.DAYS_PER_WEEK)

    fig, axes = plt.subplots(3, 1, figsize=(11, 7.2), sharex=True, facecolor=SURFACE,
                             gridspec_kw={"height_ratios": [2.4, 1, 1], "hspace": 0.45})
    top_ax, rain_ax, ei_ax = axes
    for ax in axes:
        PF.style_axes(ax)
        shade_covid(ax)
    shade_covid(top_ax, label=True, label_y=0.82)

    top_ax.plot(cases["date"], cases["cases"], color=INK, linewidth=0.9)
    top_ax.set_ylim(bottom=0)
    panel_title(top_ax, "Cases per week in Quezon City (QCESD, by onset week): what M4 forecasts, one week ahead")
    burn = f"{config.BURN_IN_YEARS[0]}–{config.BURN_IN_YEARS[-1]}"
    spans = ((cases["date"].min(), backtest_start, f"burn-in {burn}: training only"),
             (backtest_start, end, f"backtest {config.BACKTEST_FIRST_YEAR}–{config.BACKTEST_LAST_YEAR}: "
                                   "one forecast every week, each from what was known that week"))
    for start, stop, text in spans:
        top_ax.annotate("", xy=(date_num(start), 0.90), xytext=(date_num(stop), 0.90),
                        xycoords=top_ax.get_xaxis_transform(),
                        arrowprops=dict(arrowstyle="|-|", color=INK_2, linewidth=0.8, mutation_scale=3))
        top_ax.text(start + (stop - start) / 2, 0.92, text, transform=top_ax.get_xaxis_transform(), ha="center",
                    va="bottom", fontsize=7.5, color=INK_2)

    rain_ax.bar(feats["date"], feats["rain_mm"], width=6, color=MUTED, linewidth=0)
    panel_title(rain_ax, "Rain per week over QC, mm (IMERG Late, weighted by where people live); "
                         "M4 reads Rcum2, the last two weeks together")
    fit_years = f"{config.IMERG_START.year}–{config.BACKTEST_LAST_YEAR - 1}"
    ei_ax.bar(feats["date"], feats["ei"], width=6, color=MUTED, linewidth=0)
    panel_title(ei_ax, f"Flood exposure index EI, % of residents in flooded NOAH zones (return levels fitted on "
                       f"{fit_years}); M4 reads EI2, the larger of the last two weeks")
    ei_ax.set_xlim(cases["date"].min(), end)
    year_axis(ei_ax)

    months = cases.groupby(cases["date"].dt.month)["cases"].sum()
    busiest = sorted(months.nlargest(3).index)
    share = months[busiest].sum() / months.sum()
    peak = cases.loc[cases["cases"].idxmax()]
    month_names = ", ".join(date(2000, m, 1).strftime("%B") for m in busiest[:-1]) + \
        f" and {date(2000, busiest[-1], 1):%B}"
    subtitle = (f"{int(cases['cases'].sum()):,} cases in {len(cases)} weeks, {cases['date'].min():%b %Y} to "
                f"{cases['date'].max():%b %Y}. Weeks starting in {month_names} hold {share:.0%} of them: cases "
                f"follow the rainy season and its floods. The biggest week began {peak['date']:%d %b %Y}, with "
                f"{int(peak['cases'])} cases.")
    fig.subplots_adjust(left=0.05, right=0.99, bottom=0.08, top=header(fig, "The data M4 works with", subtitle))
    footer(fig, "cases_weekly.csv (A13), features_weekly.csv (B4)")
    return fig


# Figure 2: why a negative binomial

def nb_figure(ctx):
    """2. Why a negative binomial: weekly counts swing far more than a Poisson count allows."""
    data, fit = ctx["data"], ctx["fit"]
    row = forecast_row(data["table"], "M4", *config.EXPLAIN_BUSY_WEEK)
    nb = forecast_range.forecast_dist(row["mu"], row["theta"])
    poisson = stats.poisson(row["mu"])
    mu = np.asarray(fit["result"].predict(), dtype=float)
    y = np.asarray(fit["result"].model.endog, dtype=float)

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.8), facecolor=SURFACE, gridspec_kw={"wspace": 0.22})
    PF.style_axes(left)
    PF.style_axes(right, grid_axis="both")

    x = np.arange(0, int(max(nb.ppf(X_EXTENT_Q), row["y"]) * 1.1) + 1)
    for dist, color, name in ((poisson, MUTED, "Poisson"), (nb, M4_BLUE, f"Negative binomial, θ = {row['theta']:.2f}")):
        low, high = forecast_range.range_90(dist)
        left.plot(x, dist.pmf(x), color=color, linewidth=1.6, label=f"{name}: 90% range {low:.0f} to {high:.0f}")
    left.axvline(row["y"], color=INK, linewidth=1, linestyle=(0, (4, 2)))
    left.text(row["y"], 0.55, f" actual count {row['y']:.0f}", transform=left.get_xaxis_transform(), fontsize=7.5,
              color=INK, va="top")
    left.set_xlim(0, x[-1])
    left.set_ylim(bottom=0)
    left.set_xlabel("cases that week", fontsize=8.5, color=INK_2)
    left.set_ylabel("probability", fontsize=8.5, color=INK_2)
    left.legend(loc="upper right", frameon=False, fontsize=7.5, labelcolor=INK)
    year, week = config.EXPLAIN_BUSY_WEEK
    panel_title(left, f"Same expected count ({row['mu']:.1f} cases, {year} week {week}), two spreads")

    edges = np.unique(np.quantile(mu, np.linspace(0, 1, config.EXPLAIN_NB_BINS + 1)))
    group = np.clip(np.searchsorted(edges, mu, side="right") - 1, 0, len(edges) - 2)
    binned = (pd.DataFrame({"group": group, "mu": mu, "square": (y - mu) ** 2})
              .groupby("group").agg(mu=("mu", "mean"), square=("square", "mean")))
    binned = binned[binned["square"] > 0]
    grid = np.geomspace(binned["mu"].min() / 1.5, binned["mu"].max() * 1.5, 100)
    right.plot(grid, grid, color=MUTED, linewidth=1.4, linestyle=(0, (4, 2)), label="Poisson: variance = mean")
    right.plot(grid, grid + grid ** 2 / fit["theta"], color=M4_BLUE, linewidth=1.6,
               label=f"Negative binomial: variance = mean + mean²/θ, θ = {fit['theta']:.2f}")
    right.scatter(binned["mu"], binned["square"], s=30, color=INK, zorder=3, linewidths=0,
                  label=f"M4's {len(mu)} training weeks in {len(binned)} groups by expected count")
    right.set_xscale("log")
    right.set_yscale("log")
    right.set_xlabel("expected cases a week (M4's fit)", fontsize=8.5, color=INK_2)
    right.set_ylabel("average squared miss, (count − expected)²", fontsize=8.5, color=INK_2)
    right.legend(loc="upper left", frameon=False, fontsize=7.5, labelcolor=INK)
    panel_title(right, "How much weekly counts really vary, against what each model allows")

    subtitle = ("A Poisson count assumes the variance equals the mean, so its ranges are narrow. QC's weeks vary far "
                "more (right: the dots follow the blue curve, not the grey line), so every LEPTON forecast is a "
                "negative binomial: mean μ, and a spread θ where a smaller θ means wider swings. M4 fits θ = 1/α "
                "with smf.negativebinomial (rule 4; the GLM family would fix α at 1).")
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.18, top=header(fig, "Why M4 is a negative binomial model",
                                                                       subtitle))
    footer(fig, f"forecasts.csv (B10) on the left; M4's fit at the last forecast day ({ctx['train_dates'][-1]:%d %b %Y} "
                f"target) on the right")
    return fig


# Figure 3: the building blocks

def multipliers(fit, train):
    """M4's formula split into factors on its training rows: mu = start x season x momentum x rain x flood x COVID."""
    params, terms = fit["result"].params, fit["terms"]

    def linear(names):
        return sum((params[name] * train[name] for name in names if name in terms), pd.Series(0.0, index=train.index))

    parts = pd.DataFrame({
        "start": np.exp(params["Intercept"]) * train["pop"],
        "season": np.exp(linear(m4.SEASON)),
        "momentum": np.exp(linear([m4.RECENT])),
        "rain": np.exp(linear([m4.RAIN])),
        "flood": np.exp(linear([m4.EI])),
        "covid": np.exp(linear([m4.COVID])),
    }, index=train.index)
    mu = parts.prod(axis=1).to_numpy()
    if not np.allclose(mu, np.asarray(fit["result"].predict(), dtype=float), rtol=1e-6):
        raise ValueError("the multipliers do not multiply back to M4's fitted mean")
    return parts.assign(mu=mu)


def coefficient(fit, name):
    """A fitted coefficient, or NaN when this fit left the term out."""
    return float(fit["result"].params[name]) if name in fit["terms"] else np.nan


def left_out(fit, name, words):
    return words if name in fit["terms"] else "left out of this fit (no variation, or Rcum2 and EI2 too alike)"


def blocks_figure(ctx):
    """3. M4's expected count is a starting level times five multipliers, drawn on M4's own training weeks."""
    fit, train, when = ctx["fit"], ctx["train"], ctx["train_dates"]
    parts = multipliers(fit, train)
    rho, b1, b2, delta = (coefficient(fit, n) for n in (m4.RECENT, m4.RAIN, m4.EI, m4.COVID))
    rows = [
        ("start", "Starting level: population P × base rate exp(β0), in cases a week (no recent cases, no rain, "
                  "no flood, an average week of the year)"),
        ("season", "× season: three sine-cosine pairs over the year (figure 4)"),
        ("momentum", left_out(fit, m4.RECENT, rf"× momentum: $(1 + \tilde{{y}})^\rho$, ρ = {rho:.2f}; "
                                              r"$\tilde{y}$ = cases in the two newest weeks M4 may see")),
        ("rain", left_out(fit, m4.RAIN, f"× rain: exp(β1 × Rcum2 / {config.RAIN_SCALE_MM}), β1 = {b1:+.3f}; "
                                        "Rcum2 = the last two weeks of rain, mm")),
        ("flood", left_out(fit, m4.EI, f"× flood exposure: exp(β2 × EI2), β2 = {b2:+.3f}; "
                                       "EI2 = % of residents in flooded zones")),
        ("covid", left_out(fit, m4.COVID, f"× COVID: exp(δ) in {config.COVID_YEARS[0]}–{config.COVID_YEARS[-1]}, "
                                          f"δ = {delta:+.2f}, so ×{np.exp(delta):.2f}")),
    ]
    fig, axes = plt.subplots(len(rows) + 1, 1, figsize=(11, 12), sharex=True, facecolor=SURFACE,
                             gridspec_kw={"hspace": 0.62})
    for ax, (column, title) in zip(axes, rows):
        PF.style_axes(ax)
        shade_covid(ax)
        ax.plot(when, parts[column], color=M4_BLUE, linewidth=1.0)
        if column == "start":
            ax.set_ylim(0, parts[column].max() * 1.25)
        else:
            multiplier_axis(ax, parts[column])
        panel_title(ax, title)
    last = axes[-1]
    PF.style_axes(last)
    shade_covid(last)
    last.scatter(when, train["cases"], s=5, color=INK, linewidths=0, zorder=3, label="count")
    last.plot(when, parts["mu"], color=M4_BLUE, linewidth=1.0, label="M4's expected cases (in-sample)")
    last.set_ylim(bottom=0)
    last.legend(loc="upper left", frameon=False, fontsize=7.5, labelcolor=INK)
    panel_title(last, "= expected cases a week: the six rows above multiplied together")
    year_axis(last)
    last.set_xlim(when.min(), when.max())

    subtitle = (r"log μ = log P + β0 + season + ρ log(1 + $\tilde{y}$) + β1 Rcum2/50 + β2 EI2 + δ COVID. "
                "Taking exp of both sides turns every plus into a times: expected cases = population × base rate "
                "× season × momentum × rain × flood × COVID. Each row is one factor on M4's training weeks at the last "
                f"forecast day ({fit['rows']} weeks). A dashed line at ×1 means no effect; above it the factor "
                "raises the forecast.")
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.05, top=header(fig, "M4 is a product of simple multipliers",
                                                                       subtitle))
    footer(fig, "M4's fit at the last forecast day of forecasts.csv (B5, B10)")
    return fig


# Figure 4: the season

def month_ticks(ax, year):
    """Week-of-year axis labelled with the month each tick's week falls in."""
    first = weeks.week_index_of(year, 1)
    ticks = [max(1, weeks.week_index(date(year, m, 1)) - first + 1) for m in range(1, 13)]
    ax.set_xticks(ticks)
    ax.set_xticklabels([date(year, m, 1).strftime("%b") for m in range(1, 13)])


def season_figure(ctx):
    """4. The season term: three sine-cosine pairs add up to one smooth yearly curve."""
    data, fit = ctx["data"], ctx["fit"]
    params, terms = fit["result"].params, fit["terms"]
    ramp = (BLUE_250, BLUE_350, M4_BLUE)
    if config.FOURIER_K > len(ramp):
        raise ValueError(f"FOURIER_K = {config.FOURIER_K}: this figure has colours for {len(ramp)} pairs")
    year = config.BACKTEST_LAST_YEAR
    week = np.arange(1, config.MAX_WEEK + 1)
    terms_table = m4.season_terms([weeks.week_index_of(year, w) for w in week])
    names = {1: "one wave a year", 2: "adds a half-year wave", 3: "adds a third-of-a-year wave"}

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True, facecolor=SURFACE,
                                      gridspec_kw={"height_ratios": [1.5, 1], "hspace": 0.35})
    PF.style_axes(top)
    PF.style_axes(bottom)
    total = np.zeros(len(week))
    curves = []
    for k in range(1, config.FOURIER_K + 1):
        for wave in ("sin", "cos"):
            if f"{wave}{k}" in terms:
                total = total + params[f"{wave}{k}"] * terms_table[f"{wave}{k}"].to_numpy()
        curves.append(np.exp(total))
        span = "k = 1" if k == 1 else f"k = 1–{k}"
        label = f"{span}: {names.get(k, f'adds pair {k}')}" + (" (M4)" if k == config.FOURIER_K else "")
        top.plot(week, curves[-1], color=ramp[k - 1 + len(ramp) - config.FOURIER_K],
                 linewidth=1.0 if k < config.FOURIER_K else 2.0, label=label)
    multiplier_axis(top, np.concatenate(curves))
    peak = int(np.argmax(curves[-1]))
    top.annotate(f"peak ×{curves[-1][peak]:.1f} in week {week[peak]}", xy=(week[peak], curves[-1][peak]),
                 xytext=(10, 6), textcoords="offset points", fontsize=7.5, color=INK)
    top.legend(loc="upper left", frameon=False, fontsize=7.5, labelcolor=INK)
    panel_title(top, "M4's season multiplier through the year, built up one sine-cosine pair at a time")

    cases = data["cases"]
    years = [y for y in thresholds.complete_years(cases, cases["week_index"].max())
             if y not in config.COVID_YEARS]
    average = (cases[cases["year"].isin(years)].assign(w=lambda t: t["week"].map(weeks.week_of_year))
               .groupby("w")["cases"].mean().reindex(week))
    bottom.bar(week, average, width=0.8, color=MUTED, linewidth=0)
    panel_title(bottom, f"Average count in each week of the year, {PF.years_words(years)} (non-COVID years)")
    bottom.set_ylabel("cases a week", fontsize=8.5, color=INK_2)
    month_ticks(bottom, year)
    bottom.set_xlim(0.4, config.MAX_WEEK + 0.6)

    subtitle = (f"season = Σ(k=1..{config.FOURIER_K}) [α_k sin(2πkt/{config.WEEKS_PER_YEAR}) + "
                f"γ_k cos(2πkt/{config.WEEKS_PER_YEAR})], where t is the target week's index. One pair can only make "
                "a single smooth hump; three pairs let the curve rise steeply in the rainy season and fall slowly. "
                "The curve is milder than the raw averages below because momentum (figure 3) also carries the "
                "outbreak weeks.")
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.08, top=header(fig, "M4's season term", subtitle))
    footer(fig, "M4's fit at the last forecast day of forecasts.csv, and cases_weekly.csv")
    return fig


# Figure 5: the effects, and how they move as M4 is refit

EFFECTS = (   # (term, what one step of it means, the step in the term's own units)
    (m4.RECENT, "1 + recent cases doubles", np.log(2)),
    (m4.RAIN, f"{config.RAIN_SCALE_MM} mm more rain over two weeks", 1.0),
    (m4.EI, f"{config.EXPLAIN_EI_STEP} points more of QC in flood zones (EI2)", float(config.EXPLAIN_EI_STEP)),
    (m4.COVID, f"a COVID year ({config.COVID_YEARS[0]}–{config.COVID_YEARS[-1]})", 1.0),
)


def effects(fit):
    """Each effect as a rate ratio with its 95% interval: how many times next week's expected cases change per step."""
    interval = fit["result"].conf_int()
    rows = []
    for term, words, step in EFFECTS:
        if term in fit["terms"]:
            beta, low, high = fit["result"].params[term], *interval.loc[term]
            rows.append({"term": term, "words": words, "ratio": np.exp(step * beta),
                         "low": np.exp(step * low), "high": np.exp(step * high)})
        else:
            rows.append({"term": term, "words": words, "ratio": np.nan, "low": np.nan, "high": np.nan})
    return pd.DataFrame(rows)


def effect_paths(data):
    """effects() at every EXPLAIN_PATH_STEP-th forecast day of the backtest, and at the last one."""
    days = np.sort(data["table"]["forecast_week"].unique())
    chosen = list(days[::config.EXPLAIN_PATH_STEP])
    if chosen[-1] != days[-1]:
        chosen.append(days[-1])
    rows = []
    for T in chosen:
        fit, _ = fit_at(data, int(T))
        rows.append(effects(fit).assign(forecast_week=int(T)))
    out = pd.concat(rows, ignore_index=True)
    return out.assign(date=dates(out["forecast_week"]))


def effects_figure(ctx):
    """5. What each input does to next week's expected cases, at the last fit and across the backtest."""
    now = effects(ctx["fit"])
    paths = effect_paths(ctx["data"])
    fig = plt.figure(figsize=(11, 7.4), facecolor=SURFACE)
    grid = fig.add_gridspec(len(EFFECTS), 2, width_ratios=(1, 1.45), wspace=0.42, hspace=0.75)
    forest = fig.add_subplot(grid[:, 0])
    PF.style_axes(forest, grid_axis="x")
    y = np.arange(len(now))[::-1]
    forest.hlines(y, now["low"], now["high"], color=INK_2, linewidth=1.6)
    forest.scatter(now["ratio"], y, s=46, color=M4_BLUE, zorder=3, edgecolors=SURFACE, linewidths=1.5)
    for yy, row in zip(y, now.itertuples()):
        text = "left out of this fit" if np.isnan(row.ratio) else \
            f"{times(round(row.ratio, 2))}  ({row.low:.2f} to {row.high:.2f})"
        forest.text(1.0, yy + 0.22, text, transform=forest.get_yaxis_transform(), ha="right", va="bottom",
                    fontsize=7.5, color=INK)
    forest.set_yticks(y)
    forest.set_yticklabels([textwrap.fill(w, 24) for w in now["words"]], fontsize=8, color=INK)
    multiplier_axis_x(forest, np.r_[now["low"], now["high"]])
    forest.set_ylim(-0.7, len(now) - 0.3)
    panel_title(forest, f"At the last forecast day ({ctx['fit']['rows']} weeks)")

    for i, (term, words, _) in enumerate(EFFECTS):
        ax = fig.add_subplot(grid[i, 1])
        PF.style_axes(ax)
        shade_covid(ax)
        rows = paths[paths["term"] == term]
        ax.fill_between(rows["date"], rows["low"], rows["high"], color=BLUE_100, linewidth=0)
        ax.plot(rows["date"], rows["ratio"], color=M4_BLUE, linewidth=1.2)
        multiplier_axis(ax, np.r_[rows["low"].dropna(), rows["high"].dropna(), 1])
        panel_title(ax, words)
        year_axis(ax)
        ax.set_xlim(paths["date"].min(), paths["date"].max())
        if i < len(EFFECTS) - 1:
            ax.tick_params(labelbottom=False)

    subtitle = ("Each ratio says how many times next week's expected cases change for one step of an input, the "
                "others held fixed; the bar or band is its 95% interval, and ×1 means no effect. Left: M4's fit at "
                f"the last forecast day. Right: the same ratios at every {config.EXPLAIN_PATH_STEP}th forecast day, "
                f"{len(paths['forecast_week'].unique())} refits: M4 is refit every week, so its effects settle as data "
                "arrive. COVID's effect appears once COVID weeks are in the training data.")
    fig.subplots_adjust(left=0.17, right=0.99, bottom=0.08, top=header(fig, "What each input does in M4", subtitle))
    footer(fig, "M4 refit on the training rows of forecasts.csv's forecast days (B5, B10)")
    return fig


def multiplier_axis_x(ax, values):
    """multiplier_axis for an x axis, with a dashed line at ×1."""
    values = np.asarray(values, dtype=float)
    low = min(np.nanmin(values), 1 / 1.3) / 1.15
    high = max(np.nanmax(values), 1.3) * 1.15
    ax.set_xscale("log")
    ax.set_xlim(low, high)
    ticks = [v for v in NICE_MULTIPLIERS if low <= v <= high]
    ax.set_xticks(ticks)
    ax.set_xticklabels([times(v) for v in ticks])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.minorticks_off()
    ax.axvline(1, color=INK_2, linewidth=0.8, linestyle=(0, (3, 2)), zorder=1)


# Figure 6: what M4 may see on forecast day T

CELL = {   # style per kind of week: fill, edge, hatch, edge width, text colour
    "seen": (SHADE, BASELINE, None, 0.8, INK_2),
    "input": (BLUE_150, M4_BLUE, None, 1.2, INK),
    "hidden": ("white", BASELINE, "////", 0.8, INK_2),
    "target": ("white", M4_BLUE, None, 2.0, INK),
    "answer": ("white", INK, None, 2.0, INK),
    "future": ("white", BASELINE, None, 0.8, MUTED),
}
RAIN_WEEKS = (-1, 0)      # Rcum2(T) = R(T - 1) + R(T) and EI2(T) = max(EI(T - 1), EI(T)) (task B4)


def week_name(base, offset):
    """'T', 'T−2', 'T+1' (or the same with s)."""
    return base if offset == 0 else f"{base}{offset:+d}".replace("-", "−")


def check_guard_lags(option, g, momentum):
    """The weeks this figure marks as y~ are the ones view.prediction_row really adds (a made-up series)."""
    T = 100
    toy = pd.DataFrame([(i, *weeks.year_week(i)) for i in range(T + 1)], columns=["week_index", "year", "week"])
    toy["cases"] = 10.0 ** (toy["week_index"] - T + 6).clip(lower=0)    # every week a different power of 10
    got = view.prediction_row(toy, T, option, g)["recent"].iloc[0]
    expected = sum(10.0 ** (T + o - T + 6) for o in momentum)
    if not np.isclose(got, expected):
        raise ValueError(f"the figure marks weeks T{sorted(momentum)} as y~, but view.py adds other weeks")


def guard_figure(ctx):
    """6. What M4 may see at forecast day T: case counts stop g weeks early, rain and flood data do not."""
    option, g = ctx["data"]["option"], ctx["data"]["g"]
    h = config.FORECAST_HORIZON_WEEKS
    hidden = view.guard_weeks(option, g)
    lag = h + hidden                                    # y~ for target s = y(s - lag) + y(s - lag - 1) (view.py)
    momentum = {h - lag, h - lag - 1}                   # relative to T
    check_guard_lags(option, g, momentum)
    offsets = list(range(h - lag - 3, h + 1))

    def cases_kind(o):
        if o == h:
            return "target", "forecast this"
        if o > -hidden:
            return "hidden", "not in yet"
        return ("input", "used: ỹ") if o in momentum else ("seen", "seen")

    def weather_kind(o, used):
        if o > 0:
            return "future", "not yet"
        return ("input", f"used: {used}") if o in RAIN_WEEKS else ("seen", "seen")

    def training_kind(o):
        if o == h:
            return "answer", "known count"
        if o > -hidden:
            return "hidden", "skipped"
        return ("input", "used: ỹ") if o in momentum else ("seen", "seen")

    lanes = [
        ("Case counts", "guarded: the newest weeks are still being reported", "T", cases_kind),
        ("Rain", "never guarded: satellite rain is known in real time", "T", lambda o: weather_kind(o, "Rcum2")),
        ("Flood exposure", "never guarded: built from that rain", "T", lambda o: weather_kind(o, "EI2")),
        ("A training row", "every past target week s is built the same way", "s", training_kind),
    ]
    fig, ax = plt.subplots(figsize=(11, 5.8), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axis("off")
    left_label = -3.4
    ax.set_xlim(left_label - 0.1, len(offsets) + 0.1)
    ax.set_ylim(-2.0, len(lanes) * 1.25 + 0.4)
    for lane, (name, note, base, kind_of) in enumerate(lanes):
        y = (len(lanes) - 1 - lane) * 1.25
        if lane == len(lanes) - 1:
            ax.axhline(y + 1.07, xmin=0.02, xmax=0.98, color=GRID, linewidth=0.8)
        ax.text(left_label, y + 0.55, name, fontsize=9, weight="bold", color=INK, va="center")
        ax.text(left_label, y + 0.22, textwrap.fill(note, 34), fontsize=7, color=INK_2, va="center")
        for i, o in enumerate(offsets):
            kind, role = kind_of(o)
            fill, edge, hatch, width, ink = CELL[kind]
            name_o = week_name(base, o - h if base == "s" else o)
            ax.add_patch(Rectangle((i + 0.06, y + 0.1), 0.88, 0.78, facecolor=fill, edgecolor=edge, hatch=hatch,
                                   linewidth=width, linestyle=(0, (2, 2)) if kind == "future" else "-"))
            behind = dict(facecolor="white", edgecolor="none", pad=1.2) if hatch else None   # readable over hatching
            ax.text(i + 0.5, y + 0.6, name_o, ha="center", va="center", fontsize=8.5, weight="bold", color=ink,
                    bbox=behind)
            ax.text(i + 0.5, y + 0.32, role, ha="center", va="center", fontsize=6.8, color=ink, bbox=behind)
    now = offsets.index(0) + 1
    ax.plot([now, now], [-0.25, len(lanes) * 1.25 - 0.1], color=M4_BLUE, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(now, len(lanes) * 1.25, "forecast day T: the forecast is made at the end of this week", ha="center",
            va="bottom", fontsize=7.5, color=M4_BLUE)

    newest, older = max(momentum), min(momentum)
    lines = [
        rf"Recent cases: $\tilde{{y}}$ = y({week_name('T', older)}) + y({week_name('T', newest)}), the two newest "
        f"weeks M4 may see. The guard g = {g} hides the last {hidden} weeks because their counts are still coming in.",
        f"Rain and flood exposure: Rcum2(T) = R(T−1) + R(T) and EI2(T) = max(EI(T−1), EI(T)), both already observed "
        f"on day T.",
        rf"Training: the row for target week s uses $\tilde{{y}}$ = y({week_name('s', older - h)}) + "
        f"y({week_name('s', newest - h)}), the same {hidden}-week gap, so M4 learns from the inputs it will really "
        "get (rule 1).",
    ]
    for i, line in enumerate(lines):
        ax.text(left_label, -0.45 - 0.42 * i, line, fontsize=7.8, color=INK, va="center")

    option_words = {"B": "option B, report-week counts: no guard",
                    "C": f"option C, counts by onset week with no report dates: guard g = {g} weeks"}
    subtitle = (f"Decision-tree {option_words.get(option, f'option {option}')}. Blue boxes are M4's inputs, the "
                "thick blue box is the week it forecasts. Check S11 overwrites every unseen count with −999 and "
                "confirms no forecast changes.")
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.03, top=header(fig, "What M4 may see on forecast day T",
                                                                       subtitle))
    footer(fig, "src/view.py (B2) and src/features.py (B4); the marked weeks are checked against view.prediction_row")
    return fig


# Figure 7: the rolling-origin backtest

def backtest_figure(ctx):
    """7. The backtest: at every forecast day M4 is refit on all it can see and forecasts one week ahead."""
    data = ctx["data"]
    option, g, cases = data["option"], data["g"], data["cases"]
    days = np.sort(data["table"]["forecast_week"].unique())
    picks = days[np.linspace(0, len(days) - 1, BACKTEST_ROWS).round().astype(int)]
    first = int(cases.dropna(subset=["cases"])["week_index"].min())
    start = pd.Timestamp(weeks.week_start(first))
    week = pd.Timedelta(days=config.DAYS_PER_WEEK)

    fig, ax = plt.subplots(figsize=(11, 5.0), facecolor=SURFACE)
    PF.style_axes(ax, grid_axis="x")
    shade_covid(ax)
    for row, T in enumerate(picks):
        y = BACKTEST_ROWS - row
        cut = view.cutoff(int(T), option, g)
        target = int(T) + config.FORECAST_HORIZON_WEEKS
        seen_end = pd.Timestamp(weeks.week_start(cut)) + week
        guard_end = pd.Timestamp(weeks.week_start(target))
        ax.barh(y, date_num(seen_end) - date_num(start), left=date_num(start), height=0.42, color=BLUE_150,
                edgecolor=M4_BLUE, linewidth=0.6)
        ax.barh(y, date_num(guard_end) - date_num(seen_end), left=date_num(seen_end), height=0.42, color="white",
                edgecolor=BASELINE, hatch="////", linewidth=0.6)
        ax.scatter([pd.Timestamp(weeks.week_start(target)) + week / 2], [y], s=34, color=M4_BLUE, zorder=4,
                   edgecolors=SURFACE, linewidths=1.2)
        n_seen = len(view.training_rows(cases, int(T), option, g))
        ax.text(start, y + 0.3, f"forecast day {weeks.week_start(int(T)):%d %b %Y}: trains on {n_seen} weeks, "
                                f"forecasts the week of {weeks.week_start(target):%d %b %Y}",
                fontsize=7.5, color=INK, va="bottom")
    ax.vlines(dates(days) + week / 2, -0.25, 0.25, color=MUTED, linewidth=0.5)
    ax.text(start, 0.4, f"all {len(days)} forecast days, one a week", fontsize=7.5, color=INK_2, va="bottom")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_ylim(-0.6, BACKTEST_ROWS + 0.9)
    year_axis(ax)
    ax.set_xlim(start, pd.Timestamp(weeks.week_start(int(days[-1]))) + 3 * week)
    ax.legend(handles=[Patch(facecolor=BLUE_150, edgecolor=M4_BLUE, label="weeks whose counts M4 trains on"),
                       Patch(facecolor="white", edgecolor=BASELINE, hatch="////",
                             label=f"the {view.guard_weeks(option, g)} guarded weeks (too thin to see at this scale; "
                                   "figure 6)"),
                       Line2D([], [], marker="o", linestyle="", color=M4_BLUE, label="the week forecast")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=7.5, labelcolor=INK)
    subtitle = ("A rolling-origin backtest replays history: on each forecast day M4 (and M0, M1, M3) is refit using "
                "only the counts known then, forecasts the next week, and is scored when that week's count is in. The "
                "training window grows by one week each time. Rain return levels are refit at the first forecast day "
                "of each year, on earlier years only (rule 2).")
    fig.subplots_adjust(left=0.02, right=0.99, bottom=0.1, top=header(fig, "How the backtest tests M4", subtitle) - 0.06)
    footer(fig, "forecasts.csv (B10) and src/view.py (B2)")
    return fig


# Figure 8: anatomy of one forecast

def anatomy_panel(ax, row, label):
    """One forecast's distribution with its three outputs: expected cases, 90% range and Pr(breach)."""
    dist = forecast_range.forecast_dist(row["mu"], row["theta"])
    t_w = row["threshold"]
    low, high = forecast_range.range_90(dist)
    p = thresholds.breach_probability(dist, t_w)
    if not np.isclose(p, row["p_breach"], atol=5e-4) or not np.allclose((low, high), (row["q0.050"], row["q0.950"])):
        raise ValueError(f"{label}: recomputed Pr(breach) or range differs from forecasts.csv")
    top = int(max(dist.ppf(X_EXTENT_Q), row["y"], t_w) * 1.12) + 1
    x = np.arange(0, top + 1)
    over = x > t_w
    PF.style_axes(ax)
    ax.bar(x[~over], dist.pmf(x[~over]), width=0.9, color=BLUE_150, linewidth=0,
           label=f"counts up to the threshold: {1 - p:.0%}")
    ax.bar(x[over], dist.pmf(x[over]), width=0.9, color=M4_BLUE, linewidth=0,
           label=f"more than the threshold: Pr(breach) = {p:.0%}")
    ax.axvline(t_w, color=INK, linewidth=1, linestyle=(0, (4, 2)))
    ax.axvline(row["mu"], color=INK_2, linewidth=0.8)
    for x, height, words in ((t_w, 0.64, f"epidemic threshold T_w = {t_w:.1f}"),
                             (row["mu"], 0.50, f"expected cases μ = {row['mu']:.1f}")):
        ax.annotate(words, xy=(x, height), xycoords=ax.get_xaxis_transform(), xytext=(0.52, height),
                    textcoords="axes fraction", va="center", fontsize=7.5, color=INK,
                    arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=0.8, mutation_scale=7, shrinkA=2,
                                    shrinkB=0))
    ax.annotate("", xy=(low - 0.45, 1.03), xytext=(high + 0.45, 1.03), xycoords=ax.get_xaxis_transform(),
                arrowprops=dict(arrowstyle="|-|", color=INK, linewidth=0.9, mutation_scale=3), annotation_clip=False)
    ax.text((low + high) / 2, 1.06, f"90% range: {low:.0f} to {high:.0f}", transform=ax.get_xaxis_transform(),
            ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.scatter([row["y"]], [0], marker="D", s=44, color=INK, zorder=5, clip_on=False)
    ax.annotate(f"actual {row['y']:.0f}", xy=(row["y"], 0), xytext=(0, 12), textcoords="offset points", ha="center",
                fontsize=7.5, color=INK, weight="bold")
    ax.set_xlim(-0.6, top + 0.6)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("cases that week", fontsize=8.5, color=INK_2)
    ax.legend(loc="upper right", frameon=False, fontsize=7.5, labelcolor=INK)
    outcome = "a breach" if row["y"] > t_w else "no breach"
    ax.set_title(f"{label}: target week {row['week']:.0f} of {row['year']:.0f}, the week of "
                 f"{weeks.week_start(int(row['week_index'])):%d %b %Y}; actual {row['y']:.0f}, {outcome}",
                 loc="left", fontsize=8.5, color=INK, pad=26)


def anatomy_figure(ctx):
    """8. One forecast, taken apart: a whole distribution and the three numbers read off it."""
    table = ctx["data"]["table"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.9), facecolor=SURFACE, gridspec_kw={"wspace": 0.18})
    for ax, (label, when) in zip(axes, (("Dry season", config.EXPLAIN_QUIET_WEEK),
                                        ("Flood season", config.EXPLAIN_BUSY_WEEK))):
        anatomy_panel(ax, forecast_row(table, "M4", *when), label)
    axes[0].set_ylabel("probability", fontsize=8.5, color=INK_2)
    subtitle = ("Every forecast is a negative binomial, NB(μ, θ): μ from the model, θ from the size of its last 104 "
                "non-COVID misses (B6). Three outputs are read off it: the expected cases μ, the 90% range from the "
                "5% to the 95% point, and Pr(breach) = dist.sf(floor(T_w)), the chance the final count is strictly "
                "greater than the week's epidemic threshold T_w (rule 6).")
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.17, top=header(fig, "One M4 forecast, taken apart", subtitle)
                        - 0.05)
    footer(fig, "forecasts.csv (B10); the range and Pr(breach) are recomputed and checked against it")
    return fig


# Figure 9: the epidemic threshold

def threshold_figure(ctx):
    """9. How the week's epidemic threshold T_w is built, and which weeks of the year breached it."""
    data = ctx["data"]
    cases, option, g = data["cases"], data["option"], data["g"]
    year = config.EXPLAIN_THRESHOLD_YEAR
    rows = model_rows(data["table"], "M4")
    rows = rows[rows["year"] == year]
    if rows.empty:
        raise ValueError(f"forecasts.csv has no M4 forecasts in {year} (config.EXPLAIN_THRESHOLD_YEAR)")
    weekly = []
    for r in rows.itertuples():
        cut = view.cutoff(r.forecast_week, option, g)
        counts = thresholds.reference_counts(year, r.week, cases, cut)
        t_w = thresholds.epidemic_threshold(year, r.week, cases, cut)
        if not np.isclose(t_w, r.threshold, atol=5e-4):
            raise ValueError(f"{year} week {r.week}: threshold {t_w:.4f} differs from forecasts.csv's {r.threshold}")
        weekly.append({"week": r.week, "mean": counts.mean(), "t_w": t_w, "y": r.y, "years": tuple(counts.index)})
    weekly = pd.DataFrame(weekly)
    years = weekly["years"].iloc[-1]

    fig, ax = plt.subplots(figsize=(11, 5.0), facecolor=SURFACE)
    PF.style_axes(ax)
    for ref in years:
        past = cases[(cases["year"] == ref) & (cases["week"] <= config.MAX_WEEK)].sort_values("week")
        ax.plot(past["week"], past["cases"], color=MUTED, linewidth=0.8, alpha=0.8)
    ax.plot(weekly["week"], weekly["mean"], color=INK_2, linewidth=1.2, linestyle=(0, (4, 2)))
    ax.plot(weekly["week"], weekly["t_w"], color=INK, linewidth=1.8, drawstyle="steps-mid")
    breach = weekly["y"] > weekly["t_w"]
    ax.scatter(weekly.loc[~breach, "week"], weekly.loc[~breach, "y"], s=16, facecolors=SURFACE,
               edgecolors=INK_2, linewidths=0.9, zorder=4)
    ax.scatter(weekly.loc[breach, "week"], weekly.loc[breach, "y"], s=34, color=M4_BLUE, zorder=5,
               edgecolors=SURFACE, linewidths=1)
    ax.set_xlim(0.5, config.MAX_WEEK + 0.5)
    ax.set_ylim(bottom=0)
    month_ticks(ax, year)
    ax.set_ylabel("cases a week", fontsize=8.5, color=INK_2)
    ax.legend(handles=[
        Line2D([], [], color=MUTED, linewidth=0.8, label=f"each reference year: {PF.years_words(years)}"),
        Line2D([], [], color=INK_2, linewidth=1.2, linestyle=(0, (4, 2)), label="their mean for that week"),
        Line2D([], [], color=INK, linewidth=1.8, label="threshold T_w = mean + 2 SD"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor=SURFACE, markeredgecolor=INK_2,
               label=f"{year} count, at or under T_w"),
        Line2D([], [], marker="o", linestyle="", color=M4_BLUE, label=f"{year} count above T_w: a breach week"),
    ], loc="upper left", frameon=False, fontsize=7.5, labelcolor=INK)
    subtitle = (f"For each week of the year, T_w = mean + {config.THRESHOLD_SD} × SD of that week's count over up to "
                f"the {config.THRESHOLD_MAX_YEARS} most recent complete non-COVID years before the target year (at "
                f"least {config.THRESHOLD_MIN_YEARS}). A week breaches when its final count is strictly greater than "
                f"T_w. In {year}, {int(breach.sum())} of {len(weekly)} forecast weeks breached. A quiet week's "
                "threshold sits near zero, so a few cases can breach it.")
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.14, top=header(fig, f"The epidemic threshold, {year}", subtitle))
    footer(fig, "cases_weekly.csv and forecasts.csv; T_w recomputed with src/thresholds.py (B7) and checked")
    return fig


# Figure 10: the spread theta and the 90% range

def spread_figure(ctx):
    """10. How wide M4's ranges are (theta) and whether they hold 90% of the counts."""
    rows = model_rows(ctx["data"]["table"], "M4")
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 6.0), sharex=True, facecolor=SURFACE,
                                      gridspec_kw={"hspace": 0.4})
    for ax in (top, bottom):
        PF.style_axes(ax)
        shade_covid(ax)
    for source, color, words in (
            ("fit", MUTED, f"from the training fit (fewer than {config.THETA_MIN_FORECASTS} past forecasts)"),
            ("past", M4_BLUE, f"from the last {config.THETA_WINDOW} non-COVID past forecasts' misses")):
        part = rows[(rows["theta_from"] == source) & np.isfinite(rows["theta"])]
        top.scatter(part["date"], part["theta"], s=8, color=color, linewidths=0, label=f"θ {words}")
    top.set_yscale("log")
    top.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    top.yaxis.set_minor_formatter(NullFormatter())
    top.set_ylabel("θ (log scale)", fontsize=8.5, color=INK_2)
    top.legend(loc="upper right", frameon=False, fontsize=7.5, labelcolor=INK)
    panel_title(top, "θ for each forecast: smaller means a wider range")

    level = config.RANGE_HIGH_Q - config.RANGE_LOW_Q
    inside = ((rows["q0.050"] <= rows["y"]) & (rows["y"] <= rows["q0.950"])).astype(float)
    rolling = inside.rolling(config.EXPLAIN_COVERAGE_WINDOW).mean()
    bottom.plot(rows["date"], rolling, color=M4_BLUE, linewidth=1.4)
    bottom.axhline(level, color=INK_2, linewidth=0.8, linestyle=(0, (3, 2)))
    bottom.text(rows["date"].iloc[0], level + 0.012, f" {level:.0%}: a well-sized 90% range", fontsize=7.5,
                color=INK_2, va="bottom")
    bottom.set_ylim(0.6, 1.02)
    bottom.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    panel_title(bottom, f"Share of the last {config.EXPLAIN_COVERAGE_WINDOW} weeks whose count fell inside M4's 90% "
                        "range")
    year_axis(bottom)
    bottom.set_xlim(rows["date"].min(), rows["date"].max())
    poisson = int((~np.isfinite(rows["theta"])).sum())
    extra = f" {poisson} forecasts used a Poisson range (θ = ∞)." if poisson else ""
    subtitle = ("θ = Σμ² / Σ[(y − μ)² − μ], over the model's last 104 non-COVID past forecasts whose counts are "
                "already known, so the range is as wide as the model's recent misses (B6). Below 26 such forecasts "
                "θ comes from the training fit; a denominator at or below 0 gives a Poisson range." + extra)
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.08, top=header(fig, "How wide M4's range is, and whether it "
                                                                            "holds", subtitle))
    footer(fig, "forecasts.csv (B6, B10)")
    return fig


# Figure 11: the flood test

def flood_test_figure(ctx):
    """11. The flood test: M4 against M4 without EI2 in the storm years' flood seasons."""
    data = ctx["data"]
    table, feats = data["table"], data["features"]
    with_ei, without_ei = config.FLOOD_TEST
    first, last = config.EXPLAIN_FLOOD_SEASON
    years = config.EXPLAIN_FLOOD_YEARS
    fig, axes = plt.subplots(2, len(years), figsize=(11, 5.6), facecolor=SURFACE, sharey="row",
                             gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.3, "wspace": 0.08})
    for col, year in enumerate(years):
        top, bottom = axes[0, col], axes[1, col]
        PF.style_axes(top)
        PF.style_axes(bottom)
        a = model_rows(table, with_ei)
        b = model_rows(table, without_ei)
        keep = lambda t: t[(t["year"] == year) & t["week"].between(first, last)]
        a, b = keep(a), keep(b)
        top.scatter(a["week"], a["y"], s=10, color=INK, linewidths=0, zorder=4, label="count")
        top.plot(b["week"], b["mu"], color=NO_EI2_GREY, linewidth=1.4, label=PF.model_name(without_ei))
        top.plot(a["week"], a["mu"], color=M4_BLUE, linewidth=1.4, label=PF.model_name(with_ei))
        top.set_title(str(year), loc="left", fontsize=9, weight="bold", color=INK)
        ei = feats[feats["week_index"].isin(a["forecast_week"])]
        ei = ei[ei["fit_year"] == ei["week_index"].map(lambda i: weeks.year_week(int(i))[0])]
        target = ei["week_index"] + config.FORECAST_HORIZON_WEEKS
        bottom.bar(target.map(lambda i: weeks.year_week(int(i))[1]), ei["ei2"], width=0.8, color=MUTED, linewidth=0)
        for ax in (top, bottom):
            ax.set_xlim(first - 0.6, last + 0.6)
            ax.set_xticks(range(first, last + 1, 4))
        bottom.set_xlabel("target week of the year", fontsize=8, color=INK_2)
    axes[0, 0].set_ylabel("cases a week", fontsize=8.5, color=INK_2)
    axes[1, 0].set_ylabel("EI2 read, %", fontsize=8.5, color=INK_2)
    axes[0, 0].legend(loc="upper left", frameon=False, fontsize=7.5, labelcolor=INK)
    axes[0, 0].set_ylim(bottom=0)
    axes[1, 0].set_ylim(bottom=0)

    result = compare.compare(table, with_ei, without_ei, dm=False)
    row = result[result["block_weeks"] == config.BOOT_BLOCK_WEEKS].iloc[0]
    subtitle = (f"Both models are fit on the same days; the only difference is the EI2 term. Top: forecasts in weeks "
                f"{first}–{last}. Bottom: the EI2 each forecast read (the forecast day's last two weeks). Over all "
                f"{int(row['weeks'])} scored weeks, |error with EI2| − |error without| averages "
                f"{row['mean_diff']:+.2f} cases a week, 95% interval {row['low']:+.2f} to {row['high']:+.2f} "
                f"({config.BOOT_BLOCK_WEEKS}-week blocks): {row['verdict']}.")
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.13, top=header(fig, "The flood test: does EI2 help M4?",
                                                                      subtitle))
    footer(fig, "forecasts.csv (B10) and features_weekly.csv (B4); the test is src/compare.py (D6)")
    return fig


# Figure 12: the primary endpoint

def bootstrap_means(d, block=config.BOOT_BLOCK_WEEKS, resamples=config.BOOT_RESAMPLES, seed=config.RANDOM_SEED):
    """The resampled means behind compare.block_bootstrap's interval, drawn the same way with the same seed."""
    d = np.asarray(d, dtype=float)
    n = len(d)
    rng = np.random.default_rng(seed)
    blocks = -(-n // block)   # ceil(n / block)
    means = np.empty(resamples)
    for i in range(resamples):
        starts = rng.integers(0, n - block + 1, size=blocks)
        means[i] = np.concatenate([d[s:s + block] for s in starts])[:n].mean()
    return means


def endpoint_figure(ctx):
    """12. The primary endpoint (D5): M4's average miss against M3's, with its block-bootstrap interval."""
    table = ctx["data"]["table"]
    a, b = config.PRIMARY_COMPARISON
    losses = compare.loss_differences(table, a, b, config.MAE_YEARS)
    d = losses["d"].to_numpy()
    means = bootstrap_means(d)
    boot = compare.block_bootstrap(d)
    tail = 100 * (1 - config.BOOT_INTERVAL) / 2
    low, high = np.percentile(means, [tail, 100 - tail])
    if not np.allclose((low, high), (boot["low"], boot["high"])):
        raise ValueError("the redrawn bootstrap does not match compare.block_bootstrap")
    scored = table[table["year"].isin(config.MAE_YEARS)]
    mae = scored.assign(miss=(scored["y"] - scored["mu"]).abs()).groupby("model")["miss"].mean()

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 6.6), facecolor=SURFACE,
                                      gridspec_kw={"height_ratios": [1.3, 1], "hspace": 0.45})
    PF.style_axes(top)
    PF.style_axes(bottom)
    when = dates(losses["week_index"])
    colors = np.where(d < 0, M4_BLUE, np.where(d > 0, M3_ORANGE, MUTED))
    top.bar(when, d, width=6, color=colors, linewidth=0)
    top.axhline(0, color=INK_2, linewidth=0.8)
    shade_covid(top, label=True)
    year_axis(top)
    top.set_ylabel("|error M4| − |error M3|", fontsize=8.5, color=INK_2)
    top.set_yscale("symlog", linthresh=5)
    reach = np.abs(d).max()
    ticks = [v for v in (-1000, -100, -10, 0, 10, 100, 1000) if abs(v) <= reach * 1.5]
    top.set_yticks(ticks)
    top.set_yticklabels([f"{v:+,}".replace("+0", "0").replace("-", "−") for v in ticks])
    top.yaxis.set_minor_formatter(NullFormatter())
    top.set_xlim(when.min() - pd.Timedelta(days=14), when.max() + pd.Timedelta(days=14))
    top.legend(handles=[Patch(color=M4_BLUE, label=f"{a} missed by less that week"),
                        Patch(color=M3_ORANGE, label=f"{b} missed by less that week")],
               loc="lower left", frameon=False, fontsize=7.5, labelcolor=INK, ncol=2)
    panel_title(top, f"Each scored week's difference in misses, cases (symmetric log scale; {len(d)} weeks)")

    counts, edges = np.histogram(means, bins=40)
    centres = (edges[:-1] + edges[1:]) / 2
    bottom.bar(centres, counts, width=(edges[1] - edges[0]) * 0.9,
               color=np.where(centres < 0, M4_BLUE, M3_ORANGE), linewidth=0)
    marks = ((low, (0, (4, 2)), f"2.5% point: {low:+.2f} ", 0.97, "right"),
             (high, (0, (4, 2)), f"97.5% point: {high:+.2f} ", 0.97, "right"),
             (boot["mean"], "-", f" observed mean {boot['mean']:+.2f}", 0.86, "left"))
    for x, style, words, height, side in marks:
        bottom.axvline(x, color=INK, linewidth=1.0, linestyle=style)
        bottom.text(x, height, words, transform=bottom.get_xaxis_transform(), fontsize=7.5, color=INK, va="top",
                    ha=side, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.2))
    bottom.axvline(0, color=INK_2, linewidth=0.8)
    bottom.set_ylim(0, counts.max() * 1.4)     # headroom so the labels sit above the bars
    bottom.set_xlabel("mean of |error M4| − |error M3| in one resample, cases a week", fontsize=8.5, color=INK_2)
    bottom.set_ylabel("resamples", fontsize=8.5, color=INK_2)
    panel_title(bottom, f"{config.BOOT_RESAMPLES:,} moving-block resamples ({config.BOOT_BLOCK_WEEKS}-week blocks, so "
                        "outbreak runs stay together)")

    verdict = compare.verdict(boot["low"], boot["high"], a, b)
    subtitle = (f"Over {PF.years_words(config.MAE_YEARS)}, M4 missed by {mae[a]:.2f} cases a week on average and M3 "
                f"by {mae[b]:.2f}. The endpoint is the mean of |error M4| − |error M3|, {boot['mean']:+.2f}; below 0, "
                "M4 is better. Resampling blocks of whole weeks keeps neighbouring weeks together, since they are "
                f"alike; the 95% interval is {boot['low']:+.2f} to {boot['high']:+.2f}: {verdict}.")
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.12, top=header(fig, "The primary endpoint: M4 against M3",
                                                                       subtitle))
    footer(fig, "forecasts.csv (B10); the test is src/compare.py (D5) and the interval is checked against it")
    return fig


FIGURES = (
    ("m4_01_data.png", data_figure),
    ("m4_02_why_negative_binomial.png", nb_figure),
    ("m4_03_building_blocks.png", blocks_figure),
    ("m4_04_season.png", season_figure),
    ("m4_05_effects.png", effects_figure),
    ("m4_06_what_m4_sees.png", guard_figure),
    ("m4_07_backtest.png", backtest_figure),
    ("m4_08_one_forecast.png", anatomy_figure),
    ("m4_09_threshold.png", threshold_figure),
    ("m4_10_range_width.png", spread_figure),
    ("m4_11_flood_test.png", flood_test_figure),
    ("m4_12_primary_endpoint.png", endpoint_figure),
)


def main():
    data = load()
    ctx = {"data": data, **last_fit(data)}
    for name, draw in FIGURES:
        start = time.perf_counter()
        path = save(draw(ctx), name)
        print(f"wrote {PF.shown(path)} ({time.perf_counter() - start:.1f} s)")


if __name__ == "__main__":
    main()

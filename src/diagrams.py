"""The paper's two design diagrams, for Appendix A (task E8).

E8 asks for Figures 1 and 1b of the team's Methodology document (9 October 2026), updated
to the core scope. That document's Figure 1 is the study design and its next diagram (its
Figure 2) is the Layer 1 pipeline; both are redrawn here as built:

1. design_figure: one flood computation feeds both layers. Cases come from QCESD's list
   as weekly counts by onset week (no Cebu City, no report-date snapshots); rain from IMERG,
   with archived ECMWF forecasts and ERA5 for the forecast runs (no CHIRPS); people from
   WorldPop fitted to the 2024 census (no Meta grid). The flood computation uses the wettest
   3-day rain (config.RAIN_ACCUM_DAYS), not the wettest 24 hours. Layer 1 is M0, M1, M3
   and M4, one week ahead (no M2, M5 or two-week forecast). Layer 2 is checked on the four
   storms (config.STORMS), not on a validation regression.

2. layer1_figure: the six steps behind every forecast day, as B10 runs them: the delay
   guard (config.DELAY_GUARD_G) instead of report-date snapshots and nowcasts, M4's inputs,
   the four models, the forecast distribution (config.THETA_WINDOW past misses) and the
   backtest (config.BACKTEST_FIRST_YEAR to BACKTEST_LAST_YEAR).

The diagrams hold no results, only the design, so they need no data and run in a second.
Every setting they print is read from config.py, so a changed setting changes the picture.
Dose figures are stock planning, not prescriptions.

Outputs in results/ (copied into paper/figures/ for the paper, as D8's are):
    e8_fig_design.png    e8_fig_layer1.png

Run from the repository root:
    python -m src.diagrams
"""

import matplotlib

matplotlib.use("Agg")    # draw into files only; no window opens
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import config
from src import layer2_results

L2 = layer2_results                   # D7: ink colours and save_png, shared with D8
INK, INK_2, SURFACE = L2.INK, L2.INK_2, L2.SURFACE
EDGE, ARROW = "#c3c2b7", "#9a998f"    # box outline and arrows: D8's baseline grey, a shade darker
FOCUS_EDGE, FOCUS_FILL = "#2a78d6", "#e8f1fc"   # the step each figure is about: palette slot 1 and a wash
TITLE_SIZE, LINE_SIZE = 7.9, 6.8      # points; the figures print at the page's full width
LINE_STEP = 2.45                      # vertical space per text line, in the axes' units
TITLE_GAP = 3.1                       # from the title's centre to the first line's


def years_span(first, last):
    """'2018-2026' with an en dash."""
    return f"{first}–{last}"


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def canvas(width_in, height_in, height_units):
    """A figure whose axes run 0-100 across and 0-height_units up, with no axes drawn."""
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    fig.patch.set_facecolor(SURFACE)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, height_units)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, lines=(), focus=False):
    """A rounded box with its lower-left corner at (x, y): a bold title over plain lines.

    Returns the box's edges as a dict, so arrows can start and end on them.
    """
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                facecolor=FOCUS_FILL if focus else "white",
                                edgecolor=FOCUS_EDGE if focus else EDGE, linewidth=1.3 if focus else 0.9))
    lines = list(lines)
    block = (TITLE_GAP + LINE_STEP * (len(lines) - 1)) if lines else 0   # title centre to last line centre
    top = y + h / 2 + block / 2
    ax.text(x + w / 2, top, title, ha="center", va="center", fontsize=TITLE_SIZE, weight="bold", color=INK)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, top - TITLE_GAP - LINE_STEP * i, line, ha="center", va="center", fontsize=LINE_SIZE,
                color=INK_2)
    return {"left": x, "right": x + w, "bottom": y, "top": y + h, "cx": x + w / 2, "cy": y + h / 2}


def arrow(ax, points, dashed=False):
    """A line through the given points with an arrowhead at the last one."""
    xs, ys = zip(*points)
    style = (0, (4, 3)) if dashed else "-"
    if len(points) > 2:
        ax.plot(xs[:-1], ys[:-1], color=ARROW, linewidth=0.9, linestyle=style, solid_capstyle="butt")
    ax.annotate("", xy=points[-1], xytext=points[-2],
                arrowprops=dict(arrowstyle="-|>", color=ARROW, linewidth=0.9, linestyle=style,
                                shrinkA=0, shrinkB=0, mutation_scale=8))


def label(ax, x, y, text, ha="center"):
    """A small grey note beside an arrow."""
    ax.text(x, y, text, ha=ha, va="center", fontsize=LINE_SIZE - 0.6, color=INK_2, style="italic")


def heading(ax, height_units, title, subtitle):
    """Title and subtitle above the diagram, as D8's figures have them."""
    ax.text(0, height_units + 7, title, ha="left", va="bottom", fontsize=11, weight="bold", color=INK)
    ax.text(0, height_units + 2.5, subtitle, ha="left", va="bottom", fontsize=8, color=INK_2)


# ---------------------------------------------------------------------------
# Figure A1: the study design
# ---------------------------------------------------------------------------

def design_figure(path):
    """Three inputs, one flood computation, two layers, their outputs and how each was tested."""
    height = 92
    fig, ax = canvas(7.4, 4.8, height)
    heading(ax, height, "One flood computation feeds the city forecast and the barangay stock",
            "Inputs on top; the shared flood computation in the middle; what each layer gives, and how it "
            "was tested, below")
    w, h = 28, 19
    col = {"left": 0, "mid": 36, "right": 72}
    row = {"top": 70, "mid": 37, "bottom": 4}
    storms = len(config.STORMS)
    periods = ", ".join(str(t) for t in config.NOAH_RETURN_PERIODS)

    cases = box(ax, col["left"], row["top"], w, h, "Case counts",
                ["QCESD case list, 2015–2026,", "weekly counts by onset week"])
    rain = box(ax, col["mid"], row["top"], w, h, "Rain",
               ["IMERG Late daily (observed);", "archived ECMWF forecasts", "and ERA5 (Open-Meteo)"])
    maps = box(ax, col["right"], row["top"], w, h, "Flood maps + people",
               [f"NOAH {periods}-year maps;", "WorldPop fitted to the", "2024 census, per barangay"])
    layer1 = box(ax, col["left"], row["mid"], w, h, "Layer 1 · City forecast",
                 ["M0, M1, M3, M4, 1 week ahead,", "from recent cases, rain and", "the flood exposure index"])
    flood = box(ax, col["mid"], row["mid"], w, h, "Flood exposure",
                [f"wettest {config.RAIN_ACCUM_DAYS}-day catchment rain", "→ graded between the maps",
                 "× residents per hazard level"], focus=True)
    layer2 = box(ax, col["right"], row["mid"], w, h, "Layer 2 · Barangay stock",
                 ["DM 2023-0309 risk tiers", "× each tier's regimen;", "high risk first if stock is short"])
    breach = box(ax, col["left"], row["bottom"], w, h, "Breach probability",
                 ["expected cases, 90% range,", "Pr(breach) for hospitals", "and health offices"])
    evaluation = box(ax, col["mid"], row["bottom"], w, h, "Evaluation",
                     ["Layer 1: weekly backtest,",
                      f"{years_span(config.BACKTEST_FIRST_YEAR, config.BACKTEST_LAST_YEAR)}; Layer 2: {storms} storms,",
                      "observed and forecast rain"])
    stock = box(ax, col["right"], row["bottom"], w, h, "Stock per health center",
                ["doxycycline, children's courses,", "amoxicillin for pregnant women", "(planning, not prescriptions)"])

    gap = (rain["bottom"] + layer1["top"]) / 2      # the level where the input arrows turn
    arrow(ax, [(cases["cx"], cases["bottom"]), (cases["cx"], layer1["top"])])
    arrow(ax, [(rain["cx"], rain["bottom"]), (rain["cx"], flood["top"])])
    arrow(ax, [(rain["left"] + 4, rain["bottom"]), (rain["left"] + 4, gap), (layer1["right"] - 5, gap),
               (layer1["right"] - 5, layer1["top"])])
    arrow(ax, [(maps["cx"], maps["bottom"]), (maps["cx"], gap), (flood["right"] - 4, gap),
               (flood["right"] - 4, flood["top"])])
    arrow(ax, [(flood["left"], flood["cy"]), (layer1["right"], layer1["cy"])])
    label(ax, (flood["left"] + layer1["right"]) / 2, flood["cy"] + 2.4, "index")
    arrow(ax, [(flood["right"], flood["cy"]), (layer2["left"], layer2["cy"])])
    label(ax, (flood["right"] + layer2["left"]) / 2, flood["cy"] + 2.4, "residents")
    arrow(ax, [(layer1["cx"], layer1["bottom"]), (breach["cx"], breach["top"])])
    arrow(ax, [(layer2["cx"], layer2["bottom"]), (stock["cx"], stock["top"])])
    arrow(ax, [(breach["right"], breach["cy"]), (evaluation["left"], evaluation["cy"])])
    arrow(ax, [(stock["left"], stock["cy"]), (evaluation["right"], evaluation["cy"])])
    L2.save_png(fig, path)


# ---------------------------------------------------------------------------
# Figure A2: the Layer 1 pipeline
# ---------------------------------------------------------------------------

def step_label(ax, y, number, name, note):
    """The step's number and name at the left edge, with a short note under it."""
    ax.text(0, y + 1.3, f"{number} · {name}", ha="left", va="center", fontsize=TITLE_SIZE,
            weight="bold", color=INK)
    ax.text(0, y - 1.5, note, ha="left", va="center", fontsize=LINE_SIZE - 0.4, color=INK_2)


def layer1_figure(path):
    """Six steps turn raw data into a forecast at every forecast day; the backtest repeats them weekly."""
    height = 122
    fig, ax = canvas(7.4, 6.4, height)
    g = config.DELAY_GUARD_G
    heading(ax, height, "At every forecast day, six steps turn raw data into a breach probability",
            "Below the dashed line, models see only what was known on the forecast day T")
    x0, w, gutter = 22, 24, 2.2                   # three columns to the right of the step labels
    cols = [x0 + i * (w + gutter) for i in range(3)]
    full = cols[2] + w - x0
    h = 13

    y = 104
    step_label(ax, y + h / 2, 1, "Data", "raw inputs")
    cases = box(ax, cols[0], y, w, h, "Case counts", ["QCESD, by onset week"])
    rain = box(ax, cols[1], y, w, h, "Rain", ["IMERG Late, UTC days"])
    maps = box(ax, cols[2], y, w, h, "Flood maps + people", ["NOAH maps,", "residents per zone"])

    line_y = 98
    ax.plot([0, 99], [line_y, line_y], color=FOCUS_EDGE, linewidth=0.9, linestyle=(0, (4, 3)))
    ax.text(0, line_y + 1.6, "Forecast day T", ha="left", va="center", fontsize=LINE_SIZE, weight="bold",
            color=FOCUS_EDGE)

    y = 80
    step_label(ax, y + h / 2, 2, "Prepare", "as known that day")
    seen = box(ax, cols[0], y, w, h, "Cases seen", [f"up to week T − {g}", "(the delay guard)"])
    weekly = box(ax, cols[1], y, w, h, "Weekly rain", ["7-day totals over QC,", "weighted by residents"])
    index = box(ax, cols[2], y, w, h, "Flood exposure index",
                [f"wettest {config.RAIN_ACCUM_DAYS}-day rain against", "earlier years' return levels"])

    y = 61
    step_label(ax, y + h / 2, 3, "Features", "what the models read")
    features = box(ax, x0, y, full, h, "Inputs: one row per week",
                   ["M0, M1, M3: past counts only",
                    "M4: season (3 sine-cosine pairs) · recent cases · last 2 weeks' rain",
                    "· exposure index · COVID-19 years · population offset"])

    y = 42
    step_label(ax, y + h / 2, 4, "Models", "four, refit weekly")
    baselines = box(ax, cols[0], y, w, h, "M0, M1 · baselines", ["same week last year,", "same-week average"])
    m3 = box(ax, cols[1], y, w, h, "M3 · benchmark", ["Prophet + XGBoost hybrid", "(Latigay & Gonzaga)"])
    m4 = box(ax, cols[2], y, w, h, "M4 · negative binomial", ["and M4 without the index", "(the flood test)"])

    y = 22
    step_label(ax, y + h / 2, 5, "Forecast", "a range, not a point")
    forecast = box(ax, x0, y, full, h, "Forecast distribution for each model",
                   [f"negative binomial: expected count μ, spread θ from the last {config.THETA_WINDOW} "
                    "past misses",
                    "→ expected cases · 90% range · chance of breaching the epidemic threshold"],
                   focus=True)

    y = 2
    step_label(ax, y + h / 2, 6, "Backtest", "every past week")
    backtest = box(ax, cols[0], y, 2 * w + gutter, h, "Backtest and scores",
                   [f"every week, {years_span(config.BACKTEST_FIRST_YEAR, config.BACKTEST_LAST_YEAR)}",
                    "MAE, WIS, Brier score, outbreak episodes"])

    for top, bottom in ((cases, seen), (rain, weekly), (maps, index)):
        arrow(ax, [(top["cx"], top["bottom"]), (bottom["cx"], bottom["top"])])
    turn = (rain["bottom"] + line_y) / 2            # rain also sets the flood exposure index
    arrow(ax, [(rain["right"] - 4, rain["bottom"]), (rain["right"] - 4, turn), (index["left"] + 4, turn),
               (index["left"] + 4, index["top"])])
    for upper in (seen, weekly, index):
        arrow(ax, [(upper["cx"], upper["bottom"]), (upper["cx"], features["top"])])
    for model in (baselines, m3, m4):
        arrow(ax, [(model["cx"], features["bottom"]), (model["cx"], model["top"])])
        arrow(ax, [(model["cx"], model["bottom"]), (model["cx"], forecast["top"])])
    arrow(ax, [(backtest["cx"], forecast["bottom"]), (backtest["cx"], backtest["top"])])
    loop_x = 99.4                                     # the backtest moves T on a week and starts again
    arrow(ax, [(backtest["right"], backtest["cy"]), (loop_x, backtest["cy"]), (loop_x, line_y - 0.2)],
          dashed=True)
    label(ax, (backtest["right"] + loop_x) / 2, backtest["cy"] + 2.2, "repeat, one week later")
    L2.save_png(fig, path)


def main():
    design_figure(config.E8_FIG_DESIGN)
    print(f"wrote {config.E8_FIG_DESIGN.relative_to(config.ROOT)}")
    layer1_figure(config.E8_FIG_LAYER1)
    print(f"wrote {config.E8_FIG_LAYER1.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()

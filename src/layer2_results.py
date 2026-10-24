"""Layer 2 results: maps and tables from the storm runs."""

import textwrap

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")    # draw into files only; no window opens
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import config
from src import allocation, doses, exposed, forecast_run, observed_run

MAIN = observed_run.MAIN              # the main run: the D, cut-off config.CONTINUOUS_EXPOSURE_DAYS
OBSERVED = forecast_run.OBSERVED      # the name of the observed run in the forecast-run and results tables
FLAG_TAGS = observed_run.FLAG_TAGS    # "25", "50": column suffixes, one per flag share
FLAG_SCORES = ["flagged", "flagged_and_listed", "share_flagged_listed", "share_listed_flagged"]
UNITS = list(doses.UNITS)             # doxy100, courses, amox500
OBSERVED_PRODUCT = "IMERG Late"
FORECAST_COLUMNS = ["storm", "run", "rain_product", "levels_product", "window", "rain_mm", "position",
                    "ei_pct", "flood", "D", "w", "exposed", *UNITS, "label"]
TEST_COLUMNS = ["storm", "test", "flood", "D", "cutoff", "w", *exposed.TIERS, *UNITS, "label"]
INPUTS = {                            # the files this step reads, and the task that makes each
    config.C8_RUNS: "C8: python -m src.observed_run",
    config.C8_BARANGAYS: "C8: python -m src.observed_run",
    config.C8_CENTERS: "C8: python -m src.observed_run",
    config.C9_RUNS: "C9: python -m src.forecast_run",
    config.BARANGAYS_QC: "A5: python -m src.census",
}
STORM_NAMES = {                       # map titles; a storm not listed here is titled by its key
    "carina_2024": "Typhoon Carina, July 2024",
    "floods_2025": "July 2025 floods",
    "habagat_2026": "August 2026 habagat floods",
    "kristine_2024": "Severe Tropical Storm Kristine, October 2024",
}
SHOW = 5                              # health centers printed per storm, to inspect

# Map style: one hue per measure, light for little and dark for a lot.
INK, INK_2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
SHARE_CMAP = LinearSegmentedColormap.from_list(
    "blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
DOXY_CMAP = plt.colormaps["Oranges"]
DPI = 200


def check_inputs():
    """Stop with one clear message that lists every input file not on this computer."""
    missing = [f"  {path}  ({task})" for path, task in INPUTS.items() if not path.exists()]
    if missing:
        raise SystemExit("D7 needs these files; run their task or copy them from the team drive:\n"
                         + "\n".join(missing))


def load_results():
    """The three results files and the runs file, with codes kept as text."""
    return {"c8_runs": pd.read_csv(config.C8_RUNS),
            "c8_barangays": pd.read_csv(config.C8_BARANGAYS, dtype={"psgc": str}),
            "c8_centers": pd.read_csv(config.C8_CENTERS, dtype={"facility_code": str}),
            "c9_runs": pd.read_csv(config.C9_RUNS)}


def main_runs(c8_runs):
    """The main run: one row per storm (and per w in a short flood)."""
    return c8_runs[c8_runs["test"] == MAIN]


def run_order(run):
    """Sort key: the observed run first, then the leads in order (lead 1, lead 2, lead 3)."""
    return 0 if run == OBSERVED else int(run.split()[-1])


def in_order(table, by=()):
    """table sorted by storm (config.STORMS' order), then run if it has one (observed first), then by."""
    keys = table.assign(_storm=table["storm"].map({storm: i for i, storm in enumerate(config.STORMS)}))
    sort = ["_storm"]
    if "run" in table:
        keys["_run"] = table["run"].map(run_order)
        sort.append("_run")
    return keys.sort_values([*sort, *by], kind="stable").drop(columns=sort).reset_index(drop=True)


def check_runs_match(c8_runs, c9_runs):
    """Stop unless every storm ran and the main run agrees with the observed run."""
    missing = sorted(set(config.STORMS) - set(c8_runs["storm"]))
    if missing:
        raise ValueError(f"C8's results have no rows for {missing}: rerun python -m src.observed_run")
    rerun = "rerun python -m src.observed_run and python -m src.forecast_run"
    keys, cols = ["storm", "flood", "D", "w"], ["rain_mm", "ei_pct", "exposed", *UNITS]
    c8 = main_runs(c8_runs)
    c8 = c8[c8["storm"].isin(c9_runs["storm"])]
    c9 = c9_runs[c9_runs["run"] == OBSERVED]
    both = c8[keys + cols].merge(c9[keys + cols], on=keys, how="outer", suffixes=("_c8", "_c9"),
                                 validate="one_to_one", indicator=True)
    alone = both[both["_merge"] != "both"]
    if len(alone):
        raise ValueError(f"C8's main run and C9's observed run hold different runs, e.g. "
                         f"{alone[keys].iloc[0].to_dict()}: {rerun}")
    for col in cols:
        far = ~np.isclose(both[f"{col}_c8"], both[f"{col}_c9"], rtol=0, atol=config.D7_RUNS_TOLERANCE)
        if far.any():
            row = both[far].iloc[0]
            raise ValueError(f"{row['storm']}, {row['flood']}: {col} is {row[f'{col}_c8']:,.2f} in C8 "
                             f"but {row[f'{col}_c9']:,.2f} in C9: {rerun}")


def forecast_table(c8_runs, c9_runs):
    """The doses at each lead beside the observed doses: one row per storm, run, D and w."""
    observed = main_runs(c8_runs).assign(run=OBSERVED, rain_product=OBSERVED_PRODUCT, levels_product="IMERG")
    leads = c9_runs[c9_runs["run"] != OBSERVED]
    leads = leads.assign(rain_product=leads["product"], levels_product="ERA5")
    return in_order(pd.concat([observed, leads], ignore_index=True)[FORECAST_COLUMNS], by=["D", "w"])


def flag_table(c8_runs, c9_runs):
    """Flagged versus flooded: one row per storm, run (observed, then each lead) and flag share."""
    observed = main_runs(c8_runs).drop_duplicates("storm").assign(run=OBSERVED)
    leads = c9_runs[c9_runs["run"] != OBSERVED].drop_duplicates(["storm", "run"])
    runs = pd.concat([observed, leads], ignore_index=True)
    parts = []
    for share, tag in zip(config.FLAG_EXPOSED_SHARES, FLAG_TAGS):
        part = runs[["storm", "run", "rain_mm", "position", "listed_flooded"]].assign(flag_share=share)
        for score in FLAG_SCORES:
            part[score] = runs[f"{score}_{tag}"]
        parts.append(part)
    return in_order(pd.concat(parts, ignore_index=True), by=["flag_share"])


def test_table(c8_runs):
    """The cut-off test and D +/- 1 reruns: QC's adult tiers and units, one row per storm, test and w."""
    return in_order(c8_runs[TEST_COLUMNS])


def center_table(c8_centers, c8_runs):
    """Doses per health center in the main run, each pool's tiers added up and rounded up to whole units."""
    keys = ["storm", "flood", "D", "w", "facility_code", "facility_name"]
    need = c8_centers.assign(units=c8_centers[exposed.TIERS].sum(axis=1))
    table = need.pivot(index=keys, columns="pool", values="units")
    if set(table.columns) != set(UNITS) or table.isna().any().any():
        raise ValueError(f"C8's center table needs {UNITS} for every health center: rerun python -m src.observed_run")

    by_run = table.groupby(level=["storm", "flood"])
    qc = main_runs(c8_runs).set_index(["storm", "flood"])[UNITS].reindex(by_run.size().index)
    slack = 0.005 * len(exposed.TIERS) * by_run.size()
    if qc.isna().any().any() or (by_run[UNITS].sum() - qc).abs().gt(slack, axis=0).any().any():
        raise ValueError("C8's health centers do not add up to its QC totals: rerun python -m src.observed_run")

    out = table[UNITS].reset_index()
    out[UNITS] = allocation.round_up(out[UNITS]).astype(int)
    out["label"] = doses.LABEL
    return in_order(out.sort_values("doxy100", ascending=False), by=["w"])


def map_run(c8_runs, storm):
    """The main-run row a storm's map shows: its only one, or in a short flood the one at config.D7_MAP_W."""
    rows = main_runs(c8_runs)
    rows = rows[rows["storm"] == storm]
    if len(rows) > 1:
        rows = rows[np.isclose(rows["w"], config.D7_MAP_W)]
    if len(rows) != 1:
        raise ValueError(f"{storm}: C8's main run has no single row at w = {config.D7_MAP_W:g} "
                         f"(config.D7_MAP_W must be one of config.WOUND_SHARE_W)")
    return rows.iloc[0]


def classes(values, breaks):
    """Class of each value: 0 below the first break, i from break i up to the next (a break counts upward)."""
    if not all(low < high for low, high in zip(breaks, breaks[1:])):
        raise ValueError(f"map class breaks must increase: {breaks}")
    return np.digitize(values, breaks)


def class_labels(breaks, text):
    """Legend text of the classes the breaks make: under the first, between each pair, the last or more."""
    edges = [text(b) for b in breaks]
    return [f"under {edges[0]}", *[f"{low}–{high}" for low, high in zip(edges, edges[1:])], f"{edges[-1]} or more"]


def class_colors(cmap, n):
    """n colours along cmap from light to dark, one per class."""
    return [cmap(x) for x in np.linspace(0.1, 1.0, n)]


def map_table(shapes, c8_barangays, run):
    """The shapes joined to the barangay rows of one run, with the share in flood zones and the classes."""
    rows = c8_barangays[(c8_barangays["storm"] == run["storm"]) & (c8_barangays["flood"] == run["flood"])]
    table = shapes[["psgc", "geometry"]].merge(rows, on="psgc", how="left", validate="one_to_one")
    if (len(rows) != config.QC_BARANGAYS or len(table) != config.QC_BARANGAYS
            or table[["residents", "pop_2024", "doxy100"]].isna().any().any()):
        raise ValueError(f"{run['storm']}: the map needs C8's rows for all {config.QC_BARANGAYS} barangays, "
                         f"one each: rerun python -m src.observed_run")
    table["share"] = table["residents"] / table["pop_2024"]
    table["share_class"] = classes(table["share"], config.D7_MAP_SHARE_BREAKS)
    table["doxy_class"] = classes(table["doxy100"], config.D7_MAP_DOXY_BREAKS)
    return table


def draw_panel(ax, table, column, colors, labels, title, note, legend_title):
    """One map panel: a title and note above, barangays filled by class, QC's edge, the listed ones outlined, a legend below."""
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=46)
    ax.text(0.0, 1.01, note, transform=ax.transAxes, va="bottom", fontsize=8, color=INK_2)
    table.plot(ax=ax, color=[colors[c] for c in table[column]], edgecolor=SURFACE, linewidth=0.4)
    gpd.GeoSeries([table.union_all()], crs=table.crs).boundary.plot(ax=ax, color=INK_2, linewidth=0.6)
    listed = table[table["listed_flooded"]]
    if len(listed):
        listed.boundary.plot(ax=ax, color=INK, linewidth=1.4)
    ax.set_axis_off()
    handles = [Patch(facecolor=color, edgecolor="none", label=label) for color, label in zip(colors, labels)]
    handles.append(Line2D([], [], color=INK, linewidth=1.4, label=f"named flooded in A11's sources ({len(listed)})"))
    ax.legend(handles=handles, title=legend_title, loc="upper left", bbox_to_anchor=(0.0, 0.0), ncol=2,
              frameon=False, fontsize=8, title_fontsize=9, alignment="left", labelcolor=INK)


def position_words(position):
    """The position in words: "R0 to R(5)" becomes "between R0 and R(5)"; "below R0" stays."""
    if " to " in position:
        low, high = position.split(" to ")
        return f"between {low} and {high}"
    return position


def window_words(window):
    """The window "2024-07-22 to 2024-07-24" as "22 Jul to 24 Jul 2024"."""
    start, end = (pd.Timestamp(day) for day in window.split(" to "))
    return f"{start:%d %b} to {end:%d %b %Y}"


def flood_words(run):
    """What the dose panel assumes about the flood, from the run's D, cut-off and w."""
    days = f"D = {run['D']:.0f} day{'' if run['D'] == 1 else 's'}"
    if run["D"] >= run["cutoff"]:
        return f"Flood of {days}: every exposed adult high risk (2 capsules a week)"
    return (f"Flood of {days}: w = {run['w']:g} of exposed adults moderate risk (10 capsules), "
            f"the rest low (2); the tables also give w = 0 and 1")


def flag_words(run):
    """The flag scores of the run, one line per flag share, for the map's left panel."""
    lines = []
    for tag in FLAG_TAGS:
        n = int(run[f"flagged_{tag}"])
        lines.append(f"Flagged at {tag}%: {n} barangay{'' if n == 1 else 's'}, "
                     f"{int(run[f'flagged_and_listed_{tag}'])} of them named flooded")
    lines.append(f"Named flooded in A11's sources: {int(run['listed_flooded'])} (not a complete list)")
    return "\n".join(lines)


def save_png(fig, path):
    """Save a figure via a .part file, so a stopped run never leaves half a picture."""
    part = path.with_suffix(".part")
    fig.savefig(part, format="png", dpi=DPI, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    part.replace(path)


def storm_map(table, run, path):
    """Draw one storm's map of the main run: share of residents in flood zones, and doxycycline capsules."""
    n_share, n_doxy = len(config.D7_MAP_SHARE_BREAKS) + 1, len(config.D7_MAP_DOXY_BREAKS) + 1
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 9), facecolor=SURFACE)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.79, bottom=0.22, wspace=0.08)
    draw_panel(left, table, "share_class", class_colors(SHARE_CMAP, n_share),
               class_labels(config.D7_MAP_SHARE_BREAKS, lambda b: f"{100 * b:g}%"),
               "Residents in zones the rain floods", flag_words(run), "Share of the barangay's 2024 residents")
    draw_panel(right, table, "doxy_class", class_colors(DOXY_CMAP, n_doxy),
               class_labels(config.D7_MAP_DOXY_BREAKS, lambda b: f"{b:,}"),
               "Doxycycline 100 mg capsules for adults", textwrap.fill(flood_words(run), 60),
               "Capsules per barangay")

    name = STORM_NAMES.get(run["storm"], run["storm"])
    fig.text(0.03, 0.965, f"{name}: observed rain (IMERG)", fontsize=14, weight="bold", color=INK)
    fig.text(0.03, 0.915, textwrap.fill(
        f"Wettest {config.RAIN_ACCUM_DAYS}-day total, {window_words(run['window'])}: {run['rain_mm']:.1f} mm over the "
        f"catchments, {position_words(run['position'])}, about a {run['return_period']:.1f}-year rain on IMERG's "
        f"return levels fitted on the {run['levels_years']:.0f} years before. EI {run['ei_pct']:.2f}%: the share of "
        f"QC's residents in zones this rain floods.", 130), fontsize=9, color=INK_2, va="center")
    fig.text(0.03, 0.02, textwrap.fill(
        f"{doses.LABEL} Full coverage (q = u = 1). Children's courses and amoxicillin per barangay: "
        f"results/{config.C8_BARANGAYS.name}; per health center: results/{config.D7_CENTERS.name}. "
        f"Source: C8's main run (src/observed_run.py), drawn by src/layer2_results.py (D7).", 150),
        fontsize=7.5, color=INK_2)
    save_png(fig, path)


def pct(value):
    """A share as a whole percentage, or "-" when it is empty."""
    return "-" if pd.isna(value) else f"{value:.0%}"


def whole(value):
    """A count with thousands separators and no decimals."""
    return f"{value:,.0f}"


def report(forecasts, flags, tests, centers, maps):
    """Print the five results, each labelled where it holds dose figures."""
    print_table = observed_run.print_table
    print(f"D7: Layer 2 results from C8 (observed rain, IMERG) and C9 (forecasts, ECMWF). {doses.LABEL}")

    print("\n1. Maps of C8's main run (share of residents in flood zones; doxycycline capsules):")
    for storm, run, path in maps:
        print(f"  {storm}, {run['flood']}: {path.relative_to(config.ROOT)}")

    print(f"\n2. Doses per health center, C8's main run (whole units, rounded up); the {SHOW} needing the most "
          f"doxycycline. {doses.LABEL}")
    for (storm, flood), rows in centers.groupby(["storm", "flood"], sort=False):
        print(f"  {storm}, {flood}: {len(rows)} centers")
        print_table(rows.head(SHOW)[["facility_name", *UNITS]], formatters={col: whole for col in UNITS})

    print("\n3. Flagged versus flooded (flagged: at least flag_share of a barangay's residents in flood zones; "
          "listed: A11's flooded barangays):")
    print_table(flags[["storm", "run", "flag_share", "listed_flooded", *FLAG_SCORES]],
                formatters={"flag_share": pct, "share_flagged_listed": pct, "share_listed_flagged": pct})

    print(f"\n4. Cut-off test and D +/- 1 (C8), QC's adult tiers and units. {doses.LABEL}")
    print_table(tests[TEST_COLUMNS[:-1]], formatters={col: whole for col in [*exposed.TIERS, *UNITS]})

    print(f"\n5. C9's forecast doses beside the observed run (exposed people and units). {doses.LABEL}")
    cols = ["storm", "run", "rain_mm", "position", "ei_pct", "flood", "exposed", *UNITS]
    print_table(forecasts[cols], formatters={"rain_mm": "{:.1f}".format, "ei_pct": "{:.2f}".format,
                                             **{col: whole for col in ["exposed", *UNITS]}})
    print("\n  " + "\n  ".join(f"{col}: {what}" for col, what in doses.UNITS.items()))
    print(f"\n{doses.LABEL}")


def main():
    check_inputs()
    results = load_results()
    c8_runs, c9_runs = results["c8_runs"], results["c9_runs"]
    check_runs_match(c8_runs, c9_runs)
    forecasts = forecast_table(c8_runs, c9_runs)
    flags = flag_table(c8_runs, c9_runs)
    tests = test_table(c8_runs)
    centers = center_table(results["c8_centers"], c8_runs)

    shapes = allocation.load_barangays()
    maps = []
    for storm in config.STORMS:     # every map's table is checked before any file is written
        run = map_run(c8_runs, storm)
        maps.append((storm, run, config.RESULTS / config.D7_MAP_NAME.format(storm=storm),
                     map_table(shapes, results["c8_barangays"], run)))
    for storm, run, path, table in maps:
        storm_map(table, run, path)

    report(forecasts, flags, tests, centers, [(storm, run, path) for storm, run, path, _ in maps])
    forecast_run.write(forecasts.round(4), config.D7_FORECAST_VS_OBSERVED)
    forecast_run.write(flags.round(4), config.D7_FLAGS)
    forecast_run.write(tests.round(4), config.D7_TESTS)
    forecast_run.write(centers, config.D7_CENTERS)
    print(f"\nwrote {len(maps)} maps ({config.D7_MAP_NAME.format(storm='<storm>')}), "
          f"{config.D7_FORECAST_VS_OBSERVED.name} ({len(forecasts)} rows), {config.D7_FLAGS.name} ({len(flags)} rows), "
          f"{config.D7_TESTS.name} ({len(tests)} rows), {config.D7_CENTERS.name} ({len(centers)} rows) in "
          f"{config.RESULTS.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()

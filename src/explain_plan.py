"""Explainer figures for the 13-day plan (lepton-plan.md): its schedule, its task map and the data decision.

For teaching and slides, not results. Task codes and names, the gate conditions and the decision tree
are read from the plan file itself (config.PLAN_FILE), so the figures follow the plan when it is
re-exported; the dates come from config.py.

Run: python -m src.explain_plan   Writes plan_01_... to plan_03_... to results/explain/.
"""

import re
import textwrap
from datetime import timedelta

import matplotlib

matplotlib.use("Agg")    # draw into files only; no window opens
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Patch

import config
from src import explain_m4, paper_figures

EX, PF = explain_m4, paper_figures
INK, INK_2, SURFACE, MUTED, GRID, BASELINE = EX.INK, EX.INK_2, EX.SURFACE, EX.MUTED, EX.GRID, EX.BASELINE
BLUE, BLUE_100, BLUE_150 = EX.M4_BLUE, EX.BLUE_100, EX.BLUE_150

TASK_LINE = re.compile(r"^- \[[ x]\] \*\*([A-E])(\d+)(?: \(([^)]*)\))?\. (.+?)\*\*", re.MULTILINE)
STREAM_LINE = re.compile(r"^## Workstream ([A-E]): (.+)$", re.MULTILINE)
DAYS_IN_NAME = re.compile(r"Oct (\d+)(?:–(\d+))?")     # "(Oct 16–19)" or "(Thu, Oct 15)" in an E task's name
M4_TASKS = ("B1", "B2", "B4", "B5", "B6", "B7", "B10", "D5", "D6")   # tasks that build or test M4: tagged
OPTION_ROW = {"A": 0, "B": 1, "C": 2}     # the decision-tree rows of B2's three QC data options
DAY = timedelta(days=1)
NOTE = "A picture of the plan drawn by src/explain_plan.py from lepton-plan.md and config.py."


# Reading the plan

def plan_text(path=config.PLAN_FILE):
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: export the team's plan doc to it")
    return path.read_text(encoding="utf-8")


def expand(codes):
    """('A1-A3', 'B5') becomes {'A1', 'A2', 'A3', 'B5'}."""
    out = set()
    for code in codes:
        first, _, last = code.partition("-")
        if not last:
            out.add(code)
            continue
        if first[0] != last[0]:
            raise ValueError(f"{code}: a range must stay inside one workstream")
        out.update(f"{first[0]}{n}" for n in range(int(first[1:]), int(last[1:]) + 1))
    return out


def plan_tasks(text):
    """Every task in the workstream sections: code, workstream, name, and whether it is sprint, stretch or M4."""
    rows = [{"stream": s, "number": int(n), "code": f"{s}{n}", "note": note, "name": name.strip().rstrip(".")}
            for s, n, note, name in TASK_LINE.findall(text)]
    tasks = pd.DataFrame(rows)
    if tasks.empty or tasks["code"].duplicated().any():
        raise ValueError("the plan's task lines did not parse: none found, or a code twice")
    sprint = expand(config.PLAN_SPRINT_TASKS)
    unknown = sprint - set(tasks["code"])
    if unknown:
        raise ValueError(f"config.PLAN_SPRINT_TASKS names tasks the plan does not have: {sorted(unknown)}")
    tasks["stretch"] = tasks["note"].str.contains("stretch")
    tasks["sprint"] = tasks["code"].isin(sprint)
    tasks["m4"] = tasks["code"].isin(M4_TASKS)
    tasks["short"] = tasks["name"].map(lambda n: re.sub(r"\s*\([^)]*\)", "", n).rstrip("."))
    return tasks.sort_values(["stream", "number"]).reset_index(drop=True)


def plan_streams(text):
    """{'A': 'data foundation', ...} from the '## Workstream X: name' headings."""
    return dict(STREAM_LINE.findall(text))


def plan_table(text, first_header):
    """The body rows of the markdown table whose header row starts with `first_header`, as lists of cells."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(f"| {first_header}")), None)
    if start is None:
        raise ValueError(f"the plan has no table starting '| {first_header}'")
    rows = []
    for line in lines[start + 2:]:          # skip the header and the | --- | row
        if not line.startswith("|"):
            break
        rows.append([re.sub(r"\*+", "", cell).strip() for cell in line.strip().strip("|").split("|")])
    return rows


def code_runs(codes):
    """['B2', 'B4', 'B5', 'B6'] becomes 'B2, B4–B6'."""
    numbers = sorted((c[0], int(c[1:])) for c in codes)
    runs = []
    for stream, n in numbers:
        if runs and runs[-1][0] == stream and runs[-1][2] == n - 1:
            runs[-1][2] = n
        else:
            runs.append([stream, n, n])
    words = {0: "{s}{a}", 1: "{s}{a}, {s}{b}"}    # one task, or two in a row: no dash
    return ", ".join(words.get(b - a, "{s}{a}–{s}{b}").format(s=s, a=a, b=b) for s, a, b in runs)


def days_in_name(name):
    """The first and last day an E task's name gives, e.g. '(Oct 16–19)'; None if it gives none."""
    found = DAYS_IN_NAME.search(name)
    if not found:
        return None
    first = config.PLAN_START.replace(day=int(found.group(1)))
    return first, config.PLAN_START.replace(day=int(found.group(2) or found.group(1)))


# Figure 1: the schedule

def schedule_lanes(tasks, names):
    """The timeline's bars: (label, first day, last day, kind), top to bottom, kind = sprint, core or stretch."""
    lanes = []
    core = tasks[~tasks["stretch"]]
    for stream in ("A", "B", "C"):
        part = core[core["stream"] == stream]
        sprint, rest = part[part["sprint"]], part[~part["sprint"]]
        if len(sprint):
            lanes.append((f"{code_runs(sprint['code'])}: {names[stream]}", config.PLAN_START, config.GATE_A,
                          "sprint"))
        if len(rest):
            lanes.append((f"{code_runs(rest['code'])}: {names[stream]}", config.GATE_A + DAY, config.GATE_BC,
                          "core"))
    lanes.append((f"{code_runs(core[core['stream'] == 'D']['code'])}: {names['D']}", config.GATE_BC, config.GATE_D,
                  "core"))
    paper = core[core["stream"] == "E"]
    lanes.append((f"{code_runs(paper[paper['sprint']]['code'])}: {names['E']}", config.PLAN_START, config.GATE_A,
                  "sprint"))
    undated = []
    for row in paper[~paper["sprint"]].itertuples():
        span = days_in_name(row.name)
        if span:
            lanes.append((f"{row.code} {row.short.lower()}", *span, "core"))
        else:
            undated.append(row.code)
    last_paper_day = max(end for _, _, end, _ in lanes)
    if undated:
        lanes.append((f"{code_runs(undated)} (no dates in the plan)", config.PLAN_START, last_paper_day, "core"))
    stretch = tasks[tasks["stretch"]]
    lanes.append((f"{code_runs(stretch['code'])} stretch, only if gates B and C pass", config.GATE_BC + DAY,
                  config.GATE_D, "stretch"))
    return lanes


def schedule_figure(text, tasks):
    """1. The 13-day plan as a timeline: sprint, build, scoring and paper, with the four gates."""
    lanes = schedule_lanes(tasks, plan_streams(text))
    gates = plan_table(text, "Gate")
    fig, ax = plt.subplots(figsize=(11, 7.6), facecolor=SURFACE)
    PF.style_axes(ax, grid_axis="x")
    styles = {"sprint": dict(color=BLUE, edgecolor=BLUE, linewidth=0.8),
              "core": dict(color=BLUE_150, edgecolor=BLUE, linewidth=0.8),
              "stretch": dict(color="white", edgecolor=MUTED, linewidth=1.0, linestyle=(0, (3, 2)))}
    for i, (label, first, last, kind) in enumerate(lanes):
        y = len(lanes) - 1 - i
        ax.barh(y, mdates.date2num(last + DAY) - mdates.date2num(first), left=mdates.date2num(first), height=0.56,
                **styles[kind])
    ax.set_yticks(range(len(lanes)))
    ax.set_yticklabels([label for label, *_ in reversed(lanes)], fontsize=7.8, color=INK)

    marks = [(config.GATE_A, "Gate A"), (config.GATE_BC, "Gates B and C"), (config.GATE_D, "Gate D"),
             (config.SUBMIT, "Submit")]
    for day, words in marks:
        x = mdates.date2num(day + DAY)
        ax.axvline(x, color=INK, linewidth=1.0, linestyle=(0, (4, 2)))
        ax.text(x, len(lanes) - 0.35, f"{words}\nend of {day:%a %b} {day.day}", ha="center", va="bottom",
                fontsize=7.5, color=INK, weight="bold", bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5))
    first_day, last_day = config.PLAN_START, config.SUBMIT
    days = pd.date_range(first_day, last_day)
    ax.set_xlim(mdates.date2num(first_day) - 0.15, mdates.date2num(last_day + DAY) + 0.15)
    ax.set_ylim(-0.6, len(lanes) + 0.9)
    ax.set_xticks([mdates.date2num(d) + 0.5 for d in days])                # each day's label in its middle
    ax.set_xticklabels([f"{d:%a}\n{d.day}" for d in days])
    ax.set_xticks([mdates.date2num(d) for d in days], minor=True)          # the grid marks where days begin
    ax.grid(axis="x", which="major", visible=False)
    ax.grid(axis="x", which="minor", color=GRID, linewidth=0.8)
    ax.tick_params(axis="x", which="major", length=0, labelsize=7.5)
    ax.tick_params(axis="x", which="minor", length=3, color=BASELINE)
    ax.legend(handles=[Patch(color=BLUE, label=f"the Oct 15–16 sprint ({int(tasks['sprint'].sum())} tasks)"),
                       Patch(facecolor=BLUE_150, edgecolor=BLUE, label="the rest of the core"),
                       Patch(facecolor="white", edgecolor=MUTED, linestyle=(0, (3, 2)), label="stretch")],
              loc="upper left", bbox_to_anchor=(0, -0.09), ncol=3, frameon=False, fontsize=7.5, labelcolor=INK)

    passes = "\n".join(textwrap.fill(f"{gate} ({when}): {condition}.", 160) for gate, when, condition in gates)
    fig.text(0.01, 0.19, "Each gate passes when:\n" + passes, fontsize=7.3, color=INK_2, va="top", linespacing=1.4)
    core, stretch = (~tasks["stretch"]).sum(), tasks["stretch"].sum()
    subtitle = (f"{core} core tasks and {stretch} stretch tasks in five workstreams, Thu {first_day:%b} "
                f"{first_day.day} to the deadline. Layers 1 and 2 are built side by side until gates B and C; "
                "scoring ends at gate D, when the models are frozen; the paper runs underneath the whole build. If "
                "gate B or C slips, every stretch item is dropped and the core dates stay.")
    fig.subplots_adjust(left=0.27, right=0.98, bottom=0.3, top=EX.header(fig, "The 13-day plan", subtitle) - 0.03)
    PF.footer(fig, f"Source: lepton-plan.md (Schedule and the workstream sections). The plan's Submit row says Fri, "
                   f"Oct 23; the PJDSC primer the team read on Oct 18 set Sat, Oct 24, 11:59 PM (Notes.md), drawn "
                   f"here. {NOTE}")
    return fig


# Figure 2: the task map

def chip(ax, x, y, w, h, row):
    """One task: its code, its name in up to two lines, and an M4 tag if it builds or tests M4."""
    if row.stretch:
        style = dict(facecolor="white", edgecolor=MUTED, linewidth=1.0, linestyle=(0, (3, 2)))
    elif row.sprint:
        style = dict(facecolor=BLUE_100, edgecolor=BLUE, linewidth=1.0)
    else:
        style = dict(facecolor="white", edgecolor=BASELINE, linewidth=0.9)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", **style))
    ax.text(x + 0.9, y + h / 2, row.code, fontsize=7.8, weight="bold", color=INK, va="center")
    lines = textwrap.wrap(row.short + (" (stretch)" if row.stretch else ""), 30)
    if len(lines) > 2:
        lines = [lines[0], textwrap.shorten(" ".join(lines[1:]), 29, placeholder="…")]
    ax.text(x + 4.6, y + h / 2, "\n".join(lines), fontsize=6.6, color=INK, va="center", linespacing=1.15)
    if row.m4:
        ax.text(x + w - 0.6, y + h - 0.6, "M4", fontsize=6.2, weight="bold", color=BLUE, ha="right", va="top")


def task_map_figure(text, tasks):
    """2. Every task of the plan in its workstream: sprint, later core, stretch, and the ones behind M4."""
    names = plan_streams(text)
    order = sorted(tasks["stream"].unique())
    tallest = tasks["stream"].value_counts().max()
    step, h, gap = 6.2, 5.3, 1.2
    width = (100 - gap * (len(order) - 1)) / len(order)
    height = tallest * step + 9
    fig, ax = plt.subplots(figsize=(12, 10.5), facecolor=SURFACE)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, height)
    ax.axis("off")
    for col, stream in enumerate(order):
        x = col * (width + gap)
        part = tasks[tasks["stream"] == stream]
        ax.text(x, height - 1.0, f"{stream}  {names.get(stream, '')}", fontsize=9.5, weight="bold", color=INK,
                va="top")
        counts = f"{len(part)} tasks, {int(part['sprint'].sum())} in the sprint"
        if part["stretch"].any():
            counts += f", {int(part['stretch'].sum())} stretch"
        ax.text(x, height - 4.0, counts, fontsize=7.5, color=INK_2, va="top")
        for i, row in enumerate(part.itertuples()):
            chip(ax, x, height - 9 - (i + 1) * step + (step - h), width, h, row)
    ax.legend(handles=[Patch(facecolor=BLUE_100, edgecolor=BLUE, label="due in the Oct 15–16 sprint"),
                       Patch(facecolor="white", edgecolor=BASELINE, label="the rest of the core, Oct 17–23"),
                       Patch(facecolor="white", edgecolor=MUTED, linestyle=(0, (3, 2)),
                             label="stretch, only after gates B and C"),
                       Patch(facecolor="none", edgecolor="none", label="M4 tag: builds or tests M4")],
              loc="upper left", bbox_to_anchor=(0, 0.0), ncol=4, frameon=False, fontsize=7.8, labelcolor=INK)
    core = int((~tasks["stretch"]).sum())
    subtitle = (f"{len(tasks)} tasks: {core} core and {int(tasks['stretch'].sum())} stretch. The letter is the "
                "workstream and the number names the task, not the order to do them in. "
                f"{int(tasks['sprint'].sum())} of the {core} core tasks were due by Fri, Oct 16, mostly downloads, "
                f"setup and small functions. {int(tasks['m4'].sum())} tasks build or test M4: population (B1), what it "
                "may see (B2), its features (B4), the model (B5), its range (B6), the threshold (B7), the backtest "
                "(B10) and the two comparisons (D5, D6).")
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.05, top=EX.header(fig, "Every task in the plan", subtitle,
                                                                          width=150))
    PF.footer(fig, f"Source: lepton-plan.md (the workstream sections). {NOTE}")
    return fig


# Figure 3: the data decision tree

def text_box(ax, x, y, w, h, title, body, focus=False):
    """A rounded box with a bold title over plain lines, both wrapped to the box's width."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0",
                                facecolor=BLUE_100 if focus else "white", edgecolor=BLUE if focus else BASELINE,
                                linewidth=1.5 if focus else 0.9))
    head = textwrap.fill(title, int(w * 1.45))
    if not body:                            # a title alone sits in the middle of its box
        ax.text(x + 1.0, y + h / 2, head, fontsize=8, weight="bold", color=INK, va="center", linespacing=1.2)
        return
    words = "\n".join(textwrap.fill(line, int(w * 2.0)) for line in body)
    ax.text(x + 1.0, y + h - 1.0, head, fontsize=8, weight="bold", color=INK, va="top", linespacing=1.2)
    ax.text(x + 1.0, y + h - 1.0 - 2.6 * (head.count("\n") + 1), words, fontsize=7, color=INK_2, va="top",
            linespacing=1.25)


def link(ax, start, end, focus=False):
    ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="-|>", color=BLUE if focus else EX.MUTED,
                                                          linewidth=1.4 if focus else 0.8, mutation_scale=9,
                                                          shrinkA=0, shrinkB=0))


def decision_figure(text):
    """3. The data decision tree (A13): what case data arrived decides how Layer 1 is built."""
    rows = plan_table(text, "What we have")
    chosen = OPTION_ROW.get(config.DATA_OPTION)
    height, row_h, row_gap = 62, 10.6, 1.6
    fig, ax = plt.subplots(figsize=(11, 7.0), facecolor=SURFACE)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, height)
    ax.axis("off")
    root_y = height / 2 - 6
    text_box(ax, 0, root_y, 17, 12, "A13, Fri Oct 16, 5 PM", ["What case data has arrived from QCESD?"])
    for i, (have, target, change, paper) in enumerate(rows):
        y = height - (i + 1) * row_h - i * row_gap
        focus = i == chosen
        text_box(ax, 23, y, 27, row_h, have, [], focus)
        text_box(ax, 56, y, 44, row_h, f"Forecast: {target}", [change, f"Paper says: {paper}"], focus)
        link(ax, (17, root_y + 6), (23, y + row_h / 2), focus)
        link(ax, (50, y + row_h / 2), (56, y + row_h / 2), focus)
    ax.text(0, root_y - 2.5, textwrap.fill(
        f"Chosen: QCESD's weekly counts by onset week, with no report dates, so option {config.DATA_OPTION} with "
        f"the delay guard g = {config.DELAY_GUARD_G} (rerun with g = "
        f"{' and '.join(str(g) for g in config.DELAY_GUARD_G_TESTS)}).", 30), fontsize=7.5, color=BLUE, va="top",
        weight="bold")
    subtitle = ("Every Layer 1 task after Fri, Oct 16 follows the row the team was in. The guard g hides the last g "
                "weeks of counts from every model, as if they had not arrived yet: a file of final counts would "
                "otherwise let a model read numbers the health office did not have on the forecast day. Layer 2 "
                "needs no case data and follows its own rule.")
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.04, top=EX.header(fig, "The data decision tree", subtitle))
    PF.footer(fig, f"Source: lepton-plan.md (Data decision tree) and config.DATA_OPTION. {NOTE}")
    return fig


def main():
    text = plan_text()
    tasks = plan_tasks(text)
    figures = (("plan_01_schedule.png", schedule_figure(text, tasks)),
               ("plan_02_task_map.png", task_map_figure(text, tasks)),
               ("plan_03_decision_tree.png", decision_figure(text)))
    for name, fig in figures:
        print(f"wrote {PF.shown(EX.save(fig, name))}")


if __name__ == "__main__":
    main()

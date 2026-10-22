"""Rebuild every data file and result from data/raw, in order (task E10).

Each step is one task's script, run as `python -m <module>` in its own process, so a
script runs exactly as it does by hand. The steps follow the README's tables: Workstream
A, then B1, Layer 2's flood core and doses (C1-C4, C7), B4's weekly features, Layer 1
(B3, B10), the storm runs (C8, C9) and D7. The sanity checks (python -m src.checks) run
last. The run stops at the first step that fails (exit code not 0), and so does a FAIL
in the checks.

What runs and what does not:
  - Downloads. A6, A8, A10, A14 and A15 download only the files not yet in data/raw/
    (copy them from the team drive to skip the download, and to rebuild from the same
    files as everyone else). A4 (IMERG) always asks NASA for every day up to today, needs
    an Earthdata login and so gives a slightly different file each time: it runs only
    with --fetch-imerg. Without it, data/raw/imerg_daily.nc must be there.
  - Files saved by hand (HydroBASINS, the census files, the Mendeley file, PSA births)
    are checked before the first step; the run stops with the list of missing files.
  - QCESD's case list (A13) is not one of them: it is a case-level record, kept on the
    team drive only (rule 11), so a copy of the repository without it must still run.
    A13 is skipped when the list is not in data/raw/qcesd/; B10 then reads
    cases_weekly.csv if it was copied from the drive, and is skipped if not.
  - A step whose task is not built yet (its module is not in src/) is skipped, and so is
    B10 until A13's cases_weekly.csv exists and config.DATA_OPTION is set. B10's guard
    reruns (g = 1 and 3) run only in option C. D8's full run (figures 1-5) and E6's
    score tables wait for B10's results/forecasts.csv; D8's --layer2 run (figures 4 and
    5) does not.
  - --simulate runs Layer 1 on B10's made-up QC-shaped counts instead of A13's file:
    A13 and E6 are not run, B10 --simulate --option C (results/forecasts_simulated_C.csv,
    no guard reruns), D8's figures 1-3 as previews from it (results/d8_preview_*, not for
    the paper), and F2's city_forecast.json marked "simulated". Never the paper's results.
  - C5 and C6 are not steps: they only print. C8, C9 and D7 call their functions.

Run from the repository root:
    python -m src.run_all                 # everything, then the checks
    python -m src.run_all --list          # the steps, without running them
    python -m src.run_all --from C3       # start at C3's first step (e.g. after A8, which is slow)
    python -m src.run_all --only B3 D7    # just these tasks' steps
    python -m src.run_all --fetch-imerg   # also download IMERG (A4) first
    python -m src.run_all --simulate      # Layer 1 on made-up counts, without QC's case data
The first run downloads what is missing (A8's NOAH maps can take over an hour; A4, if
asked, an hour or more). B3's --diagnose takes about 5 minutes; B10 about 12 minutes per
run (M3 refits Prophet every week).
"""

import argparse
import subprocess
import sys
import time

import config

# (task, module, arguments), in the order they must run.
STEPS = [
    ("A3", "src.weeks", ()),
    ("A7", "src.catchments", ()),
    ("A4", "src.imerg", ()),                        # only with --fetch-imerg
    ("A5", "src.census", ()),
    ("A6", "src.worldpop", ()),
    ("A8", "src.noah", ()),
    ("A10", "src.facilities", ()),
    ("A14", "src.era5", ()),
    ("A9", "src.benchmark", ()),
    ("A15", "src.ecmwf", ()),
    ("A13", "src.cases", ()),                       # QC weekly cases; skipped without QCESD's list
    ("B1", "src.population", ()),
    ("C1", "src.rescale", ()),
    ("C2", "src.overlay", ()),
    ("C3", "src.flood_exposure", ()),
    ("C3", "src.flood_exposure", ("--days", "1")),  # comparison: single wettest day
    ("C3", "src.flood_exposure", ("--without-2000",)),  # comparison: fit without Jun-Dec 2000
    ("C4", "src.shares", ()),
    ("C7", "src.allocation", ()),
    ("B4", "src.features", ()),
    ("B3", "src.m3", ()),
    ("B3", "src.m3", ("--diagnose",)),
    ("B10", "src.backtest", ()),
    ("B10", "src.backtest", ("--g", "1")),          # guard rerun, option C only
    ("B10", "src.backtest", ("--g", "3")),          # guard rerun, option C only
    ("C8", "src.observed_run", ()),
    ("C9", "src.forecast_run", ()),
    ("D7", "src.layer2_results", ()),
    ("D8", "src.paper_figures", ("--layer2",)),     # figures 4 and 5 (C8's files)
    ("D8", "src.paper_figures", ()),                # all five, once B10's forecasts.csv exists
    ("E6", "src.score_tables", ()),                 # the score tables E6 quotes, from B10's forecasts
    ("F2", "src.app_data", ()),                     # the web app's data files, after C8, C9 and B10
]

FETCH_ONLY = {"A4"}   # runs only with --fetch-imerg (see the module docstring)

# With --simulate: each Layer 1 step's arguments on B10's made-up counts (None: not run).
SIMULATED = {
    ("A13", ()): None,
    ("B10", ()): ("--simulate", "--option", "C"),
    ("B10", ("--g", "1")): None,
    ("B10", ("--g", "3")): None,
    ("D8", ()): ("--preview", config.FORECASTS_SIMULATED.relative_to(config.ROOT).as_posix()),
    ("E6", ()): None,                               # reads only the real forecasts.csv
}

# Files someone saved by hand into data/raw/ (each has a note there saying where from),
# and the task that reads them. No step can rebuild these.
SAVED_BY_HAND = {
    "A7": [config.HYDROBASINS_SHP],
    "A5": [config.BOUNDARIES_ZIP, config.CENSUS_2024_XLSX, config.CENSUS_2020_AGE_XLSX],
    "A9": [config.PARRENO_RAW],
    "C4": [config.BIRTHS_2024],   # A12
}
NEEDS_IMERG = {"C3", "B4", "C8", "C9"}   # tasks that read data/raw/imerg_daily.nc


def step_name(step):
    """How a step is printed: the task and its command, e.g. "C3  python -m src.flood_exposure --days 1"."""
    task, module, args = step
    return f"{task:<4} python -m {' '.join((module,) + args)}"


def skip_reason(step, simulate=False):
    """Why a step cannot run yet, or None when it can.

    A task not built yet (its module is not in src/); A13 without QCESD's case list;
    B10 before A13's cases file and config.DATA_OPTION; B10's guard reruns outside
    option C; D8's full run before B10's forecasts.csv. With --simulate, B10 and D8 need
    none of these.
    """
    task, module, args = step
    if not (config.ROOT / (module.replace(".", "/") + ".py")).exists():
        return f"task {task} not built yet ({module} not found)"
    if simulate:
        return None
    if task == "A13" and not config.QCESD_CASES_RAW.exists():
        have = "B10 uses the copied" if config.CASES_WEEKLY.exists() else "copy it, or"
        return (f"QCESD's case list is not in {config.QCESD_CASES_RAW.parent.relative_to(config.ROOT).as_posix()}/ "
                f"(team drive only, rule 11); {have} {config.CASES_WEEKLY.name} from the drive")
    if task == "D8" and not args and not config.FORECASTS.exists():
        return f"figures 1-3 need B10's {config.FORECASTS.name} (the --layer2 step drew 4 and 5)"
    if task == "E6" and not config.FORECASTS.exists():
        return f"needs B10's {config.FORECASTS.name}"
    if task == "B10":
        if not config.CASES_WEEKLY.exists():
            return f"needs A13's {config.CASES_WEEKLY.name}"
        if config.DATA_OPTION is None:
            return "config.DATA_OPTION is not set (A13's decision)"
        if "--g" in args and config.DATA_OPTION != "C":
            return f"guard reruns are for option C; config.DATA_OPTION is {config.DATA_OPTION}"
    return None


def missing_inputs(steps, fetch_imerg):
    """The hand-saved files (and IMERG, unless A4 runs) that the chosen steps read but are not on this computer."""
    tasks = {task for task, _, _ in steps}
    missing = [(path, f"read by {task}") for task, paths in SAVED_BY_HAND.items() if task in tasks
               for path in paths if not path.exists()]
    readers = sorted(tasks & NEEDS_IMERG)
    if readers and not fetch_imerg and not config.IMERG_DAILY.exists():
        missing.append((config.IMERG_DAILY, f"made by A4, read by {' '.join(readers)}; or add --fetch-imerg"))
    return missing


def simulated(steps):
    """The steps with Layer 1 switched to B10's made-up counts (SIMULATED); dropped steps left out."""
    out = []
    for task, module, args in steps:
        new = SIMULATED.get((task, args), args)
        if new is not None:
            out.append((task, module, tuple(new)))
    return out


def choose_steps(start=None, only=None, fetch_imerg=False, simulate=False):
    """The steps to run: all of them, or from task `start` on, or only the tasks in `only`."""
    steps = [step for step in STEPS if fetch_imerg or step[0] not in FETCH_ONLY]
    if simulate:
        steps = simulated(steps)
    tasks = [task for task, _, _ in STEPS]
    for task in ([start] if start else []) + (only or []):
        if task not in tasks:
            raise SystemExit(f"no step for task {task}; the tasks are: {' '.join(dict.fromkeys(tasks))}")
        if task in FETCH_ONLY and not fetch_imerg:
            raise SystemExit(f"{task} downloads IMERG: add --fetch-imerg")
    if start:
        first = next(n for n, step in enumerate(steps) if step[0] == start)
        steps = steps[first:]
    if only:
        steps = [step for step in steps if step[0] in only]
    return steps


def run(step):
    """Run one step as `python -m module args` from the repository root; return its exit code."""
    _, module, args = step
    return subprocess.run([sys.executable, "-m", module, *args], cwd=config.ROOT).returncode


def main():
    parser = argparse.ArgumentParser(description="E10: rebuild everything from data/raw, in order")
    parser.add_argument("--list", action="store_true", help="print the steps and stop")
    parser.add_argument("--from", dest="start", metavar="TASK", help="start at this task's first step")
    parser.add_argument("--only", nargs="+", metavar="TASK", help="run only these tasks' steps")
    parser.add_argument("--fetch-imerg", action="store_true", help="also download IMERG (A4): needs an Earthdata login")
    parser.add_argument("--simulate", action="store_true", help="Layer 1 on B10's made-up counts, without QC's case data")
    args = parser.parse_args()

    steps = choose_steps(args.start, args.only, args.fetch_imerg, args.simulate)
    if args.list:
        for step in steps:
            reason = skip_reason(step, args.simulate)
            print(step_name(step) + (f"   (skip: {reason})" if reason else ""))
        print("then  python -m src.checks")
        return 0

    missing = missing_inputs(steps, args.fetch_imerg)
    if missing:
        print("Stopped before the first step: these files are not on this computer. Copy them from "
              "the team drive (each one's note in data/raw/ says where it came from):")
        for path, note in missing:
            print(f"  {path.relative_to(config.ROOT)}  ({note})")
        return 1

    if args.simulate:
        print("--simulate: Layer 1 runs on B10's made-up counts, not QC data; never the paper's results")
    done, skipped, start = [], [], time.time()
    for n, step in enumerate(steps, 1):
        reason = skip_reason(step, args.simulate)
        if reason:
            print(f"\n[{n}/{len(steps)}] SKIP  {step_name(step)}: {reason}")
            skipped.append(step)
            continue
        print(f"\n[{n}/{len(steps)}] {step_name(step)}", flush=True)
        began = time.time()
        code = run(step)
        if code != 0:
            print(f"\nSTOP: {step_name(step)} failed (exit code {code}). Fix it, then rerun from "
                  f"there: python -m src.run_all --from {step[0]}" + (" --simulate" if args.simulate else ""))
            return code
        done.append(step)
        print(f"  done in {time.time() - began:.0f} s")

    print(f"\n{len(done)} steps done, {len(skipped)} skipped, {(time.time() - start) / 60:.1f} min. "
          "Now the sanity checks:\n", flush=True)
    return subprocess.run([sys.executable, "-m", "src.checks"], cwd=config.ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())

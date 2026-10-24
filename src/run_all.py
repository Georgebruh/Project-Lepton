"""Rebuild every data file and result from data/raw, in order."""

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
    ("B5", "src.m4", ()),                           # the residual check, on the last forecast day
    ("C8", "src.observed_run", ()),
    ("C9", "src.forecast_run", ()),
    ("D7", "src.layer2_results", ()),
    ("D8", "src.paper_figures", ("--layer2",)),     # figures 4 and 5
    ("D8", "src.paper_figures", ()),                # all five, once the forecasts.csv exists
    ("E6", "src.score_tables", ()),                 # the score tables the paper quotes, from the forecasts
    ("E8", "src.diagrams", ()),                     # Appendix A's two diagrams, from config.py alone
    ("F2", "src.app_data", ()),                     # the web app's data files, after the storm runs and the backtest
]

FETCH_ONLY = {"A4"}   # runs only with --fetch-imerg

# With --simulate: each Layer 1 step's arguments on the made-up counts (None: not run).
SIMULATED = {
    ("A13", ()): None,
    ("B10", ()): ("--simulate", "--option", "C"),
    ("B10", ("--g", "1")): None,
    ("B10", ("--g", "3")): None,
    ("B5", ()): None,                               # reads only the real forecasts.csv
    ("D8", ()): ("--preview", config.FORECASTS_SIMULATED.relative_to(config.ROOT).as_posix()),
    ("E6", ()): None,                               # reads only the real forecasts.csv
}

# Files saved by hand into data/raw/ (each has a note), and the task that reads them.
SAVED_BY_HAND = {
    "A7": [config.HYDROBASINS_SHP],
    "A5": [config.BOUNDARIES_ZIP, config.CENSUS_2024_XLSX, config.CENSUS_2020_AGE_XLSX],
    "A9": [config.PARRENO_RAW],
    "C4": [config.BIRTHS_2024],
}
NEEDS_IMERG = {"C3", "B4", "C8", "C9"}   # tasks that read data/raw/imerg_daily.nc


def step_name(step):
    """How a step is printed: the task and its command, e.g. "C3 python -m src.flood_exposure --days 1"."""
    task, module, args = step
    return f"{task:<4} python -m {' '.join((module,) + args)}"


def skip_reason(step, simulate=False):
    """Why a step cannot run yet, or None when it can."""
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
    if task in ("B5", "E6") and not config.FORECASTS.exists():
        return f"needs B10's {config.FORECASTS.name}"
    if task == "B5" and not config.CASES_WEEKLY.exists():
        return f"needs A13's {config.CASES_WEEKLY.name} (M4 refits on the counts); the residual check in results/ stays as it was"
    if task == "E6" and not config.CASES_WEEKLY.exists():
        return f"needs A13's {config.CASES_WEEKLY.name} (MASE); the score tables in results/ stay as they were"
    if task == "B10":
        if not config.CASES_WEEKLY.exists():
            return f"needs A13's {config.CASES_WEEKLY.name}"
        if config.DATA_OPTION is None:
            return "config.DATA_OPTION is not set (A13's decision)"
        if "--g" in args and config.DATA_OPTION != "C":
            return f"guard reruns are for option C; config.DATA_OPTION is {config.DATA_OPTION}"
    return None


def missing_inputs(steps, fetch_imerg):
    """The hand-saved files (and IMERG, unless it is fetched) that the chosen steps need but are missing."""
    tasks = {task for task, _, _ in steps}
    missing = [(path, f"read by {task}") for task, paths in SAVED_BY_HAND.items() if task in tasks
               for path in paths if not path.exists()]
    readers = sorted(tasks & NEEDS_IMERG)
    if readers and not fetch_imerg and not config.IMERG_DAILY.exists():
        missing.append((config.IMERG_DAILY, f"made by A4, read by {' '.join(readers)}; or add --fetch-imerg"))
    return missing


def simulated(steps):
    """The steps with Layer 1 switched to the made-up counts (SIMULATED); dropped steps left out."""
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

"""What each model may see at forecast day T."""

import numpy as np
import pandas as pd

import config
from src import weeks

COLUMNS = ["week_index", "year", "week", "cases"]   # cases_weekly.csv


def guard_weeks(option=config.DATA_OPTION, g=config.DELAY_GUARD_G):
    """Weeks the delay guard hides: 0 in option B, g in option C."""
    if option == "B":
        return 0
    if option == "C":
        if g < 0 or g != int(g):
            raise ValueError(f"g = {g}: the delay guard is a whole number of weeks, 0 or more")
        return int(g)
    if option == "A":
        raise NotImplementedError("option A (case lists with report dates: snapshots and nowcast) is not built: "
                                  "it needs case-level records, ethics review first (E2), and the plan cuts it")
    raise ValueError(f"data option {option!r}: set config.DATA_OPTION to 'B' or 'C' from A13's decision-tree row")


def cutoff(forecast_week, option=config.DATA_OPTION, g=config.DELAY_GUARD_G):
    """The last week index a model may see at forecast day T: T in option B, T - g in option C."""
    return int(forecast_week) - guard_weeks(option, g)


def visible(cases, cut):
    """The rows of the weekly table (week_index, year, week, cases) a model may read."""
    missing = [col for col in COLUMNS if col not in cases.columns]
    if missing:
        raise ValueError(f"the cases table has no column {missing}")
    if cases["week_index"].duplicated().any():
        raise ValueError("a week is listed twice in the cases table: one row per week (check S4)")
    seen = cases[cases["week_index"] <= cut].sort_values("week_index").reset_index(drop=True)
    if (seen["cases"] < 0).any():
        raise ValueError(f"a count at or before the cutoff {cut} is negative")
    return seen


def recent_cases(counts, targets, lag):
    """y~(s) = y(s - lag) + y(s - lag - 1) for each target week index s."""
    targets = np.asarray(targets, dtype=int)
    newer = counts.reindex(targets - lag).to_numpy(dtype=float)
    older = counts.reindex(targets - lag - 1).to_numpy(dtype=float)
    return newer + older


def training_rows(cases, forecast_week, option=config.DATA_OPTION, g=config.DELAY_GUARD_G,
                  horizon=config.FORECAST_HORIZON_WEEKS):
    """The rows a model may train on at forecast day T: one per target week s it can see (s <= cutoff)."""
    rows = visible(cases, cutoff(forecast_week, option, g))[COLUMNS].copy()
    counts = rows.set_index("week_index")["cases"]
    rows["forecast_week"] = rows["week_index"] - horizon
    rows["recent"] = recent_cases(counts, rows["week_index"], horizon + guard_weeks(option, g))
    return rows


def prediction_row(cases, forecast_week, option=config.DATA_OPTION, g=config.DELAY_GUARD_G,
                   horizon=config.FORECAST_HORIZON_WEEKS):
    """The row for the target week T + h, with the columns of training_rows and cases missing (the future)."""
    cut = cutoff(forecast_week, option, g)
    target = int(forecast_week) + horizon
    counts = visible(cases, cut).set_index("week_index")["cases"]
    recent = recent_cases(counts, [target], horizon + guard_weeks(option, g))[0]
    if np.isnan(recent):
        raise ValueError(f"forecast day {weeks.year_week(forecast_week)} (year, week): y~ needs the counts "
                         f"of week indexes {cut - 1} and {cut}, and one is missing")
    year, week = weeks.year_week(target)
    return pd.DataFrame({"week_index": [target], "year": [year], "week": [week], "cases": [np.nan],
                         "forecast_week": [int(forecast_week)], "recent": [recent]})

"""What each model may see at forecast day T (task B2).

Case reports trickle in for weeks. If the case file holds final counts, a model that
reads last week's count uses a number the health office did not have yet on the
forecast day, which flatters it. B2 decides which counts a model may read, following
A13's row of the data decision tree (config.DATA_OPTION):

  option A  QC case list with onset and report dates: v2's snapshots and nowcast. Not
            built: it needs case-level records, which need ethics review first (E2,
            rule 11), and the plan cuts snapshots and nowcast unless such lists arrive.
  option B  weekly counts by report or consultation week. A report week is complete
            once it ends, so a model sees every week up to T:        cutoff = T
  option C  weekly counts by onset week, no report dates. The delay guard hides the
            last g weeks (config.DELAY_GUARD_G = 2, an assumption; rerun with 1 and 3):
                                                                     cutoff = T - g

T is the forecast day's week, as a continuous week index (A3; the forecast is made when
week T ends), and the target is week T + h, h = config.FORECAST_HORIZON_WEEKS (1; the
2-week stretch B11 uses 2). The guard is for case counts only. Rain and the exposure
index are observed in real time and never guarded: M4 reads them at week T, the row's
forecast_week (B4, B5), in option C too.

Recent cases, M4's input y~ ("y tilde"), are the two newest counts the model can see:
    y~(T + h) = y(cutoff) + y(cutoff - 1)
that is y(T) + y(T - 1) in option B and y(T - g) + y(T - g - 1) in option C. Every
training row is built with the same gap between its target and the counts it reads,
lag = h in option B and h + g in option C, so a row whose target is week s uses
    y~(s) = y(s - lag) + y(s - lag - 1)
which is y(s - 1) + y(s - 2) in option B and y(s - 1 - g) + y(s - 2 - g) in option C
(h = 1). In plain words: the model learns from the same momentum signal it gets on the
forecast day, not a fresher one it never has in real use.

The training rows are the target weeks the model can see (s <= cutoff), and their y~
reads only earlier weeks, so nothing after the cutoff is ever read (rule 1). Models read
cases through visible() or training_rows(), or check the cutoff themselves (M0, M1, the
thresholds and theta: B6-B8, which take cutoff()).

Check: python -m src.checks ("B2 view": made-up counts worked by hand in options B and C;
every count after the cutoff overwritten with -999 changes nothing). S11 runs the same
test on every model's forecast once B10 exists.
"""

import numpy as np
import pandas as pd

import config
from src import weeks

COLUMNS = ["week_index", "year", "week", "cases"]   # A13's cases_weekly.csv


def guard_weeks(option=config.DATA_OPTION, g=config.DELAY_GUARD_G):
    """Weeks the delay guard hides: 0 in option B, g in option C.

    Stops on option A (not built) and on an option A13 has not set yet (None).
    """
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
    """The rows of the weekly table (week_index, year, week, cases; A13) a model may read.

    Keeps the weeks at or before the cutoff, oldest first; later rows are dropped, not
    blanked, so no model can read them by accident. Stops on a missing column, a week
    listed twice, or a negative count among the kept rows (S11's -999 would mean a
    hidden week got through).
    """
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
    """y~(s) = y(s - lag) + y(s - lag - 1) for each target week index s.

    counts: visible counts, a Series indexed by week index. A y~ whose two counts are not
    both there (missing, before the data or after the cutoff) is NaN, never a smaller total.
    """
    targets = np.asarray(targets, dtype=int)
    newer = counts.reindex(targets - lag).to_numpy(dtype=float)
    older = counts.reindex(targets - lag - 1).to_numpy(dtype=float)
    return newer + older


def training_rows(cases, forecast_week, option=config.DATA_OPTION, g=config.DELAY_GUARD_G,
                  horizon=config.FORECAST_HORIZON_WEEKS):
    """The rows a model may train on at forecast day T: one per target week s it can see (s <= cutoff).

    Columns: week_index, year, week, cases (y(s)), forecast_week (s - h, the week whose rain
    and exposure M4 reads for the row) and recent (y~(s), with the lag the forecast has,
    h + the guard). A missing count or y~ stays NaN: M4 drops those rows before fitting (B5).
    """
    rows = visible(cases, cutoff(forecast_week, option, g))[COLUMNS].copy()
    counts = rows.set_index("week_index")["cases"]
    rows["forecast_week"] = rows["week_index"] - horizon
    rows["recent"] = recent_cases(counts, rows["week_index"], horizon + guard_weeks(option, g))
    return rows


def prediction_row(cases, forecast_week, option=config.DATA_OPTION, g=config.DELAY_GUARD_G,
                   horizon=config.FORECAST_HORIZON_WEEKS):
    """The row for the target week T + h, with the columns of training_rows and cases missing (the future).

    recent = y(cutoff) + y(cutoff - 1), the same lag as every training row. Stops if one
    of the two counts is missing: the forecast would be NaN (rule 5).
    """
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

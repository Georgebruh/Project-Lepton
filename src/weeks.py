"""Morbidity-week calendar (task A3).

One table that maps every date to its CDC/MMWR week, the rule DOH's
surveillance weeks follow: weeks run Sunday to Saturday, and week 1 of a year
is the first week with at least 4 of its days in that year. So a year has 52
or 53 weeks (2015 week 1 starts 4 Jan 2015; 2020 and 2025 have 53 weeks).

Columns of the table:
  date         the day
  year, week   its MMWR year and week number (the year can differ from the
               date's calendar year near 1 January)
  week_start   the Sunday that starts the week
  week_index   continuous week count: 2015 week 1 = 0, then +1 every week
               with no reset at New Year. Models use it as time t (e.g. M4's
               season terms) and to look back a fixed number of weeks.
  week_of_year the week number with week 53 mapped to 52, so the seasonal
               models and thresholds (M1, B7) always have 52 weeks to match.

Run from the repository root:  python -m src.weeks
That writes the table to config.CALENDAR.
"""

from datetime import timedelta

import pandas as pd
from epiweeks import Week, Year

import config


def week_index(day):
    """Continuous week index of the MMWR week holding `day`.

    In plain words: the number of whole weeks between the Sunday that starts
    2015 week 1 (config.FIRST_WEEK_START) and the Sunday that starts this
    day's week. Days before 2015 week 1 get negative indexes.
    """
    start = Week.fromdate(day).startdate()
    return (start - config.FIRST_WEEK_START).days // 7


def week_index_of(year, week):
    """Continuous week index of MMWR `year` week `week`.

    Stops (ValueError) on a week the year does not have, such as 2026 week 53.
    Takes whole-number floats too (2025.0), as pandas rows give them.
    """
    return week_index(Week(int(year), int(week)).startdate())


def week_start(index):
    """The Sunday that starts the week with continuous index `index` (the reverse of week_index)."""
    return config.FIRST_WEEK_START + timedelta(weeks=int(index))


def week_of_year(week):
    """Week number with week 53 mapped to 52 (config.MAX_WEEK)."""
    return min(week, config.MAX_WEEK)


def build_calendar(last_year=config.BACKTEST_LAST_YEAR):
    """Date-to-week table from 2015 week 1 to the last day of `last_year`'s last week."""
    last_day = Year(last_year).enddate()
    rows = []
    for day in pd.date_range(config.FIRST_WEEK_START, last_day, freq="D").date:
        wk = Week.fromdate(day)
        rows.append({
            "date": day,
            "year": wk.year,
            "week": wk.week,
            "week_start": wk.startdate(),
            "week_index": week_index(day),
            "week_of_year": week_of_year(wk.week),
        })
    return pd.DataFrame(rows)


def main():
    """Build the calendar, save it and print a short summary."""
    table = build_calendar()
    config.CALENDAR.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.CALENDAR, index=False)
    weeks = table.drop_duplicates("week_index")
    print(f"Saved {config.CALENDAR} ({len(table)} days, {len(weeks)} weeks, "
          f"{table['date'].iloc[0]} to {table['date'].iloc[-1]})")
    print(weeks.groupby("year")["week"].max().to_string())


if __name__ == "__main__":
    main()

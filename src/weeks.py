"""Morbidity-week calendar."""

from datetime import timedelta

import pandas as pd
from epiweeks import Week, Year

import config


def week_index(day):
    """Continuous week index of the MMWR week holding `day`."""
    start = Week.fromdate(day).startdate()
    return (start - config.FIRST_WEEK_START).days // 7


def week_index_of(year, week):
    """Continuous week index of MMWR `year` week `week`."""
    return week_index(Week(int(year), int(week)).startdate())


def week_start(index):
    """The Sunday that starts the week with continuous index `index` (the reverse of week_index)."""
    return config.FIRST_WEEK_START + timedelta(weeks=int(index))
def year_week(index):
    """MMWR (year, week) of continuous week index `index`: the reverse of week_index_of."""
    wk = Week.fromdate(config.FIRST_WEEK_START + timedelta(weeks=int(index)))
    return wk.year, wk.week


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

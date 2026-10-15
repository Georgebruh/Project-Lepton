"""Quezon City population for every week (task B1).

M4 uses the population P as its offset, log P (task B5), so it needs a value
for every week, not just the three census days. Between two censuses the
population grows by the same percentage every year:

    P(t) = P0 * (P1 / P0) ** ((t - t0) / (t1 - t0))

where P0, P1 are the census totals at decimal years t0, t1. In plain words:
the ratio P1 / P0 is spread evenly over the years between the censuses, so
each year multiplies the population by the same factor.

  - Before the 2015 census (Jan-Jul 2015): the 2015-2020 rate, run backwards.
  - After mid-2024: the 2020-2024 rate is kept, counted from the 2024 census.

Each piece starts at its own census (exponent 0 there), so the three census
days return the PSA totals exactly. A week's population is the value on its
middle day (Wednesday).

Run from the repository root:  python -m src.population
That checks the census days and writes the table to config.POP_WEEKLY.
"""

from datetime import date, timedelta

import pandas as pd
from epiweeks import Year

import config
from src import weeks


def decimal_year(day):
    """Year plus the share of the year already gone, e.g. 1 May 2020 = 2020.33.

    In plain words: year + (day of year - 1) / days in that year.
    """
    days_in_year = (date(day.year + 1, 1, 1) - date(day.year, 1, 1)).days
    return day.year + (day.timetuple().tm_yday - 1) / days_in_year


def pop_at(day):
    """QC population on `day`, growing by a constant percentage between censuses (B1).

    Picks the last census on or before `day` as the start (the first census for
    earlier days) and the growth rate of the census pair around it; after the
    last census, the rate of the last pair (2020-2024).
    """
    years = sorted(config.CENSUS_POP_QC)
    pop = config.CENSUS_POP_QC
    t = {year: decimal_year(config.CENSUS_DAYS[year]) for year in years}
    t_day = decimal_year(day)

    past = [year for year in years if t[year] <= t_day]
    i = years.index(past[-1]) if past else 0
    start = years[i]
    a, b = (years[i], years[i + 1]) if i + 1 < len(years) else (years[i - 1], years[i])

    return pop[start] * (pop[b] / pop[a]) ** ((t_day - t[start]) / (t[b] - t[a]))


def weekly_population(first_year=config.BURN_IN_YEARS[0], last_year=config.BACKTEST_LAST_YEAR):
    """One row per MMWR week: week_index, year, week, week_start, pop (on the Wednesday)."""
    rows = []
    for year in range(first_year, last_year + 1):
        for wk in Year(year).iterweeks():
            start = wk.startdate()
            rows.append({
                "week_index": weeks.week_index(start),
                "year": wk.year,
                "week": wk.week,
                "week_start": start,
                "pop": pop_at(start + timedelta(days=3)),
            })
    return pd.DataFrame(rows)


def check_census_days():
    """B1 done-when: each census day returns its PSA total exactly (1 May 2020 -> 2,960,048)."""
    for year, day in config.CENSUS_DAYS.items():
        got = pop_at(day)
        assert got == config.CENSUS_POP_QC[year], f"{day}: {got} != {config.CENSUS_POP_QC[year]}"


def main():
    """Check the census days, build the weekly table, save it and print a summary."""
    check_census_days()
    table = weekly_population()
    assert table["week_index"].diff().iloc[1:].eq(1).all(), "week index has a gap"
    assert table["pop"].notna().all(), "missing population"
    config.POP_WEEKLY.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.POP_WEEKLY, index=False)
    print(f"Census days exact: {', '.join(f'{d} = {config.CENSUS_POP_QC[y]:,}' for y, d in config.CENSUS_DAYS.items())}")
    print(f"Saved {config.POP_WEEKLY} ({len(table)} weeks, {table['week_start'].iloc[0]} to {table['week_start'].iloc[-1]})")
    print(table.groupby("year")["pop"].agg(["first", "last"]).round(0).astype(int).to_string())


if __name__ == "__main__":
    main()

"""Benchmark data for the M3 reproduction: Parreño (2023) national weekly cases."""

import re
import sys
from datetime import date

import pandas as pd

import config


def read_raw():
    """The raw Mendeley file as a DataFrame (Excel or CSV)."""
    path = config.PARRENO_RAW
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, sheet_name=config.PARRENO_SHEET)
    return pd.read_csv(path)


def inspect():
    """Print the file's size, first columns, the leptospirosis columns and the Week column."""
    df = read_raw()
    print(f"{df.shape[0]} rows x {df.shape[1]} columns")
    print("first 5 columns:", list(df.columns[:5]))
    lepto = [c for c in df.columns if config.PARRENO_DISEASE_KEY.lower() in str(c).lower()]
    print(f"\ncolumns containing {config.PARRENO_DISEASE_KEY!r} ({len(lepto)}):")
    for c in lepto:
        print("  ", repr(c))
    if config.PARRENO_WEEK_COL in df.columns:
        print(f"\n{config.PARRENO_WEEK_COL!r} column, first 5 and last 5 values:")
        print(df[config.PARRENO_WEEK_COL].tolist()[:5], "...", df[config.PARRENO_WEEK_COL].tolist()[-5:])
    else:
        print(f"\nNO column named {config.PARRENO_WEEK_COL!r}; set PARRENO_WEEK_COL to one of the names above")
    if lepto:
        print("\nthe leptospirosis columns:")
        print(df[[config.PARRENO_WEEK_COL] + lepto].to_string())


def lepto_columns(df):
    """{year: column name} for every column whose name contains the disease key and ends in a year."""
    found = {}
    for col in df.columns:
        name = str(col)
        if config.PARRENO_DISEASE_KEY.lower() not in name.lower():
            continue
        years = re.findall(r"\d{4}", name)
        if not years:
            continue
        year = int(years[-1])
        if year in found:
            raise ValueError(f"two columns for {year}: {found[year]!r} and {col!r}; make PARRENO_DISEASE_KEY more specific")
        found[year] = col
    if not found:
        names = [str(c) for c in df.columns]
        raise ValueError(f"no column contains {config.PARRENO_DISEASE_KEY!r} and a year. "
                         f"Columns in the file: {names[:15]} ... (run --inspect)")
    return found


def weekly_leptospirosis(df):
    """One row per (year, week) with the national leptospirosis count, empty where the file has none."""
    if config.PARRENO_WEEK_COL not in df.columns:
        raise ValueError(f"no column named {config.PARRENO_WEEK_COL!r} (run --inspect)")
    week = pd.to_numeric(df[config.PARRENO_WEEK_COL].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    if week.isna().any() or not week.between(1, 53).all():
        raise ValueError("the week column holds a value that is not a week number from 1 to 53")

    parts = []
    for year, col in sorted(lepto_columns(df).items()):
        # commas in numbers ("1,234") are removed; anything that is not a number becomes empty
        cases = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
        parts.append(pd.DataFrame({"iso_year": year, "iso_week": week.astype(int).to_numpy(),
                                   "cases": cases.to_numpy()}))
    table = pd.concat(parts, ignore_index=True)
    if table.duplicated(["iso_year", "iso_week"]).any():
        raise ValueError("a week number appears twice in the week column")
    return table


def full_week_range(table):
    """Every ISO week from week 1 of the first year to the last week that has a count."""
    first_year, last_year = config.M3_DATA_YEARS
    table = table[table["iso_year"].between(first_year, last_year)]
    counted = table.dropna(subset=["cases"]).sort_values(["iso_year", "iso_week"])
    last = (int(counted["iso_year"].iloc[-1]), int(counted["iso_week"].iloc[-1]))

    mondays = pd.date_range(date.fromisocalendar(first_year, 1, 1),
                            date.fromisocalendar(*last, 1), freq="7D")
    iso = mondays.isocalendar()
    grid = pd.DataFrame({"iso_year": iso["year"].astype(int).to_numpy(),
                         "iso_week": iso["week"].astype(int).to_numpy(),
                         "week_start": mondays.date})
    full = grid.merge(table, on=["iso_year", "iso_week"], how="left", validate="one_to_one")
    # A count the grid has no week for (week 53 of a 52-week ISO year) would vanish in the merge.
    if full["cases"].notna().sum() != len(counted):
        raise ValueError("a week with a count is not an ISO week of its year (week 53 in a 52-week year?)")
    return full


def check_series(table):
    """Stop on duplicates, negative counts or a wrong start; print what to look at."""
    if table.duplicated(["iso_year", "iso_week"]).any():
        raise ValueError("an ISO week appears twice")
    if (table["cases"].dropna() < 0).any():
        raise ValueError("negative case count")
    if (int(table["iso_year"].iloc[0]), int(table["iso_week"].iloc[0])) != (config.M3_DATA_YEARS[0], 1):
        raise ValueError("series does not start at week 1 of the first year")

    missing = table[table["cases"].isna()]
    last = table.iloc[-1]
    print(f"{len(table)} ISO weeks, {table['week_start'].iloc[0]} to {table['week_start'].iloc[-1]} "
          f"(last: {int(last['iso_year'])} week {int(last['iso_week'])})")
    print(f"weeks with no count: {len(missing)}")
    if len(missing):
        print(missing[["iso_year", "iso_week"]].to_string(index=False))
    print("\nweeks with a count and cases per ISO year (compare with the paper / the Mendeley totals):")
    print(table.groupby("iso_year")["cases"].agg(["count", "sum"]).to_string())
    needed = config.M3_FIRST_WINDOW + config.M3_STEP * (config.M3_FOLDS - 1) + config.M3_HORIZON
    print(f"\nthe B3 rolling origin needs {needed} weeks; the series has {len(table)}")


def main():
    if "--inspect" in sys.argv:
        inspect()
        return
    table = full_week_range(weekly_leptospirosis(read_raw()))
    check_series(table)
    config.PARRENO_WEEKLY.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.PARRENO_WEEKLY, index=False)
    print(f"\nwrote {config.PARRENO_WEEKLY}")


if __name__ == "__main__":
    main()
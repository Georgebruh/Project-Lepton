"""A prophylaxis plan for every day of the app's timeline, not only the four storms (task F16).

F2's storms.json holds C9's runs of the four storms, and until now the app's plan (F5) had
numbers only on a storm's dates. F16 gives every day its own plan: what Layer 2 says Quezon
City's health centers should stock for the 3 days of rain that start that day (the window C9
uses, config.RAIN_ACCUM_DAYS). On most days the rain is at or below R0, nobody lives in a zone
it floods, and the plan is all zeros: no stock is needed. That is the plan's answer, not
missing data. Stock planning, not prescriptions (rule 10).

The rain of the window that starts on day d, from what exists for it:
  1. Forecasts, from February 2024: ECMWF IFS 0.25 from Open-Meteo's Previous Runs archive,
     with A15's 4 cells and weights and C9's lead totals (forecast_run.lead_total): the
     forecast made L = 1, 2 or 3 days before d,
         R_L = sum over i = 0, 1, 2 of previous_day (L + i) on day d + i.
     A lead is kept when the archive has every hour of it at every cell, and the forecast was
     made by the UTC day the archive was fetched (d - L <= that day). After that day the
     archive holds only the newest run, so a later "lead 1" would really be made earlier.
  2. Days more than 3 days after the fetch (the rest of this week): the newest forecast, made
     on the fetch's UTC day, d - that day days ahead. Every day of such a window is 4 or more
     days after the fetch, where previous_day1 and previous_day3 both hold the newest run
     (newest_rain stops if they differ).
  3. Days before the archive (2018 to early February 2024): the rain that fell, IMERG Late,
     as C8's observed run.
Each product sits on its own return levels (rule 3), fitted on the years before d's year
(rule 2): ERA5's for ECMWF, IMERG's for IMERG.

Then C3 to C7 as C9 does (forecast_run.run_tables) for the two floods the app shows, a 1-day
flood at w = config.APP_SHORT_FLOOD_W and a 7-day one: residents in flood zones, exposed
people, units and each health center's need. A total at or below R0 floods nobody
(flood_exposure.map_weights), so its numbers are all 0 and it skips C5 to C7. The tables are
rounded as C9 writes its files, and put in the app's form by F2's own functions, so a day
whose window and lead match a storm's run has the same numbers as that run (check "F16 daily
plans").

Files written to app/public/data/ (config.APP_DATA), which the app fetches as /data/<file>:
  days/<year>.json   one per year: each day's plan in storms.json's form (key day_<d>, its
                     runs: the forecasts, or else the rain that fell), and each run's need per
                     health center where anyone is exposed (centers.json's needs)
  barangays/days/<d>_<run>.json   each run that exposes anyone: its barangays, as F2's files
  barangays/days/no_flood.json    the one file every run that exposes nobody points to
Every file carries doses.LABEL: stock-planning figures, not prescriptions.

The archive's reply is saved unchanged in data/raw/ecmwf_previous_runs/, one per day this
runs, named with the days it covers, that day and the fetch's UTC day.

Run from the repository root after F2 (python -m src.app_data), on the day the Simulation mode
is made (python -m src.app_simulation), so the plans reach its last date; about a minute:
    python -m src.app_days
    python -m src.app_days --day 2026-10-24   # that day again, from its saved reply
Check: python -m src.checks ("F16 daily plans").
"""

import argparse
import json
from datetime import date, datetime, timedelta, timezone

import geopandas as gpd
import numpy as np
import pandas as pd

import config
from src import allocation, app_data, catchments, doses, ecmwf, exposed, flood_exposure, forecast_run, weeks
from src.app_data import write_json

N_DAYS = config.RAIN_ACCUM_DAYS
ARCHIVE = "days"                                  # the archive's rows in forecast_run's (storm, previous_day, date) index
NEWEST_SAME_MM = 0.05                             # previous_day1 and _day3 must agree this closely where both are the newest run
FLOODS = list(app_data.app_floods(pd.DataFrame(exposed.scenarios(), columns=["flood", "D", "w"]))   # the app's two floods
              .itertuples(index=False, name=None))
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SOURCE = ("F16, python -m src.app_days: C3 to C7 as C9 runs them, on the 3-day rain from each day "
          "(ECMWF IFS 0.25 forecasts from Open-Meteo's Previous Runs archive, or IMERG Late before it)")


# ---------------------------------------------------------------------------
# The days and their rain
# ---------------------------------------------------------------------------

def plan_days(today):
    """The first and last day with a plan: 1 January of the backtest's first year to the Saturday ending today's week.

    The app's timeline runs from the backtest's first forecast day to the last day of the
    week the Simulation mode was made in (F14), so these cover it.
    """
    last = weeks.week_start(weeks.week_index(today)) + timedelta(days=config.DAYS_PER_WEEK - 1)
    return date(config.BACKTEST_FIRST_YEAR, 1, 1), last


def archive_cells():
    """A15's 0.25 degree cells over the catchments, each with its share of the area as weight."""
    shape = gpd.read_file(config.CATCHMENTS, layer="catchments")
    return catchments.grid_cells(shape, config.GRID_025_DEG)


def archive_span(today):
    """The UTC days the archive is asked for: from its start to the last plan's window end."""
    return config.FORECAST_ARCHIVE_START, plan_days(today)[1] + timedelta(days=N_DAYS - 1)


def reply_stem(today):
    """The saved reply's name up to the fetch's UTC day: days_<model>_<first>_<last>_on<today>_utc."""
    first, last = archive_span(today)
    return f"days_{config.FORECAST_MODEL}_{first:%Y%m%d}_{last:%Y%m%d}_on{today:%Y%m%d}_utc"


def saved_reply(today):
    """The archive reply saved on `today`, or None (the F16 check makes a day again only from it)."""
    saved = sorted(config.ECMWF_RAW.glob(reply_stem(today) + "*.json"))
    return saved[-1] if saved else None


def archive_reply(cells, today, fetch=True):
    """The archive's reply for archive_span(today), saved on `today`: (replies, the fetch's UTC day, path).

    A reply saved on `today` is reused. Only today's can be fetched (the archive changes every
    day), and only with fetch=True (the F16 check never fetches): a past day is made again from
    its saved reply, or stops (FileNotFoundError).
    """
    stem = reply_stem(today)
    path = saved_reply(today)
    if path is None and fetch and today == date.today():
        path = config.ECMWF_RAW / f"{stem}{datetime.now(timezone.utc).date():%Y%m%d}.json"
        print("requesting {} to {} from Open-Meteo Previous Runs".format(*archive_span(today)))
        ecmwf.fetch_retrying(cells, *archive_span(today), path)
    elif path is None:
        raise FileNotFoundError(f"no saved archive reply {stem}*.json: a past day is made again only from its saved reply")
    fetched = datetime.strptime(path.stem.removeprefix(stem), "%Y%m%d").date()
    replies = json.loads(path.read_text(encoding="utf-8"))
    replies = replies if isinstance(replies, list) else [replies]
    ecmwf.check_reply(replies, cells, path)
    return replies, fetched, path


def archive_daily(replies, cells, first, last):
    """Catchment rain per previous day N and UTC day (mm): sum of weight x rain_mm over the cells.

    A Series indexed by (ARCHIVE, previous_day, date) as forecast_run.forecast_daily's, so
    forecast_run.lead_total reads it. NaN where a cell misses an hour of the day, so a lead
    that needs that day comes out NaN and is left out.
    """
    table = ecmwf.storm_table(ARCHIVE, replies, cells, first, last)
    table = table.assign(mm=table["weight"] * table["rain_mm"], date=pd.to_datetime(table["date"]))
    return table.groupby(["storm", "previous_day", "date"])["mm"].sum(min_count=len(cells))


def newest_rain(daily, day):
    """The newest forecast's total over the window starting `day`, 4 or more days after the fetch: previous_day1's sum.

    Stops if previous_day3 differs there: both should be the newest run, and if they are not
    the archive no longer works as this file assumes.
    """
    total = 0.0
    for i in range(N_DAYS):
        on = pd.Timestamp(day + timedelta(days=i))
        one, three = daily[(ARCHIVE, 1, on)], daily[(ARCHIVE, 3, on)]
        if np.isnan(one) or np.isnan(three):
            raise ValueError(f"{on:%Y-%m-%d}: the archive misses an hour of the newest forecast; run again later today")
        if abs(one - three) > NEWEST_SAME_MM:
            raise ValueError(f"{on:%Y-%m-%d}: previous_day1 {one:.2f} mm and previous_day3 {three:.2f} mm differ, "
                             "but both should hold the newest run")
        total += one
    return total


def forecasts_of(daily, day, fetched):
    """The forecasts of the window starting `day`: [(lead in days, rain mm)], the earliest made last.

    C9's leads 1-3 made by the fetch's UTC day, with NaN rain where the archive misses an hour
    of one (all_runs leaves those out, as A15 leaves out a lead it does not cover); for a day
    more than 3 days after the fetch, the newest forecast alone (newest_rain). Empty before the
    archive.
    """
    if day < config.FORECAST_ARCHIVE_START:
        return []
    if (day - fetched).days > max(config.FORECAST_LEADS_DAYS):
        return [((day - fetched).days, newest_rain(daily, day))]
    end = day + timedelta(days=N_DAYS - 1)
    leads = [lead for lead in config.FORECAST_LEADS_DAYS if day - timedelta(days=lead) <= fetched]
    return [(lead, forecast_run.lead_total(daily, ARCHIVE, lead, end)) for lead in leads]


# ---------------------------------------------------------------------------
# One run: C3 to C7 at one rain total
# ---------------------------------------------------------------------------

def day_key(day):
    """A day's key, as storms.json keys a storm: "day_2024-07-22"."""
    return f"day_{day:%Y-%m-%d}"


def day_name(day):
    """A day's plan in words, for the app's stock list and report: "Daily plan, 22-24 Jul 2024" (an en dash)."""
    end = day + timedelta(days=N_DAYS - 1)
    to = f"{end.day} {MONTHS[end.month - 1]} {end.year}"
    if (day.year, day.month) == (end.year, end.month):
        return f"Daily plan, {day.day}–{to}"                                  # 22-24 Jul 2024
    if day.year == end.year:
        return f"Daily plan, {day.day} {MONTHS[day.month - 1]} – {to}"        # 30 Jul - 1 Aug 2024
    return f"Daily plan, {day.day} {MONTHS[day.month - 1]} {day.year} – {to}"  # 30 Dec 2024 - 1 Jan 2025


def run_tables(day, run, product, lead, rain, levels, layer2):
    """C3 to C7 at one rain total for the app's two floods: (run rows, barangay rows, center rows), as C9's tables.

    layer2: the inputs C9 reads (load_layer2). A total at or below R0 floods nobody, so its
    rows have 0 people and units, with no barangay or center rows.
    """
    end = day + timedelta(days=N_DAYS - 1)
    row = {"storm": day_key(day), "run": run, "product": product, "lead_days": lead,
           "window": f"{day:%Y-%m-%d} to {end:%Y-%m-%d}", "rain_mm": rain, "levels_years": levels["n_years"],
           "r0": levels["r0"], "r5": levels[5], "r25": levels[25], "r100": levels[100],
           "position": forecast_run.position(rain, levels)}
    if not any(flood_exposure.map_weights(rain, levels).values()):
        row.update({"ei_pct": 0.0, app_data.FLAG_COLUMN: 0})
        zero = dict.fromkeys(forecast_run.UNIT_COLUMNS, 0.0)
        return [{**row, "flood": label, "D": days, "w": w, **zero} for label, days, w in FLOODS], [], []
    residents = flood_exposure.graded_exposure(rain, levels, layer2["overlay"])
    flagged = forecast_run.flagged(residents, layer2["shares"], config.APP_FLAG_SHARE)
    row.update({"ei_pct": 100 * residents["residents"].sum() / layer2["qc_total"], app_data.FLAG_COLUMN: len(flagged)})
    return forecast_run.run_tables(row, residents, layer2["shares"], layer2["center_table"], FLOODS)


def load_layer2():
    """C9's inputs: C2's overlay, C4's shares, C7's center shares and QC's 2024 total (rule 7)."""
    census = pd.read_csv(config.CENSUS_QC, dtype={"psgc": str})
    return {"overlay": pd.read_csv(config.OVERLAY, dtype={"psgc": str}), "shares": exposed.load_shares(),
            "center_table": allocation.load_center_shares(), "qc_total": float(census["pop_2024"].sum())}


def all_runs(first, last, daily, fetched, imerg, era5_max, layer2):
    """Every day's runs, first..last: the three tables C9 writes, rounded as it writes them, and the leads left out.

    imerg: (IMERG's n-day totals by last day, its annual maxima). A day gets its forecasts,
    or else the rain that fell. Stops if a day has neither (rule 5: no plan may be missing
    without an error).
    """
    imerg_totals, imerg_max = imerg
    levels = {}   # (product, year): return levels, fitted once per year
    tables = ([], [], [])
    left_out, no_run = 0, []
    for day in pd.date_range(first, last, freq="D").date:
        found = forecasts_of(daily, day, fetched)
        left_out += sum(np.isnan(rain) for _, rain in found)
        found = [(lead, rain) for lead, rain in found if not np.isnan(rain)]
        if found:
            if ("ERA5", day.year) not in levels:
                levels[("ERA5", day.year)] = flood_exposure.return_levels(era5_max, day.year)   # rule 3
            runs = [(f"lead {lead}", "ECMWF IFS 0.25", lead, rain, levels[("ERA5", day.year)]) for lead, rain in found]
        else:
            rain = imerg_totals.get(pd.Timestamp(day + timedelta(days=N_DAYS - 1)), np.nan)
            if np.isnan(rain):
                no_run.append(f"{day:%Y-%m-%d}")
                continue
            if ("IMERG", day.year) not in levels:
                levels[("IMERG", day.year)] = flood_exposure.return_levels(imerg_max, day.year)
            runs = [(forecast_run.OBSERVED, "IMERG Late", "", rain, levels[("IMERG", day.year)])]
        for run, product, lead, rain, run_levels in runs:
            for part, rows in zip(tables, run_tables(day, run, product, lead, rain, run_levels, layer2)):
                part.extend(rows)
    if no_run:
        raise ValueError(f"no forecast and no IMERG rain for {len(no_run)} days ({no_run[0]} to {no_run[-1]}): "
                         "extend IMERG (python -m src.imerg) or check the archive's reply")
    runs = pd.DataFrame(tables[0]).round(4)
    barangays = one_table(tables[1], [*forecast_run.KEYS, "psgc", "residents", *forecast_run.UNIT_COLUMNS]).round(2)
    centers = one_table(tables[2], [*forecast_run.KEYS, "pool", "facility_code", *exposed.TIERS]).round(2)
    return runs, barangays, centers, left_out


def one_table(parts, columns):
    """The tables in `parts` as one, with C9's columns; an empty one when no run exposes anyone."""
    return pd.concat(parts, ignore_index=True)[columns] if parts else pd.DataFrame(columns=columns)


# ---------------------------------------------------------------------------
# The app's files
# ---------------------------------------------------------------------------

def data_name(path):
    """A file's name as the app fetches it, under /data/: "barangays/days/no_flood.json"."""
    return path.relative_to(config.APP_DATA).as_posix()


def no_flood_file(pop):
    """barangays/days/no_flood.json: every barangay with nobody exposed and no units, for every run below R0."""
    rows = pd.DataFrame([{"psgc": psgc, "residents": 0.0, "D": days, **dict.fromkeys(forecast_run.UNIT_COLUMNS, 0.0)}
                         for _, days, _ in FLOODS for psgc in pop.index])
    content = app_data.barangay_file(rows, pop, ARCHIVE, "no flood")
    return {**content, "source": SOURCE + "; every run whose rain is at or below R0"}


def day_entry(day, rows, files):
    """One day in a year file, in storms.json's form: key, name, window, and each run (app_data.run_entry).

    files: each run's barangay file by run name; a run not in it exposes nobody and points to
    the no-flood file. D, the days a storm flooded (A11), is not known for a day: null.
    """
    end = day + timedelta(days=N_DAYS - 1)
    runs = []
    for run, run_rows in rows.groupby("run", sort=False):
        entry = app_data.run_entry(run_rows)
        entry["file"] = files.get(run, data_name(config.APP_DAY_RUNS / "no_flood.json"))
        runs.append(entry)
    return {"storm": day_key(day), "name": day_name(day), "start_date": f"{day:%Y-%m-%d}",
            "end_date": f"{end:%Y-%m-%d}", "D": None, "runs": runs}


def days_files(today, fetch=True):
    """Every F16 file for the day `today`: ({name under app/public/data/: content}, what main() prints).

    Names are data_name's; the year files are days/<year>.json.
    """
    first, last = plan_days(today)
    cells = archive_cells()
    replies, fetched, path = archive_reply(cells, today, fetch)
    daily = archive_daily(replies, cells, *archive_span(today))
    imerg_totals = flood_exposure.n_day_totals(flood_exposure.catchment_rain(), N_DAYS)
    imerg = (imerg_totals, flood_exposure.annual_maxima(imerg_totals))
    layer2 = load_layer2()
    runs, barangays, centers, left_out = all_runs(first, last, daily, fetched, imerg, forecast_run.era5_maxima(), layer2)

    pop = app_data.barangay_population()
    files = {data_name(config.APP_DAY_RUNS / "no_flood.json"): no_flood_file(pop)}
    run_files = {}
    for (key, run), rows in barangays.groupby(["storm", "run"], sort=False):
        name = data_name(config.APP_DAY_RUNS / f"{key.removeprefix('day_')}_{app_data.run_slug(run)}.json")
        files[name] = {**app_data.barangay_file(rows, pop, key, run), "source": SOURCE + "; 2024 residents from C8"}
        run_files.setdefault(key, {})[run] = name
    needs = app_data.center_needs(centers, runs) if len(centers) else {}

    by_year = {}
    for key, rows in runs.groupby("storm", sort=False):
        day = date.fromisoformat(key.removeprefix("day_"))
        by_year.setdefault(day.year, []).append(day_entry(day, rows, run_files.get(key, {})))
    for year, entries in by_year.items():
        keys = {entry["storm"] for entry in entries}
        files[data_name(config.APP_DAYS / f"{year}.json")] = {
            "label": doses.LABEL, "source": SOURCE, "made_on": f"{today:%Y-%m-%d}",
            "fetched_utc": f"{fetched:%Y-%m-%d}", "first": f"{first:%Y-%m-%d}", "last": f"{last:%Y-%m-%d}",
            "year": year, "units": dict(doses.UNITS), "days": entries,
            "needs": {key: need for key, need in needs.items() if key in keys}}

    shown = runs.drop_duplicates(["storm", "run"])
    exposed_runs = shown[shown["ei_pct"] > 0]
    report = [f"plans for {first} to {last}; ECMWF archive from {path.name} (fetched {fetched} UTC)",
              f"{shown['storm'].nunique()} days, {len(shown)} runs: "
              f"{(shown['run'] == forecast_run.OBSERVED).sum()} on the rain that fell (IMERG), "
              f"{(shown['run'] != forecast_run.OBSERVED).sum()} forecasts (ECMWF); {left_out} forecasts left out, "
              "the archive missing an hour of them",
              f"{len(exposed_runs)} runs expose anyone, on {exposed_runs['storm'].nunique()} days; "
              f"every other run is below R0: no stock needed"]
    return files, report


def write_files(files):
    """Write every file, then delete the year and barangay files of an earlier run that this one did not write."""
    for name, content in files.items():
        write_json(content, config.APP_DATA / name)
    for folder in (config.APP_DAYS, config.APP_DAY_RUNS):
        for path in sorted(folder.glob("*.json")):
            if data_name(path) not in files:
                path.unlink()
                print(f"removed {data_name(path)}: not in this run")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(),
                        help="the day the plans run to the end of the week of, YYYY-MM-DD (default today); "
                             "a past day needs its saved archive reply")
    args = parser.parse_args()
    files, report = days_files(args.day)
    write_files(files)
    print("\n".join(report))
    print(f"wrote {len(files)} files under {config.APP_DATA.name}/. {doses.LABEL}")


if __name__ == "__main__":
    main()

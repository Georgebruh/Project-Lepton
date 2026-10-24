"""The app's Simulation mode: Quezon City's weeks since the last real count, made up, to next week."""

import argparse
import json
from datetime import date, datetime, timedelta, timezone

import geopandas as gpd
import pandas as pd
import requests

import config
from src import backtest, catchments, ecmwf, flood_exposure, forecast_range, forecast_run, weeks
from src.app_data import MODEL_NAMES, write_json

TIMEOUT_S = 120
LABEL = "Simulated: made-up counts after QCESD's last week, and today's ECMWF rain forecast"


# Today's weather forecast (step 1)

def forecast_params(points, first, last):
    """Open-Meteo's forecast request: hourly rain at each point from `first` to the day after `last`, in UTC."""
    utc_today = datetime.now(timezone.utc).date()
    if (utc_today - first).days > config.SIM_MAX_PAST_DAYS:
        raise SystemExit(f"the simulation needs ECMWF's rain from {first}, more than Open-Meteo's "
                         f"{config.SIM_MAX_PAST_DAYS} past days: extend IMERG and B4 (python -m src.features) first")
    return {
        "latitude": ",".join(f"{v:.4f}" for v in points["lat"]),
        "longitude": ",".join(f"{v:.4f}" for v in points["lon"]),
        "hourly": "precipitation",
        "models": config.FORECAST_MODEL,
        "past_days": (utc_today - first).days,
        "forecast_days": (last - utc_today).days + 2,
        "timezone": "GMT",
        "cell_selection": "nearest",
    }


def fetch_forecast(points, first, last, today, fetch=True):
    """Today's reply for these points, saved unchanged in data/raw/ecmwf_forecast/ and reused the same day."""
    path = config.SIM_FORECAST_RAW / f"{config.FORECAST_MODEL}_{today:%Y%m%d}_{len(points)}points_{first:%Y%m%d}.json"
    if not path.exists() and (today != date.today() or not fetch):
        raise FileNotFoundError(f"no saved ECMWF reply {path.name}: a past day can be made again only from its saved reply")
    if not path.exists():
        reply = requests.get(config.SIM_FORECAST_API, params=forecast_params(points, first, last),
                             timeout=TIMEOUT_S)
        reply.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part")
        part.write_bytes(reply.content)
        part.replace(path)
    replies = json.loads(path.read_text(encoding="utf-8"))
    return replies if isinstance(replies, list) else [replies], path


def weighted_daily(replies, weights, first, last, source):
    """Rain per UTC day, first to last: each point's day totals times its weight, added up (mm)."""
    if len(replies) != len(weights):
        raise ValueError(f"{source.name}: {len(replies)} points, expected {len(weights)} (delete it to refresh)")
    days = pd.date_range(first, last, freq="D")
    total = pd.Series(0.0, index=days)
    for reply, weight in zip(replies, weights):
        if reply["utc_offset_seconds"] != 0 or reply["hourly_units"]["precipitation"] != "mm":
            raise ValueError(f"{source.name}: not UTC hours in mm")
        hourly = pd.DataFrame(reply["hourly"]).set_index("time").astype(float)
        hourly.index = pd.to_datetime(hourly.index)
        daily = ecmwf.utc_day_totals(hourly)["precipitation"].reindex(days)
        if daily.isna().any():
            raise ValueError(f"{source.name}: a day from {first} to {last} misses an hour")
        total += weight * daily
    return total


def qc_points():
    """The IMERG cells that hold QC residents, with weights that add up to 1 (residents in each)."""
    cells = pd.read_csv(config.IMERG_WEIGHTS_QC)
    cells = cells[cells["weight"] > 0]
    return cells.assign(weight=cells["weight"] / cells["weight"].sum())[["lon", "lat", "weight"]]


def catchment_points():
    """The 0.25 degree cells over the catchments, weighted by catchment area (catchments.grid_cells)."""
    shape = gpd.read_file(config.CATCHMENTS, layer="catchments")
    return catchments.grid_cells(shape, config.GRID_025_DEG)[["lon", "lat", "weight"]]


def gap_features(first_week, last_week, fit_years, today, fetch=True):
    """Rcum2 and EI2 for weeks first_week..last_week from today's ECMWF run (step 1), one set per fit year."""
    first = weeks.week_start(first_week - 1) - timedelta(days=config.RAIN_ACCUM_DAYS - 1)
    last = weeks.week_start(last_week) + timedelta(days=config.DAYS_PER_WEEK - 1)
    points = qc_points()
    basin = catchment_points()
    replies, path = fetch_forecast(pd.concat([points, basin], ignore_index=True), first, last, today, fetch)
    qc_rain = weighted_daily(replies[:len(points)], points["weight"], first, last, path)
    basin_rain = weighted_daily(replies[len(points):], basin["weight"], first, last, path)

    weekly = {t: float(qc_rain[pd.date_range(weeks.week_start(t), periods=config.DAYS_PER_WEEK, freq="D")].sum())
              for t in range(first_week - 1, last_week + 1)}
    maxima = forecast_run.era5_maxima()
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    qc_total = float(pd.read_csv(config.CENSUS_QC, dtype={"psgc": str})["pop_2024"].sum())   # rule 7
    rmax = flood_exposure.weekly_rmax(flood_exposure.n_day_totals(basin_rain, config.RAIN_ACCUM_DAYS),
                                      weeks.build_calendar(max(fit_years)))
    rows = []
    for year in fit_years:
        levels = flood_exposure.return_levels(maxima, year)   # rule 3: ERA5's levels for ECMWF rain
        ei = flood_exposure.weekly_ei(rmax, levels, flood_exposure.map_totals(overlay), qc_total).set_index("week_index")["ei"]
        for t in range(first_week, last_week + 1):
            rows.append({"fit_year": year, "week_index": t, "rain_mm": weekly[t], "rcum2": weekly[t - 1] + weekly[t],
                         "ei": float(ei[t]), "ei2": max(float(ei[t - 1]), float(ei[t]))})
    return pd.DataFrame(rows), path


# The forecast days (steps 2 and 3)

def simulated_count(mu, theta):
    """One week's simulated count: the median of NB(mu, theta), Poisson where theta is infinite."""
    return int(forecast_range.forecast_dist(mu, theta).ppf(0.5))


def with_weeks_to(cases, last):
    """cases with a row (no count) for every week up to the week index `last` that it lacks."""
    missing = [t for t in range(int(cases["week_index"].max()) + 1, last + 1)]
    rows = [{"week_index": t, "year": weeks.year_week(t)[0], "week": weeks.year_week(t)[1], "cases": float("nan")}
            for t in missing]
    return pd.concat([cases, pd.DataFrame(rows, columns=cases.columns)], ignore_index=True) if rows else cases.copy()


def simulate(cases, features, pop, real, first_day, last_day, models=backtest.MODELS):
    """Forecast days first_day..last_day in order, simulating each ended week QCESD has no count for."""
    cases = with_weeks_to(cases, last_day + config.FORECAST_HORIZON_WEEKS)
    past = {model: rows[["week_index", "mu"]].reset_index(drop=True) for model, rows in real.groupby("model")}
    tables, drawn = [], []
    for T in range(first_day, last_day + 1):
        day = backtest.forecast_day(T, cases, features, pop, past, config.DATA_OPTION, config.DELAY_GUARD_G, models)
        tables.append(day)
        target = T + config.FORECAST_HORIZON_WEEKS
        known = cases.loc[cases["week_index"] == target, "cases"].notna().any()
        if target < last_day and not known:   # the week has ended (last_day is this week, still under way)
            m4 = day.set_index("model").loc[config.APP_LEVEL_MODEL]
            cases.loc[cases["week_index"] == target, "cases"] = simulated_count(m4["mu"], m4["theta"])
            drawn.append(target)
    return pd.concat(tables, ignore_index=True), cases, drawn


def week_entries(table, cases, drawn, gap):
    """The simulated target weeks in city_forecast.json's form, y null where the week has not ended."""
    low, high = (f"q{q:.3f}" for q in (config.RANGE_LOW_Q, config.RANGE_HIGH_Q))
    counts = cases.set_index("week_index")["cases"]
    weather = gap[gap["fit_year"] == gap["fit_year"].max()].set_index("week_index")
    out = []
    for index, rows in table.groupby("week_index"):
        start = weeks.week_start(index)
        by_model = rows.set_index("model")
        threshold = float(rows["threshold"].iloc[0])
        y = int(counts[index]) if pd.notna(counts.get(index)) else None
        out.append({
            "week_index": int(index), "year": int(rows["year"].iloc[0]), "week": int(rows["week"].iloc[0]),
            "start": f"{start:%Y-%m-%d}", "end": f"{start + timedelta(days=config.DAYS_PER_WEEK - 1):%Y-%m-%d}",
            "y": y, "threshold": round(threshold, 2), "breached": None if y is None else bool(y > threshold),
            "simulated_y": index in drawn,
            "forecasts": {model: {"mu": round(float(by_model.at[model, "mu"]), 2),
                                  "low": int(by_model.at[model, low]), "high": int(by_model.at[model, high]),
                                  "p_breach": round(float(by_model.at[model, "p_breach"]), 4)}
                          for model in by_model.index},
            **({"ecmwf_rain_mm": round(float(weather.at[index - 1, "rain_mm"]), 1),
                "ecmwf_ei": round(float(weather.at[index - 1, "ei"]), 2)} if index - 1 in weather.index else {}),
        })
    return out


def simulation_file(today, fetch=True, models=backtest.MODELS):
    """city_simulation.json's content for the day `today` (a date), and what main() prints about it."""
    real = pd.read_csv(config.FORECASTS)
    real = real.assign(model=real["model"].replace(MODEL_NAMES))
    cases = backtest.load_cases()
    pop = backtest.load_population()
    features = backtest.load_features()
    this_week = weeks.week_index(today)
    first_day = int(real["forecast_week"].max()) + 1   # the week after the real run's last forecast day
    last_real = int(cases.loc[cases["cases"].notna(), "week_index"].max())
    fit_years = sorted({weeks.year_week(T)[0] for T in range(first_day, this_week + 1)})
    missing = [year for year in fit_years if year not in set(features["fit_year"])]
    if missing:
        raise SystemExit(f"B4 has no fit year {missing}: extend C3 and B4 (and config.BACKTEST_LAST_YEAR) first")

    gap_first = int(features.dropna()["week_index"].max()) + 1   # the first week the weekly features have no rain for
    gap, reply = gap_features(gap_first, this_week, fit_years, today, fetch)
    features = pd.concat([features, gap[["fit_year", "week_index", "rcum2", "ei2"]]], ignore_index=True)

    table, cases, drawn = simulate(cases, features, pop, real, first_day, this_week, models)
    backtest.check_numbers(table)
    end = weeks.week_start(last_real) + timedelta(days=config.DAYS_PER_WEEK - 1)
    content = {
        "label": LABEL,
        "made_on": f"{today:%Y-%m-%d}",
        "last_real_week": {"week_index": last_real, "end": f"{end:%Y-%m-%d}"},
        "weather": {"model": config.FORECAST_MODEL, "fetched_on": f"{today:%Y-%m-%d}",
                    "weeks": [int(t) for t in gap["week_index"]]},
        "weeks": week_entries(table, cases, drawn, gap),
    }
    report = [f"real counts end {end:%Y-%m-%d} (week index {last_real}); forecast days {first_day} to {this_week}",
              f"ECMWF rain for week indexes {gap_first} to {this_week} from {reply.name}:",
              gap[gap["fit_year"] == fit_years[-1]].round(2).to_string(index=False),
              f"simulated counts for week indexes {drawn}"]
    return content, report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(),
                        help="the day to simulate to, YYYY-MM-DD (default today); a past day needs its saved ECMWF reply")
    args = parser.parse_args()
    content, report = simulation_file(args.day)
    write_json(content, config.APP_DATA / config.APP_SIMULATION_FILE)
    print("\n".join(report))
    last = content["weeks"][-1]
    m4 = last["forecasts"][config.APP_LEVEL_MODEL]
    print(f"next week, {last['start']} to {last['end']}: {config.APP_LEVEL_MODEL} {m4['mu']} expected "
          f"({m4['low']}-{m4['high']}), Pr(breach) {m4['p_breach']:.0%}")
    print(f"wrote {config.APP_SIMULATION_FILE}. {LABEL}.")


if __name__ == "__main__":
    main()

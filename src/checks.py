"""Sanity checks S1-S11."""

import sys
from datetime import date

import numpy as np
import pandas as pd
import xarray as xr
from epiweeks import Week, Year
from scipy import stats

import config
from src import baselines, breach_scores, compare, forecast_range, scores, thresholds, view, weeks


class NotBuilt(Exception):
    """Raised by a check whose task has not been done yet."""


def need_file(path, task):
    """Raise NotBuilt if a task's output file is not on this computer."""
    if not path.exists():
        raise NotBuilt(f"{path.name} not found: run task {task} or copy the file from the team drive")


def s1_calendar():
    """S1: CDC/MMWR weeks."""
    wk = Week.fromdate(date(2026, 8, 9))
    assert (wk.year, wk.week) == (2026, 32), f"got {wk}"
    assert wk.startdate() == date(2026, 8, 9), wk.startdate()
    assert wk.enddate() == date(2026, 8, 15), wk.enddate()
    for year in (2020, 2025):
        assert Year(year).totalweeks() == 53, f"{year} has {Year(year).totalweeks()} weeks"
    assert Week(2015, 1).startdate() == config.FIRST_WEEK_START, (
        f"2015 week 1 starts {Week(2015, 1).startdate()}, expected {config.FIRST_WEEK_START}")

    # The calendar table: the same answers, plus a gap-free week index.
    table = weeks.build_calendar()
    row = table.set_index("date").loc[date(2026, 8, 9)]
    assert (row["year"], row["week"]) == (2026, 32), f"got {row['year']} week {row['week']}"
    assert table["date"].iloc[0] == config.FIRST_WEEK_START, (
        f"the calendar starts {table['date'].iloc[0]}, expected {config.FIRST_WEEK_START}")
    assert table["week_index"].iloc[0] == 0, f"the week index starts at {table['week_index'].iloc[0]}, expected 0"
    per_week = table.groupby("week_index").size()
    assert (per_week == 7).all(), "every week index must cover exactly 7 days"
    assert (per_week.index == range(len(per_week))).all(), "week index has a gap"
    for year in (2020, 2025):
        n = table.loc[table["year"] == year, "week"].nunique()
        assert n == 53, f"{year} has {n} weeks in the table"
        wk53 = table[(table["year"] == year) & (table["week"] == 53)]
        assert (wk53["week_of_year"] == 52).all(), f"{year} week 53 not mapped to 52"
    assert table["week_of_year"].max() == config.MAX_WEEK, (
        f"largest week_of_year is {table['week_of_year'].max()}, expected {config.MAX_WEEK}")


def s3_census():
    """S3: boundaries, 2024 totals and 2020 age tables joined on PSGC."""
    import geopandas as gpd

    if not config.BARANGAYS_QC.exists():
        raise NotBuilt("needs task A5 (run python -m src.census)")
    brgy = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "pop_2020", "pop_2024"])
    age = pd.read_csv(config.AGE_SEX_2020_QC, dtype={"psgc": str})

    assert len(brgy) == config.QC_BARANGAYS, f"{len(brgy)} barangays"
    assert brgy["psgc"].is_unique, "duplicate psgc"
    assert brgy["psgc"].str.fullmatch(config.QC_PSGC_PREFIX + r"\d{5}").all(), "psgc not a 10-digit QC code"
    assert brgy.geometry.notna().all() and not brgy.geometry.is_empty.any(), "barangay without a shape"
    assert brgy[["pop_2020", "pop_2024"]].notna().all().all(), "barangay without a census total"
    for year in (2020, 2024):
        total = int(brgy[f"pop_{year}"].sum())
        assert total == config.CENSUS_POP_QC[year], f"{year}: {total} != {config.CENSUS_POP_QC[year]}"

    assert set(age["psgc"]) == set(brgy["psgc"]), "age table and boundaries hold different barangays"
    assert len(age) == config.QC_BARANGAYS * 2 * 81, f"age table has {len(age)} rows, expected 142 x 2 sexes x 81 ages"
    by_brgy = age.groupby("psgc")["pop"].sum()
    assert (by_brgy == brgy.set_index("psgc")["pop_2020"]).all(), "single ages do not add up to pop_2020"


def s2_rain_file():
    """S2: scan imerg_daily.nc in the rain box."""
    need_file(config.IMERG_DAILY, "A4 (python -m src.imerg)")
    with xr.open_dataset(config.IMERG_DAILY) as ds:
        rain = ds["precipitation"].load()

    # The box: cell centres run from half a cell inside one edge to half a cell inside the other.
    lon_min, lat_min, lon_max, lat_max = config.IMERG_BOX
    half = config.IMERG_CELL_DEG / 2
    for name, low, high in (("lon", lon_min, lon_max), ("lat", lat_min, lat_max)):
        centres = rain[name].values
        expected = round((high - low) / config.IMERG_CELL_DEG)
        assert len(centres) == expected, f"{len(centres)} {name} cells, expected {expected}"
        assert np.isclose(centres.min(), low + half, atol=1e-3), f"{name} starts at {centres.min()}"
        assert np.isclose(centres.max(), high - half, atol=1e-3), f"{name} ends at {centres.max()}"

    days = pd.DatetimeIndex(rain["time"].values)
    assert days.is_unique, "a day appears twice"
    assert days[0] == pd.Timestamp(config.IMERG_START), f"first day is {days[0]:%Y-%m-%d}"
    missing = pd.date_range(days[0], days[-1], freq="D").difference(days)
    assert len(missing) == 0, f"{len(missing)} days missing, first {missing[0]:%Y-%m-%d}"

    fill_days = days[rain.isnull().any(dim=["lon", "lat"]).values]  # fill values are read in as missing
    assert len(fill_days) == 0, f"fill values on {len(fill_days)} days, first {fill_days[0]:%Y-%m-%d}"
    assert float(rain.min()) >= 0, f"negative rain: {float(rain.min())} mm"

    box_mean = rain.mean(dim=["lon", "lat"]).to_series()

    carina = config.STORMS["carina_2024"]
    first, last = carina["wettest_days"]
    year = box_mean[box_mean.index.year == carina["year"]]
    year_rank = year.rank(ascending=False, method="min").astype(int)
    carina_best = year_rank[pd.Timestamp(first):pd.Timestamp(last)].min()
    carina_text = f"Carina #{carina_best} of {len(year)} days in {carina['year']}"
    assert carina_best <= config.S2_CARINA_TOP_SHARE * len(year), carina_text

    record_rank = box_mean.rank(ascending=False, method="min").astype(int)
    storm_text = []
    for name, (first, last) in config.S2_KNOWN_STORMS.items():
        best = record_rank[pd.Timestamp(first):pd.Timestamp(last)].min()
        storm_text.append(f"{name} #{best}")
        assert best <= config.S2_KNOWN_STORMS_TOP_SHARE * len(box_mean), (
            f"{name}'s wettest day is #{best} of {len(box_mean)} days")
    return (f"{len(days)} days {days[0]:%Y-%m-%d} to {days[-1]:%Y-%m-%d}; {carina_text}; "
            f"{', '.join(storm_text)} of {len(box_mean)} days")


def a11_storms():
    """The storm facts in config.STORMS that the storm runs read."""
    for storm, facts in config.STORMS.items():
        start, end = facts["start_date"], facts["end_date"]
        assert start <= end, f"{storm}: flooding ends ({end}) before it starts ({start})"
        days = (end - start).days + 1
        assert facts["D"] == days, f"{storm}: D = {facts['D']}, but {start} to {end} is {days} days"
        first, last = facts["wettest_days"]
        assert first.year == last.year == facts["year"], f"{storm}: wettest days {first} to {last} not in {facts['year']}"
        assert (last - first).days + 1 >= config.RAIN_ACCUM_DAYS, (
            f"{storm}: wettest days {first} to {last} are fewer than {config.RAIN_ACCUM_DAYS} (config.RAIN_ACCUM_DAYS)")
        codes = facts["flooded_psgc"]
        assert len(codes) == len(set(codes)), f"{storm}: a flooded barangay is listed twice"
        bad = [c for c in codes if not (len(c) == 10 and c.isdigit() and c.startswith(config.QC_PSGC_PREFIX))]
        assert not bad, f"{storm}: not 10-digit QC PSGC codes: {bad}"

    need_file(config.CENSUS_QC, "A5 (python -m src.census)")
    known = set(pd.read_csv(config.CENSUS_QC, dtype={"psgc": str})["psgc"])
    for storm, facts in config.STORMS.items():
        unknown = sorted(set(facts["flooded_psgc"]) - known)
        assert not unknown, f"{storm}: flooded barangays not among A5's {len(known)}: {unknown}"

    need_file(config.IMERG_DAILY, "A4 (python -m src.imerg)")
    from src import flood_exposure as fe

    totals = fe.n_day_totals(fe.catchment_rain(), config.RAIN_ACCUM_DAYS)
    peaks = []
    for storm, facts in config.STORMS.items():
        peak_mm, peak_end = fe.storm_peak(totals, facts["start_date"], facts["end_date"])
        first, last = facts["wettest_days"]
        assert first <= peak_end.date() <= last, (
            f"{storm}: IMERG's wettest {config.RAIN_ACCUM_DAYS}-day window during the flood ends on "
            f"{peak_end:%Y-%m-%d}, outside the wettest days {first} to {last}")
        peaks.append(f"{storm} D = {facts['D']}, {len(facts['flooded_psgc'])} flooded barangays, "
                     f"peak {peak_mm:.0f} mm ending {peak_end:%d %b}")
    return "; ".join(peaks)


def s4_cases():
    """S4: cases_weekly.csv, the weekly counts every Layer 1 model reads."""
    from src import backtest, cases as case_list

    need_file(config.CASES_WEEKLY, "A13 (python -m src.cases)")
    table = backtest.load_cases()
    assert list(pd.read_csv(config.CASES_WEEKLY, nrows=0).columns) == view.COLUMNS, "columns are not week_index, year, week, cases"
    assert table["week_index"].is_unique and not table.duplicated(["year", "week"]).any(), "a week is listed twice"
    assert (table["week_index"] == range(len(table))).all(), "the rows are not one per week from 2015 week 1 (index 0), in order"
    calendar = [weeks.year_week(i) for i in table["week_index"]]
    assert list(zip(table["year"], table["week"])) == calendar, "a row's year and week do not match its week index"
    counts = table["cases"].dropna()
    assert (counts >= 0).all() and (counts == counts.round()).all(), "a count is negative or not a whole number"

    need_file(config.QCESD_CASES_RAW, "A13 (QCESD's case list, team drive: data/raw/qcesd.md)")
    listed = case_list.read_case_list()
    complete = case_list.last_complete_week(case_list.data_date(listed))
    missing = table["cases"].isna()
    assert (missing == (table["week_index"] > complete)).all(), (
        f"missing weeks must be exactly those after the last complete week {weeks.year_week(complete)}")
    fresh = case_list.weekly_counts(listed)
    pd.testing.assert_frame_equal(table, fresh, check_dtype=False, obj="cases_weekly.csv against a fresh build (rerun python -m src.cases)")
    in_missing = case_list.onset_weeks(listed).gt(complete).sum()
    assert counts.sum() + in_missing == len(listed), f"the weeks hold {counts.sum() + in_missing:.0f} cases, the list {len(listed)}"

    delay = case_list.delay_days(listed).dropna()
    within = (delay <= config.CASES_COMPLETE_DAYS).mean()
    assert within >= config.CASES_COMPLETE_SHARE, (
        f"only {within:.1%} of cases admitted within {config.CASES_COMPLETE_DAYS} days of onset: "
        f"raise config.CASES_COMPLETE_DAYS")
    published = case_list.published_totals(listed)
    far = published[published["gap"].abs() > config.S4_PUBLISHED_TOLERANCE]
    assert far.empty, f"published totals not reproduced within {config.S4_PUBLISHED_TOLERANCE:.0%}:\n{far.to_string(index=False)}"
    totals = ", ".join(f"{row.published} to {row.end:%d %b %Y} -> {row.by_onset} ({row.gap:+.1%})" for row in published.itertuples())
    return (f"{len(table)} weeks, {counts.sum():,.0f} cases in final weeks to {weeks.year_week(complete)}, "
            f"{missing.sum()} later weeks missing; {within:.1%} admitted within {config.CASES_COMPLETE_DAYS} days; "
            f"published {totals}")


def toy_cases(last_year, first_year=config.FIRST_WEEK_START.year):
    """Made-up weekly counts from `first_year` to `last_year`: 10 x (year - 2014) + week."""
    rows = []
    for year in range(first_year, last_year + 1):
        for wk in Year(year).iterweeks():
            count = 10_000 if year in config.COVID_YEARS else 10 * (year - 2014) + wk.week
            rows.append({"week_index": weeks.week_index(wk.startdate()), "year": year,
                         "week": wk.week, "cases": count})
    return pd.DataFrame(rows)


def hide_after(cases, cutoff):
    """Copy of `cases` with every count after week index `cutoff` overwritten, as S11 does."""
    hidden = cases.copy()
    hidden.loc[hidden["week_index"] > cutoff, "cases"] = config.S11_HIDDEN_COUNT
    return hidden


def stops_with(text, func, *args):
    """True when func(*args) stops with a ValueError whose message holds `text`."""
    try:
        func(*args)
    except ValueError as e:
        return text in str(e)
    return False


def simulated_m4_rows(rng):
    """One made-up S5 dataset: M4's rows for config.S5_WEEKS target weeks, and each row's true mu."""
    from src import m4, population

    sim, true, base, theta = config.S5_SIM, config.S5_TRUE, config.S5_BASE, config.S5_THETA
    n_weeks = config.S5_WEEKS + 2                     # 2 weeks before the first target, for y~
    calendar = population.weekly_population()
    calendar = calendar[calendar["week_index"] < n_weeks].reset_index(drop=True)
    t, pop = calendar["week_index"].to_numpy(), calendar["pop"].to_numpy()
    wet = calendar["week"].between(*sim["wet_weeks"]).to_numpy()
    rain_mean = np.where(wet, sim["rain_mean_wet_mm"], sim["rain_mean_dry_mm"])
    rain = rng.gamma(sim["rain_shape"], rain_mean / sim["rain_shape"])
    ei = np.where(wet & (rng.random(n_weeks) < sim["flood_chance"]), rng.uniform(*sim["ei_range"], n_weeks), 0.0)
    rcum2 = np.concatenate([[np.nan], rain[1:] + rain[:-1]])      # Rcum2(t) = R(t - 1) + R(t)
    ei2 = np.concatenate([[np.nan], np.maximum(ei[1:], ei[:-1])])  # EI2(t) = max(EI(t - 1), EI(t))
    season = sum(base[f"sin{k}"] * np.sin(2 * np.pi * k * t / config.WEEKS_PER_YEAR)
                 + base[f"cos{k}"] * np.cos(2 * np.pi * k * t / config.WEEKS_PER_YEAR)
                 for k in range(1, config.FOURIER_K + 1))
    covid = calendar["year"].isin(config.COVID_YEARS).to_numpy()

    y, mu = np.zeros(n_weeks), np.full(n_weeks, np.nan)
    start = sim["start_cases"]
    y[:2] = rng.negative_binomial(theta, theta / (theta + start), 2)
    for s in range(2, n_weeks):                        # target s, forecast week T = s - 1
        T = s - 1
        log_mu = (np.log(pop[T]) + base["Intercept"] + season[s] + true["rho"] * np.log1p(y[s - 1] + y[s - 2])
                  + true["beta1"] * rcum2[T] / config.RAIN_SCALE_MM + true["beta2"] * ei2[T] + true["delta"] * covid[s])
        mu[s] = np.exp(log_mu)
        y[s] = rng.negative_binomial(theta, theta / (theta + mu[s]))

    targets = pd.DataFrame({"week_index": t[2:], "year": calendar["year"].to_numpy()[2:],
                            "week": calendar["week"].to_numpy()[2:], "cases": y[2:],
                            "forecast_week": t[2:] - 1, "recent": y[1:-1] + y[:-2]})
    features = pd.DataFrame({"week_index": t, "rcum2": rcum2, "ei2": ei2})
    return m4.model_rows(targets, features, calendar[["week_index", "pop"]]), mu[2:]


def s5_m4():
    """S5: M4 gets back the true values of made-up data, and forecasts with the offset."""
    from src import m4

    rng = np.random.default_rng(config.RANDOM_SEED)
    names = {"rho": m4.RECENT, "beta1": m4.RAIN, "beta2": m4.EI, "delta": m4.COVID}
    estimates, misses = [], []
    for _ in range(config.S5_DATASETS):
        rows, true_mu = simulated_m4_rows(rng)
        fit = m4.fit_m4(rows)
        assert fit["terms"] == m4.ALL_TERMS and fit["dropped"] == 0, (
            f"made-up data: terms {fit['terms']}, {fit['dropped']} rows dropped")
        estimates.append({**{name: fit["result"].params[term] for name, term in names.items()}, "theta": fit["theta"]})
        misses.append(np.median(np.abs(m4.predict_m4(fit, rows) / true_mu - 1)))
    mean = pd.DataFrame(estimates).mean()
    for name, tolerance in config.S5_TOLERANCE.items():
        assert abs(mean[name] - config.S5_TRUE[name]) <= tolerance, (
            f"mean {name} of {config.S5_DATASETS} fits is {mean[name]:.3f}, true {config.S5_TRUE[name]} (within {tolerance})")
    low, high = config.S5_THETA_RANGE
    assert low <= mean["theta"] <= high, f"mean theta {mean['theta']:.2f}, expected {low}-{high}"
    miss = float(np.median(misses))
    assert miss < config.S5_PREDICTION_TOLERANCE, f"forecasts miss the true means by {miss:.1%} (median)"

    mu = m4.predict_m4(fit, rows)
    assert np.allclose(m4.predict_m4(fit, rows.assign(pop=2 * rows["pop"])), 2 * mu), "doubling P must double the forecast"
    without = m4.fit_m4(rows, with_ei=False)
    assert without["rows"] == fit["rows"] and m4.EI not in without["terms"] and m4.RAIN in without["terms"], (
        f"M4 without EI2: {without['rows']} rows, terms {without['terms']}")
    gap = rows.copy()
    gap.loc[gap.index[10], ["rcum2", m4.RAIN]] = np.nan
    assert m4.fit_m4(gap)["rows"] == fit["rows"] - 1, "a row with a missing input must be dropped from the fit"
    assert stops_with("missing", m4.predict_m4, fit, gap.iloc[[10]]), "a forecast row with a missing input must stop"
    copy = rows.assign(**{m4.EI: 2 * rows[m4.RAIN] + rng.normal(0, 0.01, len(rows))})
    collinear = m4.fit_m4(copy)
    assert m4.RAIN not in collinear["terms"] and m4.EI in collinear["terms"], (
        f"correlation {collinear['corr_rain_ei']:.2f}: Rcum2 must be left out, terms {collinear['terms']}")
    early = m4.fit_m4(rows[rows["year"] < min(config.COVID_YEARS)])
    assert m4.COVID not in early["terms"], "before 2020 the COVID term cannot be estimated and must be left out"
    negative = rows.assign(cases=rows["cases"].where(rows.index != rows.index[5], config.S11_HIDDEN_COUNT))
    assert stops_with("negative", m4.fit_m4, negative), "a negative count must stop the fit"
    return (f"mean of {config.S5_DATASETS} fits: rho {mean['rho']:.3f}, beta1 {mean['beta1']:.3f}, "
            f"beta2 {mean['beta2']:.3f}, delta {mean['delta']:.3f}, theta {mean['theta']:.2f}; "
            f"forecasts with the offset within {miss:.1%} of the true means (median)")


def s6_theta():
    """S6: theta from past misses, and which past forecasts theta_for uses."""
    dist = forecast_range.forecast_dist(20, 5)
    assert np.isclose(dist.mean(), 20) and np.isclose(dist.var(), 100), (
        f"forecast_dist(20, 5): mean {dist.mean()}, variance {dist.var()}")
    draws = dist.rvs(size=config.S6_DRAWS, random_state=config.RANDOM_SEED)
    theta = forecast_range.estimate_theta(draws, np.full(config.S6_DRAWS, 20.0))
    low, high = config.S6_THETA_RANGE
    assert low <= theta <= high, f"theta from {config.S6_DRAWS:,} draws is {theta:.2f}, expected {low}-{high}"
    assert np.isinf(forecast_range.estimate_theta([5, 5, 5], [5, 5, 5])), "no extra spread must give infinity"
    assert forecast_range.forecast_dist(5, np.inf).var() == 5, "theta = infinity must give Poisson"

    cases = toy_cases(2024)
    sign = np.where(cases["week_index"] % 2 == 0, 1, -1)
    cutoff = weeks.week_index_of(2024, 30)
    far_off = cases["year"].isin(config.COVID_YEARS) | (cases["week_index"] > cutoff)
    past = pd.DataFrame({"week_index": cases["week_index"],
                         "mu": np.where(far_off, 1.0, cases["cases"] * (1 + 0.3 * sign))})
    used = forecast_range.scored_past(past, cases, cutoff)
    assert len(used) == config.THETA_WINDOW, f"{len(used)} past forecasts used, expected {config.THETA_WINDOW}"
    window = (used["week_index"].iloc[0], used["week_index"].iloc[-1])
    assert window == (weeks.week_index_of(2022, 31), cutoff), f"window runs from week index {window[0]} to {window[1]}"
    assert not used["year"].isin(config.COVID_YEARS).any(), "a COVID-year forecast was used"
    by_hand = forecast_range.estimate_theta(used["y"], used["mu"])
    got = forecast_range.theta_for(past, cases, cutoff, fit_theta=7.5)
    assert np.isclose(got, by_hand), f"theta_for gave {got}, by hand {by_hand}"
    hidden = hide_after(cases, cutoff)
    assert forecast_range.theta_for(past, hidden, cutoff, fit_theta=7.5) == got, (
        "theta used a count after the cutoff")

    late = past[past["week_index"] >= weeks.week_index_of(2022, 1)]
    short = forecast_range.theta_for(late, cases, weeks.week_index_of(2022, 20), fit_theta=7.5)
    assert short == 7.5, f"with 20 past forecasts theta_for gave {short}, expected the fit's 7.5"
    assert stops_with("same target week", forecast_range.theta_for,
                      pd.concat([past, past.tail(1)]), cases, cutoff, 7.5), "a duplicate forecast must stop"
    return f"theta from {config.S6_DRAWS:,} draws of NB(20, 5): {theta:.2f}; toy window theta {got:.1f}"


def s7_breach():
    """S7, first part: breach probability and thresholds."""
    dist = forecast_range.forecast_dist(20, 5)
    p = thresholds.breach_probability(dist, 12.4)
    assert round(p, 3) == 0.758, f"Pr(breach) at 12.4 = {p}"
    assert np.isclose(p, 1 - dist.cdf(12)), "Pr(breach) at 12.4 must be P(Y >= 13)"
    assert thresholds.breach_probability(dist, 200) < 1e-9, "Pr(breach) at 200 must be about 0"
    assert thresholds.breach_probability(dist, 12.0) == p, "at 12.0 a breach is also Y >= 13"
    assert thresholds.breached(13, 12.4) and not thresholds.breached(12, 12.4), (
        "with threshold 12.4, a count of 13 must be a breach and 12 must not")
    assert not thresholds.breached(12, 12.0), "a count equal to the threshold is not a breach"

    cases = toy_cases(2024)
    cutoff = weeks.week_index_of(2018, 50)
    t = thresholds.epidemic_threshold(2019, 1, cases, cutoff)
    assert np.isclose(t, 41), f"2019 week 1 threshold is {t}, expected 41"
    hidden = hide_after(cases, cutoff)
    assert thresholds.epidemic_threshold(2019, 1, hidden, cutoff) == t, "the threshold used a count after the cutoff"

    end_2024 = weeks.week_index(Year(2024).enddate())
    years = thresholds.reference_years(2025, cases, end_2024)
    assert years == [2018, 2019, 2022, 2023, 2024], f"2025 reference years {years}"
    t_52 = thresholds.epidemic_threshold(2025, 52, cases, end_2024)
    assert thresholds.epidemic_threshold(2025, 53, cases, end_2024) == t_52, "week 53 must use week 52"
    gap = cases.copy()
    gap.loc[(gap["year"] == 2023) & (gap["week"] == 20), "cases"] = np.nan
    years = thresholds.reference_years(2025, gap, end_2024)
    assert years == [2017, 2018, 2019, 2022, 2024], f"with 2023 incomplete: {years}"

    assert stops_with("reference years", thresholds.epidemic_threshold, 2017, 1, cases, end_2024), (
        "2017 has only 2 reference years and must stop")
    return f"Pr(Y > 12.4) = {p:.3f}; toy 2019 week 1 threshold {t:g}"


def s7_scores():
    """S7, second part: WIS, episodes and the exact interval, then each score by hand."""
    assert scores.wis(7, stats.randint(7, 8)) == 0, "all weight on the truth must give WIS 0"
    dist = forecast_range.forecast_dist(20, 5)
    w20, w60 = scores.wis(20, dist), scores.wis(60, dist)
    assert round(w20, 2) == 2.12 and round(w60, 1) == 32.0, f"WIS at 20 = {w20:.3f}, at 60 = {w60:.3f}"
    assert breach_scores.episodes([3, 4, 6, 10, 11]) == [[3, 4, 6], [10, 11]], (
        f"episodes of weeks 3, 4, 6, 10, 11: {breach_scores.episodes([3, 4, 6, 10, 11])}, expected [[3, 4, 6], [10, 11]]")
    assert breach_scores.episodes([]) == [], "no breach weeks must give no episodes"
    ci = breach_scores.caught_share(5, 6)
    assert (round(ci["low"], 3), round(ci["high"], 3)) == (0.359, 0.996), f"5 of 6: {ci}"

    s = scores.point_scores([10, 20], [12, 17])
    assert np.isclose(s["mae"], 2.5) and np.isclose(s["rmse"], np.sqrt(6.5)) and np.isclose(s["bias"], -0.5), s
    assert scores.covered(20, dist, 0.9) and not scores.covered(60, dist, 0.9), (
        "the 90% range for mu = 20, theta = 5 must cover 20 and not 60")
    brier = breach_scores.brier([0.9, 0.2], [1, 0])
    assert np.isclose(brier, 0.025), f"Brier of 0.9, 0.2 on outcomes 1, 0 is {brier}, expected 0.025"
    skill = breach_scores.brier_skill_score([0.9, 0.2], [1, 0], [0.5, 0.5])
    assert np.isclose(skill, 0.9), f"Brier skill against 0.5, 0.5 is {skill}, expected 0.9"
    steps = breach_scores.reliability([0.1, 0.2, 0.3, 0.4], [0, 1, 0, 1])
    assert list(steps["observed"]) == [0, 0.5, 1] and list(steps["forecasts"]) == [1, 2, 1], steps
    p_star = breach_scores.best_p_star([0.1, 0.4, 0.6, 0.9], [0, 0, 1, 1])
    assert p_star == 0.6, f"best p* is {p_star}, expected 0.6"
    assert breach_scores.alarm_scores([0.1, 0.4, 0.6, 0.9], [0, 0, 1, 1], 0.6)["f1"] == 1, (
        "alarms at p* = 0.6 must catch both breaches with no false alarm (F1 = 1)")
    outcomes = pd.DataFrame({"week_index": [100, 160, 161, 270], "year": [2017, 2018, 2018, 2020],
                             "breached": [True, True, False, True]})
    assert breach_scores.base_rate(outcomes, 300) == 0.5, "only 2018-on, non-COVID weeks count"

    table = pd.DataFrame({"model": ["M0", "M0", "M4", "M4"], "week_index": [1, 2, 1, 2],
                          "year": [2022] * 4, "y": [10, 20, 10, 20], "mu": [12, 17, 10, 21],
                          "theta": [5, 5, np.inf, 5]})
    by_model = scores.score_models(table, config.PROB_SCORE_YEARS)
    assert np.isclose(by_model.loc["M0", "mae"], 2.5) and np.isclose(by_model.loc["M4", "mae"], 0.5), by_model
    assert stops_with("same weeks", scores.score_models, table.iloc[:3], config.PROB_SCORE_YEARS), (
        "a model missing a week must stop")
    return f"WIS {w20:.2f} at 20, {w60:.1f} at 60; episodes and 5-of-6 interval as the plan; D1/D3 toys match"


def d4_lead_time():
    """Lead time per outbreak episode, worked by hand."""
    def week(n):
        return weeks.week_index_of(2023, n)

    target = [week(n) for n in range(1, 17)]
    breach = [week(n) for n in (4, 5, 7, 11, 12, 15)]
    p = [0.9 if t in (week(3), week(11)) else 0.7 if t in (week(5), week(7)) else 0.2 for t in target]
    covid = [weeks.week_index_of(2021, n) for n in (1, 2, 3)]   # breached and alarmed, but a COVID year
    forecasts = pd.DataFrame({"week_index": target + covid, "year": [2023] * 16 + [2021] * 3,
                              "p": p + [0.9] * 3, "breached": [int(t in breach) for t in target] + [1] * 3})
    worked = {
        "B": ([0, 1, np.nan], [False, True, False], 1, 0.5),
        "C": ([2, 3, np.nan], [True, True, False], 2, 2.5),
    }
    for option, (leads, advance, k, median) in worked.items():
        table = breach_scores.lead_times(forecasts, 0.5, option=option, g=2)
        assert list(table["first_week"]) == [week(4), week(11), week(15)], f"option {option}: episodes {table}"
        assert np.allclose(table["lead_weeks"], leads, equal_nan=True), f"option {option}: leads {list(table['lead_weeks'])}"
        assert list(table["in_advance"]) == advance, f"option {option}: in advance {list(table['in_advance'])}"
        summary = breach_scores.caught_in_advance(table)
        got = (summary["k"], summary["n"], summary["alarmed"], summary["median_lead_weeks"])
        assert got == (k, 3, 2, median), f"option {option}: {summary}"
    quiet_alarm = forecasts.assign(p=np.where(forecasts["week_index"] == week(6), 0.9, 0.2))
    assert breach_scores.lead_times(quiet_alarm, 0.5, "B")["lead_weeks"].isna().all(), (
        "an alarm for a quiet week inside an episode must not count")

    lead = breach_scores.lead_times
    missing = forecasts.assign(p=forecasts["p"].where(forecasts["week_index"] != week(6)))
    twice = pd.concat([forecasts, forecasts.iloc[[3]]])
    assert stops_with("p* is nan", lead, forecasts, np.nan, "B"), "a missing p* must stop"
    assert stops_with("must lie in 0-1", lead, forecasts, 1.5, "B"), "a p* above 1 must stop"
    assert stops_with("same target week", lead, twice, 0.5, "B"), "a repeated week must stop"
    assert stops_with("missing", lead, missing, 0.5, "B"), "a missing p must stop"
    quiet = lead(forecasts.assign(breached=0), 0.5, "B")
    assert stops_with("no outbreak episode", breach_scores.caught_in_advance, quiet), "no episode must stop"
    return "3 episodes (a 2021 one left out); option B: 1 of 3 caught in advance, option C (g = 2): 2 of 3, as by hand"


def d2_mase():
    """MASE's fixed denominator on made-up counts, worked by hand."""
    cases = toy_cases(2018)
    cases.loc[(cases["year"] == 2017) & (cases["week"] == 5), "cases"] += 52
    denominator = scores.mase_denominator(cases)
    assert np.isclose(denominator, 10.5), f"MASE denominator {denominator}, by hand 10.5"
    by_model = scores.add_mase(pd.DataFrame({"mae": [21, 5.25]}, index=["M0", "M4"]), denominator)
    assert np.allclose(by_model["mase"], [2, 0.5]), by_model

    def changed(year, week, column, value):
        """Copy of `cases` with `column` set to `value` in one week's row."""
        out = cases.copy()
        out.loc[(out["year"] == year) & (out["week"] == week), column] = value
        return out

    swapped = changed(2015, 10, "week_index", weeks.week_index_of(2015, 11))   # 2015 weeks 10 and 11
    swapped.loc[(swapped["year"] == 2015) & (swapped["week"] == 11), "week_index"] = weeks.week_index_of(2015, 10)
    twice = pd.concat([cases, cases[(cases["year"] == 2017) & (cases["week"] == 20)]])
    absent = cases[~((cases["year"] == 2017) & (cases["week"] == 20))]
    mase = scores.mase_denominator
    assert stops_with("is missing", mase, changed(2016, 10, "cases", np.nan)), "a missing 2016 count must stop"
    assert stops_with("is missing", mase, changed(2015, 10, "cases", np.nan)), "a missing 2015 count must stop"
    assert stops_with("is negative", mase, changed(2015, 10, "cases", config.S11_HIDDEN_COUNT)), (
        "a negative count must stop")
    assert stops_with("repeated [20]", mase, twice), "a repeated week must stop and be named"
    assert stops_with("missing [20]", mase, absent), "a missing week must stop and be named"
    assert stops_with("week index is not", mase, swapped), "week indexes that disagree with year and week must stop"
    assert stops_with("rows in the cases table, expected 1", mase, cases[cases["year"] >= 2016]), (
        "2016 with no 2015 to look back to must stop")
    assert stops_with("at least 1", mase, cases, ()), "no years must stop, not give NaN"
    assert stops_with("equals last year's", mase, cases.assign(cases=5)), "a denominator of 0 must stop"
    assert stops_with("positive", scores.add_mase, by_model, 0), "add_mase must stop on a denominator of 0"
    return f"denominator {denominator} (by hand 10.5); MASE 2 and 0.5 as by hand; bad tables stop"


def toy_forecasts(misses, years=(2022, 2023)):
    """Made-up forecasts for the comparison checks: every week of `years`, count y = 20."""
    rows = []
    targets = [(year, wk) for year in years for wk in Year(year).iterweeks()]
    for i, (year, wk) in enumerate(targets):
        for model, miss in misses.items():
            rows.append({"model": model, "week_index": weeks.week_index(wk.startdate()), "year": year,
                         "y": 20, "mu": 20 + miss[i % len(miss)]})
    for year in (2017, 2020):
        for n, model in enumerate(misses):
            rows.append({"model": model, "week_index": weeks.week_index_of(year, 10), "year": year,
                         "y": 20, "mu": 1020 if n == 0 else 20})
    return pd.DataFrame(rows)


def d5_primary_endpoint():
    """The block bootstrap, the Diebold-Mariano test and M4 vs M3, worked by hand."""
    boot = compare.block_bootstrap([1, 2, 3, 4], block=2)
    assert (boot["mean"], boot["low"], boot["high"]) == (2.5, 1.5, 3.5), f"d = 1-4, 2-week blocks: {boot}"
    one = compare.block_bootstrap([1, 5, 2, 8], block=4)
    assert one["low"] == one["high"] == 4, f"one block as long as d must give its mean, 4: {one}"
    dm = compare.dm_test([1, -1, 2, 0])
    assert np.isclose(dm["dm_stat"], np.sqrt(0.6)), f"DM {dm['dm_stat']}, by hand sqrt(0.6) = {np.sqrt(0.6):.4f}"
    assert np.isclose(dm["dm_p"], stats.ttest_1samp([1, -1, 2, 0], 0).pvalue), "DM's p must equal the paired t test's"

    table = toy_forecasts({"M4": [1, 3], "M3": [0]})
    result = compare.primary_endpoint(table).set_index("block_weeks")
    assert list(result.index) == [config.BOOT_BLOCK_WEEKS, *config.BOOT_BLOCK_WEEKS_TESTS], result
    assert (result["weeks"] == 104).all() and np.allclose(result["mean_diff"], 2), result
    for block in (8, 4):
        assert result.at[block, "low"] == result.at[block, "high"] == 2, f"{block}-week blocks: {result.loc[block]}"
        assert result.at[block, "verdict"] == "M3 misses less", result.at[block, "verdict"]
    assert result.at[13, "low"] < 2 < result.at[13, "high"], f"13-week blocks: {result.loc[13]}"
    assert np.allclose(result["dm_stat"], 2 * np.sqrt(103)), f"DM {result['dm_stat'].iloc[0]}, by hand 2 sqrt(103)"

    in_window = table["year"].isin(config.MAE_YEARS)
    missing_week = table.drop(table[in_window & (table["model"] == "M4")].index[0])
    other_count = table.copy()
    other_count.loc[table[in_window & (table["model"] == "M4")].index[0], "y"] = 21
    assert stops_with("same weeks", compare.primary_endpoint, missing_week), "a model missing a week must stop"
    assert stops_with("different counts", compare.primary_endpoint, other_count), "different counts must stop"
    assert stops_with("need forecasts of both", compare.primary_endpoint, table[table["model"] == "M4"]), (
        "a model with no forecasts must stop")
    assert stops_with("fewer than one", compare.block_bootstrap, [1, 2, 3], 8), "fewer weeks than a block must stop"
    assert stops_with("undefined", compare.dm_test, [2, 2, 2]), "DM must stop when every d is the same"
    assert stops_with("undefined", compare.dm_test, [0.1] * 7), "DM must stop on equal d that floats store inexactly"
    return (f"bootstrap 1.5-3.5 and DM sqrt(0.6) as by hand; M4 vs M3 on made-up misses: mean 2, "
            f"8- and 4-week intervals 2-2, 13-week {result.at[13, 'low']:.2f}-{result.at[13, 'high']:.2f}; bad tables stop")


def d6_flood_test():
    """The flood test and the practical test on made-up misses, worked by hand."""
    helps = compare.flood_and_practical_tests(toy_forecasts({"M4": [0], "M4_no_EI2": [1, 3], "M1": [1, 3]}))
    eight = helps[helps["block_weeks"] == config.BOOT_BLOCK_WEEKS].set_index("comparison")
    for name in ("M4 vs M4_no_EI2", "M4 vs M1"):
        assert (eight.at[name, "mean_diff"], eight.at[name, "low"], eight.at[name, "high"]) == (-2, -2, -2), eight
        assert eight.at[name, "verdict"] == "M4 misses less", eight.at[name, "verdict"]
    flood = helps["comparison"] == "M4 vs M4_no_EI2"
    assert helps.loc[flood, "dm_stat"].isna().all(), "the flood test must have no DM (nested models)"
    assert np.allclose(helps.loc[~flood, "dm_stat"], -2 * np.sqrt(103)), helps.loc[~flood, "dm_stat"]
    found = compare.flood_finding(helps)
    assert found.startswith("The flood exposure index makes M4 more accurate") and found.endswith("agree."), found

    nothing = compare.flood_and_practical_tests(toy_forecasts({"M4": [1, 0], "M4_no_EI2": [0, 1], "M1": [3]}))
    row = nothing[(nothing["comparison"] == "M4 vs M4_no_EI2") & (nothing["block_weeks"] == 8)].iloc[0]
    assert (row["mean_diff"], row["low"], row["high"], row["verdict"]) == (0, 0, 0, "no clear difference"), row
    found_nothing = compare.flood_finding(nothing)
    assert "adds no clear accuracy" in found_nothing and "Layer 2, not Layer 1" in found_nothing, found_nothing
    assert found_nothing.endswith("agree."), found_nothing

    split = pd.DataFrame({"comparison": "M4 vs M4_no_EI2", "block_weeks": [8, 4, 13], "mean_diff": -0.3,
                          "low": [-0.4, -0.5, -0.6], "high": [-0.1, -0.1, 0.2],
                          "verdict": ["M4 misses less", "M4 misses less", "no clear difference"]})
    assert compare.flood_finding(split).endswith("depends on the block length."), compare.flood_finding(split)
    return f"EI2 helps: interval -2 to -2; EI2 adds nothing: 0 to 0, \"{found_nothing[:46]}...\"; no DM for nested models"


def b8_baselines():
    """M0 and M1 on made-up counts, worked by hand."""
    cases = toy_cases(2026, first_year=2021)
    models = {"M0": baselines.m0_forecast, "M1": baselines.m1_forecast}
    worked = [
        # model, target (year, week), cutoff (year, week), answer by hand
        ("M0", (2022, 10), (2022, 9), 10_000),  # 2021 week 10: COVID years are not skipped
        ("M0", (2025, 10), (2025, 9), 110),     # 2024 week 10 = 100 + 10
        ("M0", (2025, 53), (2025, 52), 111),    # 52 weeks back stays in 2025: week 1
        ("M0", (2026, 1), (2025, 53), 112),     # after a 53-week year: 2025 week 2
        ("M1", (2025, 10), (2025, 9), 100),     # 2022-2024, COVID 2021 skipped: (90 + 100 + 110) / 3
        ("M1", (2025, 53), (2025, 52), 142),    # week 52's counts: (132 + 142 + 152) / 3
        ("M1", (2026, 1), (2025, 53), 96),      # 2022-2025: (81 + 91 + 101 + 111) / 4
        ("M1", (2026, 2), (2025, 52), 92),      # 2025 week 53 hidden, so 2022-2024: (82 + 92 + 102) / 3
    ]
    for name, (year, week), (cut_year, cut_week), answer in worked:
        model = models[name]
        cutoff = weeks.week_index_of(cut_year, cut_week)
        label = f"{name} {year} week {week}, cutoff {cut_year} week {cut_week}"
        got = model(year, week, cases, cutoff)
        assert np.isclose(got, answer), f"{label}: {got}, by hand {answer}"
        assert model(year, week, hide_after(cases, cutoff), cutoff) == got, f"{label}: used a count after the cutoff"
        assert model(float(year), float(week), cases, cutoff) == got, f"{label}: fails on float year and week"

    m0, m1 = baselines.m0_forecast, baselines.m1_forecast
    missing = cases.copy()
    missing.loc[(missing["year"] == 2024) & (missing["week"] == 10), "cases"] = np.nan
    twice = pd.concat([cases, cases[(cases["year"] == 2023) & (cases["week"] == 10)]])
    assert stops_with("after the cutoff", m0, 2025, 10, cases, weeks.week_index_of(2024, 9)), (
        "M0 must stop when 52 weeks back is after the cutoff")
    assert stops_with("missing count", m0, 2025, 10, missing, weeks.week_index_of(2025, 9)), (
        "M0 must stop when the count 52 weeks back is missing")
    assert stops_with("0 rows", m0, 2021, 10, cases, weeks.week_index_of(2021, 9)), (
        "M0 must stop when 52 weeks back is before the data")
    assert stops_with("reference years", m1, 2024, 10, cases, weeks.week_index_of(2024, 9)), (
        "M1 must stop with 2 reference years (2022, 2023; 2021 is COVID)")
    assert stops_with("expected one week-10 count", m1, 2025, 10, twice, weeks.week_index_of(2025, 9)), (
        "M1 must stop when a reference year has two week-10 rows")
    for model in (m0, m1):
        assert stops_with("Week must be in", model, 2026, 53, cases, weeks.week_index_of(2026, 52)), (
            "M0 and M1 must stop on 2026 week 53, which does not exist")
    return f"{len(worked)} forecasts match the hand answers; leaks, gaps, duplicates and bad weeks stop"


def b9_m3():
    """M3's gap filling worked by hand, then its forecast on made-up counts."""
    from src import m3_port   # imports Prophet and xgboost; only this check needs them

    cases = toy_cases(2021)
    for year, week in [(2015, 1), (2015, 2), (2017, 30), (2018, 3), (2019, 3), (2020, 14)]:
        cases.loc[(cases["year"] == year) & (cases["week"] == week), "cases"] = np.nan
    fills = {
        (2020, 20): {(2017, 30): (60, "monsoon"), (2018, 3): (43, "interpolated"),
                     (2019, 3): (53, "interpolated"), (2020, 14): (22, "lockdown")},
        (2019, 3): {(2017, 30): (160 / 3, "monsoon"), (2018, 3): (43, "interpolated"),
                    (2019, 3): (52, "interpolated")},
    }
    for (cut_year, cut_week), worked in fills.items():
        cutoff = weeks.week_index_of(cut_year, cut_week)
        filled = m3_port.fill_gaps(m3_port.seen_weeks(cases, cutoff))
        assert (filled["year"].iloc[0], filled["week"].iloc[0]) == (2015, 3), "training must start at the first count"
        gaps = filled[filled["fill_rule"] != "observed"].set_index(["year", "week"])
        got = {key: (round(row["y"], 4), row["fill_rule"]) for key, row in gaps.iterrows()}
        assert got == {key: (round(v, 4), rule) for key, (v, rule) in worked.items()}, (
            f"cutoff {cut_year} week {cut_week}: fills {got}, by hand {worked}")
        hidden = m3_port.fill_gaps(m3_port.seen_weeks(hide_after(cases, cutoff), cutoff))
        assert hidden.equals(filled), f"cutoff {cut_year} week {cut_week}: gap filling used a count after the cutoff"
    no_first_row = cases[~((cases["year"] == 2015) & (cases["week"] == 1))]
    seen = m3_port.seen_weeks(no_first_row, weeks.week_index_of(2019, 3))
    assert (seen["year"].iloc[0], seen["week"].iloc[0]) == (2015, 3), "rows before the first count must not matter"

    assert weeks.week_start(weeks.week_index_of(2026, 32)) == date(2026, 8, 9), "2026 week 32 starts 9 August"
    assert weeks.week_start(weeks.week_index_of(2026, 1)) == date(2026, 1, 4), "2026 week 1 starts 4 January"
    assert list(m3_port.iso_weeks([date(2026, 8, 9), date(2019, 3, 3)])) == [33, 10], (
        "ISO week: 33 for MMWR 2026 week 32 (2026 starts on a Thursday), 10 for 2019 week 10")

    forecasts = []
    for cut_week in (9, 7):
        cutoff = weeks.week_index_of(2019, cut_week)
        label = f"M3 2019 week 10, cutoff 2019 week {cut_week}"
        got = m3_port.m3_forecast(2019, 10, cases, cutoff)
        assert got["target_date"] == date(2019, 3, 3), f"{label}: target dated {got['target_date']}, not 3 March"
        assert abs(got["mu"] - 60) <= 6, f"{label}: {got['mu']:.2f}, true count 60"
        assert m3_port.m3_forecast(2019, 10, hide_after(cases, cutoff), cutoff) == got, (
            f"{label}: used a count after the cutoff")
        assert m3_port.m3_forecast(2019.0, 10.0, cases, cutoff) == got, f"{label}: fails on float year and week"
        forecasts.append(f"{got['mu']:.1f}")

    m3 = m3_port.m3_forecast
    cutoff = weeks.week_index_of(2019, 9)
    skipped = cases[~((cases["year"] == 2018) & (cases["week"] == 5))]
    twice = pd.concat([cases, cases[(cases["year"] == 2018) & (cases["week"] == 5)]])
    negative = cases.copy()
    negative.loc[(negative["year"] == 2018) & (negative["week"] == 5), "cases"] = -5
    mislabelled = cases.copy()
    mislabelled.loc[(mislabelled["year"] == 2018) & (mislabelled["week"] == 5), "week"] = 6
    assert stops_with("not after the cutoff", m3, 2019, 9, cases, cutoff), "M3 must stop when the target is seen"
    assert stops_with("Week must be in", m3, 2026, 53, cases, cutoff), "M3 must stop on 2026 week 53"
    assert stops_with("skips a week", m3, 2019, 10, skipped, cutoff), "M3 must stop when a week has no row"
    assert stops_with("two rows", m3, 2019, 10, twice, cutoff), "M3 must stop when a week has two rows"
    assert stops_with("negative", m3, 2019, 10, negative, cutoff), "M3 must stop on a negative seen count"
    assert stops_with("not the MMWR week", m3, 2019, 10, mislabelled, cutoff), (
        "M3 must stop when a row's year and week disagree with its week index")
    assert stops_with("no row for the cutoff", m3, 2022, 2, cases, weeks.week_index_of(2022, 1)), (
        "M3 must stop when the table ends before the cutoff")

    rng = np.random.default_rng(config.RANDOM_SEED)
    simulated = []
    for year in range(2015, 2020):
        for wk in Year(year).iterweeks():
            mu = 15 * np.exp(0.9 * np.cos(2 * np.pi * (wk.week - 32) / config.WEEKS_PER_YEAR))
            simulated.append({"week_index": weeks.week_index(wk.startdate()), "year": year, "week": wk.week,
                              "cases": float(rng.negative_binomial(5, 5 / (5 + mu)))})
    fit_theta = m3(2019, 10, pd.DataFrame(simulated), cutoff)["fit_theta"]
    low, high = config.B9_FIT_THETA_RANGE
    assert low <= fit_theta <= high, f"M3's fit_theta on counts with theta 5 is {fit_theta:.2f}, expected {low}-{high}"
    return (f"gap fills match the hand answers at 2 cutoffs; forecasts {' and '.join(forecasts)} (true 60) "
            f"unchanged with later counts hidden; fit_theta {fit_theta:.2f} (true 5); bad tables stop")


def b2_view():
    """What a model may see at forecast day T, on made-up counts worked by hand."""
    cases = toy_cases(2026, first_year=2022)
    T = weeks.week_index_of(2024, 10)
    worked = [
        # option, g, horizon, forecast day (year, week), y~ by hand, last training row (year, week, y~)
        ("B", 2, 1, (2024, 10), 219, (2024, 10, 217)),
        ("C", 2, 1, (2024, 10), 215, (2024, 8, 209)),
        ("C", 1, 1, (2024, 10), 217, (2024, 9, 107 + 106)),
        ("C", 3, 1, (2024, 10), 213, (2024, 7, 103 + 102)),
        ("B", 2, 2, (2024, 10), 219, (2024, 10, 215)),
        ("B", 2, 1, (2026, 1), 121 + 163, (2026, 1, 163 + 162)),
    ]
    for option, g, h, (year, week), answer, (last_year, last_week, last_recent) in worked:
        day = weeks.week_index_of(year, week)
        label = f"option {option}, g = {g}, h = {h}, forecast day {year} week {week}"
        cut = view.cutoff(day, option, g)
        assert cut == day - (g if option == "C" else 0), f"{label}: cutoff {cut}"
        row = view.prediction_row(cases, day, option, g, h)
        assert row["recent"].iloc[0] == answer, f"{label}: y~ = {row['recent'].iloc[0]}, by hand {answer}"
        assert row["week_index"].iloc[0] == day + h and row["forecast_week"].iloc[0] == day, f"{label}: wrong target"
        assert weeks.year_week(row["week_index"].iloc[0]) == (row["year"].iloc[0], row["week"].iloc[0]), (
            f"{label}: the target's year and week do not match its week index")
        train = view.training_rows(cases, day, option, g, h)
        last = train.iloc[-1]
        assert (last["year"], last["week"], last["recent"]) == (last_year, last_week, last_recent), (
            f"{label}: last training row {last['year']} week {last['week']}, y~ {last['recent']}")
        assert (train["week_index"] <= cut).all() and len(train) == (cases["week_index"] <= cut).sum(), (
            f"{label}: training rows must be every week up to the cutoff and none after it")
        assert (train["forecast_week"] == train["week_index"] - h).all(), f"{label}: forecast_week is not target - h"
        hidden = hide_after(cases, cut)
        assert view.training_rows(hidden, day, option, g, h).equals(train), f"{label}: training rows read a hidden count"
        assert view.prediction_row(hidden, day, option, g, h).equals(row), f"{label}: y~ read a hidden count"
        # the same target, once it can be seen, gets the same y~ in training
        later = view.training_rows(cases, day + h + view.guard_weeks(option, g), option, g, h)
        same = later.loc[later["week_index"] == day + h, "recent"]
        assert list(same) == [answer], f"{label}: the training row for the same target has y~ {list(same)}"

    first = view.training_rows(cases, T, "B", 2, 1)["recent"].iloc[:3]
    assert first.iloc[:2].isna().all() and first.iloc[2] == 163, f"first training rows' y~: {list(first)}"

    missing = cases.copy()
    missing.loc[missing["week_index"] == T, "cases"] = np.nan
    twice = pd.concat([cases, cases.tail(1)])
    assert stops_with("DATA_OPTION", view.cutoff, T, None, 2), "no data option set must stop"
    try:
        view.cutoff(T, "A", 2)
        raise AssertionError("option A must stop: it is not built")
    except NotImplementedError:
        pass
    assert stops_with("one is missing", view.prediction_row, missing, T, "B", 2, 1), "a missing count at the cutoff must stop"
    assert stops_with("listed twice", view.training_rows, twice, T, "B", 2, 1), "a week listed twice must stop"
    return (f"{len(worked)} forecast days match the hand answers in options B and C (g = 1-3, h = 1 and 2); "
            f"counts after the cutoff hidden: nothing changes")


def s8_census_fit():
    """S8, first part: each barangay's rescaled pixels add up to its 2024 census total."""
    # Files first: without them the check is a SKIP, even where exactextract is not installed.
    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.WORLDPOP_SCALE_QC, "C1 (python -m src.rescale)")

    import geopandas as gpd

    from src import rescale

    brgy = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "pop_2024"])
    scale = pd.read_csv(config.WORLDPOP_SCALE_QC, dtype={"psgc": str})

    assert len(scale) == config.QC_BARANGAYS and scale["psgc"].is_unique, (
        f"scale file has {len(scale)} rows, {scale['psgc'].nunique()} barangays")
    assert set(scale["psgc"]) == set(brgy["psgc"]), "scale file and A5's barangays hold different barangays"
    assert np.isfinite(scale["scale"]).all() and (scale["scale"] > 0).all(), "a scale factor is missing, 0 or negative"

    fitted = rescale.rescaled_residents(brgy)
    gap = (fitted / brgy["pop_2024"] - 1).abs()
    worst = gap.idxmax()
    assert gap[worst] <= config.S8_CENSUS_TOLERANCE, (
        f"{brgy.loc[worst, 'psgc']}: rescaled pixels add up to {fitted[worst]:,.1f}, "
        f"census {brgy.loc[worst, 'pop_2024']:,}")
    return (f"{len(brgy)} barangays, largest gap {gap[worst]:.1e}; "
            f"QC {fitted.sum():,.0f} vs census {brgy['pop_2024'].sum():,}")


def s8_overlay():
    """S8, second and third parts: the overlay table, and the barangays to inspect."""
    # Files first: without them the check is a SKIP, even where exactextract is not installed.
    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.OVERLAY, "C2 (python -m src.overlay)")

    import geopandas as gpd

    from src import overlay

    brgy = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "adm4_name", "pop_2024"])
    table = pd.read_csv(config.OVERLAY, dtype={"psgc": str})

    expected = config.QC_BARANGAYS * len(config.NOAH_RETURN_PERIODS) * len(config.NOAH_HAZARD_LEVELS)
    assert len(table) == expected, f"{len(table)} rows, expected {expected} (barangays x maps x levels)"
    assert not table.duplicated(overlay.KEYS).any(), "a barangay, map and level appears twice"
    assert set(table["psgc"]) == set(brgy["psgc"]), "overlay and A5's barangays hold different barangays"
    assert set(table["return_period"]) == set(config.NOAH_RETURN_PERIODS), "unexpected maps"
    assert set(table["var"]) == set(config.NOAH_HAZARD_LEVELS), "unexpected hazard levels"
    for col in ("area_km2", "residents"):
        assert table[col].notna().all() and (table[col] >= 0).all(), f"missing or negative {col}"

    exposed = overlay.exposed_by_map(table)
    pop = brgy.set_index("psgc")["pop_2024"]
    over = exposed.gt(pop * (1 + config.S8_CENSUS_TOLERANCE), axis=0).any(axis=1)
    assert not over.any(), f"exposed residents exceed the census total in {list(exposed.index[over])}"

    falls = overlay.falls_with_rarer_map(table)
    names = ", ".join(brgy.set_index("psgc").loc[falls.index, "adm4_name"])
    return (f"at most {exposed.div(pop, axis=0).max().max():.1%} of a barangay exposed; "
            f"{len(falls)} barangays fall in a rarer map, inspect: {names}")


def toy_overlay():
    """Made-up overlay table for S9: 2 barangays x 3 maps x 3 levels, residents worked by hand."""
    pops = {  # (psgc, var): (Pop_5, Pop_25, Pop_100)
        ("A", 1): (100, 200, 400), ("A", 2): (10, 50, 90), ("A", 3): (0, 0, 30),
        ("B", 1): (80, 60, 70), ("B", 2): (0, 20, 20), ("B", 3): (0, 0, 0),
    }
    rows = [{"psgc": b, "var": k, "return_period": t, "residents": float(n)}
            for (b, k), values in pops.items() for t, n in zip(config.NOAH_RETURN_PERIODS, values)]
    return pd.DataFrame(rows)


def s9_return_levels():
    """S9: Gumbel return levels, the fit, and graded exposure."""
    from src import flood_exposure as fe

    true = [round(fe.gumbel_level(100, 30, t), 1) for t in config.NOAH_RETURN_PERIODS]
    assert true == [145.0, 196.0, 238.0], f"true R(5), R(25), R(100) = {true}"

    rng = np.random.default_rng(config.RANDOM_SEED)
    fitted = []
    for _ in range(config.S9_SAMPLES):
        sample = stats.gumbel_r.rvs(loc=100, scale=30, size=config.S9_SAMPLE_YEARS, random_state=rng)
        mu, beta = fe.fit_gumbel(sample)
        fitted.append(fe.gumbel_level(mu, beta, 25))
    median, low, high = np.median(fitted), *np.percentile(fitted, [5, 95])
    tol = config.S9_FIT_TOLERANCE_MM
    assert abs(median - 191) <= tol, f"median fitted R(25) = {median:.1f}, expected about 191"
    assert abs(low - 164) <= tol and abs(high - 224) <= tol, f"90% of fits in {low:.0f}-{high:.0f}, expected 164-224"

    levels = {"r0": 50.0, 5: 100.0, 25: 150.0, 100: 200.0}
    overlay = toy_overlay()
    pops = fe.map_table(overlay)

    def exposure(rain):
        table = fe.graded_exposure(rain, levels, overlay)
        assert list(table.columns) == ["psgc", "var", "residents"], f"columns {list(table.columns)} (C5 takes psgc, var, residents)"
        return table.set_index(["psgc", "var"])["residents"]

    assert (exposure(50.0) == 0).all() and (exposure(10.0) == 0).all(), "exposure at or below R0 must be 0"
    assert np.allclose(exposure(75.0), pops[5] / 2), "halfway between R0 and R(5) must be half of Pop_5"
    assert np.allclose(exposure(100.0), pops[5]), "exposure at R(5) must be Pop_5 exactly"
    assert np.allclose(exposure(125.0), (pops[5] + pops[25]) / 2), "halfway between R(5) and R(25) must be halfway"
    assert np.allclose(exposure(200.0), pops[100]) and np.allclose(exposure(500.0), pops[100]), (
        "exposure at and above R(100) must be Pop_100")
    totals = fe.map_totals(overlay)
    assert np.isclose(fe.exposed_total(125.0, levels, totals), exposure(125.0).sum()), "city total != sum of barangays"

    maxima = pd.Series(stats.gumbel_r.rvs(loc=100, scale=30, size=20, random_state=rng), index=range(2000, 2020))
    before = fe.return_levels(maxima, 2015)
    changed = maxima.copy()
    changed[changed.index >= 2015] = 999.0
    assert fe.return_levels(changed, 2015) == before, "the 2015 fit used 2015 or a later year (rule 2)"
    assert before["n_years"] == 15, f"the 2015 fit used {before['n_years']} years, expected 2000-2014"
    assert stops_with("at least", fe.return_levels, maxima, 2009), "a fit on 9 years must stop"

    daily = pd.Series([10.0, 20.0, 30.0, 0.0, 5.0], index=pd.date_range("2024-07-21", periods=5, freq="D"))
    three = fe.n_day_totals(daily, 3)
    assert three.tolist() == [60.0, 50.0, 35.0], f"3-day totals {three.tolist()}, by hand 60, 50, 35"
    assert three.index[0] == pd.Timestamp("2024-07-23"), "a total must be labelled with its last day"
    assert fe.n_day_totals(daily, 1).equals(daily), "1-day totals must be the daily rain unchanged"
    assert stops_with("every day", fe.n_day_totals, daily.drop(daily.index[2]), 3), "a missing day must stop"
    return (f"median fitted R(25) {median:.1f}, 90% of fits {low:.0f}-{high:.0f}; toy exposure and "
            f"n-day totals match by hand")


def s9_exposure_index():
    """S9, real data: ei_weekly.csv."""
    need_file(config.EI_WEEKLY, "C3 (python -m src.flood_exposure)")
    ei = pd.read_csv(config.EI_WEEKLY)
    assert "rain_days" in ei.columns, "ei_weekly.csv has no rain_days column: rerun python -m src.flood_exposure"
    made_with = sorted(ei["rain_days"].unique())
    assert made_with == [config.RAIN_ACCUM_DAYS], (
        f"ei_weekly.csv was made with {made_with}-day totals, config says {config.RAIN_ACCUM_DAYS}: rerun C3")
    fit_years = list(range(config.BACKTEST_FIRST_YEAR, config.BACKTEST_LAST_YEAR + 1))
    assert sorted(ei["fit_year"].unique()) == fit_years, f"fit years {sorted(ei['fit_year'].unique())}"
    assert not ei.duplicated(["fit_year", "week_index"]).any(), "a fit year and week appear twice"
    assert ei[["rmax_mm", "ei"]].notna().all().all(), "missing rain or EI"
    assert ei["ei"].between(0, 100).all(), f"EI outside 0-100: {ei['ei'].min()} to {ei['ei'].max()}"
    for year, rows in ei.groupby("fit_year"):
        index = rows["week_index"].to_numpy()
        assert index[0] == 0 and (np.diff(index) == 1).all(), f"fit {year}: weeks do not run from 0 without a gap"
        assert rows.loc[rows["rmax_mm"].idxmax(), "ei"] == rows["ei"].max(), f"fit {year}: EI does not grow with rain"
    last = ei[ei["fit_year"] == config.BACKTEST_LAST_YEAR]
    return (f"{config.RAIN_ACCUM_DAYS}-day totals; {len(fit_years)} fit years x {len(last)} weeks; "
            f"EI above 0 in {(last['ei'] > 0).mean():.1%} "
            f"of weeks, highest {last['ei'].max():.1f}% ({config.BACKTEST_LAST_YEAR} fit)")


def s10_shares():
    """S10, first part: child, pregnant and adult shares."""
    from src import shares

    # Made-up city of two barangays with 100 pregnant women in all, worked by hand.
    toy = pd.DataFrame({"pop_2020": [1000, 2000], "pop_2024": [1250, 2500], "children": [300, 500],
                        "women_15_49": [250, 750], "women_15_17": [25, 50]}, index=["a", "b"])
    got = shares.group_shares(toy, 100)
    for col, expected in (("preg", [25, 75]), ("s_preg", [0.02, 0.03]),
                          ("s_child", [0.298, 0.248]), ("s_adult", [0.682, 0.722])):
        assert np.allclose(got[col], expected), f"made-up city: {col} = {list(got[col])}, expected {expected}"

    need_file(config.CENSUS_QC, "A5 (python -m src.census)")
    need_file(config.BIRTHS_2024, "A12 (copy psa_births_2024.csv from the team drive)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    table = pd.read_csv(config.SHARES_QC, dtype={"psgc": str}).set_index("psgc")
    counts = shares.barangay_counts()

    assert len(table) == config.QC_BARANGAYS and table.index.is_unique, (
        f"shares file has {len(table)} rows, {table.index.nunique()} barangays")
    assert set(table.index) == set(counts.index), "shares file and A5's barangays hold different barangays"
    preg_qc = shares.pregnant_from_births(shares.qc_births())
    upper_qc = shares.upper_bound_pregnant(counts)
    assert preg_qc < upper_qc, f"{preg_qc:,.0f} pregnant women is above the 3.5% upper bound ({upper_qc:,.0f})"
    upper = shares.group_shares(counts, upper_qc)
    for label, t in (("shares file", table), ("upper bound", upper)):
        s = t[shares.SHARES]
        assert s.notna().all().all(), f"{label}: a share is missing"
        assert (s >= 0).all().all(), f"{label}: negative share in {list(s.index[(s < 0).any(axis=1)])}"
        off = (s.sum(axis=1) - 1).abs()
        assert off.max() <= config.S10_SHARE_TOLERANCE, f"{label}: shares add to {s.sum(axis=1)[off.idxmax()]} in {off.idxmax()}"
    assert np.isclose(table["preg"].sum(), preg_qc), f"pregnant counts add up to {table['preg'].sum():,.1f}, QC has {preg_qc:,.1f}"

    fresh = shares.group_shares(counts, preg_qc).loc[table.index]
    cols = ["pop_2020", "pop_2024", "children", "women_15_49", "women_15_17", "preg", *shares.SHARES]
    assert np.allclose(table[cols], fresh[cols]), "shares file differs from a fresh run: rerun python -m src.shares"
    return (f"QC child {(table['s_child'] * table['pop_2024']).sum() / table['pop_2024'].sum():.1%}, "
            f"pregnant {preg_qc:,.0f}, smallest adult share {table['s_adult'].min():.3f} "
            f"({upper['s_adult'].min():.3f} at the 3.5% upper bound)")


def s10_exposed():
    """S10: exposed people per group, and the adult risk tiers."""
    from src import exposed

    # Made-up city of two barangays, q = 0.5, worked by hand.
    toy_shares = pd.DataFrame({"s_child": [0.30, 0.25], "s_preg": [0.02, 0.03], "s_adult": [0.68, 0.72]},
                              index=pd.Index(["a", "b"], name="psgc"))
    toy = pd.DataFrame({"psgc": ["a"] * 3 + ["b"] * 3, "var": [1, 2, 3] * 2,
                        "residents": [100, 200, 300, 0, 50, 0]})
    got = exposed.exposed_people(toy, toy_shares, q=0.5, contact={1: 0.5, 2: 1.0, 3: 1.0})
    for col, expected in (("exposed", [275, 25]), ("e_child", [82.5, 6.25]),
                          ("e_preg", [5.5, 0.75]), ("e_adult", [187, 18])):
        assert np.allclose(got[col], expected), f"made-up city: {col} = {list(got[col])}, expected {expected}"

    # S10's input: 100 exposed adults. (D, cut-off, w) -> (high, moderate, low)
    adults = pd.Series([100.0])
    for days, cutoff, w, expected in (
        (1, 2, 0.5, (0, 50, 50)),     # short flood, split by w: 2 x 50 + 10 x 50 = 600 capsules
        (3, 2, 0.5, (100, 0, 0)),     # 2 days or more, all high: 2 x ceil(3/7) x 100 = 200
        (10, 2, 0.5, (100, 0, 0)),    # 2 x ceil(10/7) x 100 = 400
        (1, 2, 0.0, (0, 0, 100)),     # the bounds of w
        (1, 2, 1.0, (0, 100, 0)),
        (2, 3, 0.5, (0, 50, 50)),     # cut-off tests: 2 days is short under a 3-day cut-off
        (1, 1, 0.5, (100, 0, 0)),     # and every flood is long under a 1-day cut-off
    ):
        tiers = tuple(exposed.adult_tiers(adults, days, w, cutoff).iloc[0][exposed.TIERS])
        assert np.allclose(tiers, expected), (
            f"D = {days}, cut-off {cutoff}, w = {w}: (high, moderate, low) = {tiers}, expected {expected}")

    for label, bad in (("barangay b missing", toy[toy["psgc"] == "a"]), ("two maps mixed", pd.concat([toy, toy]))):
        try:
            exposed.exposed_people(bad, toy_shares)
        except ValueError:
            continue
        raise AssertionError(f"{label}: exposed_people did not stop")

    need_file(config.OVERLAY, "C2 (python -m src.overlay)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    table = exposed.load_shares()
    full_contact = {k: 1.0 for k in config.NOAH_HAZARD_LEVELS}
    parts = []
    for period in config.NOAH_RETURN_PERIODS:
        residents = exposed.map_residents(overlay, period)
        people = exposed.exposed_people(residents, table)
        assert len(people) == config.QC_BARANGAYS, f"{period}-year map: {len(people)} barangays"
        assert people.notna().all().all() and (people >= 0).all().all(), f"{period}-year map: missing or negative counts"
        flooded = residents.groupby("psgc")["residents"].sum().loc[people.index]
        everyone = exposed.exposed_people(residents, table, q=1.0, contact=full_contact)["exposed"]
        assert np.allclose(everyone, flooded), f"{period}-year map: with q = r_k = 1, exposed differs from the map's residents"
        assert np.allclose(people[list(exposed.GROUPS)].sum(axis=1), people["exposed"]), (
            f"{period}-year map: the groups do not add up to everyone exposed")
        for label, days, w in exposed.scenarios():
            tiers = exposed.adult_tiers(people["e_adult"], days, w)
            assert np.allclose(tiers.sum(axis=1), people["e_adult"]), f"{period}-year map, {label}: tiers do not add up"
        parts.append(f"R({period}) {people['exposed'].sum():,.0f}")
    return f"QC exposed at {', '.join(parts)}; groups and tiers add up"


def s10_doses():
    """S10: drug units per barangay."""
    from src import doses, exposed

    def made_up(adults=0, children=0, pregnant=0, days=1):
        """One made-up barangay's exposure table, with w = 0.5 and a 2-day cut-off."""
        tiers = exposed.adult_tiers(pd.Series([float(adults)]), days, w=0.5, cutoff=2)
        return tiers.assign(e_child=float(children), e_preg=float(pregnant))

    for days, expected in ((1, 600), (3, 200), (10, 400)):
        got = doses.doses(made_up(adults=100, days=days), days, u=1.0)["doxy100"].iloc[0]
        assert np.isclose(got, expected), f"100 adults, D = {days}: {got} capsules, expected {expected}"
    for days, expected in ((1, 10), (7, 10), (8, 20), (15, 30)):
        got = doses.doses(made_up(children=10, days=days), days, u=1.0)["courses"].iloc[0]
        assert np.isclose(got, expected), f"10 children, D = {days}: {got} courses, expected {expected}"
    got = doses.doses(made_up(pregnant=5), 1, u=1.0)["amox500"].iloc[0]
    assert np.isclose(got, 30), f"5 pregnant women: {got} tablets, expected 30"
    half = doses.doses(made_up(adults=100, children=10, pregnant=5), 1, u=0.5).iloc[0]
    for col, expected in (("doxy100", 300), ("courses", 5), ("amox500", 15)):
        assert np.isclose(half[col], expected), f"u = 0.5: {col} = {half[col]}, expected {expected}"

    for label, call in (("u = 1.5", lambda: doses.doses(made_up(adults=100), 1, u=1.5)),
                        ("a missing count", lambda: doses.doses(made_up(adults=100).assign(e_child=np.nan), 1))):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError(f"{label}: doses did not stop")

    need_file(config.OVERLAY, "C2 (python -m src.overlay)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    table = exposed.load_shares()
    shown = []
    for period in config.NOAH_RETURN_PERIODS:
        residents = exposed.map_residents(overlay, period)
        for label, days, w in exposed.scenarios():
            stock = doses.barangay_doses(residents, table, days, w)
            units = stock[[*doses.DOXY_BY_TIER, *doses.UNITS]]
            assert len(stock) == config.QC_BARANGAYS, f"R({period}), {label}: {len(stock)} barangays"
            assert units.notna().all().all() and (units >= 0).all().all(), f"R({period}), {label}: missing or negative units"
            assert np.allclose(stock[doses.DOXY_BY_TIER].sum(axis=1), stock["doxy100"]), (
                f"R({period}), {label}: the doxycycline tiers do not add up to the total")
            if period == exposed.PREVIEW_MAP:
                shown.append(f"{label}: {stock['doxy100'].sum():,.0f}")
    return (f"QC doxycycline capsules at R({exposed.PREVIEW_MAP}), {'; '.join(shown)} "
            f"(stock planning, not prescriptions)")


def s10_allocate():
    """S10: allocation, and how the barangays' need reaches the health centers."""
    from src import allocation, doses, exposed

    need = pd.DataFrame({"high": [100, 50], "moderate": [40, 60], "low": [20, 0]}, index=["a", "b"])
    for stock, expected in ((180, [[100, 12, 0], [50, 18, 0]]),   # S10
                            (1000, need.to_numpy()),               # enough for everyone: exactly the need
                            (0, [[0, 0, 0], [0, 0, 0]]),
                            (120, [[80, 0, 0], [40, 0, 0]])):      # short in the high tier: shared 100 : 50
        got = allocation.allocate(need, stock)
        assert np.allclose(got.to_numpy(), expected), f"stock {stock}: got {got.to_numpy().tolist()}, expected {np.asarray(expected).tolist()}"
    for label, call in (("negative stock", lambda: allocation.allocate(need, -1)),
                        ("a missing need", lambda: allocation.allocate(need.astype(float).where(need > 0), 10))):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError(f"{label}: allocate did not stop")

    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.FACILITIES_QC, "A10 (python -m src.facilities)")
    need_file(config.WORLDPOP_SCALE_QC, "C1 (python -m src.rescale)")
    need_file(config.CENTER_SHARES, "C7 (python -m src.allocation)")
    table = allocation.load_center_shares()
    barangays = allocation.load_barangays()
    centers, _ = allocation.load_centers(barangays)

    assert set(table["psgc"]) == set(barangays["psgc"]), "the shares file and A5's barangays hold different barangays"
    assert not table.duplicated(["psgc", "facility_code"]).any(), "a barangay and health center appear twice"
    total = table.groupby("psgc")["share"].sum()
    assert np.allclose(total, 1), f"shares do not add to 1 in {list(total.index[~np.isclose(total, 1)])}"
    assert (table["share"] > 0).all(), "a share is 0 or negative"
    assert set(table["facility_code"]) <= set(centers["facility_code"]), "a health center in the file cannot be placed"
    home = centers.groupby("psgc")["facility_code"].apply(set)
    centroid = barangays.set_index("psgc").geometry.centroid
    for psgc, rows in table.groupby("psgc"):
        if psgc in home.index:
            assert set(rows["facility_code"]) == home[psgc], f"{psgc} does not send its need to its own health centers"
        else:
            assert len(rows) == 1 and (rows["rule"] == "nearest").all(), f"{psgc} has no center but is not sent to one nearest"
            distance = centers.set_index("facility_code").distance(centroid[psgc])
            assert np.isclose(distance[rows["facility_code"].iloc[0]], distance.min()), f"{psgc} is not sent to its nearest center"
    fresh = allocation.center_shares(barangays, centers)
    keys = ["psgc", "facility_code"]
    merged = table.merge(fresh, on=keys, how="outer", suffixes=("", "_fresh"), indicator=True)
    assert (merged["_merge"] == "both").all() and np.allclose(merged["share"], merged["share_fresh"]), (
        "shares file differs from a fresh run: rerun python -m src.allocation")

    need_file(config.OVERLAY, "C2 (python -m src.overlay)")
    need_file(config.SHARES_QC, "C4 (python -m src.shares)")
    residents = exposed.map_residents(pd.read_csv(config.OVERLAY, dtype={"psgc": str}), exposed.PREVIEW_MAP)
    group_shares = exposed.load_shares()
    for label, days, w in exposed.scenarios():
        stock = doses.barangay_doses(residents, group_shares, days, w)
        by_barangay = allocation.pool_needs(stock, days, w)
        by_center = allocation.center_needs(residents, group_shares, table, days, w)
        for pool in allocation.POOLS:
            assert np.allclose(by_center[pool].sum(), by_barangay[pool].sum()), (
                f"R({exposed.PREVIEW_MAP}), {label}, {pool}: the health centers' need does not add up to the barangays'")
            assert np.isclose(by_barangay[pool].to_numpy().sum(), stock[pool].sum()), f"{label}, {pool}: tiers do not add up"
    rules = table.drop_duplicates("psgc")["rule"].value_counts()
    return (f"{table['facility_code'].nunique()} health centers; barangays own {rules.get('own', 0)}, "
            f"split {rules.get('split', 0)}, nearest {rules.get('nearest', 0)} "
            f"(farthest {table['distance_km'].max():.2f} km); need adds up")


def s11_leakage():
    """S11: no model reads a count it may not see; every model forecasts every week, no NaN."""
    from src import backtest

    need_file(config.FEATURES_WEEKLY, "B4 (python -m src.features)")
    features, pop = backtest.load_features(), backtest.load_population()
    cases = backtest.simulated_cases(features, pop)
    T = weeks.week_index_of(2023, 30)
    counts = cases.set_index("week_index")["cases"]
    targets = np.arange(T - 59, T + 1)
    made_up = pd.DataFrame({"week_index": targets, "mu": 1.2 * counts.reindex(targets).to_numpy() + 1})
    for option in ("B", "C"):
        cut = view.cutoff(T, option, config.DELAY_GUARD_G)
        hidden = hide_after(cases, cut)
        assert (hidden["cases"] == config.S11_HIDDEN_COUNT).sum() == (cases["week_index"] > cut).sum() > 0, (
            f"option {option}: every count after the cutoff must be hidden, and there must be some")
        for label, past_mu in (("past", made_up), ("fit", made_up.iloc[:0])):
            past = {model: past_mu for model in backtest.MODELS}
            seen = backtest.forecast_day(T, cases, features, pop, past, option, config.DELAY_GUARD_G)
            blind = backtest.forecast_day(T, hidden, features, pop, past, option, config.DELAY_GUARD_G)
            assert list(seen["model"]) == list(backtest.MODELS), f"option {option}: models {list(seen['model'])}"
            assert (seen["theta_from"] == label).all(), f"option {option}: theta from {list(seen['theta_from'])}"
            assert seen.equals(blind), (f"option {option}, theta from {label}: a forecast changed with the counts "
                                        f"after the cutoff hidden:\n{seen.compare(blind)}")
    real = s11_real_counts(features, pop) if config.CASES_WEEKLY.exists() else "real counts not here (A13), not tested"
    runs = sorted(config.RESULTS.glob("forecasts*.csv"))
    for path in runs:
        table = pd.read_csv(path)
        scores.check_same_weeks(table)
        assert set(table["model"]) == set(backtest.MODELS) or "_partial" in path.name, f"{path.name}: models {set(table['model'])}"
        numbers = table.select_dtypes("number")
        assert not numbers.isna().any().any(), f"{path.name}: NaN in {list(numbers.columns[numbers.isna().any()])}"
    return (f"forecast day 2023 week 30, options B and C, theta from past misses and from the fit: "
            f"{len(backtest.MODELS)} models unchanged with later counts set to {config.S11_HIDDEN_COUNT}; {real}; "
            f"{len(runs)} run file(s) complete" + (f" ({', '.join(p.name for p in runs)})" if runs else ""))


def s11_real_counts(features, pop):
    """S11's hiding test on the real counts: config.S11_REAL_DAYS, option C, g = 2, 1 and 3."""
    from src import backtest

    cases = backtest.load_cases()
    tested = []
    for g in (config.DELAY_GUARD_G, *config.DELAY_GUARD_G_TESTS):
        path = backtest.output_path(False, "C", g, partial=False)
        run = pd.read_csv(path) if path.exists() else None
        for year, week in config.S11_REAL_DAYS:
            T = weeks.week_index_of(year, week)
            none = pd.DataFrame({"week_index": pd.Series(dtype=int), "mu": pd.Series(dtype=float)})
            past = {model: none if run is None else
                    run.loc[(run["forecast_week"] < T) & (run["model"] == model), ["week_index", "mu"]].reset_index(drop=True)
                    for model in backtest.MODELS}
            hidden = hide_after(cases, view.cutoff(T, "C", g))
            seen = backtest.forecast_day(T, cases, features, pop, past, "C", g)
            blind = backtest.forecast_day(T, hidden, features, pop, past, "C", g)
            assert seen.equals(blind), (f"real counts, {year} week {week}, g = {g}: a forecast changed with the "
                                        f"counts after the cutoff hidden:\n{seen.compare(blind)}")
        tested.append(f"g = {g}" + ("" if run is not None else f" (no {path.name}: theta from the fit)"))
    days = ", ".join(f"{year} week {week}" for year, week in config.S11_REAL_DAYS)
    return f"real counts at {days}, option C, {', '.join(tested)}: unchanged"


def f2_app_data():
    """The web app's data files (app/public/data/) hold the results' numbers, and every shape joins."""
    import json

    import geopandas as gpd
    import shapely

    from src import app_data, doses

    need_file(config.APP_DATA / "storms.json", "F2 (python -m src.app_data)")
    need_file(config.BARANGAYS_QC, "A5 (python -m src.census)")
    need_file(config.FACILITIES_QC, "A10 (python -m src.facilities)")
    need_file(config.CENTER_SHARES, "C7 (python -m src.allocation)")

    rerun = "rerun python -m src.app_data"

    def read(name):
        assert (config.APP_DATA / name).exists(), f"{name} is missing: {rerun}"
        with open(config.APP_DATA / name, encoding="utf-8") as f:
            return json.load(f)

    def as_written(content):
        return json.loads(json.dumps(content))   # what json makes of it: tuples become lists

    def find(items, key, value, where):
        found = [item for item in items if item[key] == value]
        assert found, f"{where} has no {key} {value!r}: {rerun}"
        return found[0]

    fresh = app_data.layer2_files()
    folder = config.APP_BARANGAY_RUNS.name
    on_disk = {f"{folder}/{path.name}" for path in config.APP_BARANGAY_RUNS.glob("*.json")}
    assert on_disk == {name for name in fresh if name.startswith(folder + "/")}, f"barangay files are not one per C9 run: {rerun}"
    for name, content in fresh.items():
        assert read(name) == as_written(content), f"{name} differs from a fresh export of the results: {rerun}"
        assert content["label"] == doses.LABEL, f"{name} lacks the not-prescriptions label"

    storms = fresh["storms.json"]
    kristine = find(storms["storms"], "storm", "kristine_2024", "storms.json")
    lead1 = find(kristine["runs"], "run", "lead 1", "Kristine in storms.json")
    short = find(lead1["floods"], "key", "D1", "Kristine's lead 1 in storms.json")
    got = (lead1["flagged"], short["exposed"], short["doxy100"], short["courses"], short["amox500"])
    assert got == (72, 789_689, 3_174_170, 254_430, 37_386), f"Kristine 1 day ahead (D = 1, w = 0.5): {got}"
    tatalon = find(fresh[lead1["file"]]["barangays"], "psgc", "1381300121", lead1["file"])
    got = (tatalon["exposed"], tatalon["pop_2024"], round(100 * tatalon["share"]), *tatalon["units"]["D1"].values())
    assert got == (36_809, 58_286, 63, 138_400, 13_463, 1_680), f"Tatalon, Kristine 1 day ahead: {got}"

    country = gpd.read_file(config.APP_DATA / config.APP_CITIES_FILE)
    assert len(country) == config.PH_CITY_COUNT and country["psgc"].is_unique, (
        f"{len(country)} cities and municipalities, expected {config.PH_CITY_COUNT} with one PSGC each: {rerun}")
    assert country["province"].notna().all() and (country["province"] != "").all(), f"a city without its province: {rerun}"
    assert set(country.loc[country["has_data"].astype(bool), "psgc"]) == {config.QC_CITY_PSGC}, "only Quezon City may have data"
    assert country.is_valid.all() and not country.is_empty.any(), f"a city outline is invalid or empty: {rerun}"
    cities = country[country["province"] == "National Capital Region"].reset_index(drop=True)
    assert len(cities) == config.NCR_CITY_COUNT, f"{len(cities)} NCR cities, expected {config.NCR_CITY_COUNT}"
    shapes = gpd.read_file(config.APP_DATA / "qc_barangays.geojson")
    a5 = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc"])
    assert len(shapes) == config.QC_BARANGAYS and set(shapes["psgc"]) == set(a5["psgc"]), "the barangay shapes do not join A5's 142"
    assert shapes.is_valid.all() and not shapes.is_empty.any(), "a barangay shape is invalid or empty after simplifying"
    flat = cities.to_crs(config.CRS_OVERLAY)
    union = flat.union_all()
    gaps = sum(len(polygon.interiors) for polygon in getattr(union, "geoms", [union]))
    overlap = flat.area.sum() - union.area
    assert flat.is_valid.all() and gaps == 0 and overlap < 1, f"NCR cities: {gaps} gaps, {overlap:,.0f} m2 of overlap: {rerun}"
    qc_city = flat.loc[flat["psgc"] == config.QC_CITY_PSGC].geometry.iloc[0]
    apart = qc_city.hausdorff_distance(shapes.to_crs(config.CRS_OVERLAY).union_all())
    assert apart < 1, f"Quezon City's outline lies up to {apart:.0f} m from its barangays' outline: {rerun}"
    labeled = country["label_lon"].notna() & country["label_lat"].notna()
    assert set(country.loc[labeled, "psgc"]) == {config.QC_CITY_PSGC}, f"only Quezon City, the city with data, gets a label point: {rerun}"
    points = gpd.points_from_xy(country.loc[labeled, "label_lon"], country.loc[labeled, "label_lat"], crs=config.CRS_LONLAT)
    outside = [name for name, shape, point in zip(country.loc[labeled, "name"], country.loc[labeled].geometry, points)
               if not shape.contains(point)]
    assert not outside, f"label points outside their city: {outside}"
    islands = gpd.read_file(config.APP_DATA / config.APP_ISLANDS_FILE).to_crs(config.CRS_OVERLAY)
    coasts = shapely.get_parts(islands.geometry.values)
    assert len(coasts) and shapely.is_valid(coasts).all() and not any(len(coast.interiors) for coast in coasts), (
        f"{config.APP_ISLANDS_FILE}: every island must be valid, with no holes: {rerun}")
    land = country.to_crs(config.CRS_OVERLAY).union_all()
    outside_coasts = land.difference(islands.union_all()).area / land.area
    added = islands.area.sum() / land.area - 1
    assert outside_coasts < 0.01 and added <= 0.02, (f"{config.APP_ISLANDS_FILE} leaves {outside_coasts:.1%} of the "
                                                     f"cities' land outside its coasts and adds {added:.1%}: {rerun}")
    for storm in storms["storms"]:
        for run in storm["runs"]:
            rows = fresh[run["file"]]["barangays"]
            assert {row["psgc"] for row in rows} == set(shapes["psgc"]), f"{run['file']}: its barangays do not join the shapes"
            assert sum(row["flagged"] for row in rows) == run["flagged"], f"{run['file']}: flagged count differs from storms.json"
            slack = 0.51 * len(rows) + 0.5
            for flood in run["floods"]:
                for name in ("exposed", *app_data.UNITS):
                    total = sum(row["exposed"] if name == "exposed" else row["units"][flood["key"]][name] for row in rows)
                    assert abs(total - flood[name]) <= slack, (f"{run['file']}, {flood['key']}: barangays add up to "
                                                               f"{total:,} {name}, storms.json says {flood[name]:,}")

    centers = fresh["centers.json"]["centers"]
    for center in centers:
        located = center["lat"] is not None and center["lon"] is not None
        assert located or center["left_out"], f"{center['name']} has no coordinates and is not listed as left out"
        assert center["gets_stock"] == (center["left_out"] is None), f"{center['name']}: gets stock, or is left out, not both"
    held = fresh["centers.json"]["barangay_centers"]
    stocked = {center["facility_code"] for center in centers if center["gets_stock"]}
    assert set(held) == set(shapes["psgc"]), f"centers.json: barangay_centers does not join the 142 barangays: {rerun}"
    for psgc, rows in held.items():
        assert rows and {row["facility_code"] for row in rows} <= stocked, f"barangay {psgc}: its health centers get no stock"
        assert abs(sum(row["share"] for row in rows) - 1) < 1e-3, f"barangay {psgc}: its centers' shares do not add up to 1"

    table, simulated, path = app_data.load_forecasts()
    forecast_path, scores_path = config.APP_DATA / "city_forecast.json", config.APP_DATA / "scores.json"
    if table is not None:
        on_disk, export = read("city_forecast.json"), as_written(app_data.city_forecast(table, simulated, path))
        if simulated:
            # M3 differs by computer, so a simulated file from another computer is compared without M3.
            for content in (on_disk, export):
                for week in content["weeks"]:
                    week["forecasts"].pop("M3", None)
        assert on_disk == export, f"city_forecast.json differs from a fresh export of {path.name}: {rerun}"
        if not simulated:
            from src import backtest
            need_file(config.CASES_WEEKLY, "A13 (python -m src.cases)")   # MASE's denominator needs the counts
            assert read("scores.json") == as_written(app_data.scores_file(table, backtest.load_cases())), (
                f"scores.json differs from a fresh export of {path.name}: {rerun}")
    if forecast_path.exists():
        forecast = read("city_forecast.json")
        assert scores_path.exists() == (not forecast["simulated"]), "scores.json must sit beside a real run only"
        levels = [{"level": level, "from": start} for level, start in config.APP_LEVELS]
        assert forecast.get("map_model") == config.APP_LEVEL_MODEL and forecast.get("levels") == levels, (
            f"city_forecast.json lacks the map's model and outbreak levels from config.py: {rerun}")
        layer1 = f"city_forecast.json {'SIMULATED' if forecast['simulated'] else 'real'}, {len(forecast['weeks'])} weeks"
    else:
        layer1 = "no city_forecast.json yet"
    left_out = sum(bool(center["left_out"]) for center in centers)
    return (f"{len(fresh)} files equal a fresh export; Kristine 1 day ahead and Tatalon as the plan; {len(country):,} "
            f"cities (NCR's 17 a clean coverage) and 142 barangays join; Quezon City's label inside it; {len(coasts)} "
            f"islands' coasts hold all but {outside_coasts:.1%} of the land; {len(centers) - left_out} centers "
            f"get stock, {left_out} left out and listed; {len(held)} barangays name their centers; {layer1}")


PERSON_COLUMNS = {   # columns of a person's record; no tracked table may have one
    # Not a bare "name": results tables use it for a model's or a comparison's name
    "full_name", "first_name", "last_name", "patient", "patient_name", "patient_id",
    "case_id", "age", "sex", "gender", "address", "birthdate", "birth_date", "date_of_birth",
    "onset", "onset_date", "date_onset", "contact", "phone",
    # QCESD's case list columns, lower-cased; District and Barangay are left out (aggregated tables use them).
    "year_of_onset", "date_of_onset", "morbidity_week", "date_of_admission", "admission_date",
}


def e10_package():
    """What the code package ships."""
    import ast
    import re
    import subprocess
    from importlib import metadata

    def norm(name):
        return re.sub(r"[-_.]+", "-", name).lower()

    pins, bad = {}, []
    for line in (config.ROOT / "requirements.txt").read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==(\S+)", line)
        if not match:
            bad.append(f"not pinned with ==: {line}")
            continue
        pins[norm(match[1])] = match[2]
        try:
            installed = metadata.version(match[1])
        except metadata.PackageNotFoundError:
            installed = "not installed"
        if installed != match[2]:
            bad.append(f"{match[1]}: requirements.txt pins {match[2]}, this computer has {installed}")

    # Read the import statements themselves (ast), so a docstring line starting "from ..." is not one
    sources = sorted((config.ROOT / "src").glob("*.py")) + [config.ROOT / "config.py"]
    imported = set()
    for path in sources:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imported.add(node.module.split(".")[0])
    by_import = metadata.packages_distributions()
    for name in sorted(imported - set(sys.stdlib_module_names) - {"src", "config"}):
        dists = [norm(dist) for dist in by_import.get(name, [])]
        if not any(dist in pins for dist in dists):
            bad.append(f"src/ imports {name}, which is not in requirements.txt"
                       + ("" if dists else " (not installed either)"))
    assert not bad, "; ".join(bad) + ". Fix: pip install -r requirements.txt, or pin the package"

    listed = subprocess.run(["git", "ls-files"], cwd=config.ROOT, capture_output=True, text=True)
    if listed.returncode != 0:
        return f"{len(pins)} packages pinned and installed; not a git checkout, so tracked files not checked"
    tracked = listed.stdout.splitlines()
    data_files = [path for path in tracked if path.startswith("data/")
                  and not path.endswith(".md") and not path.endswith(".gitkeep")]
    assert not data_files, f"git tracks data files (share them through the team drive): {data_files}"
    tables = [path for path in tracked if path.endswith(".csv")]
    for path in tables:
        columns = {str(col).strip().lower() for col in pd.read_csv(config.ROOT / path, nrows=0).columns}
        person = sorted(columns & PERSON_COLUMNS)
        assert not person, f"{path} has columns of a person's record: {person} (rule 11)"
    return (f"{len(pins)} packages pinned and installed; {len(tracked)} tracked files, none under data/ "
            f"but notes; {len(tables)} tracked tables, no person columns")


def f9_scores():
    """The scores Compare models shows (scores.json) equal the figure 2 table."""
    import json

    need_file(config.FORECASTS, "B10 (python -m src.backtest, after A13)")
    need_file(config.APP_DATA / "scores.json", "F2 (python -m src.app_data)")
    need_file(config.D8_FIG2_TABLE, "D8 (python -m src.paper_figures)")
    rerun = "rerun python -m src.app_data and python -m src.paper_figures on the same forecasts.csv"
    tolerance = 1e-4   # one unit in the 4th decimal, the rounding of both files

    with open(config.APP_DATA / "scores.json", encoding="utf-8") as f:
        app = json.load(f)
    fig2 = pd.read_csv(config.D8_FIG2_TABLE)
    by_model = fig2[fig2["part"] == "MAE by model"].set_index("name")["value"]
    assert set(by_model.index) == set(app["models"]), (
        f"models differ: d8_fig2_mae.csv has {sorted(by_model.index)}, scores.json {sorted(app['models'])}: {rerun}")
    for model, mae in by_model.items():
        assert abs(app["models"][model]["mae"] - mae) <= tolerance, (
            f"{model}: scores.json MAE {app['models'][model]['mae']}, d8_fig2_mae.csv {mae}: {rerun}")

    comparison = " vs ".join(config.PRIMARY_COMPARISON)
    rows = fig2[(fig2["name"] == comparison) & (fig2["block_weeks"] == config.BOOT_BLOCK_WEEKS)]
    assert len(rows) == 1, f"d8_fig2_mae.csv has {len(rows)} rows for {comparison} with {config.BOOT_BLOCK_WEEKS}-week blocks"
    head, primary = rows.iloc[0], app["primary"]
    assert primary["comparison"] == comparison and primary["block_weeks"] == config.BOOT_BLOCK_WEEKS, (
        f"scores.json's primary result is {primary['comparison']} with {primary['block_weeks']}-week blocks: {rerun}")
    for key, column in (("mean_diff", "value"), ("low", "low"), ("high", "high")):
        assert abs(primary[key] - head[column]) <= tolerance, (
            f"{comparison} {key}: scores.json {primary[key]}, d8_fig2_mae.csv {head[column]}: {rerun}")
    assert primary["weeks"] == head["weeks"] and primary["verdict"] == head["verdict"], (
        f"{comparison}: scores.json {primary['weeks']} weeks, {primary['verdict']!r}; "
        f"d8_fig2_mae.csv {head['weeks']} weeks, {head['verdict']!r}: {rerun}")
    return (f"{len(by_model)} models' MAE and {comparison} ({primary['mean_diff']:+.2f}, 95% interval "
            f"{primary['low']:+.2f} to {primary['high']:+.2f}) equal d8_fig2_mae.csv")


def e6_score_tables():
    """The score tables (src/score_tables.py) agree with the forecasts and the figure tables."""
    need_file(config.FORECASTS, "B10 (python -m src.backtest, after A13)")
    need_file(config.D8_FIG2_TABLE, "D8 (python -m src.paper_figures)")
    need_file(config.D8_FIG3_TABLE, "D8 (python -m src.paper_figures)")
    for path in (config.D_SCORES, config.D_TESTS_ALL_YEARS):
        need_file(path, "E6's score tables (python -m src.score_tables)")
    rerun = "rerun python -m src.paper_figures and python -m src.score_tables on the same forecasts.csv"
    tolerance = 1e-4   # one unit in the 4th decimal, the rounding of every file

    forecasts = pd.read_csv(config.FORECASTS, usecols=["model", "week_index", "year"])
    table = pd.read_csv(config.D_SCORES)
    windows = {"MAE years": config.MAE_YEARS, "prob years": config.PROB_SCORE_YEARS, "all years": config.ALL_YEARS}
    for window, years in windows.items():
        expected = forecasts.loc[forecasts["year"].isin(years), "week_index"].nunique()
        found = set(table.loc[table["window"] == window, "weeks"])
        assert found == {expected}, f"{window}: d1_scores.csv has weeks {found}, forecasts.csv {expected}: {rerun}"

    point = table[table["window"] == "MAE years"].set_index("model")["mae"]
    fig2 = pd.read_csv(config.D8_FIG2_TABLE)
    by_model = fig2[fig2["part"] == "MAE by model"].set_index("name")["value"]
    assert set(point.index) == set(by_model.index), f"models differ from d8_fig2_mae.csv: {rerun}"
    for model, mae in by_model.items():
        assert abs(point[model] - mae) <= tolerance, f"{model}: MAE {point[model]}, d8_fig2_mae.csv {mae}: {rerun}"

    brier = table[table["window"] == "prob years"].set_index("model")["brier"]
    fig3 = pd.read_csv(config.D8_FIG3_TABLE).drop_duplicates("model").set_index("model")["brier"]
    for model, value in fig3.items():
        assert abs(brier[model] - value) <= tolerance, f"{model}: Brier {brier[model]}, d8_fig3_reliability.csv {value}: {rerun}"

    all_years = pd.read_csv(config.D_TESTS_ALL_YEARS)
    weeks_all = forecasts.loc[forecasts["year"].isin(config.ALL_YEARS), "week_index"].nunique()
    assert set(all_years["weeks"]) == {weeks_all}, f"d5_d6_all_years.csv weeks {set(all_years['weeks'])}, not {weeks_all}: {rerun}"
    return (f"{len(point)} models' MAE equal d8_fig2_mae.csv and {len(fig3)} Brier scores d8_fig3_reliability.csv; "
            f"windows of {', '.join(str(int(table.loc[table['window'] == w, 'weeks'].iloc[0])) for w in windows)} weeks")


def f14_noah_tiles():
    """The map's NOAH tiles (app/public/data/noah_flood_<T>yr.pmtiles) cover the whole country."""
    import struct

    import pandas as pd

    rerun = "rerun python -m src.noah_national"
    lines = []
    manifest_path = config.NOAH_NATIONAL_CLEAN / "manifest.csv"
    manifest = pd.read_csv(manifest_path) if manifest_path.exists() else None
    for t in config.NOAH_RETURN_PERIODS:
        path = config.APP_DATA / config.APP_NOAH_TILES.format(return_period=t)
        need_file(path, "F14 (python -m src.noah_national)")
        size = path.stat().st_size
        assert size <= config.APP_NOAH_TILES_MAX_BYTES, f"{path.name} is {size / 1e6:.0f} MB, over GitHub's limit"
        with open(path, "rb") as f:
            header = f.read(127)
        assert header[:7] == b"PMTiles" and header[7] == 3, f"{path.name} is not a PMTiles v3 file: {rerun}"
        tile_type, min_zoom, max_zoom = header[99], header[100], header[101]
        west, south, east, north = (v / 1e7 for v in struct.unpack_from("<4i", header, 102))
        assert tile_type == 1, f"{path.name} holds tile type {tile_type}, not vector tiles (1)"
        assert (min_zoom, max_zoom) == tuple(config.NOAH_TILE_ZOOMS), (
            f"{path.name}: zooms {min_zoom}-{max_zoom}, config says {config.NOAH_TILE_ZOOMS}: {rerun}")
        reach_west, reach_south, reach_east, reach_north = config.APP_NOAH_TILES_REACH
        assert west <= reach_west and south <= reach_south and east >= reach_east and north >= reach_north, (
            f"{path.name} reaches only {west:.2f}-{east:.2f} E, {south:.2f}-{north:.2f} N: not the whole country: {rerun}")
        if manifest is not None:
            rows = manifest[manifest["return_period"] == t]
            empty_at_source = rows["features"].eq(0) if "features" in rows else rows["shapefiles"].eq(0)
            lost = rows.loc[(rows["patches"] == 0) & ~empty_at_source, "province"].tolist()
            assert len(rows) and not lost, f"{t}-year map: no flood patches kept for {lost}, though NOAH's files have shapes"
            lines.append(f"{t}-year {len(rows)} provinces, {size / 1e6:.0f} MB")
        else:
            lines.append(f"{t}-year {size / 1e6:.0f} MB")
    return "; ".join(lines)


def f14_simulation():
    """The map's Simulation mode (app/public/data/city_simulation.json) follows the real weeks."""
    import json
    from datetime import date

    from src import app_simulation, backtest, weeks

    path = config.APP_DATA / config.APP_SIMULATION_FILE
    need_file(path, "F14 (python -m src.app_simulation)")
    rerun = "rerun python -m src.app_simulation"
    with open(path, encoding="utf-8") as f:
        simulation = json.load(f)
    with open(config.APP_DATA / "city_forecast.json", encoding="utf-8") as f:
        real = json.load(f)
    made_on = date.fromisoformat(simulation["made_on"])
    this_week = weeks.week_index(made_on)
    indexes = [week["week_index"] for week in simulation["weeks"]]
    first = real["weeks"][-1]["week_index"] + 1
    assert indexes == list(range(first, this_week + 2)), (
        f"simulated weeks {indexes[0]}-{indexes[-1]}, expected {first}-{this_week + 1} (made on {made_on}): {rerun}")
    assert simulation["weather"]["fetched_on"] == simulation["made_on"], "the ECMWF rain is from another day than made_on"
    for week in simulation["weeks"]:
        assert set(week["forecasts"]) == set(backtest.MODELS), f"week {week['week_index']}: models {sorted(week['forecasts'])}"
        ended = week["week_index"] < this_week
        assert (week["y"] is not None) == ended, f"week {week['week_index']}: a count only for the weeks ended by {made_on}"
        assert not week["simulated_y"] or week["y"] is not None, f"week {week['week_index']}: simulated, but no count"
        assert week["y"] is None or (isinstance(week["y"], int) and week["y"] >= 0), f"week {week['week_index']}: count {week['y']}"
    try:
        without_m3 = [model for model in backtest.MODELS if model != "M3"]
        fresh = (json.loads(json.dumps(app_simulation.simulation_file(made_on, fetch=False, models=without_m3)[0]))
                 if config.FORECASTS.exists() else None)
    except FileNotFoundError:   # that day's ECMWF reply is not on this computer: a past day is never fetched again
        fresh = None
    if fresh is not None:
        for content in (fresh, simulation):
            for week in content["weeks"]:
                week["forecasts"].pop("M3", None)
        assert fresh == simulation, f"city_simulation.json differs from a fresh run for {made_on}: {rerun} --day {made_on}"
        return f"{len(indexes)} weeks to {simulation['weeks'][-1]['start']}, equal to a fresh run for {made_on}"
    return f"{len(indexes)} weeks to {simulation['weeks'][-1]['start']} (no fresh run: B10's forecasts or the ECMWF reply are not here)"


def f16_daily_plans():
    """Every date the app's map shows has a prophylaxis plan (app/public/data/days/), made as the runs are."""
    import json
    from datetime import timedelta

    from src import app_days, doses, forecast_run

    need_file(config.APP_DAYS / f"{config.BACKTEST_FIRST_YEAR}.json", "F16 (python -m src.app_days)")
    rerun = "rerun python -m src.app_days"

    def read(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    years = {int(path.stem): read(path) for path in sorted(config.APP_DAYS.glob("*.json"))}
    plans = [day for year in sorted(years) for day in years[year]["days"]]
    for year, content in years.items():
        assert content["label"] == doses.LABEL, f"days/{year}.json lacks the not-prescriptions label"
        assert all(day["start_date"].startswith(str(year)) for day in content["days"]), f"days/{year}.json holds another year's day"
    starts = [date.fromisoformat(day["start_date"]) for day in plans]
    assert all(b - a == timedelta(days=1) for a, b in zip(starts, starts[1:])), f"the daily plans skip or repeat a day: {rerun}"

    # The map's dates (forecast.ts, dateRange): from the first target week back one forecast horizon, to the last's Saturday
    real = read(config.APP_DATA / "city_forecast.json")
    weeks_shown = real["weeks"] + read(config.APP_DATA / config.APP_SIMULATION_FILE)["weeks"]
    lead = timedelta(days=config.DAYS_PER_WEEK * real["horizon_weeks"])
    first_shown = date.fromisoformat(weeks_shown[0]["start"]) - lead
    last_shown = date.fromisoformat(weeks_shown[-1]["start"]) - lead + timedelta(days=config.DAYS_PER_WEEK - 1)
    assert starts[0] <= first_shown and last_shown <= starts[-1], (
        f"the plans run {starts[0]} to {starts[-1]}; the map shows {first_shown} to {last_shown}: {rerun} "
        "on the day python -m src.app_simulation was run")

    centers = read(config.APP_DATA / "centers.json")
    stocked = {center["facility_code"] for center in centers["centers"] if center["gets_stock"]}
    no_flood = app_days.data_name(config.APP_DAY_RUNS / "no_flood.json")
    files = {name: read(config.APP_DATA / name) for name in
             [no_flood] + [app_days.data_name(path) for path in config.APP_DAY_RUNS.glob("*.json") if path.name != "no_flood.json"]}
    assert all(content["label"] == doses.LABEL for content in files.values()), "a barangay file lacks the not-prescriptions label"
    assert len(files[no_flood]["barangays"]) == config.QC_BARANGAYS and not any(
        barangay["exposed"] or any(any(units.values()) for units in barangay["units"].values())
        for barangay in files[no_flood]["barangays"]), "no_flood.json must have every barangay at 0"

    pointed = set()
    exposing = 0
    first_forecast = None   # the first day with a forecast: no day after it may fall back on the rain that fell
    for day in plans:
        runs = day["runs"]
        observed = [run for run in runs if run["lead_days"] is None]
        assert runs and (observed == runs or not observed), f"{day['storm']}: forecasts and the rain that fell, or no run"
        if observed:
            assert first_forecast is None, f"{day['storm']}: the rain that fell after {first_forecast}, inside ECMWF's archive"
        elif first_forecast is None:
            first_forecast = day["start_date"]
            assert date.fromisoformat(first_forecast) >= config.FORECAST_ARCHIVE_START, f"a forecast before the archive: {first_forecast}"
        needs = years[int(day["start_date"][:4])]["needs"].get(day["storm"], {})
        for run in runs:
            pointed.add(run["file"])
            people = [flood["exposed"] for flood in run["floods"]]
            if run["file"] == no_flood:
                assert not any(flood[key] for flood in run["floods"] for key in ("exposed", *doses.UNITS)), (
                    f"{day['storm']}, {run['run']}: numbers, but no barangay file")
                assert run["run"] not in needs, f"{day['storm']}, {run['run']}: a need, but nobody exposed"
                continue
            exposing += 1
            assert all(people), f"{day['storm']}, {run['run']}: a barangay file, but nobody exposed: {rerun}"
            barangays = files[run["file"]]["barangays"]
            assert len(barangays) == config.QC_BARANGAYS, f"{run['file']}: {len(barangays)} barangays"
            for flood in run["floods"]:
                for key in ("exposed", *doses.UNITS):
                    total = sum(b["exposed"] if key == "exposed" else b["units"][flood["key"]][key] for b in barangays)
                    assert abs(total - flood[key]) <= 0.5 * len(barangays), (
                        f"{run['file']}: {key} in {flood['key']} adds to {total}, the run says {flood[key]}")
                assert set(needs[run["run"]][flood["key"]]) == stocked, (
                    f"{day['storm']}, {run['run']}, {flood['key']}: needs for other centers than C7 stocks")
    assert pointed == set(files), f"barangay files no run points to, or runs pointing to no file: {rerun}"

    # Against the storm runs: a storm forecast is the day plan of its window's first day, at its lead
    by_start = {day["start_date"]: day for day in plans}
    storms = read(config.APP_DATA / "storms.json")
    matched = 0
    for storm in storms["storms"]:
        for run in storm["runs"]:
            if run["lead_days"] is None:
                continue
            day = by_start[run["window"]["start"]]
            found = [each for each in day["runs"] if each["lead_days"] == run["lead_days"]]
            where = f"{storm['storm']}, {run['run']}"
            assert found, f"{where}: no day plan for {run['window']['start']} at that lead"
            mine = found[0]
            assert {**mine, "file": run["file"]} == run, f"{where} differs from {day['storm']}'s: {rerun}"
            if mine["file"] != no_flood:
                assert files[mine["file"]]["barangays"] == read(config.APP_DATA / run["file"])["barangays"], (
                    f"{where}: barangays differ from {mine['file']}")
            want = centers["needs"][storm["storm"]][run["run"]]
            got = years[int(day["start_date"][:4])]["needs"].get(day["storm"], {}).get(mine["run"])
            if got is None:
                assert not any(any(units.values()) for need in want.values() for units in need.values()), (
                    f"{where}: centers.json has needs, the day plan none")
            else:
                assert got == want, f"{where}: needs per health center differ from centers.json's"
            matched += 1
    expected = len(storms["storms"]) * len(config.FORECAST_LEADS_DAYS)
    assert matched == expected, f"{matched} storm forecasts matched, expected {expected} (every storm at leads 1-3)"

    made_on = date.fromisoformat(years[max(years)]["made_on"])
    note = f"{len(plans)} days to {starts[-1]}, {exposing} runs expose anyone, {matched} storm forecasts as C9"
    if app_days.saved_reply(made_on) is None:   # a past day is never fetched again: only its saved reply makes it again
        return note + f" (no fresh run: the archive reply saved on {made_on} is not here)"
    fresh, _ = app_days.days_files(made_on, fetch=False)
    on_disk = {**{f"days/{year}.json": content for year, content in years.items()}, **files}
    assert set(fresh) == set(on_disk), f"the files differ from a fresh run for {made_on}: {rerun} --day {made_on}"
    for name, content in fresh.items():
        assert json.loads(json.dumps(content)) == on_disk[name], f"{name} differs from a fresh run for {made_on}: {rerun} --day {made_on}"
    return note + f", equal to a fresh run for {made_on}"


CHECKS = {
    "S1 calendar": s1_calendar,
    "S2 rain file": s2_rain_file,
    "S3 census join": s3_census,
    "A11 storm facts": a11_storms,
    "S4 cases file": s4_cases,
    "S5 M4 simulation": s5_m4,
    "S6 theta": s6_theta,
    "S7 breach": s7_breach,
    "S7 scores": s7_scores,
    "D4 lead time": d4_lead_time,
    "D2 MASE": d2_mase,
    "D5 primary endpoint": d5_primary_endpoint,
    "D6 flood test": d6_flood_test,
    "B8 M0 and M1": b8_baselines,
    "B9 M3": b9_m3,
    "S8 census fit": s8_census_fit,
    "S8 overlay": s8_overlay,
    "S9 return levels": s9_return_levels,
    "S9 exposure index": s9_exposure_index,
    "S10 shares": s10_shares,
    "S10 exposed": s10_exposed,
    "S10 doses": s10_doses,
    "S10 allocate": s10_allocate,
    "B2 view": b2_view,
    "S11 leakage": s11_leakage,
    "F2 app data": f2_app_data,
    "F9 scores": f9_scores,
    "E6 score tables": e6_score_tables,
    "F14 NOAH tiles": f14_noah_tiles,
    "F14 simulation": f14_simulation,
    "F16 daily plans": f16_daily_plans,
    "E10 package": e10_package,
}


def main():
    """Run every check, print PASS / SKIP / FAIL, and return the exit code."""
    if not __debug__:   # python -O strips every assert, so each check would pass without testing anything
        sys.exit("run the checks without -O: they are asserts")
    failed = 0
    for name, check in CHECKS.items():
        try:
            detail = check()
            print(f"PASS  {name}" + (f" ({detail})" if detail else ""))
        except NotBuilt as e:
            print(f"SKIP  {name} ({e})")
        except Exception as e:
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

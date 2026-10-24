"""Layer 2 on observed rain: the storm runs."""

import pandas as pd
from scipy import stats

import config
from src import allocation, doses, exposed, flood_exposure, forecast_run

N_DAYS = config.RAIN_ACCUM_DAYS
MAIN = "main run"
KEYS = ["storm", "test", "flood", "D", "cutoff", "w"]   # one run of the exposure, dose and allocation steps; the key of every output row
PEOPLE = ["exposed", *exposed.GROUPS, *exposed.TIERS]   # exposed, e_child, e_preg, e_adult, high, moderate, low
FLAG_TAGS = [f"{100 * share:.0f}" for share in config.FLAG_EXPOSED_SHARES]   # "25", "50"
BARANGAY_COLUMNS = [*KEYS, "psgc", "adm4_name", "pop_2024", "residents", "share_in_flood_zones",
                    *[f"flagged_{tag}" for tag in FLAG_TAGS], "listed_flooded", *PEOPLE, *doses.UNITS]
CENTER_COLUMNS = [*KEYS, "pool", "facility_code", "facility_name", *exposed.TIERS]
INPUTS = {                                              # the files this step reads, and the task that makes each
    config.IMERG_DAILY: "A4: python -m src.imerg",
    config.CATCHMENTS: "A7: python -m src.catchments",
    config.CENSUS_QC: "A5: python -m src.census",
    config.OVERLAY: "C2: python -m src.overlay",
    config.SHARES_QC: "C4: python -m src.shares",
    config.CENTER_SHARES: "C7: python -m src.allocation",
}


def check_inputs():
    """Stop with one clear message that lists every input file not on this computer."""
    missing = [f"  {path}  ({task})" for path, task in INPUTS.items() if not path.exists()]
    if missing:
        raise SystemExit("C8 needs these files; run their task or copy them from the team drive:\n"
                         + "\n".join(missing))


def observed_rain(totals, facts):
    """The storm's wettest n-day IMERG total whose last day falls during the flood: (mm, last day)."""
    days = pd.date_range(facts["start_date"], facts["end_date"], freq="D")
    missing = days.difference(totals.index)
    if len(missing):
        raise ValueError(f"IMERG has no {N_DAYS}-day total for {len(missing)} flood days, "
                         f"first {missing[0]:%Y-%m-%d}: rerun python -m src.imerg")
    return flood_exposure.storm_peak(totals, facts["start_date"], facts["end_date"])


def return_period(rain, levels):
    """T = 1 / (1 - F(rain)): IMERG sees an n-day total this big about once every T years."""
    return 1 / stats.gumbel_r.sf(rain, loc=levels["mu"], scale=levels["beta"])


def share_of_way(rain, levels):
    """How far an n-day total lies from the level below it to the level above it: 0 to 1."""
    anchors = [levels["r0"]] + [levels[p] for p in flood_exposure.RETURN_PERIODS]
    for low, high in zip(anchors, anchors[1:]):
        if low <= rain < high:
            return (rain - low) / (high - low)
    return None


def rain_columns(facts, rain, end, levels, residents, shares, qc_total):
    """The columns of a storm's runs that do not depend on D, the cut-off or w."""
    start = end - pd.Timedelta(days=N_DAYS - 1)
    flooded = facts["flooded_psgc"]
    row = {"window": f"{start:%Y-%m-%d} to {end:%Y-%m-%d}", "rain_mm": rain,
           "levels_years": levels["n_years"], "mu": levels["mu"], "beta": levels["beta"],
           "r0": levels["r0"], "r5": levels[5], "r25": levels[25], "r100": levels[100],
           "position": forecast_run.position(rain, levels), "share_of_way": share_of_way(rain, levels),
           "return_period": return_period(rain, levels),
           "ei_pct": 100 * residents["residents"].sum() / qc_total,   # rule 7: QC's 2024 total
           "listed_flooded": len(flooded)}
    for share, tag in zip(config.FLAG_EXPOSED_SHARES, FLAG_TAGS):
        scores = forecast_run.flag_scores(forecast_run.flagged(residents, shares, share), flooded)
        row.update({f"{name}_{tag}": value for name, value in scores.items()})
    return row


def tests(flood_days):
    """(test, D, cut-off) for one storm: the main run, then the reruns, each changing one thing."""
    cutoff = config.CONTINUOUS_EXPOSURE_DAYS
    out = [(MAIN, flood_days, cutoff)]
    for test_cutoff in config.CONTINUOUS_EXPOSURE_DAYS_TESTS:
        out.append((f"cut-off {test_cutoff} day{'' if test_cutoff == 1 else 's'}", flood_days, test_cutoff))
    step = config.STORM_D_TEST_DAYS
    if flood_days - step >= 1:
        out.append((f"D - {step}", flood_days - step, cutoff))
    out.append((f"D + {step}", flood_days + step, cutoff))
    return out


def scenarios(flood_days, cutoff):
    """(label, D, w) for one flood duration and cut-off."""
    if flood_days >= cutoff:
        return [(f"D = {flood_days} (any w)", flood_days, config.WOUND_SHARE_W[0])]
    return [(f"D = {flood_days}, w = {w:g}", flood_days, w) for w in config.WOUND_SHARE_W]


def barangay_rows(stock, residents, shares, flooded_psgc, keys):
    """The main run per barangay: residents in flood zones, flagged, listed, the people and the units."""
    out = shares[["adm4_name", "pop_2024"]].join(residents.groupby("psgc")["residents"].sum())
    out["share_in_flood_zones"] = out["residents"] / out["pop_2024"]
    for share, tag in zip(config.FLAG_EXPOSED_SHARES, FLAG_TAGS):
        out[f"flagged_{tag}"] = out.index.isin(forecast_run.flagged(residents, shares, share))
    out["listed_flooded"] = out.index.isin(flooded_psgc)
    out = out.join(stock[[*PEOPLE, *doses.UNITS]])
    if len(out) != config.QC_BARANGAYS or out[["residents", *PEOPLE]].isna().any().any():
        raise ValueError(f"the barangay table needs all {config.QC_BARANGAYS} barangays with no missing count")
    return out.reset_index().assign(**keys)


def center_rows(residents, shares, center_table, flood_days, w, cutoff, keys):
    """The main run's need per health center and pool, by tier, with the center's name."""
    names = center_table.drop_duplicates("facility_code").set_index("facility_code")["facility_name"]
    needs = allocation.center_needs(residents, shares, center_table, flood_days, w, cutoff)
    return pd.concat([need.join(names).reset_index().assign(pool=pool, **keys) for pool, need in needs.items()])


def storm_tables(storm, facts, rain, end, levels, overlay, shares, center_table, qc_total):
    """Every run of one storm at its observed rain: (run rows, barangay rows, center rows)."""
    residents = flood_exposure.graded_exposure(rain, levels, overlay)
    rain_row = rain_columns(facts, rain, end, levels, residents, shares, qc_total)
    runs, barangays, centers = [], [], []
    for test, flood_days, cutoff in tests(facts["D"]):
        for label, days, w in scenarios(flood_days, cutoff):
            keys = {"storm": storm, "test": test, "flood": label, "D": days, "cutoff": cutoff, "w": w}
            stock = doses.barangay_doses(residents, shares, days, w, cutoff)
            totals = stock[[*PEOPLE, *doses.DOXY_BY_TIER, *doses.UNITS]].sum().to_dict()
            runs.append({**keys, **rain_row, **totals, "label": doses.LABEL})
            if test == MAIN:
                barangays.append(barangay_rows(stock, residents, shares, facts["flooded_psgc"], keys))
                centers.append(center_rows(residents, shares, center_table, days, w, cutoff, keys))
    return runs, barangays, centers


def print_table(table, **formats):
    """Print a table indented by 2 spaces, without its index."""
    print("  " + table.to_string(index=False, **formats).replace("\n", "\n  "))


def report_flags(runs, barangays):
    """Print the flag shares per storm, and the barangays flagged and listed, to check by eye."""
    by_storm = runs[runs["test"] == MAIN].drop_duplicates("storm")
    cols = ["storm", "listed_flooded"] + [f"{name}_{tag}" for tag in FLAG_TAGS
                                          for name in ("flagged", "share_flagged_listed", "share_listed_flagged")]
    print(f"\n2. Flagged versus flooded (flagged: at least {' / '.join(t + '%' for t in FLAG_TAGS)} of a "
          f"barangay's residents in zones the rain floods; listed: A11's flooded barangays):")
    print_table(by_storm[cols].round(2))
    tag = FLAG_TAGS[0]
    print(f"  at {tag}%, flagged (* = listed) and listed but not flagged:")
    for storm, rows in barangays.drop_duplicates(["storm", "psgc"]).groupby("storm", sort=False):
        hit = rows[rows[f"flagged_{tag}"]]
        missed = rows[rows["listed_flooded"] & ~rows[f"flagged_{tag}"]]
        flagged_names = [f"{name}{'*' if listed else ''}" for name, listed in zip(hit["adm4_name"], hit["listed_flooded"])]
        print(f"  {storm}: flagged {', '.join(flagged_names) or 'none'}")
        print(f"  {' ' * len(storm)}  not flagged {', '.join(missed['adm4_name']) or 'none'}")


def report_centers(centers):
    """Print, per storm and flood, how many health centers get stock and which needs the most doxycycline."""
    doxy = centers[centers["pool"] == "doxy100"]
    doxy = doxy.assign(units=doxy[exposed.TIERS].sum(axis=1))
    print("  health centers (C7; units rounded up):")
    for (storm, label), rows in doxy.groupby(["storm", "flood"], sort=False):
        top = rows.loc[rows["units"].idxmax()]
        print(f"  {storm}, {label}: {(rows['units'] > 0).sum()} centers get doxycycline; the most, "
              f"{top['facility_name']}: {allocation.round_up(pd.Series([top['units']])).iloc[0]:,.0f} capsules")


def report(runs, barangays, centers):
    """Print the three results (where the storms fall, flagged versus flooded, doses) and the tests."""
    main_runs = runs[runs["test"] == MAIN]
    print(f"C8 on observed rain: each storm's wettest {N_DAYS}-day IMERG total over the catchments, on "
          f"IMERG's return levels fitted on the years before the storm's year")
    print(f"\n1. Where each storm falls (mm per {N_DAYS} UTC days; share = how far from the level below to the "
          f"level above; T = the rain's return period in years; EI = % of QC residents in zones it floods):")
    cols = ["storm", "window", "rain_mm", "levels_years", "r0", "r5", "r25", "r100",
            "position", "share_of_way", "return_period", "ei_pct"]
    print_table(main_runs.drop_duplicates("storm")[cols].round(2))

    report_flags(runs, barangays)

    print(f"\n3. Doses, main run (A11's D, cut-off {config.CONTINUOUS_EXPOSURE_DAYS} days; full coverage, "
          f"q = u = 1). {doses.LABEL}")
    print_table(main_runs[["storm", "flood", "exposed", *doses.UNITS]], float_format="{:,.0f}".format)
    report_centers(centers)

    print(f"\n4. Tests, QC's units (cut-off at {' and '.join(map(str, config.CONTINUOUS_EXPOSURE_DAYS_TESTS))} "
          f"days; A11's D +/- {config.STORM_D_TEST_DAYS}). {doses.LABEL}")
    print_table(runs[["storm", "test", "flood", "cutoff", *exposed.TIERS, *doses.UNITS]], float_format="{:,.0f}".format)
    print("\n  " + "\n  ".join(f"{col}: {what}" for col, what in doses.UNITS.items()))
    print(f"\n{doses.LABEL}")


def main():
    check_inputs()
    totals = flood_exposure.n_day_totals(flood_exposure.catchment_rain(), N_DAYS)
    maxima = flood_exposure.annual_maxima(totals)
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    shares = exposed.load_shares()
    if len(shares) != config.QC_BARANGAYS:
        raise ValueError(f"{config.SHARES_QC.name} has {len(shares)} barangays, expected {config.QC_BARANGAYS}")
    center_table = allocation.load_center_shares()
    census = pd.read_csv(config.CENSUS_QC, dtype={"psgc": str})
    qc_total = float(census["pop_2024"].sum())   # EI over QC's 2024 total from the same maps

    tables = ([], [], [])
    for storm, facts in config.STORMS.items():
        rain, end = observed_rain(totals, facts)
        levels = flood_exposure.return_levels(maxima, facts["year"])   # IMERG's, years before the storm's
        for part, rows in zip(tables, storm_tables(storm, facts, rain, end, levels, overlay,
                                                   shares, center_table, qc_total)):
            part.extend(rows)

    runs = pd.DataFrame(tables[0])
    barangays = pd.concat(tables[1], ignore_index=True)[BARANGAY_COLUMNS].assign(label=doses.LABEL)   # rule 10
    centers = pd.concat(tables[2], ignore_index=True)[CENTER_COLUMNS].assign(label=doses.LABEL)
    report(runs, barangays, centers)
    forecast_run.write(runs.round(4), config.C8_RUNS)
    forecast_run.write(barangays.round(2).assign(share_in_flood_zones=barangays["share_in_flood_zones"].round(4)),
                       config.C8_BARANGAYS)
    forecast_run.write(centers.round(2), config.C8_CENTERS)
    print(f"\nwrote {config.C8_RUNS} ({len(runs)} rows), {config.C8_BARANGAYS} ({len(barangays)} rows), "
          f"{config.C8_CENTERS} ({len(centers)} rows)")


if __name__ == "__main__":
    main()

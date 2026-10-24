"""Exposed people per barangay and group, and the adult risk tiers."""

import pandas as pd

import config
from src.shares import SHARES

GROUPS = {"e_child": "s_child", "e_preg": "s_preg", "e_adult": "s_adult"}  # E_{b,g} -> s^g_b
TIERS = ["high", "moderate", "low"]
PREVIEW_MAP = 25    # map whose barangays the script prints
SHOW = 5            # barangays printed, to inspect


def load_shares():
    """The table, one row per barangay (index psgc), with s_child, s_preg, s_adult and pop_2024."""
    return pd.read_csv(config.SHARES_QC, dtype={"psgc": str}).set_index("psgc")


def map_residents(overlay, return_period):
    """N_{b,k} when a storm's wettest n-day total equals the T-year map's rain: that map's rows of the table."""
    rows = overlay[overlay["return_period"] == return_period]
    if rows.empty:
        raise ValueError(f"no {return_period}-year map in the overlay table")
    return rows[["psgc", "var", "residents"]]


def check_inputs(residents, shares, q, contact):
    """Stop on input that would give wrong counts without an error."""
    if not 0 <= q <= 1:
        raise ValueError(f"q = {q}: the share who touch floodwater must be from 0 to 1")
    missing_r = sorted(set(config.NOAH_HAZARD_LEVELS) - set(contact))
    if missing_r or any(contact[k] < 0 for k in config.NOAH_HAZARD_LEVELS):
        raise ValueError(f"relative contact r_k must be given, and 0 or more, for every level: {contact}")

    rows = list(zip(residents["psgc"], residents["var"]))
    if len(rows) != len(set(rows)):
        raise ValueError("a barangay and level appear twice in residents: pass one map's or one storm's rows")
    expected = {(b, k) for b in shares.index for k in config.NOAH_HAZARD_LEVELS}
    missing, extra = expected - set(rows), set(rows) - expected
    if missing or extra:
        raise ValueError(f"residents and shares do not match: {len(missing)} barangay-levels missing "
                         f"(e.g. {sorted(missing)[:3]}), {len(extra)} unexpected (e.g. {sorted(extra)[:3]})")

    counts = residents["residents"]
    if counts.isna().any() or (counts < 0).any():
        raise ValueError("missing or negative residents")
    if shares[SHARES].isna().any().any():
        raise ValueError(f"missing shares in {list(shares.index[shares[SHARES].isna().any(axis=1)])}")


def exposed_people(residents, shares, q=config.CONTACT_SHARE_Q, contact=config.CONTACT_BY_LEVEL):
    """E_{b,g} = q * (sum over k of r_k * N_{b,k}) * s^g_b, per barangay."""
    check_inputs(residents, shares, q, contact)
    weighted = residents["residents"] * residents["var"].map(contact)
    in_contact = q * weighted.groupby(residents["psgc"]).sum()
    out = pd.DataFrame({"exposed": in_contact.loc[shares.index]})
    for group, share in GROUPS.items():
        out[group] = out["exposed"] * shares[share]
    return out


def adult_tiers(e_adult, flood_days, w, cutoff=config.CONTINUOUS_EXPOSURE_DAYS):
    """Split exposed adults into high, moderate and low risk (DM 2023-0309)."""
    if not 0 <= w <= 1:
        raise ValueError(f"w = {w}: the share with a wound or mucosal exposure must be from 0 to 1")
    if flood_days <= 0:
        raise ValueError(f"D = {flood_days}: a flood lasts at least part of a day")
    if e_adult.isna().any():
        raise ValueError("missing exposed adults")
    none = 0.0 * e_adult
    if flood_days >= cutoff:    # continuous exposure
        return pd.DataFrame({"high": e_adult, "moderate": none, "low": none})
    return pd.DataFrame({"high": none, "moderate": w * e_adult, "low": (1 - w) * e_adult})


def exposed_with_tiers(residents, shares, flood_days, w, cutoff=config.CONTINUOUS_EXPOSURE_DAYS,
                       q=config.CONTACT_SHARE_Q, contact=config.CONTACT_BY_LEVEL):
    """Exposed people plus the adult tiers in one call, one row per barangay."""
    people = exposed_people(residents, shares, q, contact)
    return people.join(adult_tiers(people["e_adult"], flood_days, w, cutoff))


def scenarios():
    """(label, D, w) for the preview: the two flood durations, the short one at each w."""
    out = []
    for days in config.FORECAST_RUN_D:
        if days >= config.CONTINUOUS_EXPOSURE_DAYS:
            out.append((f"D = {days} (any w)", days, config.WOUND_SHARE_W[0]))
        else:
            out += [(f"D = {days}, w = {w:g}", days, w) for w in config.WOUND_SHARE_W]
    return out


def report(overlay, shares):
    """Print QC's exposed people per map and group, the adult tiers, and barangays to inspect."""
    qc_pop = shares["pop_2024"].sum()
    by_map = {T: exposed_people(map_residents(overlay, T), shares) for T in config.NOAH_RETURN_PERIODS}

    totals = pd.DataFrame({T: people.sum() for T, people in by_map.items()}).T
    totals["% of QC"] = 100 * totals["exposed"] / qc_pop
    totals.index.name = "map"
    print(f"QC people exposed if a storm's wettest {config.RAIN_ACCUM_DAYS}-day total equals each map's "
          f"rain, Rn = R(T), at full "
          f"coverage (q = {config.CONTACT_SHARE_Q:g}, r_k = {config.CONTACT_BY_LEVEL}); "
          f"2024 census total {qc_pop:,}:")
    print(totals.to_string(float_format="{:,.0f}".format, formatters={"% of QC": "{:.1f}".format}))

    rows = {}
    for T, people in by_map.items():
        for label, days, w in scenarios():
            tiers = adult_tiers(people["e_adult"], days, w)
            rows[(T, label)] = tiers.sum()
    tiers = pd.DataFrame(rows).T
    tiers.index.names = ["map", "flood"]
    print(f"\nexposed adults by risk tier, QC (D >= {config.CONTINUOUS_EXPOSURE_DAYS} days: all high; "
          f"shorter: moderate = w x adults, low = the rest):")
    print(tiers.to_string(float_format="{:,.0f}".format))

    people = by_map[PREVIEW_MAP].join(shares[["adm4_name", "pop_2024"]])
    people["% exposed"] = 100 * people["exposed"] / people["pop_2024"]
    cols = ["adm4_name", "pop_2024", "exposed", "% exposed", *GROUPS]
    print(f"\nthe {SHOW} barangays with the most people exposed at R({PREVIEW_MAP}) (inspect):")
    print(people.nlargest(SHOW, "exposed")[cols].to_string(
        float_format="{:,.0f}".format, formatters={"pop_2024": "{:,}".format, "% exposed": "{:.1f}".format}))
    print("\nStock-planning figures, not a clinical assessment: DM 2023-0309 requires a physician's "
          "consultation before prophylaxis.")


def main():
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    shares = load_shares()
    if len(shares) != config.QC_BARANGAYS:
        raise ValueError(f"{config.SHARES_QC.name} has {len(shares)} barangays, expected {config.QC_BARANGAYS}")
    report(overlay, shares)
    print("\nwrote nothing (the storm runs are C8 and C9); now run python -m src.checks (S10, C5 part)")


if __name__ == "__main__":
    main()

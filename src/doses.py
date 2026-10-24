"""Drug units per barangay."""

import math

import pandas as pd

import config
from src import exposed

LABEL = ("Stock-planning figures, not prescriptions: DM 2023-0309 requires a physician's "
         "consultation before any prophylaxis.")
DOXY_BY_TIER = ["doxy100_high", "doxy100_moderate", "doxy100_low"]
UNITS = {                                   # Doxy100_b, Courses_b and Amox500_b
    "doxy100": "doxycycline 100 mg capsules, adults",
    "courses": "children's courses (doxycycline 4 mg/kg once, or an alternative; by weight)",
    "amox500": "amoxicillin 500 mg tablets, pregnant women (or erythromycin 250 mg if allergic)",
}
SHOW = 5    # barangays printed, to inspect


def weeks_of_flooding(flood_days):
    """ceil(D / 7): the weeks a flood of D days lasts, a part week counted whole (7 days = 1, 8 = 2)."""
    return math.ceil(flood_days / config.DOSE_WEEK_DAYS)


def doses(people, flood_days, u=config.UPTAKE_U):
    """Units of stock per barangay."""
    if not 0 <= u <= 1:
        raise ValueError(f"u = {u}: the uptake must be from 0 to 1")
    if flood_days <= 0:
        raise ValueError(f"D = {flood_days}: a flood lasts at least part of a day")
    counts = people[["e_child", "e_preg", *exposed.TIERS]]
    if counts.isna().any().any() or (counts < 0).any().any():
        raise ValueError("missing or negative exposed people")

    weeks = weeks_of_flooding(flood_days)
    out = pd.DataFrame(index=people.index)
    out["doxy100_high"] = u * config.DOXY_CAPS_HIGH_PER_WEEK * weeks * people["high"]
    out["doxy100_moderate"] = u * config.DOXY_CAPS_MOD * people["moderate"]
    out["doxy100_low"] = u * config.DOXY_CAPS_LOW * people["low"]
    out["doxy100"] = out[DOXY_BY_TIER].sum(axis=1)
    out["courses"] = u * max(1, weeks) * people["e_child"]     # at least one course
    out["amox500"] = u * config.AMOX_TABS_PREG * people["e_preg"]
    return out


def barangay_doses(residents, shares, flood_days, w, cutoff=config.CONTINUOUS_EXPOSURE_DAYS,
                   u=config.UPTAKE_U, q=config.CONTACT_SHARE_Q, contact=config.CONTACT_BY_LEVEL):
    """Exposed people, adult tiers and units for one flood duration D, one row per barangay."""
    people = exposed.exposed_with_tiers(residents, shares, flood_days, w, cutoff, q, contact)
    return people.join(doses(people, flood_days, u))


def report(overlay, shares):
    """Print QC's stock per map and flood, and the barangays that need the most, all labelled."""
    print(LABEL + "\n")
    stock = {}
    for period in config.NOAH_RETURN_PERIODS:
        residents = exposed.map_residents(overlay, period)
        for label, days, w in exposed.scenarios():
            stock[(period, label)] = barangay_doses(residents, shares, days, w)
    totals = pd.DataFrame({key: table[[*DOXY_BY_TIER, *UNITS]].sum() for key, table in stock.items()}).T
    totals.index.names = ["map", "flood"]
    print(f"QC stock if a storm's wettest {config.RAIN_ACCUM_DAYS}-day total equals each map's rain, "
          f"Rn = R(T), at full coverage "
          f"(q = {config.CONTACT_SHARE_Q:g}, u = {config.UPTAKE_U:g}):")
    print(totals.to_string(float_format="{:,.0f}".format))
    print("\n" + "\n".join(f"  {col}: {what}" for col, what in UNITS.items()))

    label, days, w = exposed.scenarios()[-1]    # the long flood
    table = stock[(exposed.PREVIEW_MAP, label)].join(shares[["adm4_name", "pop_2024"]])
    cols = ["adm4_name", "pop_2024", "exposed", *UNITS]
    print(f"\nthe {SHOW} barangays that need the most doxycycline at R({exposed.PREVIEW_MAP}), {label} (inspect):")
    print(table.nlargest(SHOW, "doxy100")[cols].to_string(
        float_format="{:,.0f}".format, formatters={"pop_2024": "{:,}".format}))
    print("\n" + LABEL)


def main():
    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    shares = exposed.load_shares()
    if len(shares) != config.QC_BARANGAYS:
        raise ValueError(f"{config.SHARES_QC.name} has {len(shares)} barangays, expected {config.QC_BARANGAYS}")
    report(overlay, shares)
    print("\nwrote nothing (the storm runs are C8 and C9); now run python -m src.checks (S10, C6 part)")


if __name__ == "__main__":
    main()

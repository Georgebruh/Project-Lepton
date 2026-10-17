"""Drug units per barangay (task C6). Stock planning, not prescriptions.

C5 gives each barangay's exposed children, pregnant women and adults, with the adults in
DM 2023-0309's risk tiers. C6 turns them into units of stock, with u the uptake (the
share of exposed people who take the drug) and D the flood duration in days:

    Doxy100_b = u * (2 * Low_b + 10 * Mod_b + 2 * ceil(D/7) * High_b)   doxycycline 100 mg capsules
    Courses_b = u * max(1, ceil(D/7)) * E_{b,child}                     children's courses
    Amox500_b = 6 * u * E_{b,preg}                                      amoxicillin 500 mg tablets

The regimens. Adults follow the PhilHealth policy statements, checked identical to
DM 2023-0309 Table 1:
  - low risk: doxycycline 200 mg once = 2 capsules;
  - moderate risk: 200 mg daily for 3-5 days, planned at 5 (config.MODERATE_COURSE_DAYS,
    the upper end, v2) = 10 capsules;
  - high risk: 200 mg once a week until exposure ends = 2 capsules for each week of
    flooding, ceil(D/7) weeks, a part week counted whole (a 7-day flood is 1 week, 8 days 2).
Children (DM 2023-0309 Table 2): doxycycline 4 mg/kg once (at most 200 mg) for every
child, or azithromycin 10 mg/kg once (at most 500 mg) or amoxicillin 50 mg/kg/day in 4
doses for 3-5 days; repeated after 1 week if exposure lasts over 7 days. So each child
needs one course per week of flooding, at least one. The dose depends on weight, so C6
counts courses and the pharmacy turns them into tablets.
Pregnant women (DM 2023-0309 section II.B.2.b): amoxicillin 500 mg twice a day for 3
days = 6 tablets; 6 erythromycin 250 mg tablets instead if allergic, so the same count
sizes that stock too.

In plain words: 2 capsules per low-risk adult, 10 per moderate-risk adult, 2 per week of
flooding per high-risk adult; one course per child per week of flooding; 6 tablets per
pregnant woman.

Assumption: u = 1 (config.UPTAKE_U). Like C5's q, u scales every barangay by the same
factor, so stock is reported at full coverage and the health office multiplies by its
own uptake.

The adult doxycycline is also given per tier (doxy100_high, doxy100_moderate and
doxy100_low), because C7 serves high risk first when stock runs short. Units are expected
values and are not rounded.

These are stock-planning figures, not prescriptions (rule 10): DM 2023-0309 requires a
physician's consultation before any prophylaxis. Print LABEL with every dose figure.

C7, C8 and C9 call barangay_doses(residents, shares, D, w), which runs C5 and C6 with the
same D, with residents from C3's graded exposure at the storm's rain.

Run from the repository root:  python -m src.doses
Like C5's script, it previews C6 at each map's own rain, R24 = R(5), R(25) and R(100),
for C9's two flood durations, so it needs only C2's overlay_qc.csv and C4's
shares_qc.csv. It prints QC's totals and writes no file; the storm runs are C8 and C9.
Then run the checks (S10, C6 part):  python -m src.checks
"""

import math

import pandas as pd

import config
from src import exposed

LABEL = ("Stock-planning figures, not prescriptions: DM 2023-0309 requires a physician's "
         "consultation before any prophylaxis.")
DOXY_BY_TIER = ["doxy100_high", "doxy100_moderate", "doxy100_low"]
UNITS = {                                   # the plan's Doxy100_b, Courses_b and Amox500_b
    "doxy100": "doxycycline 100 mg capsules, adults",
    "courses": "children's courses (doxycycline 4 mg/kg once, or an alternative; by weight)",
    "amox500": "amoxicillin 500 mg tablets, pregnant women (or erythromycin 250 mg if allergic)",
}
SHOW = 5    # barangays printed, to inspect


def weeks_of_flooding(flood_days):
    """ceil(D / 7): the weeks a flood of D days lasts, a part week counted whole (7 days = 1, 8 = 2)."""
    return math.ceil(flood_days / config.DOSE_WEEK_DAYS)


def doses(people, flood_days, u=config.UPTAKE_U):
    """Units of stock per barangay, with the formulas at the top of this file.

    people: C5's table (exposed.exposed_with_tiers): e_child, e_preg and the adult tiers
    high, moderate and low, one row per barangay. flood_days must be the D that C5 split
    the tiers with; barangay_doses passes the same D to both. u: the uptake, 0 to 1.
    Returns doxy100_high, doxy100_moderate, doxy100_low, doxy100 (the three added up),
    courses and amox500, with people's index. Stops on a missing or negative count, which
    would otherwise give wrong stock without an error (rule 5).
    """
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
    """C5 then C6 with one D, for C7 to C9: exposed people, adult tiers and units, one row per barangay.

    residents and shares as in exposed.exposed_people; flood_days (D), w and cutoff as in
    exposed.adult_tiers; u as in doses.
    """
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
    print(f"QC stock if a storm's wettest day equals each map's rain, R24 = R(T), at full coverage "
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

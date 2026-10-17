"""Exposed people per barangay and group, and the adult risk tiers (task C5).

C3 gives N_{b,k}: the residents of barangay b in hazard level k (1 low, 2 medium, 3 high)
whom a storm's wettest day floods, interpolated between NOAH's maps (graded_exposure).
C4 gives each barangay's child, pregnant and adult shares. C5 turns the two into the
people each drug in C6 is for:

    E_{b,g} = q * (sum over k of r_k * N_{b,k}) * s^g_b      for g = child, preg, adult

where q is the share of flooded residents who touch floodwater, r_k the relative contact
at level k and s^g_b C4's share. In plain words: add up the barangay's flooded residents
over the three levels, each level weighted by how much contact its depth brings; take the
share who touch the water; split them into the three groups by the barangay's shares. The
groups add up to everyone exposed, because the shares add to 1.

Assumptions (config.py and the plan's assumptions table):
  - q = 1 (config.CONTACT_SHARE_Q). q, and C6's uptake u, scale every barangay by the same
    factor, so everything is reported at full coverage and the health office multiplies
    by its own q and u.
  - r_k = 1 for every level (config.CONTACT_BY_LEVEL), v2's default: ankle-deep water
    counts as much as head-deep.

Adults are then split into DM 2023-0309's risk tiers, which set their doxycycline regimen
in C6. D is the flood duration in days (A11's, per storm; C9 uses D = 1 and D = 7):

    D >= 2:  High_b = E_{b,adult},  Mod_b = Low_b = 0
    D <  2:  High_b = 0,  Mod_b = w * E_{b,adult},  Low_b = (1 - w) * E_{b,adult}

In plain words: a flood of 2 days or more is continuous exposure, which makes every
exposed adult high risk. In a shorter flood, the adults with a wound or a mucosal
exposure (swallowed or splashed floodwater), a share w, are moderate risk and the rest
low risk. Nobody knows w for QC, so it is reported at w = 0, 0.5 and 1
(config.WOUND_SHARE_W); 0 and 1 are the bounds. The 2-day cut-off
(config.CONTINUOUS_EXPOSURE_DAYS) is rerun at 1 and 3 days in C8.

Children and pregnant women get no tiers here: every exposed child needs children's
courses and every exposed pregnant woman amoxicillin, whatever the tier (C6). Lactating
women stay in the adult group (C4). Counts are expected values and are not rounded.
They plan stock; they are not a clinical risk assessment of anyone: DM 2023-0309 requires
a physician's consultation before any prophylaxis.

C8 and C9 call exposed_with_tiers(residents, shares, D, w), with residents from C3's
graded exposure at the storm's rain.

Run from the repository root:  python -m src.exposed
The script previews C5 at each map's own rain, R24 = R(5), R(25) and R(100), where C3's
graded exposure is exactly that map's residents (check S9), so it needs only C2's
overlay_qc.csv and C4's shares_qc.csv. It prints QC's totals and writes no file; the
storm runs are C8 and C9. Then run the checks (S10, C5 part):  python -m src.checks
"""

import pandas as pd

import config
from src.shares import SHARES

GROUPS = {"e_child": "s_child", "e_preg": "s_preg", "e_adult": "s_adult"}  # E_{b,g} -> C4's s^g_b
TIERS = ["high", "moderate", "low"]
PREVIEW_MAP = 25    # map whose barangays the script prints
SHOW = 5            # barangays printed, to inspect


def load_shares():
    """C4's table, one row per barangay (index psgc), with s_child, s_preg, s_adult and pop_2024."""
    return pd.read_csv(config.SHARES_QC, dtype={"psgc": str}).set_index("psgc")


def map_residents(overlay, return_period):
    """N_{b,k} when a storm's wettest day equals the T-year map's rain: that map's rows of C2's table.

    At exactly R24 = R(T), C3's graded exposure is the T-year map's residents (check S9),
    so C5 can run on C2's table alone. Returns the columns psgc, var and residents.
    """
    rows = overlay[overlay["return_period"] == return_period]
    if rows.empty:
        raise ValueError(f"no {return_period}-year map in the overlay table")
    return rows[["psgc", "var", "residents"]]


def check_inputs(residents, shares, q, contact):
    """Stop on input that would give wrong counts without an error (rule 5).

    residents needs exactly one row for every barangay in shares and every hazard level:
    a missing row would quietly count as nobody, and two maps' rows passed together would
    be added up. No count or share may be missing, and no count negative. q is a share,
    from 0 to 1; every level needs an r_k of 0 or more.
    """
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
    """E_{b,g} = q * (sum over k of r_k * N_{b,k}) * s^g_b, per barangay.

    residents: one row per barangay and hazard level, with columns psgc, var and residents
    (N_{b,k}): C3's graded exposure at a storm's rain, or one map's rows of C2's table
    (map_residents). shares: C4's table (load_shares). q and contact (r_k by level) default
    to config's values. Returns one row per barangay of shares (index psgc), in the same
    order: exposed (q x the weighted sum, everyone exposed), e_child, e_preg and e_adult.
    """
    check_inputs(residents, shares, q, contact)
    weighted = residents["residents"] * residents["var"].map(contact)
    in_contact = q * weighted.groupby(residents["psgc"]).sum()
    out = pd.DataFrame({"exposed": in_contact.loc[shares.index]})
    for group, share in GROUPS.items():
        out[group] = out["exposed"] * shares[share]
    return out


def adult_tiers(e_adult, flood_days, w, cutoff=config.CONTINUOUS_EXPOSURE_DAYS):
    """Split exposed adults into high, moderate and low risk (DM 2023-0309, C5).

    flood_days (D) >= cutoff: every exposed adult is high risk.
    flood_days < cutoff: moderate = w x adults, low = (1 - w) x adults, high = 0.
    e_adult: exposed adults per barangay; w: the share with a wound or mucosal exposure,
    from 0 to 1 (used only in short floods). Returns high, moderate and low with e_adult's
    index; the three add up to e_adult.
    """
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
    """C5 in one call, for C6 to C9: exposed_people plus the adult tiers, one row per barangay."""
    people = exposed_people(residents, shares, q, contact)
    return people.join(adult_tiers(people["e_adult"], flood_days, w, cutoff))


def scenarios():
    """(label, D, w) for the preview: C9's two flood durations, the short one at each w."""
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
    print(f"QC people exposed if a storm's wettest day equals each map's rain, R24 = R(T), at full "
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

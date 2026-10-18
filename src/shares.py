"""Child, pregnant and adult shares per barangay (task C4, corrections 3 and 4).

C5 splits each barangay's exposed residents into three groups, because each group gets a
different drug (C6): children get children's courses, pregnant women amoxicillin, and
everyone else (adults) doxycycline. C4 gives each group's share of the barangay.

From the 2020 census by single-year age and sex (A5), per barangay b:
    C_b      children under 18 (both sexes)
    W_b      women 15-49
    G_b      women 15-17 (girls old enough to be pregnant but still in the child group)

Pregnant women in QC, from A12's registered births to mothers who live in QC:
    Preg_QC = births x 0.75
In plain words: a pregnancy lasts about 9 of a year's 12 months, so on a given day about
three quarters of a year's births are still on the way (v2's factor).

The plan's formulas:

    preg_b  = Preg_QC x W_b / W_QC                 split by each barangay's share of QC's women 15-49
    s_preg  = preg_b / P2024_b
    s_child = C_b / P2020_b - s_preg x G_b / W_b
    s_adult = 1 - s_child - s_preg

In plain words:
  - No table says where in QC the pregnant women live, so each barangay gets the city's
    count in proportion to its women 15-49 (assumption, correction 4).
  - The child share is the 2020 census's share under 18, used on 2024 totals (assumption:
    2020 age structure).
  - Some pregnant women are 15-17, so they also sit in the child share. Taking the
    pregnant women to be spread evenly over ages 15-49, a fraction G_b / W_b of them are
    under 18; that part moves out of the child group, so nobody is counted twice
    (correction 3). Adults are everyone left, so the three shares add up to exactly 1.

Pregnant counts are expected values and are not rounded. Lactating women cannot be
counted from these tables, and DM 2023-0309 gives them no regimen; they stay in the adult
group and the paper says so.

Assumption test (the plan's assumptions table): the pregnant count's upper bound is 3.5%
of QC's 2024 population (config.PREG_UPPER_SHARE), split the same way. The script prints
those shares too; C5 and C6 can get them with group_shares(counts, upper_bound_pregnant(counts)).

Output: data/clean/shares_qc.csv (config.SHARES_QC), one row per barangay:
    psgc, adm4_name
    pop_2020, pop_2024   census totals (A5)
    children             C_b, under 18 in 2020
    women_15_49          W_b, in 2020
    women_15_17          G_b, in 2020
    preg                 preg_b, pregnant women now (2024 births)
    s_child, s_preg, s_adult   the three shares; they add up to 1

Run from the repository root:  python -m src.shares
Needs A5 (python -m src.census) and A12's births file in data/raw/. Then run the checks;
the first part of S10 tests this task:  python -m src.checks
"""

import pandas as pd

import config

SHOW = 5    # barangays printed at each end of the child share, to inspect
SHARES = ["s_child", "s_preg", "s_adult"]


def people_aged(age_sex, ages, sex=None):
    """People per barangay with an age from ages[0] to ages[1] (both included), of one sex or both."""
    first, last = ages
    rows = age_sex["age"].between(first, last)
    if sex is not None:
        rows &= age_sex["sex"] == sex
    return age_sex[rows].groupby("psgc")["pop"].sum()


def age_groups(age_sex):
    """C_b, W_b and G_b per barangay from A5's long 2020 table (psgc, sex, age, pop)."""
    return pd.DataFrame({
        "children": people_aged(age_sex, config.CHILD_AGES),
        "women_15_49": people_aged(age_sex, config.WOMEN_AGES, "F"),
        "women_15_17": people_aged(age_sex, config.GIRLS_AGES, "F"),
    })


def barangay_counts():
    """One row per barangay (index psgc): name, both census totals and the three age groups.

    Stops unless A5's census table and its age table hold the same 142 barangays.
    """
    census = pd.read_csv(config.CENSUS_QC, dtype={"psgc": str},
                         usecols=["psgc", "adm4_name", "pop_2020", "pop_2024"]).set_index("psgc")
    groups = age_groups(pd.read_csv(config.AGE_SEX_2020_QC, dtype={"psgc": str}))
    if len(census) != config.QC_BARANGAYS or set(census.index) != set(groups.index):
        raise ValueError(f"{config.CENSUS_QC.name} ({len(census)} barangays) and "
                         f"{config.AGE_SEX_2020_QC.name} ({len(groups)}) hold different barangays")
    return census.join(groups).sort_index()


def qc_births():
    """A12: 2024 registered births to mothers who live in QC, from PSA's OpenSTAT CSV.

    Names are indented with dots by level ("......Quezon City"), so the dots are dropped
    and the whole name must match config.BIRTHS_QC_ROW exactly once.
    """
    table = pd.read_csv(config.BIRTHS_2024, encoding=config.BIRTHS_ENCODING)
    names = table["Geolocation"].str.lstrip(".").str.strip()
    qc = table[names == config.BIRTHS_QC_ROW]
    if len(qc) != 1:
        raise ValueError(f"found {len(qc)} rows named {config.BIRTHS_QC_ROW!r} in {config.BIRTHS_2024.name}")
    return int(qc[config.BIRTHS_COLUMN].iloc[0])


def pregnant_from_births(births):
    """Preg_QC = births x 0.75 (config.PREG_BIRTHS_FACTOR)."""
    return births * config.PREG_BIRTHS_FACTOR


def upper_bound_pregnant(counts):
    """The assumption test's Preg_QC: 3.5% of QC's 2024 population (config.PREG_UPPER_SHARE)."""
    return config.PREG_UPPER_SHARE * counts["pop_2024"].sum()


def group_shares(counts, preg_qc):
    """Add preg, s_child, s_preg and s_adult to counts, with the formulas at the top of this file.

    counts: one row per barangay with pop_2020, pop_2024, children, women_15_49 and
    women_15_17; preg_qc: pregnant women in the whole city. W_QC is the sum of
    women_15_49 over the rows, so pass every barangay of the city at once.
    Stops if a census total or W_b is 0, which would divide by zero.
    """
    for col in ("pop_2020", "pop_2024", "women_15_49"):
        if (counts[col] <= 0).any():
            raise ValueError(f"{col} is 0 in {list(counts.index[counts[col] <= 0])}: cannot divide by it")
    out = counts.copy()
    out["preg"] = preg_qc * out["women_15_49"] / out["women_15_49"].sum()
    out["s_preg"] = out["preg"] / out["pop_2024"]
    out["s_child"] = out["children"] / out["pop_2020"] - out["s_preg"] * out["women_15_17"] / out["women_15_49"]
    out["s_adult"] = 1 - out["s_child"] - out["s_preg"]
    return out


def summary(table):
    """QC's people in each group (shares x 2024 totals) and the share of QC, as one line."""
    qc = table["pop_2024"].sum()
    parts = []
    for share in SHARES:
        people = (table[share] * table["pop_2024"]).sum()
        parts.append(f"{share.removeprefix('s_')} {people:,.0f} ({people / qc:.2%})")
    return ", ".join(parts)


def report(table, births, preg_qc, upper):
    """Print the inputs, QC's totals per group, the spread across barangays and the upper bound."""
    print(f"A12: {births:,} births to mothers living in QC in 2024 x {config.PREG_BIRTHS_FACTOR} "
          f"= {preg_qc:,.1f} pregnant women ({preg_qc / table['pop_2024'].sum():.2%} of QC's 2024 total)")
    moved = (table["s_preg"] * table["women_15_17"] / table["women_15_49"] * table["pop_2024"]).sum()
    print(f"pregnant girls 15-17 moved out of the child group: {moved:,.0f}")
    print(f"QC, 2024: {summary(table)}")
    print("\nshares across the 142 barangays:")
    print(table[SHARES].describe().loc[["min", "25%", "50%", "75%", "max"]].round(4).to_string())

    ordered = table.sort_values("s_child")
    cols = ["adm4_name", "pop_2024", "children", "women_15_49", "preg"] + SHARES
    print(f"\nthe {SHOW} lowest and {SHOW} highest child shares (inspect):")
    print(pd.concat([ordered.head(SHOW), ordered.tail(SHOW)])[cols].round(
        {"preg": 1, "s_child": 4, "s_preg": 4, "s_adult": 4}).to_string())

    print(f"\nupper-bound test, {config.PREG_UPPER_SHARE:.1%} of QC pregnant ({upper_bound_pregnant(table):,.0f}): "
          f"{summary(upper)}; smallest adult share {upper['s_adult'].min():.4f}")


def main():
    counts = barangay_counts()
    births = qc_births()
    preg_qc = pregnant_from_births(births)
    table = group_shares(counts, preg_qc)
    upper = group_shares(counts, upper_bound_pregnant(counts))
    for label, t in (("shares", table), ("upper-bound shares", upper)):
        if t[SHARES].isna().any().any() or (t[SHARES] < 0).any().any():
            raise ValueError(f"missing or negative {label}:\n{t[t[SHARES].isna().any(axis=1) | (t[SHARES] < 0).any(axis=1)]}")

    part = config.SHARES_QC.with_suffix(".part")    # a stopped run leaves no half file
    table.reset_index()[["psgc", *counts.columns, "preg", *SHARES]].to_csv(part, index=False)
    part.replace(config.SHARES_QC)
    report(table, births, preg_qc, upper)
    print(f"\nwrote {config.SHARES_QC} ({len(table)} rows); now run python -m src.checks (S10, first part)")


if __name__ == "__main__":
    main()

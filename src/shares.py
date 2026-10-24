"""Child, pregnant and adult shares per barangay."""

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
    """C_b, W_b and G_b per barangay from the long 2020 table (psgc, sex, age, pop)."""
    return pd.DataFrame({
        "children": people_aged(age_sex, config.CHILD_AGES),
        "women_15_49": people_aged(age_sex, config.WOMEN_AGES, "F"),
        "women_15_17": people_aged(age_sex, config.GIRLS_AGES, "F"),
    })


def barangay_counts():
    """One row per barangay (index psgc): name, both census totals and the three age groups."""
    census = pd.read_csv(config.CENSUS_QC, dtype={"psgc": str},
                         usecols=["psgc", "adm4_name", "pop_2020", "pop_2024"]).set_index("psgc")
    groups = age_groups(pd.read_csv(config.AGE_SEX_2020_QC, dtype={"psgc": str}))
    if len(census) != config.QC_BARANGAYS or set(census.index) != set(groups.index):
        raise ValueError(f"{config.CENSUS_QC.name} ({len(census)} barangays) and "
                         f"{config.AGE_SEX_2020_QC.name} ({len(groups)}) hold different barangays")
    return census.join(groups).sort_index()


def qc_births():
    """2024 registered births to mothers who live in QC, from PSA's OpenSTAT CSV."""
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
    """Add preg, s_child, s_preg and s_adult to counts."""
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

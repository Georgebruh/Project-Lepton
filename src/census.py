"""Barangay boundaries joined to the 2024 and 2020 census tables."""

import re
import unicodedata

import geopandas as gpd
import pandas as pd

import config


def name_key(name):
    """A barangay name in a plain form for matching across tables."""
    name = re.sub(r"\(.*?\)", "", str(name))
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", name.lower())


def hdx_to_old_code(pcode):
    """HDX boundary code -> old 9-digit PSGC: PH1307404001 -> PH137404001."""
    if len(pcode) != 12 or pcode[4] != "0":
        raise ValueError(f"unexpected HDX code {pcode}")
    return pcode[:4] + pcode[5:]


def read_boundaries():
    """QC barangay polygons from the HDX geodatabase, one row per barangay."""
    gdf = gpd.read_file(
        f"zip://{config.BOUNDARIES_ZIP.as_posix()}",
        layer="phl_admin4",
        where=f"adm3_pcode = '{config.QC_HDX_ADM3_PCODE}'",
        columns=["adm4_pcode", "adm4_name", "adm3_pcode", "area_sqkm"],  # the where field must be listed
    )
    gdf["psgc_old"] = gdf["adm4_pcode"].map(hdx_to_old_code)
    return gdf


def read_census_2020():
    """QC rows of the HDX 2020 age-sex table (all 250 columns), keyed by `psgc`."""
    df = pd.read_excel(config.CENSUS_2020_AGE_XLSX, dtype={"BgyCode_new": str, "BgyCode_old": str}).copy()
    df["psgc"] = df["BgyCode_new"].str.removeprefix("PH")
    return df[df["psgc"].str.startswith(config.QC_PSGC_PREFIX)].reset_index(drop=True)


def read_census_2024():
    """QC barangay totals from the PSA 2024 workbook, in PSA's order."""
    sheet = pd.read_excel(config.CENSUS_2024_XLSX, sheet_name=config.QC_SHEET_2024, header=None)
    rows = sheet[sheet[1].notna() & sheet[3].notna()]
    city_total = int(rows[3].iloc[0])
    table = pd.DataFrame({
        "name_2024": rows[1].iloc[1:].str.strip().to_numpy(),
        "pop_2024": rows[3].iloc[1:].astype(int).to_numpy(),
    })
    return table, city_total


def read_city_totals():
    """QC's 2015, 2020 and 2024 totals from Table B of the PSA 2024 workbook."""
    sheet = pd.read_excel(config.CENSUS_2024_XLSX, sheet_name="Table B", header=None)
    qc = sheet[sheet[0].astype(str).str.strip().str.upper() == "QUEZON CITY"]
    if len(qc) != 1:
        raise ValueError(f"found {len(qc)} Quezon City rows in Table B")
    row = qc.iloc[0]
    return {2015: int(row[3]), 2020: int(row[4]), 2024: int(row[5])}


def age_sex_long(census_2020):
    """The 2020 single-year columns as a long table: psgc, sex, age, pop."""
    parts = []
    for sex in ("M", "F"):
        cols = [c for c in census_2020.columns
                if c.endswith(f"_{sex}") and not c.startswith("Total")]
        ages = []
        for c in cols:
            label = c.rsplit("_", 1)[0]
            ages.append(0 if label == "Under 1" else 80 if label == "80 and Over" else int(label))
        if sorted(ages) != list(range(81)):
            raise ValueError(f"expected ages 0-80 for sex {sex}, got {sorted(ages)}")

        bad = census_2020[cols].sum(axis=1) != census_2020[f"Total_{sex}"]
        if bad.any():
            raise ValueError(f"single ages do not add up to Total_{sex} for {census_2020.loc[bad, 'Bgy'].tolist()}")

        wide = census_2020[["psgc"] + cols].rename(columns=dict(zip(cols, ages)))
        long = wide.melt(id_vars="psgc", var_name="age", value_name="pop")
        parts.append(long.assign(sex=sex))

    bad = census_2020["Total_M"] + census_2020["Total_F"] != census_2020["Total_MF"]
    if bad.any():
        raise ValueError(f"M + F != Total_MF for {census_2020.loc[bad, 'Bgy'].tolist()}")

    out = pd.concat(parts)[["psgc", "sex", "age", "pop"]]
    out["age"] = out["age"].astype(int)
    return out.sort_values(["psgc", "sex", "age"]).reset_index(drop=True)


def join_boundaries_2020(boundaries, census_2020):
    """Exact join on the old 9-digit code; every barangay must match once, names must agree."""
    c20 = census_2020[["psgc", "BgyCode_old", "Bgy", "Total_MF"]].rename(
        columns={"BgyCode_old": "psgc_old", "Bgy": "name_2020", "Total_MF": "pop_2020"})
    joined = boundaries.merge(c20, on="psgc_old", how="outer", indicator=True, validate="one_to_one")
    unmatched = joined[joined["_merge"] != "both"]
    if len(unmatched):
        raise ValueError(f"boundaries and 2020 table do not match:\n{unmatched[['psgc_old', 'adm4_name', 'name_2020', '_merge']]}")

    differ = joined[joined["adm4_name"].map(name_key) != joined["name_2020"].map(name_key)]
    if len(differ):
        raise ValueError(f"same code, different name:\n{differ[['psgc_old', 'adm4_name', 'name_2020']]}")
    return joined.drop(columns="_merge")


def join_2024(joined, census_2024):
    """Join the 2024 totals by plain-form name, then check PSA's row order agrees."""
    c24 = census_2024.assign(key=census_2024["name_2024"].map(name_key), order_2024=range(1, len(census_2024) + 1))
    left = joined.assign(key=joined["adm4_name"].map(name_key))
    for label, table in (("boundaries", left), ("2024 table", c24)):
        dup = table[table["key"].duplicated(keep=False)]
        if len(dup):
            raise ValueError(f"two barangays share a plain-form name in the {label}:\n{dup}")

    out = left.merge(c24, on="key", how="outer", indicator=True, validate="one_to_one")
    unmatched = out[out["_merge"] != "both"]
    if len(unmatched):
        raise ValueError(f"names that did not match the 2024 table:\n{unmatched[['psgc', 'adm4_name', 'name_2024', '_merge']]}")

    # Second check: the n-th row of PSA's sheet is the barangay whose code ends in n.
    code_order = out["psgc"].str[-3:].astype(int)
    off = out[code_order != out["order_2024"]]
    if len(off):
        raise ValueError(f"name match disagrees with PSA's code order:\n{off[['psgc', 'adm4_name', 'name_2024', 'order_2024']]}")
    return out.drop(columns=["_merge", "key", "order_2024"])


def check_totals(table, city_total_2024, city_totals):
    """Barangay sums must equal the PSA city totals, and the workbook must agree with config."""
    if city_totals != config.CENSUS_POP_QC:
        raise ValueError(f"Table B gives {city_totals}, config.CENSUS_POP_QC has {config.CENSUS_POP_QC}")
    if city_total_2024 != config.CENSUS_POP_QC[2024]:
        raise ValueError(f"QC sheet total {city_total_2024} != {config.CENSUS_POP_QC[2024]}")
    for year in (2020, 2024):
        total = int(table[f"pop_{year}"].sum())
        if total != config.CENSUS_POP_QC[year]:
            raise ValueError(f"{year} barangays add up to {total:,}, PSA city total is {config.CENSUS_POP_QC[year]:,}")


def main():
    boundaries = read_boundaries()
    census_2020 = read_census_2020()
    census_2024, city_total_2024 = read_census_2024()
    city_totals = read_city_totals()
    for label, table in (("boundaries", boundaries), ("2020 table", census_2020), ("2024 table", census_2024)):
        if len(table) != config.QC_BARANGAYS:
            raise ValueError(f"{label} has {len(table)} QC barangays, expected {config.QC_BARANGAYS}")

    joined = join_boundaries_2020(boundaries, census_2020)
    joined = join_2024(joined, census_2024)
    check_totals(joined, city_total_2024, city_totals)

    cols = ["psgc", "adm4_pcode", "psgc_old", "adm4_name", "name_2020", "name_2024",
            "pop_2020", "pop_2024", "area_sqkm"]
    barangays = gpd.GeoDataFrame(joined[cols], geometry=joined.geometry, crs=boundaries.crs)
    barangays = barangays.sort_values("psgc").reset_index(drop=True)
    age_sex = age_sex_long(census_2020)

    config.BARANGAYS_QC.unlink(missing_ok=True)
    barangays.to_file(config.BARANGAYS_QC, layer="barangays", driver="GPKG")
    barangays.drop(columns="geometry").to_csv(config.CENSUS_QC, index=False)
    age_sex.to_csv(config.AGE_SEX_2020_QC, index=False)

    print(f"{len(barangays)} QC barangays matched in all three sources")
    print(f"2020 total {barangays['pop_2020'].sum():,}   2024 total {barangays['pop_2024'].sum():,}   "
          f"area {barangays['area_sqkm'].sum():.1f} km2")
    print(f"city totals for B1 (Table B): {city_totals}")
    written_differently = barangays[barangays["adm4_name"] != barangays["name_2024"]]
    print("\nmatched by plain-form name, written differently in the two tables (inspect):")
    print(written_differently[["psgc", "adm4_name", "name_2024"]].to_string(index=False))
    print(f"\nwrote {config.BARANGAYS_QC}, {config.CENSUS_QC} and {config.AGE_SEX_2020_QC}")


if __name__ == "__main__":
    main()

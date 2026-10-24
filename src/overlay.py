"""Residents per barangay, hazard level and flood map."""

import itertools

import geopandas as gpd
import pandas as pd

import config
from src import rescale

KEYS = ["psgc", "return_period", "var"]


def zones_by_barangay(barangays, flood):
    """One shape per barangay, map and level: the part of the barangay that zone floods."""
    barangays = barangays.to_crs(config.CRS_OVERLAY)
    flood = flood.to_crs(config.CRS_OVERLAY)
    qc = barangays.union_all()
    flood = flood.assign(geometry=flood.intersection(qc)).explode(index_parts=False)
    pieces = gpd.overlay(barangays[["psgc", "geometry"]], flood[["return_period", "var", "geometry"]],
                         how="intersection", keep_geom_type=True)
    return pieces.dissolve(by=KEYS).reset_index()


def levels_overlap(zones):
    """Largest area (km2) that two hazard levels of one map share inside one barangay."""
    by_map = ["psgc", "return_period"]
    levels_km2 = zones.assign(km2=zones.area / 1e6).groupby(by_map)["km2"].sum()
    joined_km2 = zones.dissolve(by=by_map).area / 1e6
    return float((levels_km2 - joined_km2).max())


def full_table(zones, residents, barangays):
    """Every barangay x map x level, with 0 km2 and 0 residents where the map does not flood it."""
    found = pd.DataFrame({
        "psgc": zones["psgc"],
        "return_period": zones["return_period"].astype(int),
        "var": zones["var"].astype(int),
        "area_km2": zones.area / 1e6,
        "residents": residents,
    })
    every = pd.DataFrame(list(itertools.product(barangays["psgc"], config.NOAH_RETURN_PERIODS,
                                                config.NOAH_HAZARD_LEVELS)), columns=KEYS)
    table = every.merge(found, on=KEYS, how="left", validate="one_to_one").fillna({"area_km2": 0, "residents": 0})
    table.insert(1, "adm4_name", table["psgc"].map(barangays.set_index("psgc")["adm4_name"]))
    return table.sort_values(KEYS).reset_index(drop=True)


def exposed_by_map(table):
    """Residents in any flood zone, per barangay (rows) and map (columns): the three levels added up."""
    return table.pivot_table(index="psgc", columns="return_period", values="residents", aggfunc="sum")


def falls_with_rarer_map(table):
    """Barangays whose exposed residents fall from the 5-year map to the 25- or 100-year map."""
    exposed = exposed_by_map(table)
    first, *rarer = config.NOAH_RETURN_PERIODS
    falls = (exposed[rarer].lt(exposed[first], axis=0)).any(axis=1)
    return exposed[falls]


def report(table, barangays):
    """Print QC's residents and area per map and level, and the barangays to inspect for S8."""
    qc_total = barangays["pop_2024"].sum()
    per_level = table.pivot_table(index="return_period", columns="var", values="residents", aggfunc="sum")
    per_level["all levels"] = per_level.sum(axis=1)
    per_level["% of QC"] = 100 * per_level["all levels"] / qc_total
    print(f"QC residents in each map's flood zones (2024 census total {qc_total:,}):")
    shown = per_level.round(0)                              # whole residents
    shown["% of QC"] = per_level["% of QC"].round(1)        # but keep the share's decimal
    print(shown.to_string(float_format="{:,.1f}".format))
    area = table.pivot_table(index="return_period", columns="var", values="area_km2", aggfunc="sum")
    area["all levels"] = area.sum(axis=1)
    print("\nflooded area in QC, km2:")
    print(area.round(2).to_string())

    falls = falls_with_rarer_map(table)
    names = barangays.set_index("psgc")["adm4_name"]
    print(f"\nS8: {len(falls)} barangays have fewer residents exposed in a rarer map than in the 5-year map (inspect):")
    if len(falls):
        print(falls.round(0).assign(adm4_name=falls.index.map(names)).to_string())


def main():
    barangays = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "adm4_name", "pop_2024"])
    if len(barangays) != config.QC_BARANGAYS:
        raise ValueError(f"{config.BARANGAYS_QC.name} has {len(barangays)} barangays, expected {config.QC_BARANGAYS}")
    flood = gpd.read_file(config.NOAH_FLOOD, layer="flood_hazard")

    zones = zones_by_barangay(barangays, flood)
    overlap = levels_overlap(zones)
    if overlap > config.NOAH_OVERLAP_TOLERANCE_KM2:
        raise ValueError(f"two hazard levels of one map share {overlap:.4f} km2 in a barangay; "
                         f"{config.NOAH_FLOOD.name} predates A8's fix: run python -m src.noah again")
    residents = rescale.rescaled_residents(zones)
    table = full_table(zones, residents, barangays)
    if table["residents"].isna().any() or (table["residents"] < 0).any():
        raise ValueError("missing or negative residents in the overlay table")

    part = config.OVERLAY.with_suffix(".part")    # a stopped run leaves no half file
    table.to_csv(part, index=False)
    part.replace(config.OVERLAY)
    report(table, barangays)
    print(f"\nwrote {config.OVERLAY} ({len(table)} rows); now run python -m src.checks (S8)")


if __name__ == "__main__":
    main()

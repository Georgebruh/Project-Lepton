"""WorldPop's 2024 population map fitted to the 2024 census."""

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from exactextract import exact_extract
from rasterio.crs import CRS

import config

SHOW = 5    # barangays printed at each end of the scale factors, to inspect


def worldpop_in(shapes):
    """WorldPop's people inside each shape, counting a cut pixel by the share inside."""
    geoms = shapes.geometry.to_crs(config.CRS_EXACTEXTRACT)
    people = np.zeros(len(geoms))
    pixels = np.zeros(len(geoms))
    filled = np.flatnonzero(~(geoms.isna() | geoms.is_empty).to_numpy())   # positions of real shapes
    features = gpd.GeoDataFrame({"row": filled}, geometry=geoms.iloc[filled].to_numpy(),
                                crs=config.CRS_EXACTEXTRACT)

    with rasterio.open(config.WORLDPOP_BOX) as grid:
        if grid.crs != CRS.from_user_input(config.CRS_EXACTEXTRACT):
            raise ValueError(f"{config.WORLDPOP_BOX.name} is in {grid.crs}, expected {config.CRS_EXACTEXTRACT}")
        sums = exact_extract(grid, features, ["sum", "count"], include_cols=["row"], output="pandas")

    people[sums["row"]] = sums["sum"]
    pixels[sums["row"]] = sums["count"]
    return pd.DataFrame({"people": people, "pixels": pixels}, index=shapes.index)


def scale_factors(barangays):
    """One row per barangay: its census total, WorldPop's people in it, and s_b = P_b / W_b."""
    found = worldpop_in(barangays)
    table = pd.DataFrame({
        "psgc": barangays["psgc"].to_numpy(),
        "adm4_name": barangays["adm4_name"].to_numpy(),
        "pop_2024": barangays["pop_2024"].to_numpy(),
        "worldpop_2024": found["people"].to_numpy(),
        "worldpop_pixels": found["pixels"].to_numpy(),
    })
    empty = table[table["worldpop_2024"] <= 0]
    if len(empty):
        raise ValueError(f"WorldPop has nobody in these barangays, so they cannot be scaled:\n{empty}")
    table["scale"] = table["pop_2024"] / table["worldpop_2024"]
    return table


def rescaled_residents(shapes):
    """Census-fitted residents inside each shape: s_b x WorldPop's people in the shape."""
    scale = pd.read_csv(config.WORLDPOP_SCALE_QC, dtype={"psgc": str}).set_index("psgc")["scale"]
    factor = shapes["psgc"].map(scale)
    if factor.isna().any():
        raise ValueError(f"no scale factor for psgc {sorted(set(shapes.loc[factor.isna(), 'psgc']))}")
    return worldpop_in(shapes)["people"] * factor


def report(table):
    """Print the city totals and the barangays WorldPop misses most, to check the run by eye."""
    worldpop, census = table["worldpop_2024"].sum(), table["pop_2024"].sum()
    print(f"WorldPop puts {worldpop:,.0f} people in QC's {len(table)} barangays; "
          f"the 2024 census counts {census:,} (census / WorldPop = {census / worldpop:.3f})")
    q = table["scale"].quantile([0, 0.25, 0.5, 0.75, 1])
    print("scale factors: min {:.2f}, quartiles {:.2f} / {:.2f} / {:.2f}, max {:.2f}".format(*q))

    ordered = table.sort_values("scale")
    cols = ["psgc", "adm4_name", "pop_2024", "worldpop_2024", "worldpop_pixels", "scale"]
    print(f"\nthe {SHOW} smallest and {SHOW} largest factors (inspect; a tiny barangay holds few pixels):")
    print(pd.concat([ordered.head(SHOW), ordered.tail(SHOW)])[cols]
          .round({"worldpop_2024": 0, "worldpop_pixels": 1, "scale": 3}).to_string(index=False))


def main():
    barangays = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "adm4_name", "pop_2024"])
    if len(barangays) != config.QC_BARANGAYS:
        raise ValueError(f"{config.BARANGAYS_QC.name} has {len(barangays)} barangays, expected {config.QC_BARANGAYS}")
    table = scale_factors(barangays)
    part = config.WORLDPOP_SCALE_QC.with_suffix(".part")    # a stopped run leaves no half file
    table.to_csv(part, index=False)
    part.replace(config.WORLDPOP_SCALE_QC)
    report(table)
    print(f"\nwrote {config.WORLDPOP_SCALE_QC}; now run python -m src.checks (S8, first part)")


if __name__ == "__main__":
    main()

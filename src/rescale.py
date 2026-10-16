"""WorldPop's 2024 population map fitted to the 2024 census (task C1).

WorldPop says where people live, pixel by pixel (A6); the PSA 2024 census says how many
live in each barangay (A5). The two disagree: WorldPop puts about 3.19 million people in
QC's 142 barangays and the census 3.08 million, and single barangays are off by far more,
in both directions. C1 keeps WorldPop's pattern inside each barangay and scales it to the
census total:

    p'_i = p_i * P_b / W_b,    W_b = sum over pixels j of f_j(b) * p_j

where p_i is WorldPop's count in pixel i, P_b the barangay's 2024 census total, and f_j(b)
the share of pixel j that lies inside barangay b (1 inside, 0 outside, a fraction where the
boundary cuts the pixel). In plain words: the map decides where people live inside a
barangay; the census decides how many. s_b = P_b / W_b is the barangay's scale factor.

Why the output is one factor per barangay and not a rescaled map: a pixel cut by a
barangay boundary has a part in each barangay, and each part is scaled by its own
barangay's factor, so no single new pixel value is right for both. C2 counts people with
the same part-pixel rule (the plan's overlay rule), so its sum of rescaled pixels is

    Pop_{b,k,T} = s_b * sum_i f_i(b and H_k,T) * p_i

rescaled_residents() computes it, for C2 and for check S8. Because the factor is fitted
with the same rule, a barangay's rescaled pixels add up to its census total exactly, and
the hazard levels of one map, which do not overlap (A8), can never hold more people than
the barangay.

WorldPop's nodata pixels (no buildings) hold nobody, before and after the rescaling.

Output: data/clean/worldpop_scale_qc.csv (config.WORLDPOP_SCALE_QC), one row per barangay:
    psgc, adm4_name
    pop_2024         P_b, the 2024 census total (A5)
    worldpop_2024    W_b, WorldPop's people in the barangay (cut pixels by their share)
    worldpop_pixels  pixels with a WorldPop value in the barangay (cut pixels by their share)
    scale            s_b = pop_2024 / worldpop_2024

Run from the repository root:  python -m src.rescale
Needs A5 (python -m src.census) and A6 (python -m src.worldpop) first. Then run the
checks; the first part of S8 tests this task:  python -m src.checks
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from exactextract import exact_extract
from rasterio.crs import CRS

import config

SHOW = 5    # barangays printed at each end of the scale factors, to inspect


def worldpop_in(shapes):
    """WorldPop's people inside each shape, counting a cut pixel by the share inside.

    In plain words: sum over pixels of (share of the pixel inside the shape) x (WorldPop's
    people in the pixel); exactextract computes the shares. Returns a table with the same
    index as shapes and two columns: people (that sum) and pixels (the sum of the shares
    alone, over pixels that have a WorldPop value).

    The shapes are converted to EPSG:4326, the grid's CRS, first: exactextract does not
    convert them, and shapes in metres (EPSG:32651) silently get 0 people. An empty shape
    holds 0 people; exactextract cannot read one, so it is not sent.
    """
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
    """One row per barangay: its census total, WorldPop's people in it, and s_b = P_b / W_b.

    Stops if WorldPop has nobody in a barangay: the map then gives no place to put the
    census's people, and the factor would be infinite.
    """
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
    """Census-fitted residents inside each shape: s_b x WorldPop's people in the shape.

    shapes: a GeoDataFrame with a psgc column naming the barangay each shape lies in, e.g.
    the barangays themselves (check S8) or one barangay's part of a hazard level (C2). In
    plain words: count WorldPop's people in the shape, cut pixels by their share, then
    multiply by that barangay's scale factor from config.WORLDPOP_SCALE_QC. A shape that
    reaches outside its barangay would get the wrong factor out there, so C2 cuts each
    hazard level by the barangay first. Returns a Series with the same index as shapes.
    """
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
    table.to_csv(config.WORLDPOP_SCALE_QC, index=False)
    report(table)
    print(f"\nwrote {config.WORLDPOP_SCALE_QC}; now run python -m src.checks (S8, first part)")


if __name__ == "__main__":
    main()

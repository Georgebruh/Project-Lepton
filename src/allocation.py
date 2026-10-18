"""Stock per health center, and allocation when stock is short (task C7).
Stock planning, not prescriptions.

C6 gives each barangay's need: doxycycline capsules for adults (by risk tier), children's
courses and amoxicillin tablets for pregnant women. Health centers hold and hand out the
stock, so C7 does two things.

1. Each barangay's need goes to health centers (v2's rule):
   - a barangay with one health center sends all of it there;
   - a barangay with several splits it by population: each center gets the share of the
     barangay's residents who live nearer to it than to the barangay's other centers
     (the centers' Voronoi cells inside the barangay, residents counted with C1's
     census-fitted map, as C2 does);
   - a barangay with none sends all of it to the nearest health center, measured from
     the barangay's centroid.
   A center's need is what its barangays send it:

       need_c = sum over barangays b of share_{b,c} * need_b

   Health centers are A10's registry facilities of the types in
   config.CENTER_FACILITY_TYPES: health centers (registered as "Rural Health Unit") and
   barangay health stations, not the City Health Office (assumption). A center can be
   placed only if the registry gives it coordinates inside its own barangay; the others
   are left out and listed, and their barangays use the centers that can be placed.

2. When a pool's stock is short, allocate (v2's) shares it among the health centers, high
   risk first, then moderate, then low. Each tier is served in full while stock lasts;
   the tier the remaining stock cannot cover is shared in proportion to need, and the
   tiers after it get nothing:

       served_{c,tier} = need_{c,tier} * min(1, stock left / the tier's total need)

   The three pools are allocated separately: adult doxycycline (C5's tiers), children's
   courses and amoxicillin for pregnant women. For the last two, high risk means a flood
   of D >= 2 days (v2); in shorter floods they are split by w like the adults. D and w are
   the same in every barangay, so these two pools come out in proportion to need whatever
   the tier labels.

Units are expected values and are not rounded; tables print them rounded up to whole
units per health center, the level at which stock is ordered.

Output: data/clean/center_shares_qc.csv (config.CENTER_SHARES), one row per barangay and
health center that gets part of its need:
    psgc, adm4_name
    facility_code, facility_name   the health center (A10)
    rule          own, split or nearest
    share         the part of the barangay's need it gets; each barangay's shares add to 1
    distance_km   barangay centroid to the center, for rule nearest
C8 and C9 call center_needs(residents, shares, center_table, D, w), then allocate_pools.

Run from the repository root:  python -m src.allocation   (a few seconds)
Needs A5, A10 and C1 (WorldPop grid and scale factors) for the shares file, and C2 and C4
for the preview. It writes the shares file, then previews C7 at the 25-year map's own rain,
Rn = R(25) (n-day totals, config.RAIN_ACCUM_DAYS): the need per health center in a
week-long flood, and allocate with stock
covering half of each pool's need (illustrative, config.ALLOCATE_PREVIEW_STOCK_SHARE) in a
1-day flood at w = 0.5. Then run the checks (S10, C7 part):  python -m src.checks
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

import config
from src import doses, exposed

POOLS = ["doxy100", "courses", "amox500"]   # C6's units: adult doxycycline, children's courses, amoxicillin
SHOW = 10    # health centers printed, to inspect


def round_up(units):
    """Whole units, rounded up. Rounded to 6 decimals first, so float noise (12.0000000001) stays 12."""
    return np.ceil(units.round(6))


def load_barangays():
    """A5's 142 barangays in EPSG:32651 (metres): psgc, adm4_name, pop_2024 and the shape."""
    barangays = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "adm4_name", "pop_2024"])
    if len(barangays) != config.QC_BARANGAYS:
        raise ValueError(f"{config.BARANGAYS_QC.name} has {len(barangays)} barangays, expected {config.QC_BARANGAYS}")
    return barangays.to_crs(config.CRS_OVERLAY)


def load_centers(barangays):
    """A10's health centers, split into those that can be placed and those left out.

    Keeps the facility types in config.CENTER_FACILITY_TYPES. A center is placed when the
    registry gives coordinates that lie inside its own barangay. Returns (placed, left_out):
    placed is a GeoDataFrame of points in EPSG:32651; left_out a table with the reason.
    """
    table = pd.read_csv(config.FACILITIES_QC, dtype={"psgc": str, "facility_code": str})
    table = table[table["facility_type"].isin(config.CENTER_FACILITY_TYPES)].reset_index(drop=True)
    has_point = table["lat"].notna() & table["lon"].notna()
    points = gpd.GeoSeries(gpd.points_from_xy(table["lon"], table["lat"]), crs=config.CRS_LONLAT).to_crs(config.CRS_OVERLAY)
    shape_of = barangays.set_index("psgc").geometry
    inside = pd.Series([ok and shape_of[psgc].contains(point)
                        for ok, psgc, point in zip(has_point, table["psgc"], points)])

    placed = gpd.GeoDataFrame(table[inside], geometry=points[inside], crs=config.CRS_OVERLAY)
    left_out = table[~inside].assign(reason=np.where(has_point[~inside], "point outside its barangay", "no coordinates"))
    return placed.reset_index(drop=True), left_out[["facility_code", "name", "psgc", "barangay_name", "reason"]]


def split_by_nearest_residents(shape, psgc, centers):
    """Each center's share of a barangay's residents who live nearer to it than to its other centers.

    The centers' Voronoi cells, cut to the barangay, hold those residents; C1's
    rescaled_residents counts them. Returns shares in the order of centers; they add to 1.
    """
    # C1's rescale needs rasterio and exactextract, so it is imported only here: allocate
    # and check S10 then run on a computer without them.
    from src import rescale

    cells = shapely.voronoi_polygons(shapely.MultiPoint(list(centers.geometry)), extend_to=shape, ordered=True)
    if not all(cell.contains(point) for cell, point in zip(cells.geoms, centers.geometry)):
        raise ValueError(f"barangay {psgc}: Voronoi cells came back out of order, so shares would go to the wrong centers")
    pieces = gpd.GeoDataFrame({"psgc": [psgc] * len(centers)},
                              geometry=[cell.intersection(shape) for cell in cells.geoms], crs=config.CRS_OVERLAY)
    residents = rescale.rescaled_residents(pieces).to_numpy()
    if residents.sum() <= 0:
        raise ValueError(f"nobody lives in barangay {psgc}, so its centers cannot split it by population")
    return residents / residents.sum()


def center_shares(barangays, centers):
    """One row per barangay and health center that gets part of its need, with the share (v2's rule)."""
    rows = []
    for b in barangays.itertuples():
        own = centers[centers["psgc"] == b.psgc]
        if len(own) == 1:
            rows.append((b.psgc, own["facility_code"].iloc[0], "own", 1.0, np.nan))
        elif len(own) > 1:
            for code, share in zip(own["facility_code"], split_by_nearest_residents(b.geometry, b.psgc, own)):
                rows.append((b.psgc, code, "split", share, np.nan))
        else:
            distance = centers.distance(b.geometry.centroid)
            nearest = distance.idxmin()
            rows.append((b.psgc, centers.loc[nearest, "facility_code"], "nearest", 1.0, distance[nearest] / 1000))

    table = pd.DataFrame(rows, columns=["psgc", "facility_code", "rule", "share", "distance_km"])
    table.insert(1, "adm4_name", table["psgc"].map(barangays.set_index("psgc")["adm4_name"]))
    table.insert(3, "facility_name", table["facility_code"].map(centers.set_index("facility_code")["name"]))
    return table


def load_center_shares():
    """C7's shares file (center_shares_qc.csv)."""
    return pd.read_csv(config.CENTER_SHARES, dtype={"psgc": str, "facility_code": str})


def pool_needs(stock, flood_days, w, cutoff=config.CONTINUOUS_EXPOSURE_DAYS):
    """Each pool's need by tier (columns high, moderate, low), one row per barangay, from C6's table.

    Adult doxycycline keeps C5's tiers. Children's courses and amoxicillin use the adults'
    rule: all high risk when D >= the cut-off, else split by w (v2). flood_days, w and
    cutoff must be the ones C6's table was made with; center_needs passes the same ones.
    """
    return {
        "doxy100": stock[doses.DOXY_BY_TIER].set_axis(exposed.TIERS, axis=1),
        "courses": exposed.adult_tiers(stock["courses"], flood_days, w, cutoff),
        "amox500": exposed.adult_tiers(stock["amox500"], flood_days, w, cutoff),
    }


def to_centers(need, center_table):
    """need_c = sum over barangays b of share_{b,c} x need_b, per tier.

    need: one row per barangay (index psgc), columns high, moderate, low. Stops unless
    every barangay has shares adding to 1 and the two tables hold the same barangays.
    """
    total = center_table.groupby("psgc")["share"].sum()
    if set(total.index) != set(need.index) or not np.allclose(total, 1):
        raise ValueError("every barangay needs health-center shares that add to 1: rerun python -m src.allocation")
    rows = center_table[["psgc", "facility_code", "share"]].join(need, on="psgc")
    return rows[exposed.TIERS].mul(rows["share"], axis=0).groupby(rows["facility_code"]).sum()


def center_needs(residents, shares, center_table, flood_days, w, cutoff=config.CONTINUOUS_EXPOSURE_DAYS,
                 u=config.UPTAKE_U, q=config.CONTACT_SHARE_Q, contact=config.CONTACT_BY_LEVEL):
    """C5, C6 and C7's step 1 with one D: each pool's need by tier, one row per health center.

    residents and shares as in exposed.exposed_people; center_table from load_center_shares.
    """
    stock = doses.barangay_doses(residents, shares, flood_days, w, cutoff, u, q, contact)
    return {pool: to_centers(need, center_table) for pool, need in pool_needs(stock, flood_days, w, cutoff).items()}


def allocate(need, stock):
    """Share one pool's stock among health centers, high risk first (v2's allocate, C7).

    need: one row per health center, columns high, moderate, low, in units of the pool.
    stock: units on hand, 0 or more. Each tier in turn is served in full while stock
    lasts; the first tier it cannot cover gets the rest in proportion to need, and later
    tiers get nothing. Returns what each center gets, in need's shape.
    """
    if not stock >= 0:     # also stops on NaN
        raise ValueError(f"stock = {stock}: must be 0 or more")
    if need[exposed.TIERS].isna().any().any() or (need[exposed.TIERS] < 0).any().any():
        raise ValueError("missing or negative need")
    left = float(stock)
    served = pd.DataFrame(0.0, index=need.index, columns=exposed.TIERS)
    for tier in exposed.TIERS:
        total = need[tier].sum()
        if total <= left:
            served[tier] = need[tier]
            left -= total
        else:
            served[tier] = need[tier] * (left / total)
            left = 0.0
    return served


def allocate_pools(needs, stock):
    """allocate for each pool on its own. needs from center_needs; stock: units on hand per pool."""
    return {pool: allocate(needs[pool], stock[pool]) for pool in POOLS}


def report_shares(center_table, left_out):
    """Print how the barangays' need reaches the health centers, to check by eye."""
    by_rule = center_table.drop_duplicates("psgc")["rule"].value_counts()
    print(f"{center_table['facility_code'].nunique()} health centers; barangays by rule: "
          + ", ".join(f"{rule} {by_rule.get(rule, 0)}" for rule in ("own", "split", "nearest")))
    print("\nleft out (not placed inside their own barangay; place them by hand to use them):")
    print(left_out.to_string(index=False) if len(left_out) else "  none")
    split = center_table[center_table["rule"] == "split"]
    print("\nbarangays with several health centers, split by who lives nearest:")
    print(split[["adm4_name", "facility_name", "share"]].round({"share": 3}).to_string(index=False))
    far = center_table[center_table["rule"] == "nearest"].nlargest(5, "distance_km")
    print("\nbarangays without a health center that are farthest from the nearest one (inspect):")
    print(far[["adm4_name", "facility_name", "distance_km"]].round({"distance_km": 2}).to_string(index=False))


def report_preview(center_table, overlay, shares):
    """Print the need per health center at R(25), and allocate with stock covering half the need."""
    residents = exposed.map_residents(overlay, exposed.PREVIEW_MAP)
    print(f"\n{doses.LABEL}")
    long_flood = config.FORECAST_RUN_D[-1]
    needs = center_needs(residents, shares, center_table, long_flood, w=0.5)
    table = pd.DataFrame({pool: needs[pool].sum(axis=1) for pool in POOLS})
    table.insert(0, "barangays", center_table.groupby("facility_code")["psgc"].nunique())
    table.insert(0, "facility_name", center_table.drop_duplicates("facility_code").set_index("facility_code")["facility_name"])
    print(f"\nthe {SHOW} health centers that need the most doxycycline at R({exposed.PREVIEW_MAP}), D = {long_flood} "
          f"(units rounded up; barangays = how many send them need):")
    top = table.nlargest(SHOW, "doxy100")
    print(top.assign(**{pool: round_up(top[pool]) for pool in POOLS}).to_string(float_format="{:,.0f}".format))
    print(f"QC, all {len(table)} centers: " + ", ".join(f"{pool} {table[pool].sum():,.0f}" for pool in POOLS))

    short_flood, w = config.FORECAST_RUN_D[0], 0.5
    needs = center_needs(residents, shares, center_table, short_flood, w)
    have = {pool: config.ALLOCATE_PREVIEW_STOCK_SHARE * needs[pool].to_numpy().sum() for pool in POOLS}
    served = allocate_pools(needs, have)
    print(f"\nallocate at R({exposed.PREVIEW_MAP}), D = {short_flood}, w = {w:g}, with stock for "
          f"{config.ALLOCATE_PREVIEW_STOCK_SHARE:.0%} of each pool's need (illustrative): share of each tier served")
    shares_served = pd.DataFrame({pool: served[pool].sum() / needs[pool].sum() for pool in POOLS}).T
    print(shares_served.to_string(float_format="{:.0%}".format, na_rep="-"))    # "-": the tier needs nothing
    print(f"\n{doses.LABEL}")


def main():
    barangays = load_barangays()
    centers, left_out = load_centers(barangays)
    center_table = center_shares(barangays, centers)
    part = config.CENTER_SHARES.with_suffix(".part")    # a stopped run leaves no half file
    center_table.to_csv(part, index=False)
    part.replace(config.CENTER_SHARES)
    report_shares(center_table, left_out)

    overlay = pd.read_csv(config.OVERLAY, dtype={"psgc": str})
    report_preview(center_table, overlay, exposed.load_shares())
    print(f"\nwrote {config.CENTER_SHARES} ({len(center_table)} rows); now run python -m src.checks (S10, C7 part)")


if __name__ == "__main__":
    main()

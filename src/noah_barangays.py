"""NOAH's flood zones cut to each Quezon City barangay, for the map while a barangay is open (F13).

While a barangay's pop-up is open and the flood zones are on, the map draws only that
barangay's zones, from one small file, instead of NOAH's national tiles.

  1. A8's maps (config.NOAH_FLOOD, EPSG:32651): each flood patch becomes a row of its own,
     and a patch smaller than config.APP_NOAH_MIN_M2 is dropped, as for the national tiles.
  2. The patches inside Quezon City are simplified together (GeoPandas simplify_coverage, as
     map_shapes does), so the hazard levels still meet without gaps or overlaps.
  3. Each patch is cut along the barangay outlines the map draws (qc_barangays.geojson).
  4. One file per map and barangay, app/public/data/noah_barangays/<T>yr/<psgc>.json: one row
     per hazard level (var), the level's pieces as one MultiPolygon.

For looking at only: every number in the app uses A8's full maps.

Run from the repository root after A8 (python -m src.noah) and src.app_data, which writes
qc_barangays.geojson; about a minute:
    python -m src.noah_barangays
Commit app/public/data/noah_barangays/ afterwards. Check: python -m src.checks ("F13 NOAH barangays").
"""

import geopandas as gpd
import numpy as np
import shapely
import shapely.geometry

import config
from src.app_data import write_json


def barangay_path(return_period, psgc):
    """Where one barangay's zones of one map go: app/public/data/noah_barangays/<T>yr/<psgc>.json."""
    return config.APP_NOAH_BARANGAYS / f"{return_period}yr" / f"{psgc}.json"


def load_barangays():
    """The barangay outlines the map draws (qc_barangays.geojson), in metres (EPSG:32651)."""
    path = config.APP_DATA / "qc_barangays.geojson"
    if not path.exists():
        raise SystemExit(f"{path.name} not found: run python -m src.app_data first")
    barangays = gpd.read_file(path)
    if len(barangays) != config.QC_BARANGAYS:
        raise ValueError(f"{path.name} holds {len(barangays)} barangays, expected {config.QC_BARANGAYS}")
    return barangays[["psgc", "geometry"]].to_crs(config.CRS_OVERLAY)


def city_patches(flood, return_period, city):
    """One map's flood patches that reach into the city: big enough, simplified together (steps 1 and 2)."""
    patches = flood.loc[flood["return_period"] == return_period, ["var", "geometry"]].explode(index_parts=False)
    patches = patches[(patches.area >= config.APP_NOAH_MIN_M2) & patches.intersects(city)].copy()
    patches["geometry"] = patches.geometry.simplify_coverage(config.APP_NOAH_BARANGAY_SIMPLIFY_M).values
    return patches[~patches.is_empty].reset_index(drop=True)


def cut_by_barangay(patches, barangays):
    """Each patch cut along the barangay outlines (step 3): one row per piece, with its barangay's psgc."""
    outlines = barangays.geometry.values
    patch_index, barangay_index = shapely.STRtree(outlines).query(patches.geometry.values, predicate="intersects")
    cut = shapely.intersection(patches.geometry.values[patch_index], outlines[barangay_index])
    # A patch that only touches a barangay leaves a line or a point there: keep the polygons only
    parts, row = shapely.get_parts(cut, return_index=True)
    polygon = (shapely.get_type_id(parts) == shapely.GeometryType.POLYGON) & (shapely.area(parts) > 0)
    return gpd.GeoDataFrame({"psgc": barangays["psgc"].to_numpy()[barangay_index[row[polygon]]],
                             "var": patches["var"].to_numpy()[patch_index[row[polygon]]]},
                            geometry=parts[polygon], crs=config.CRS_OVERLAY)


def level_rows(pieces):
    """One row per barangay and hazard level, the level's pieces as one MultiPolygon (step 4)."""
    rows = pieces.groupby(["psgc", "var"]).geometry.apply(lambda shapes: shapely.multipolygons(shapes.values))
    return gpd.GeoDataFrame(rows.reset_index(), geometry="geometry", crs=config.CRS_OVERLAY)


def feature_collection(rows):
    """Rows as GeoJSON in longitude/latitude, each point rounded on its own to config.APP_NOAH_BARANGAY_DECIMALS.

    Not write_geojson: GDAL repairs the shapes after rounding them, which here makes a level
    a GeometryCollection (the map draws no fill from it) or makes two levels overlap. A border
    two levels share has the same points in both, so rounding each point keeps them meeting.
    """
    rows = rows.to_crs(config.CRS_LONLAT)
    shapes = shapely.transform(rows.geometry.values, lambda xy: np.round(xy, config.APP_NOAH_BARANGAY_DECIMALS))
    features = [{"type": "Feature", "properties": {"var": int(var)}, "geometry": shapely.geometry.mapping(shape)}
                for var, shape in zip(rows["var"], shapes)]
    return {"type": "FeatureCollection", "features": features}


def write_map_files(rows, barangays, return_period):
    """One map's file for every barangay, even one without a flood zone, so the app never asks for a missing file."""
    names = set()
    for psgc in barangays["psgc"]:
        path = barangay_path(return_period, psgc)
        own = rows.loc[rows["psgc"] == psgc, ["var", "geometry"]].sort_values("var")
        write_json(feature_collection(own), path)
        names.add(path.name)
    for old in sorted(path.parent.glob("*.json")):
        if old.name not in names:   # a barangay no longer among the outlines
            old.unlink()
            print(f"removed {old.name}: no such barangay in qc_barangays.geojson")


def main():
    if not config.NOAH_FLOOD.exists():
        raise SystemExit(f"{config.NOAH_FLOOD.name} not found: run A8 first (python -m src.noah)")
    flood = gpd.read_file(config.NOAH_FLOOD, layer="flood_hazard")
    barangays = load_barangays()
    city = barangays.union_all()
    for return_period in config.NOAH_RETURN_PERIODS:
        pieces = cut_by_barangay(city_patches(flood, return_period, city), barangays)
        write_map_files(level_rows(pieces), barangays, return_period)
        full = flood.loc[flood["return_period"] == return_period].intersection(city).area.sum()
        sizes = [barangay_path(return_period, psgc).stat().st_size for psgc in barangays["psgc"]]
        print(f"{return_period}-year map: {pieces.area.sum() / full:.1%} of its flooded area in the city, "
              f"{pieces['psgc'].nunique()} barangays with zones; {len(sizes)} files, {sum(sizes) / 1e6:.1f} MB, "
              f"the largest {max(sizes) / 1e3:.0f} KB")


if __name__ == "__main__":
    main()

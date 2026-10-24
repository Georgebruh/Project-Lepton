"""NOAH's flood zones cut to each Metro Manila city, for the map while a city is open or found (F13).

While Quezon City's panel is open, or the search has found one of NCR's 17 cities, and the
flood zones are on, the map draws only that city's zones, from one file, instead of NOAH's
national tiles. A8's maps cover Metro Manila only, so every other city keeps the tiles.

  1. A8's maps (config.NOAH_FLOOD, EPSG:32651): each flood patch becomes a row of its own,
     and a patch smaller than config.APP_NOAH_MIN_M2 is dropped, as for the national tiles.
  2. The patches inside NCR are simplified together (GeoPandas simplify_coverage, as
     map_shapes does), so the hazard levels still meet without gaps or overlaps.
  3. Each patch is cut along the city outlines the map draws (ph_cities.json, NCR's 17).
  4. One file per map and city, app/public/data/noah_cities/<T>yr/<psgc>.json: one row per
     hazard level (var), the level's pieces as one MultiPolygon.

For looking at only: every number in the app uses A8's full maps.

Run from the repository root after A8 (python -m src.noah) and src.app_data, which writes
ph_cities.json; about a minute:
    python -m src.noah_cities
Commit app/public/data/noah_cities/ afterwards. Check: python -m src.checks ("F13 NOAH cities").
"""

import geopandas as gpd
import numpy as np
import shapely
import shapely.geometry

import config
from src.app_data import write_json

NCR = "National Capital Region"   # ph_cities.json's province for Metro Manila's 17 cities


def city_path(return_period, psgc):
    """Where one city's zones of one map go: app/public/data/noah_cities/<T>yr/<psgc>.json."""
    return config.APP_NOAH_CITIES / f"{return_period}yr" / f"{psgc}.json"


def load_cities():
    """NCR's city outlines as the map draws them (ph_cities.json), in metres (EPSG:32651)."""
    path = config.APP_DATA / config.APP_CITIES_FILE
    if not path.exists():
        raise SystemExit(f"{path.name} not found: run python -m src.app_data first")
    cities = gpd.read_file(path)
    cities = cities[cities["province"] == NCR]
    if len(cities) != config.NCR_CITY_COUNT:
        raise ValueError(f"{path.name} holds {len(cities)} cities in {NCR}, expected {config.NCR_CITY_COUNT}")
    return cities[["psgc", "geometry"]].to_crs(config.CRS_OVERLAY).reset_index(drop=True)


def region_patches(flood, return_period, region):
    """One map's flood patches that reach into NCR: big enough, simplified together (steps 1 and 2)."""
    patches = flood.loc[flood["return_period"] == return_period, ["var", "geometry"]].explode(index_parts=False)
    patches = patches[(patches.area >= config.APP_NOAH_MIN_M2) & patches.intersects(region)].copy()
    patches["geometry"] = patches.geometry.simplify_coverage(config.APP_NOAH_CITY_SIMPLIFY_M).values
    return patches[~patches.is_empty].reset_index(drop=True)


def cut_by_city(patches, cities):
    """Each patch cut along the city outlines (step 3): one row per piece, with its city's psgc."""
    outlines = cities.geometry.values
    patch_index, city_index = shapely.STRtree(outlines).query(patches.geometry.values, predicate="intersects")
    cut = shapely.intersection(patches.geometry.values[patch_index], outlines[city_index])
    # A patch that only touches a city leaves a line or a point there: keep the polygons only
    parts, row = shapely.get_parts(cut, return_index=True)
    polygon = (shapely.get_type_id(parts) == shapely.GeometryType.POLYGON) & (shapely.area(parts) > 0)
    return gpd.GeoDataFrame({"psgc": cities["psgc"].to_numpy()[city_index[row[polygon]]],
                             "var": patches["var"].to_numpy()[patch_index[row[polygon]]]},
                            geometry=parts[polygon], crs=config.CRS_OVERLAY)


def level_rows(pieces):
    """One row per city and hazard level, the level's pieces as one MultiPolygon (step 4)."""
    rows = pieces.groupby(["psgc", "var"]).geometry.apply(lambda shapes: shapely.multipolygons(shapes.values))
    return gpd.GeoDataFrame(rows.reset_index(), geometry="geometry", crs=config.CRS_OVERLAY)


def feature_collection(rows):
    """Rows as GeoJSON in longitude/latitude, each point rounded on its own to config.APP_NOAH_CITY_DECIMALS.

    Not write_geojson: GDAL repairs the shapes after rounding them, which here makes a level
    a GeometryCollection (the map draws no fill from it) or makes two levels overlap. A border
    two levels share has the same points in both, so rounding each point keeps them meeting.
    """
    rows = rows.to_crs(config.CRS_LONLAT)
    shapes = shapely.transform(rows.geometry.values, lambda xy: np.round(xy, config.APP_NOAH_CITY_DECIMALS))
    features = [{"type": "Feature", "properties": {"var": int(var)}, "geometry": shapely.geometry.mapping(shape)}
                for var, shape in zip(rows["var"], shapes)]
    return {"type": "FeatureCollection", "features": features}


def write_map_files(rows, cities, return_period):
    """One map's file for every NCR city, even one without a flood zone, so the app never asks for a missing file."""
    names = set()
    for psgc in cities["psgc"]:
        path = city_path(return_period, psgc)
        own = rows.loc[rows["psgc"] == psgc, ["var", "geometry"]].sort_values("var")
        write_json(feature_collection(own), path)
        names.add(path.name)
    for old in sorted(path.parent.glob("*.json")):
        if old.name not in names:   # a city no longer among NCR's outlines
            old.unlink()
            print(f"removed {old.name}: no such city in ph_cities.json")


def main():
    if not config.NOAH_FLOOD.exists():
        raise SystemExit(f"{config.NOAH_FLOOD.name} not found: run A8 first (python -m src.noah)")
    flood = gpd.read_file(config.NOAH_FLOOD, layer="flood_hazard")
    cities = load_cities()
    region = cities.union_all()
    for return_period in config.NOAH_RETURN_PERIODS:
        pieces = cut_by_city(region_patches(flood, return_period, region), cities)
        write_map_files(level_rows(pieces), cities, return_period)
        full = flood.loc[flood["return_period"] == return_period].intersection(region).area.sum()
        sizes = {psgc: city_path(return_period, psgc).stat().st_size for psgc in cities["psgc"]}
        largest = max(sizes, key=sizes.get)
        print(f"{return_period}-year map: {pieces.area.sum() / full:.1%} of its flooded area in NCR, "
              f"{pieces['psgc'].nunique()} cities with zones; {len(sizes)} files, {sum(sizes.values()) / 1e6:.1f} MB, "
              f"the largest {sizes[largest] / 1e6:.1f} MB ({largest})")


if __name__ == "__main__":
    main()

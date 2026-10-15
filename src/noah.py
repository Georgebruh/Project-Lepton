"""NOAH flood hazard maps for Metro Manila (task A8).

Downloads Project NOAH's 5-, 25- and 100-year rain return flood hazard maps for Metro
Manila, unchanged, into data/raw/noah/, then for each map:
1. reprojects it to EPSG:32651 (UTM 51N, metres), the overlay CRS (config.CRS_OVERLAY);
2. repairs invalid shapes with make_valid (NOAH's shapes are all invalid as published),
   keeping only the polygon parts;
3. dissolves by hazard level, so each map has one row per `Var` (1 low, 2 medium, 3 high);
4. removes the overlaps between levels (the higher level keeps the area), so C2 can add
   the levels up without counting anyone twice.
The result is one file, data/clean/noah_flood_mm.gpkg: 9 rows (return_period, var,
geometry). C2 overlays it on the barangays and the WorldPop pixels.

Hazard levels (NOAH's metadata_flood.txt): flood depth 0-0.5 m is low (Var 1),
>0.5-1.5 m medium (Var 2), >1.5 m high (Var 3); fast-flowing water can raise the level.
Licence: ODC-ODbL; anything built from these maps is shared under the same licence.

Where the files are: NOAH's site (https://noah.up.edu.ph, "Downloads") links a public
Google Drive folder; config.NOAH_FLOOD_FILES holds the Drive id of each map. Each
download's "Last-Modified" date and the shapefile's own date inside the zip are printed:
together they are the map's version (NOAH gives no version number).

Run from the repository root:
    python -m src.noah
Files already in data/raw/noah/ are not downloaded again (delete them to refresh).
"""

import zipfile
from datetime import datetime
from itertools import combinations

import geopandas as gpd
import pandas as pd
import requests

import config

DRIVE_DOWNLOAD = "https://drive.usercontent.google.com/download"
TIMEOUT_S = 300
CHUNK_BYTES = 1 << 20
FILE_SIGNATURES = {".zip": b"PK", ".pdf": b"%PDF"}   # first bytes of a real file of that type


def drive_download(file_id, path):
    """Save a public Google Drive file to path, unchanged; return its Last-Modified date.

    Skips the download if path already exists (returns None). Google sends a web page
    instead of the file when a link is wrong or the daily quota is used up, so a reply
    that is a web page stops the run, and the first bytes of a zip or pdf are checked
    against the file type before the file is kept.
    """
    if path.exists():
        print(f"{path.name} already downloaded")
        return None
    params = {"id": file_id, "export": "download", "confirm": "t"}
    part = path.with_name(path.name + ".part")
    with requests.get(DRIVE_DOWNLOAD, params=params, stream=True, timeout=TIMEOUT_S) as r:
        r.raise_for_status()
        if r.headers.get("Content-Type", "").startswith("text/html"):
            raise IOError(f"Drive id {file_id} sent a web page, not {path.name} (quota or wrong id?)")
        modified = r.headers.get("Last-Modified")
        with open(part, "wb") as f:
            for chunk in r.iter_content(CHUNK_BYTES):
                f.write(chunk)
    signature = FILE_SIGNATURES.get(path.suffix)
    if signature:
        with open(part, "rb") as f:
            first_bytes = f.read(len(signature))
        if first_bytes != signature:
            raise IOError(f"Drive id {file_id} did not return a {path.suffix} file (quota or wrong id?); "
                          f"see {part}")
    part.replace(path)
    print(f"downloaded {path.name} ({path.stat().st_size:,} bytes, Drive Last-Modified {modified})")
    return modified


def zip_path(return_period):
    """Where the zip of one map is saved: data/raw/noah/MetroManila_<T>yr.zip."""
    return config.NOAH_RAW / f"MetroManila_{return_period}yr.zip"


def shapefile_in(zip_file):
    """The .shp inside a zip, and the date written on it inside the zip."""
    with zipfile.ZipFile(zip_file) as z:
        shp = [info for info in z.infolist() if info.filename.lower().endswith(".shp")]
    if len(shp) != 1:
        raise ValueError(f"{zip_file.name} holds {len(shp)} shapefiles, expected 1")
    return shp[0].filename, datetime(*shp[0].date_time)


def read_map(return_period):
    """Read one NOAH map as published (EPSG:4326, one or more rows per Var)."""
    zip_file = zip_path(return_period)
    shp, _ = shapefile_in(zip_file)
    hazard = gpd.read_file(f"zip://{zip_file.as_posix()}!{shp}")
    if hazard.crs is None or hazard.crs.to_epsg() != 4326:
        raise ValueError(f"{shp}: expected EPSG:4326, got {hazard.crs}")
    levels = set(hazard["Var"].astype(int))
    if not levels <= set(config.NOAH_HAZARD_LEVELS):
        raise ValueError(f"{shp}: unexpected Var values {sorted(levels)}")
    return hazard


def separate_levels(hazard):
    """Remove the overlaps between the hazard levels of one map: the higher level keeps the area.

    In plain words: Var 3 stays as it is, Var 2 loses what Var 3 covers, and Var 1 loses
    what Var 2 and Var 3 cover. NOAH's own 100-year map has 0.80 km2 where two levels
    overlap (the 25-year map 0.0003 km2, the 5-year map none), and C2 adds residents level
    by level, so anyone living there would be counted twice. Every level has the same
    contact rate in C5 (config.CONTACT_BY_LEVEL), so which level keeps the area does not
    change the doses; only removing the double count does.
    """
    shapes = dict(zip(hazard["var"], hazard.geometry))
    separated = {}
    for var, shape in shapes.items():
        for higher in (v for v in shapes if v > var):
            shape = shape.difference(shapes[higher])
        separated[var] = shape
    hazard = hazard.copy()
    hazard["geometry"] = hazard["var"].map(separated)
    return hazard


def clean_map(hazard, return_period):
    """Reproject to EPSG:32651, repair the shapes, dissolve to one row per Var, separate the levels.

    make_valid can turn a broken polygon into a mix of polygons, lines and points;
    only the polygons have area, so lines and points are dropped. (Checked on the 2026-10-15
    files: the repair keeps every level's published area; NOAH's shapes are invalid because
    their rings cross or touch themselves, not because parts overlap.)
    """
    hazard = hazard.to_crs(config.CRS_OVERLAY)
    hazard["geometry"] = hazard.geometry.make_valid()
    hazard = hazard.explode(index_parts=False)
    hazard = hazard[hazard.geom_type.isin(["Polygon", "MultiPolygon"])]
    hazard["var"] = hazard["Var"].astype(int)
    hazard = hazard[["var", "geometry"]].dissolve(by="var").reset_index()
    hazard = separate_levels(hazard)
    if not hazard.is_valid.all():
        raise ValueError(f"{return_period}-year map: shapes still invalid after make_valid")
    hazard.insert(0, "return_period", return_period)
    return hazard


def level_overlaps(hazard):
    """Area (km2) where two hazard levels of the same map overlap; 0 after separate_levels.

    C2 adds residents level by level, so an overlap would count people twice.
    """
    shapes = dict(zip(hazard["var"], hazard.geometry))
    texts = []
    for a, b in combinations(sorted(shapes), 2):
        km2 = shapes[a].intersection(shapes[b]).area / 1e6
        texts.append(f"Var {a}/{b}: {km2:.4f} km2")
    return ", ".join(texts)


def main():
    config.NOAH_RAW.mkdir(parents=True, exist_ok=True)
    for name, file_id in config.NOAH_METADATA_FILES.items():
        drive_download(file_id, config.NOAH_RAW / name)
    for return_period, file_id in config.NOAH_FLOOD_FILES.items():
        drive_download(file_id, zip_path(return_period))

    maps = []
    for return_period in config.NOAH_RETURN_PERIODS:
        shp, shp_date = shapefile_in(zip_path(return_period))
        raw = read_map(return_period)
        clean = clean_map(raw, return_period)
        clean["area_km2"] = clean.area / 1e6
        print(f"\n{return_period}-year map: {shp}, dated {shp_date:%Y-%m-%d} inside the zip; "
              f"{len(raw)} rows, {(~raw.is_valid).sum()} invalid as published")
        print("  " + ", ".join(f"Var {v}: {a:.2f} km2" for v, a in zip(clean["var"], clean["area_km2"])))
        print(f"  overlaps between levels: {level_overlaps(clean)}")
        maps.append(clean)

    flood = gpd.GeoDataFrame(pd.concat(maps, ignore_index=True), crs=config.CRS_OVERLAY)
    totals = flood.groupby("return_period")["area_km2"].sum()
    print("\nflooded area, all levels: " + ", ".join(f"{t}-year {a:.2f} km2" for t, a in totals.items()))
    if not totals.is_monotonic_increasing:
        print("  NOTE: a rarer storm floods less area than a commoner one; inspect before C2")

    config.NOAH_FLOOD.unlink(missing_ok=True)
    flood.to_file(config.NOAH_FLOOD, layer="flood_hazard", driver="GPKG")
    print(f"wrote {config.NOAH_FLOOD} ({len(flood)} rows)")


if __name__ == "__main__":
    main()

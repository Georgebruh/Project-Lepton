"""NOAH's flood hazard maps for the whole Philippines, as map tiles for the app."""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path, PureWindowsPath

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely

import config
from src.noah import drive_download

FOLDER_VIEW = "https://drive.google.com/embeddedfolderview?id={folder}"
TIMEOUT_S = 60
METRES_PER_DEGREE = 111_320          # of latitude; of longitude, times the cosine of the latitude
DOWNLOADS_AHEAD = 2                  # zips downloading at once while one is prepared (Drive sends each slowly)
DOWNLOAD_ATTEMPTS = 5
RETRY_WAIT_S = 15
ENTRY = re.compile(r'href="https://drive\.google\.com/file/d/([^/]+)/[^"]*"[^>]*>.*?flip-entry-title">([^<]+)<'
                   r'.*?flip-entry-last-modified"><div>([^<]*)<', re.S)
MONTHS = {name: i for i, name in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}
MANIFEST_COLUMNS = ["return_period", "province", "file_name", "drive_id", "drive_modified",
                    "shapefiles", "features", "patches", "area_km2", "prepared_on"]


# Listing NOAH's Drive folders

def drive_date(text, today):
    """Drive's "last modified" as a date: "11/11/21" as written, "Apr 8" this year, a time ("3:45 PM") today."""
    text = text.strip()
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2}", text):
        return datetime.strptime(text, "%m/%d/%y").date()
    month_day = re.fullmatch(r"([A-Z][a-z]{2}) (\d{1,2})", text)
    if month_day:
        return date(today.year, MONTHS[month_day.group(1)], int(month_day.group(2)))
    return today


def province_key(file_name):
    """A province's name without spaces, underscores, case or ".zip", so "Misamis Oriental.zip" = "MisamisOriental.zip"."""
    return re.sub(r"[\s_]+", "", file_name.removesuffix(".zip")).lower()


def list_folder(return_period):
    """The province zips of one map's Drive folder: one row per province (the newer file where one appears twice)."""
    folder = config.NOAH_NATIONAL_FOLDERS[return_period]
    page = requests.get(FOLDER_VIEW.format(folder=folder), timeout=TIMEOUT_S)
    page.raise_for_status()
    today = date.today()
    rows = [{"return_period": return_period, "province": province_key(name), "file_name": name.strip(),
             "drive_id": file_id, "drive_modified": drive_date(modified, today)}
            for file_id, name, modified in ENTRY.findall(page.text) if name.strip().lower().endswith(".zip")]
    if not rows:
        raise IOError(f"NOAH's {return_period}-year folder listed no zips: has Drive changed its page?")
    files = pd.DataFrame(rows).sort_values(["province", "drive_modified"])
    return files.drop_duplicates("province", keep="last").reset_index(drop=True)


# Preparing one province

def prepared_path(return_period, province):
    """Where one province's patches go: data/clean/noah_national/<T>yr/<province>.fgb."""
    return config.NOAH_NATIONAL_CLEAN / f"{return_period}yr" / f"{province}.fgb"


def hazard_column(columns):
    """The name of the hazard level column; NOAH writes `Var`, but a few provinces use another case."""
    for name in columns:
        if name.lower() == "var":
            return name
    raise ValueError(f"no Var column among {list(columns)}")


def read_zip(zip_file):
    """Every shapefile in one NOAH zip as one GeoDataFrame in EPSG:4326, with counts."""
    with zipfile.ZipFile(zip_file) as z:
        shapefiles = [name for name in z.namelist() if name.lower().endswith(".shp")]
    if not shapefiles:
        return None, 0, 0
    parts = []
    for shp in shapefiles:
        hazard = gpd.read_file(f"zip://{Path(zip_file).as_posix()}!{shp}")
        if hazard.crs is None:
            raise ValueError(f"{zip_file.name}!{shp} has no CRS")
        hazard = hazard.rename(columns={hazard_column(hazard.columns): "var"})[["var", "geometry"]]
        parts.append(hazard.to_crs(config.CRS_LONLAT))
    hazard = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=config.CRS_LONLAT)
    features = len(hazard)
    hazard["var"] = pd.to_numeric(hazard["var"], errors="coerce")
    hazard = hazard[hazard["var"].isin(config.NOAH_HAZARD_LEVELS)].astype({"var": "int8"})
    return hazard, len(shapefiles), features


def square_metres(shapes):
    """The area of shapes in longitude/latitude degrees, in m2."""
    xmin, ymin, xmax, ymax = shapely.bounds(shapes).T
    return shapely.area(shapes) * METRES_PER_DEGREE ** 2 * np.cos(np.radians((ymin + ymax) / 2))


def flood_patches(hazard):
    """The map's separate flood patches, without the smallest, lightly simplified (EPSG:4326)."""
    parts, row = shapely.get_parts(hazard.geometry.values, return_index=True)
    var = hazard["var"].to_numpy()[row]
    polygon = shapely.get_type_id(parts) == shapely.GeometryType.POLYGON
    parts, var = parts[polygon], var[polygon]
    big = square_metres(parts) >= config.APP_NOAH_MIN_M2
    parts, var = parts[big], var[big]
    parts = shapely.simplify(parts, config.NOAH_NATIONAL_PRESIMPLIFY_M / METRES_PER_DEGREE)
    kept = ~shapely.is_empty(parts)
    return gpd.GeoDataFrame({"var": var[kept]}, geometry=parts[kept], crs=config.CRS_LONLAT)


def prepare(row, zip_file):
    """Prepare one province's zip into its FlatGeobuf; returns its manifest row."""
    hazard, shapefiles, features = read_zip(zip_file)
    if hazard is None:
        print(f"{row['return_period']}-year {row['file_name']}: an empty zip on NOAH's Drive, left out")
        return {**row, "shapefiles": 0, "features": 0, "patches": 0, "area_km2": 0.0,
                "prepared_on": date.today().isoformat()}
    if features == 0:
        print(f"{row['return_period']}-year {row['file_name']}: NOAH's shapefile holds no shapes")
    patches = flood_patches(hazard)
    path = prepared_path(row["return_period"], row["province"])
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")   # "<province>.fgb.part": tile()'s *.fgb never picks up half a file
    part.unlink(missing_ok=True)
    patches.to_file(part, driver="FlatGeobuf")
    part.replace(path)
    area = patches.to_crs(config.CRS_OVERLAY).area.sum() / 1e6
    return {**row, "shapefiles": shapefiles, "features": features, "patches": len(patches), "area_km2": round(area, 2),
            "prepared_on": date.today().isoformat()}


def read_manifest():
    """The provinces prepared so far (data/clean/noah_national/manifest.csv); empty if none."""
    path = config.NOAH_NATIONAL_CLEAN / "manifest.csv"
    if not path.exists():
        return pd.DataFrame(columns=MANIFEST_COLUMNS)
    return pd.read_csv(path, dtype={"drive_id": str})


def write_manifest(manifest):
    path = config.NOAH_NATIONAL_CLEAN / "manifest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest[MANIFEST_COLUMNS].sort_values(["return_period", "province"]).to_csv(path, index=False)


def prepare_all(order):
    """Download and prepare every province not yet prepared from today's Drive file, map by map in `order`."""
    manifest = read_manifest()
    done = {(int(r.return_period), r.drive_id) for r in manifest.itertuples()
            if r.shapefiles == 0 or prepared_path(int(r.return_period), r.province).exists()}
    todo = [row for return_period in order
            for row in list_folder(return_period).to_dict("records")
            if (return_period, row["drive_id"]) not in done]
    print(f"{len(todo)} province maps to prepare ({len(done)} already prepared)")
    config.NOAH_NATIONAL_CLEAN.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=config.NOAH_NATIONAL_CLEAN) as temp, ThreadPoolExecutor(DOWNLOADS_AHEAD) as pool:
        def fetch(row):
            path = Path(temp) / f"{row['return_period']}yr_{row['province']}.zip"
            for attempt in range(DOWNLOAD_ATTEMPTS):   # a slow line drops a connection now and then
                try:
                    drive_download(row["drive_id"], path)
                    return path
                except requests.RequestException as error:
                    if attempt == DOWNLOAD_ATTEMPTS - 1:
                        raise
                    print(f"{path.name}: {error}; trying again in {RETRY_WAIT_S} s")
                    time.sleep(RETRY_WAIT_S)
        downloads = [pool.submit(fetch, row) for row in todo[:DOWNLOADS_AHEAD]]
        for i, row in enumerate(todo):
            zip_file = downloads[i].result()
            if i + DOWNLOADS_AHEAD < len(todo):
                downloads.append(pool.submit(fetch, todo[i + DOWNLOADS_AHEAD]))
            try:
                entry = prepare(row, zip_file)
            finally:
                zip_file.unlink(missing_ok=True)
            manifest = pd.concat([manifest[~((manifest["return_period"] == row["return_period"])
                                             & (manifest["province"] == row["province"]))],
                                  pd.DataFrame([entry])], ignore_index=True)
            write_manifest(manifest)
            print(f"[{i + 1}/{len(todo)}] {row['return_period']}-year {row['file_name']}: "
                  f"{entry['patches']:,} patches, {entry['area_km2']:,.1f} km2")


# Tiling

def tile_path(return_period):
    """The app's tiles of one map: app/public/data/noah_flood_<T>yr.pmtiles."""
    return config.APP_DATA / config.APP_NOAH_TILES.format(return_period=return_period)


def wsl_path(path):
    r"""A Windows path as WSL sees it: C:\Users\x becomes /mnt/c/Users/x."""
    windows = PureWindowsPath(Path(path).resolve())
    return f"/mnt/{windows.drive[0].lower()}/" + "/".join(windows.parts[1:])


def tippecanoe(arguments):
    """Run tippecanoe with these arguments (paths as Path objects): natively, or on Windows in WSL."""
    if shutil.which("tippecanoe"):
        command = ["tippecanoe", *[str(a) for a in arguments]]
    elif sys.platform == "win32":
        # bash runs it from the WSL folder it was built in, with the arguments passed on unchanged ("$@")
        run = f'PATH="{config.TIPPECANOE_WSL_DIR}:$PATH" exec tippecanoe "$@"'
        command = ["wsl", "-e", "bash", "-c", run, "tippecanoe",
                   *[wsl_path(a) if isinstance(a, Path) else a for a in arguments]]
    else:
        raise SystemExit("tippecanoe not found: install it (https://github.com/felt/tippecanoe)")
    subprocess.run(command, check=True)


def tile(return_period):
    """One map's provinces as one PMTiles file (layer "flood", attribute var)."""
    provinces = sorted((config.NOAH_NATIONAL_CLEAN / f"{return_period}yr").glob("*.fgb"))
    if not provinces:
        raise SystemExit(f"no prepared provinces for the {return_period}-year map: run without --tile first")
    path = tile_path(return_period)
    part = path.with_name(path.stem + ".part.pmtiles")
    low, high = config.NOAH_TILE_ZOOMS
    for limit in config.NOAH_TILE_LIMITS:
        part.unlink(missing_ok=True)
        # tippecanoe's temporary files (a few GB) go in its own /tmp.
        tippecanoe(["-o", part, "--force", "--quiet", "-l", "flood", "-y", "var",
                    f"-Z{low}", f"-z{high}", f"-D{config.NOAH_TILE_DETAIL}", f"--maximum-tile-bytes={limit}",
                    "--drop-smallest-as-needed", "--no-tile-stats", f"--name=NOAH {return_period}-year flood hazard",
                    f"--description=tiles of at most {limit:,} bytes",
                    "--attribution=UP Resilience Institute / NOAH Center (ODbL)", *provinces])
        size = part.stat().st_size
        if size <= config.APP_NOAH_TILES_MAX_BYTES:
            part.replace(path)
            print(f"wrote {path.name}: {len(provinces)} provinces, {size / 1e6:.1f} MB, tiles of at most {limit:,} bytes")
            return
        print(f"{part.name}: {size / 1e6:.0f} MB with tiles of at most {limit:,} bytes, over "
              f"{config.APP_NOAH_TILES_MAX_BYTES / 1e6:.0f} MB; trying the next")
    part.unlink(missing_ok=True)
    raise ValueError(f"the {return_period}-year map stays over {config.APP_NOAH_TILES_MAX_BYTES / 1e6:.0f} MB "
                     f"at every tile limit in config.NOAH_TILE_LIMITS: lower config.NOAH_TILE_ZOOMS")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tile", action="store_true", help="tile again from the prepared provinces only")
    parser.add_argument("--maps", type=int, nargs="+", default=list(config.NOAH_RETURN_PERIODS),
                        choices=config.NOAH_RETURN_PERIODS, help="which maps, in this order (default: all)")
    args = parser.parse_args()
    for return_period in args.maps:   # each map is tiled as soon as its provinces are ready
        if not args.tile:
            prepare_all([return_period])
        tile(return_period)


if __name__ == "__main__":
    main()

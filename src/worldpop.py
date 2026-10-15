"""WorldPop 2024 population grid, clipped to the rain box (task A6).

Downloads WorldPop's constrained 2024 population counts for the Philippines (100 m,
release R2025A v1) into data/raw/, unchanged, and saves a copy clipped to
config.IMERG_BOX (the A4 rain box) in data/clean/.

Each pixel holds the estimated number of people living in it in 2024. "Constrained"
means WorldPop only puts people in pixels with buildings; every other pixel is nodata.
The pixels are 3 arc-seconds (about 90 m here), in EPSG:4326.

Why the rain box and not just QC: C1 and C2 need the pixels inside QC's barangays, and
B4 needs the QC residents inside each IMERG cell, and some of those cells straddle the
city edge. The box holds all of them.

The clip keeps whole pixels: the box is widened to the next pixel edge, so no pixel is
cut and the pixel values are WorldPop's, unchanged.

Run from the repository root:
    python -m src.worldpop
The 63 MB download is skipped if the file is already in data/raw/ (e.g. copied from the
team drive), so the clip also runs offline.
"""

import math

import numpy as np
import rasterio
import requests
from rasterio.windows import Window

import config

TIMEOUT_S = 120
CHUNK_BYTES = 1 << 20


def download(url, path, expected_bytes):
    """Save url to path, unchanged, and check it is the copy the project uses.

    The copy used is recorded by its size, expected_bytes (config.WORLDPOP_BYTES, also in
    the file's note in data/raw/). If path is already there with that size, nothing is
    downloaded. A file of any other size, on disk or from the server, stops the run instead
    of replacing the raw file: WorldPop calls R2025A an alpha release, so the server's file
    can change, and every result must come from the recorded copy.

    Writes to path + ".part" first and renames at the end, so a stopped download
    never leaves a half file under the real name.
    """
    if path.exists():
        size = path.stat().st_size
        if size != expected_bytes:
            raise IOError(f"{path} has {size:,} bytes, expected {expected_bytes:,}; "
                          "replace it with the team drive's copy")
        print(f"{path.name} already downloaded ({size:,} bytes)")
        return
    part = path.with_name(path.name + ".part")
    with requests.get(url, stream=True, timeout=TIMEOUT_S) as r:
        r.raise_for_status()
        with open(part, "wb") as f:
            for chunk in r.iter_content(CHUNK_BYTES):
                f.write(chunk)
    size = part.stat().st_size
    if size != expected_bytes:
        raise IOError(f"{part.name} has {size:,} bytes, expected {expected_bytes:,}: the download "
                      "stopped early or WorldPop changed the file; use the team drive's copy")
    part.replace(path)
    print(f"downloaded {path.name} ({size:,} bytes)")


def box_window(src, box):
    """The window of whole pixels that covers box = (lon_min, lat_min, lon_max, lat_max).

    The box edges are moved outward to the next pixel edge, so every pixel touching
    the box is kept whole.
    """
    lon_min, lat_min, lon_max, lat_max = box
    left, bottom, right, top = src.bounds
    if not (left <= lon_min and lon_max <= right and bottom <= lat_min and lat_max <= top):
        raise ValueError(f"box {box} is not inside the grid {tuple(src.bounds)}")
    inverse = ~src.transform                      # (lon, lat) -> (column, row)
    col_start, row_start = inverse * (lon_min, lat_max)   # top-left corner
    col_end, row_end = inverse * (lon_max, lat_min)       # bottom-right corner
    col_start, row_start = math.floor(col_start), math.floor(row_start)
    col_end, row_end = math.ceil(col_end), math.ceil(row_end)
    return Window(col_start, row_start, col_end - col_start, row_end - row_start)


def clip(src_path, dst_path, box):
    """Copy the pixels of src_path inside box to dst_path (GeoTIFF, same values and nodata)."""
    with rasterio.open(src_path) as src:
        window = box_window(src, box)
        pixels = src.read(1, window=window)
        profile = src.profile.copy()
        profile.update(
            height=window.height, width=window.width,
            transform=src.window_transform(window),
            compress="lzw", tiled=False,
        )
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)
    with rasterio.open(dst_path, "w", **profile) as dst:
        dst.write(pixels, 1)


def describe(path):
    """Print the clipped grid's size, edges and total people, so the run can be checked by eye."""
    with rasterio.open(path) as src:
        pixels = src.read(1, masked=True)
        left, bottom, right, top = src.bounds
        print(f"{path.name}: {src.width} x {src.height} pixels, {src.crs}, "
              f"pixel {src.res[0]:.6f} deg, nodata {src.nodata}")
        print(f"  edges lon {left:.4f} to {right:.4f}, lat {bottom:.4f} to {top:.4f}")
        print(f"  {pixels.count():,} pixels with people, {np.ma.count_masked(pixels):,} nodata; "
              f"total {float(pixels.sum()):,.0f} people in the box")
        if (pixels < 0).any():
            raise ValueError("negative population in a pixel")


def main():
    download(config.WORLDPOP_URL, config.WORLDPOP, config.WORLDPOP_BYTES)
    clip(config.WORLDPOP, config.WORLDPOP_BOX, config.IMERG_BOX)
    describe(config.WORLDPOP_BOX)
    print(f"wrote {config.WORLDPOP_BOX}")


if __name__ == "__main__":
    main()

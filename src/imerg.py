"""IMERG Late daily rain over Quezon City's catchments."""

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import netCDF4
import numpy as np
import pandas as pd
import requests
import xarray as xr

import config

CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
CMR_PAGE_SIZE = 2000                    # the most CMR returns per request
EARTHDATA_LOGIN = "https://urs.earthdata.nasa.gov"
HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"   # first 8 bytes of every netCDF-4 file
TIMEOUT_S = 120
RETRIES = 3
RETRY_WAIT_S = 10

LOGIN_HELP = f"""Check your Earthdata login (steps at the top of src/imerg.py):
  - {config.EARTHDATA_TOKEN_FILE} holds a token from "Generate Token" at
    https://urs.earthdata.nasa.gov, less than 60 days old (or generate a new one)
  - "NASA GESDISC DATA ARCHIVE" is approved under Applications > Authorized Apps"""


class LoginError(Exception):
    """NASA refused the login."""


class DownloadError(Exception):
    """The server answered, but not with a netCDF file."""


def find_granules(start, end):
    """Every IMERG Late daily file from start to end (dates), from NASA's catalogue (CMR)."""
    params = {
        "short_name": config.IMERG_PRODUCT,
        "version": config.IMERG_VERSION,
        "temporal": f"{start:%Y-%m-%d}T00:00:00Z,{end:%Y-%m-%d}T23:59:59Z",
        "sort_key": "start_date",
        "page_size": CMR_PAGE_SIZE,
    }
    headers = {}
    rows = []
    while True:
        r = requests.get(CMR_GRANULES, params=params, headers=headers, timeout=TIMEOUT_S)
        r.raise_for_status()
        items = r.json()["items"]
        if not items:
            break
        for item in items:
            umm = item["umm"]
            begin = umm["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
            opendap = [u["URL"] for u in umm["RelatedUrls"] if u.get("Subtype") == "OPENDAP DATA"]
            rows.append({
                "date": pd.Timestamp(begin[:10]),
                "granule": umm["GranuleUR"].split(":")[-1],
                "url": opendap[0],
            })
        # CMR sends one page at a time; this header asks for the page after this one
        headers = {"CMR-Search-After": r.headers["CMR-Search-After"]}

    table = pd.DataFrame(rows)
    if table.empty:
        raise SystemExit(f"CMR lists no {config.IMERG_PRODUCT} files from {start} to {end}")
    if table["date"].duplicated().any():
        raise ValueError(f"CMR lists two files for one day:\n{table[table['date'].duplicated(keep=False)]}")
    return table.sort_values("date").reset_index(drop=True)


def earthdata_session():
    """A requests session that logs in to NASA Earthdata."""
    session = requests.Session()
    token_file = config.EARTHDATA_TOKEN_FILE
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8-sig").strip()  # utf-8-sig: ignore a Notepad BOM
        session.headers["Authorization"] = f"Bearer {token}"
    elif requests.utils.get_netrc_auth(EARTHDATA_LOGIN) is None:
        raise SystemExit(f"No Earthdata login: {token_file} not found (and no netrc file).\n{LOGIN_HELP}")
    return session


def fetch(session, url, constraint, path):
    """Download one OPeNDAP subset of one daily file and save it at path (netCDF-4)."""
    r = session.get(
        url + ".dap.nc4",
        params={"dap4.ce": constraint},
        headers={"Accept-Encoding": "identity"},  # PO.DAAC's workaround for compressed replies
        timeout=TIMEOUT_S,
    )
    if r.status_code in (401, 403) or r.url.startswith(EARTHDATA_LOGIN):
        raise LoginError(f"HTTP {r.status_code} from {r.url}\n{LOGIN_HELP}")
    r.raise_for_status()
    if not r.content.startswith(HDF5_SIGNATURE):
        raise DownloadError(f"expected a netCDF file, got: {r.text[:300]!r}\n{LOGIN_HELP}")
    part = path.with_suffix(".part")
    part.write_bytes(r.content)
    part.replace(path)


def download(session, url, constraint, path):
    """fetch() with up to RETRIES tries, waiting a little longer after each failure."""
    for attempt in range(1, RETRIES + 1):
        try:
            return fetch(session, url, constraint, path)
        except LoginError:
            raise
        except (requests.RequestException, DownloadError):
            if attempt == RETRIES:
                raise
            time.sleep(RETRY_WAIT_S * attempt)


def read_grid(session, url, folder):
    """IMERG's full lon and lat axes, and the order of the rain variables' dimensions."""
    axes_path = folder / "grid_axes.nc4"
    download(session, url, "lon;lat", axes_path)
    with xr.open_dataset(axes_path) as ds:
        lon, lat = ds["lon"].values, ds["lat"].values

    order_path = folder / "grid_order.nc4"
    one_cell = ["time[0:1:0]", "lon[0:1:0]", "lat[0:1:0]"]
    one_cell += [f"{v}[0:1:0][0:1:0][0:1:0]" for v in config.IMERG_VARIABLES]
    download(session, url, ";".join(one_cell), order_path)
    with xr.open_dataset(order_path, decode_times=False) as ds:
        orders = {v: ds[v].dims for v in config.IMERG_VARIABLES}

    dims = orders[config.IMERG_VARIABLES[0]]
    if set(dims) != {"time", "lon", "lat"} or len(set(orders.values())) != 1:
        raise ValueError(f"unexpected dimensions {orders}; expected time, lon and lat")
    return lon, lat, dims


def box_ranges(lon, lat, box):
    """First and last index, per axis, of the cells whose centres lie inside the box."""
    lon_min, lat_min, lon_max, lat_max = box
    ranges = {"time": (0, 0)}  # a daily file holds one time step
    for name, axis, low, high in (("lon", lon, lon_min, lon_max), ("lat", lat, lat_min, lat_max)):
        inside = np.flatnonzero((axis > low) & (axis < high))
        if len(inside) == 0 or inside[-1] - inside[0] + 1 != len(inside):
            raise ValueError(f"box {box} does not cover one unbroken run of {name} cells")
        ranges[name] = (int(inside[0]), int(inside[-1]))
    return ranges


def day_constraint(dims, ranges):
    """The DAP4 request for one day: each rain variable over the box, plus its axes."""
    def cut(dim):
        first, last = ranges[dim]
        return f"[{first}:1:{last}]"

    variables = [v + "".join(cut(d) for d in dims) for v in config.IMERG_VARIABLES]
    axes = [d + cut(d) for d in dims]
    return ";".join(variables + axes)


def day_path(folder, day):
    """Where one day's subset is saved, e.g. data/raw/imerg_daily/imerg_20240723.nc4."""
    return folder / f"imerg_{day:%Y%m%d}.nc4"


def read_day(path, day):
    """One day's subset, labelled with its UTC day from the catalogue."""
    data_vars = {}
    with netCDF4.Dataset(path) as nc:
        for name in config.IMERG_VARIABLES:
            var = nc[name]
            if set(var.dimensions) != {"time", "lon", "lat"}:
                raise ValueError(f"{path.name}: {name} has dimensions {var.dimensions}")
            values = var[:]
            if np.ma.is_masked(values):
                values = values.astype("float32").filled(np.nan)
            attrs = {k: var.getncattr(k) for k in var.ncattrs() if k != "_FillValue"}
            data_vars[name] = (var.dimensions, np.asarray(values), attrs)
        coords = {"time": [pd.Timestamp(day)], "lon": np.asarray(nc["lon"][:]), "lat": np.asarray(nc["lat"][:])}
    return xr.Dataset(data_vars, coords=coords)


def download_all(session, granules, constraint, folder, workers):
    """Download every day not yet on disk, several at once."""
    todo = [row for row in granules.itertuples() if not day_path(folder, row.date).exists()]
    print(f"{len(granules) - len(todo)} days already on disk, {len(todo)} to download")
    if not todo:
        return

    # The first day on its own: a login or file problem shows up now, not hours later.
    first = todo.pop(0)
    download(session, first.url, constraint, day_path(folder, first.date))
    read_day(day_path(folder, first.date), first.date)

    failed = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {
            pool.submit(download, session, row.url, constraint, day_path(folder, row.date)): row.date
            for row in todo
        }
        for n, job in enumerate(as_completed(jobs), start=1):
            try:
                job.result()
            except LoginError:
                pool.shutdown(cancel_futures=True)
                raise
            except Exception as e:
                failed.append(jobs[job])
                print(f"  {jobs[job]:%Y-%m-%d} failed: {type(e).__name__}: {e}")
            if n % 250 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)} days, {(time.time() - started) / 60:.0f} min")

    if failed:
        raise SystemExit(f"{len(failed)} days failed (first {min(failed):%Y-%m-%d}). "
                         "Run the same command again: it retries only the missing days.")


def combine(granules, folder):
    """Stack the daily files into one dataset, keeping IMERG's own dimension order."""
    days = [read_day(day_path(folder, row.date), row.date) for row in granules.itertuples()]
    # join="exact": stop if any day sits on different cells from the others
    ds = xr.concat(days, dim="time", data_vars="all", coords="minimal", compat="override", join="exact")
    ds["granule"] = ("time", granules["granule"].to_numpy(dtype=str))
    ds["granule"].attrs["long_name"] = "NASA file each day came from (V07B, V07C: release label)"
    ds["time"].attrs["long_name"] = "UTC day: 00:00-24:00 UTC = 8 AM-8 AM Philippine time"
    lon_min, lat_min, lon_max, lat_max = config.IMERG_BOX
    ds.attrs = {
        "title": "IMERG Late daily rain over Quezon City's catchments (task A4)",
        "source": f"NASA GES DISC {config.IMERG_PRODUCT} version {config.IMERG_VERSION}, "
                  "subset through OPeNDAP (opendap.earthdata.nasa.gov)",
        "box": f"lon {lon_min} to {lon_max}, lat {lat_min} to {lat_max} (cell edges)",
        "dimensions": "IMERG's own order; select by name, never by position (rule 8)",
        "created": date.today().isoformat(),
        "created_by": "src/imerg.py",
    }
    return ds


def save(ds, path):
    """Write the dataset compressed, under a temporary name first, then rename it."""
    for name in ds.variables:
        ds[name].encoding = {}
    part = path.with_suffix(".part")
    ds.to_netcdf(part, encoding={v: {"zlib": True} for v in config.IMERG_VARIABLES})
    part.replace(path)


def output_path(full_run, granules):
    """Where the stacked file is saved."""
    if full_run:
        return config.IMERG_DAILY
    first, last = granules["date"].iloc[0], granules["date"].iloc[-1]
    return config.IMERG_DAILY.with_name(f"imerg_daily_{first:%Y%m%d}_{last:%Y%m%d}.nc")


def parse_args():
    p = argparse.ArgumentParser(description="Download IMERG Late daily rain over the A4 box (task A4).")
    p.add_argument("--start", type=date.fromisoformat,
                   help=f"first UTC day, YYYY-MM-DD (default {config.IMERG_START}); "
                        "a test run, saved under its own name")
    p.add_argument("--end", type=date.fromisoformat,
                   help="last UTC day, YYYY-MM-DD (default: the latest NASA has); "
                        "a test run, saved under its own name")
    p.add_argument("--workers", type=int, default=config.IMERG_DOWNLOAD_WORKERS,
                   help=f"downloads at once (default {config.IMERG_DOWNLOAD_WORKERS})")
    return p.parse_args()


def main():
    args = parse_args()
    full_run = args.start is None and args.end is None
    granules = find_granules(args.start or config.IMERG_START, args.end or date.today())
    print(f"CMR lists {len(granules)} days, {granules['date'].iloc[0]:%Y-%m-%d} "
          f"to {granules['date'].iloc[-1]:%Y-%m-%d}")

    folder = config.IMERG_SUBSETS
    folder.mkdir(parents=True, exist_ok=True)
    session = earthdata_session()
    lon, lat, dims = read_grid(session, granules["url"].iloc[0], folder)
    ranges = box_ranges(lon, lat, config.IMERG_BOX)
    constraint = day_constraint(dims, ranges)
    print(f"dimension order in the file: {dims}")
    print(f"request per day: {constraint}")

    download_all(session, granules, constraint, folder, args.workers)
    ds = combine(granules, folder)
    out = output_path(full_run, granules)
    save(ds, out)

    box_mean = ds["precipitation"].mean(dim=["lon", "lat"])
    wettest = box_mean.idxmax(dim="time").values
    print(f"\n{ds.sizes['time']} days x {ds.sizes['lon']} lon x {ds.sizes['lat']} lat cells")
    print(f"wettest day (box average): {pd.Timestamp(wettest):%Y-%m-%d}, {float(box_mean.max()):.1f} mm")
    if full_run:
        print(f"wrote {out}; now run: python -m src.checks")
    else:
        print(f"wrote {out} (test run; {config.IMERG_DAILY.name} was not changed)")


if __name__ == "__main__":
    main()

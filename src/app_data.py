"""The data files the web app reads (task F2). Stock planning, not prescriptions.

The LEPTON app (app/, Workstream F) is a static site with no server: it only draws the
numbers this script writes, so the app and the model never disagree. Every number comes
from results/ (C8, C9 and B10's backtest) or from A5's and
A10's files. Nothing about rain, exposure, doses or forecasts is computed again here, and
barangays and cities join on their 10-digit PSGC.

Files written to app/public/data/ (config.APP_DATA), which the app fetches as /data/<file>:

  ph_cities.json        F14: the outlines of the Philippines' 1,642 cities and municipalities
                        (PSGC as of 2023, from faeldon/philippines-json-maps, MIT): psgc, name,
                        province and has_data (only Quezon City has data). NCR's 17 are cleaned
                        into one coverage with no gaps or overlaps, Quezon City's outline being
                        A5's barangays joined, so the map lines up when it drills down
                        (map_shapes); the others are simplified province by province
                        (province_cities, towns_apart). Also label_lon and label_lat, where the
                        map writes the name of a city with data (F4, label_points). It replaces
                        F4's ncr_cities.geojson
  ph_islands.json       F14: the coastline of every island of 1 km2 or more, the cities and
                        municipalities joined (island_outlines), for the map zoomed out
  qc_barangays.geojson  A5's 142 barangays: psgc and name
  storms.json           C9's runs of each storm: the rain that fell (observed, IMERG) and
                        the forecasts 1, 2 and 3 days ahead (ECMWF). Each run gives its
                        3-day window, rain, where the rain falls against the return levels,
                        EI and the barangays flagged, then residents exposed and the three
                        units for each flood: a short one (key D1: D = 1, w = 0.5) and a long
                        one (D7), the two C9 runs every forecast at; the observed run has
                        A11's D. Also (F15) C6's units per person, for the barangay report
  barangays/<storm>_<run>.json   one per run: each barangay's residents exposed, their share
                        of its 2024 residents, the map class, flagged, and the units per flood
  centers.json          A10's health centers (name, type, lat, lon, barangay), each run's
                        need per center and flood, and (F15) each barangay's health centers:
                        the share of its need each one holds, as C7 sends it
  city_forecast.json    B10's forecasts per target week: the week's dates, the count y, the
                        threshold, and each model's mean, 90% range (the 5% and 95%
                        quantiles) and Pr(breach). From results/forecasts.csv; until it
                        exists, from the made-up-count run (config.FORECASTS_SIMULATED) with
                        "simulated": true. Also the map's model and outbreak levels (F4:
                        config.APP_LEVEL_MODEL, config.APP_LEVELS)
  scores.json           only from the real run: each model's MAE and MASE (2018-2019 and
                        2022-2026), WIS, 90% coverage and Brier score (2022-2026), and D5's
                        M4 - M3 difference with its 95% interval

The words behind the numbers:
  - residents exposed: C5's exposed people. share: the residents in zones the rain floods
    over the barangay's 2024 residents (C3's graded exposure), the measure behind the map
    class and the flag. A barangay is flagged at config.APP_FLAG_SHARE (25%) or more, as
    forecast_run.flagged decides. The classes break at config.APP_SHARE_BREAKS, and a share
    on a break goes to the class above (as on D7's maps), so classes 3 and 4 are the flagged.
  - units: doxy100 (doxycycline 100 mg capsules, adults), courses (children's courses) and
    amox500 (amoxicillin 500 mg tablets, pregnant women), as C6 counts them.
  - rounding: people and units are whole numbers. QC's and each barangay's are rounded to
    the nearest one; a health center's are rounded up, the level stock is ordered at
    (allocation.round_up, as D7 does), so the centers add up to a little more than QC.

Every file with doses carries doses.LABEL: stock-planning figures, not prescriptions (rule 10).

Two more of the app's files have their own scripts (F14): NOAH's flood tiles for the whole
country (python -m src.noah_national) and the Simulation mode's weeks (python -m src.app_simulation).
F13's Metro Manila overlays (noah_<T>yr.json) are gone: the tiles replace them.

Run from the repository root after C8 and C9 (and B10, or its --simulate run, for
city_forecast.json); a few seconds:
    python -m src.app_data
It downloads the NCR outlines once into data/raw/ncr_cities/, and the rest of the country's into
data/raw/ph_cities/. Commit app/public/data/ afterwards, so the deployed app gets the new files.
Check: python -m src.checks ("F2 app data").
"""

import json
from datetime import timedelta

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely
import shapely.ops

import config
from src import (allocation, backtest, breach_scores, compare, doses, exposed, forecast_run,
                 layer2_results, observed_run, scores, weeks)

UNITS = list(doses.UNITS)                         # doxy100, courses, amox500
OBSERVED = forecast_run.OBSERVED                  # C9's name for its observed (IMERG) run
FLAG_COLUMN = f"flagged_{100 * config.APP_FLAG_SHARE:.0f}"   # C9's count of barangays flagged at that share
MODEL_NAMES = {"M4_noEI": config.FLOOD_TEST[1]}   # B10's old name, in forecasts files written before Oct 21 (Notes.md 1.4)
MODELS = list(backtest.MODELS)                    # the order the app lists them in
SIMULATED_NOTE = "Made-up QC-shaped counts from B10's --simulate run, not QC data: no number here is a result."
INPUTS = {                                        # the files F2 reads, and the task that makes each
    config.C8_BARANGAYS: "C8: python -m src.observed_run",
    config.C9_RUNS: "C9: python -m src.forecast_run",
    config.C9_BARANGAYS: "C9: python -m src.forecast_run",
    config.C9_CENTERS: "C9: python -m src.forecast_run",
    config.CENTER_SHARES: "C7: python -m src.allocation",
    config.BARANGAYS_QC: "A5: python -m src.census",
    config.FACILITIES_QC: "A10: python -m src.facilities",
}
DOWNLOAD_TIMEOUT_S = 60
DOWNLOAD_ATTEMPTS = 3


def check_inputs():
    """Stop with one clear message that lists every input file not on this computer."""
    missing = [f"  {path}  ({task})" for path, task in INPUTS.items() if not path.exists()]
    if missing:
        raise SystemExit("F2 needs these files; run their task or copy them from the team drive:\n"
                         + "\n".join(missing))


def whole(value):
    """A count as a whole number, rounded to the nearest (halves up); float noise below 1e-6 is ignored."""
    return int(np.floor(round(float(value), 6) + 0.5))


def units_of(row):
    """The three units of one row, rounded to whole units: {"doxy100": ..., "courses": ..., "amox500": ...}."""
    return {unit: whole(row[unit]) for unit in UNITS}


# ---------------------------------------------------------------------------
# Map shapes
# ---------------------------------------------------------------------------

def download_ncr_cities():
    """The four NCR district files of city outlines, downloaded once into data/raw/ncr_cities/, unchanged.

    Stops unless each file has the pinned file's size (config.NCR_CITIES_BYTES), so a cut-off
    download, or a file from another commit, is never used.
    """
    config.NCR_CITIES_RAW.mkdir(parents=True, exist_ok=True)
    paths = []
    for district in config.NCR_DISTRICTS:
        url = config.NCR_CITIES_URL.format(district=district)
        path = config.NCR_CITIES_RAW / url.rsplit("/", 1)[1]
        if not path.exists():
            reply = requests.get(url, timeout=DOWNLOAD_TIMEOUT_S)
            reply.raise_for_status()
            part = path.with_name(path.name + ".part")
            part.write_bytes(reply.content)
            part.replace(path)
            print(f"downloaded {path.name}")
        if path.stat().st_size != config.NCR_CITIES_BYTES[district]:
            raise ValueError(f"{path} has {path.stat().st_size:,} bytes, not the pinned file's "
                             f"{config.NCR_CITIES_BYTES[district]:,}: delete it and rerun")
        paths.append(path)
    return paths


def load_cities(paths):
    """faeldon's 17 NCR cities and municipalities: psgc, name and the shape, as downloaded (EPSG:4326)."""
    raw = pd.concat([gpd.read_file(path) for path in paths], ignore_index=True)
    cities = gpd.GeoDataFrame({"psgc": raw["adm3_psgc"].astype("int64").astype(str).str.zfill(10),
                               "name": raw["adm3_en"]}, geometry=raw.geometry, crs=raw.crs)
    if len(cities) != config.NCR_CITY_COUNT or not cities["psgc"].is_unique:
        raise ValueError(f"expected {config.NCR_CITY_COUNT} NCR cities, one PSGC each; got {len(cities)} rows")
    if config.QC_CITY_PSGC not in set(cities["psgc"]):
        raise ValueError(f"Quezon City ({config.QC_CITY_PSGC}) is not among the NCR outlines")
    return cities.sort_values("psgc", ignore_index=True)


def load_barangays():
    """A5's 142 barangays: psgc, name and the shape (EPSG:4326, not simplified)."""
    shapes = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc", "adm4_name"])
    if len(shapes) != config.QC_BARANGAYS or not shapes["psgc"].is_unique:
        raise ValueError(f"{config.BARANGAYS_QC.name} must hold {config.QC_BARANGAYS} barangays, one each")
    return shapes.rename(columns={"adm4_name": "name"}).sort_values("psgc", ignore_index=True)


def biggest_neighbour(i, pieces, tree, owner, allowed):
    """The owner, among `allowed`, of the pieces sharing the longest border with piece i; None if none touches it."""
    shared = {}
    for j in tree.query(pieces[i], predicate="touches"):
        if owner[j] in allowed:
            shared[owner[j]] = shared.get(owner[j], 0.0) + pieces[i].boundary.intersection(pieces[j].boundary).length
    return max(shared, key=shared.get) if shared else None


def map_shapes(cities, barangays):
    """NCR's cities and Quezon City's barangays as one clean coverage, simplified once: (cities, barangays).

    faeldon simplified its four district files one at a time, so where two districts meet
    their borders do not match: about 90 slivers of gap and 0.2 km2 of overlap, up to about
    100 m wide. Its Quezon City also lies up to 161 m from A5's barangays, which the map
    shows when it drills down. So Quezon City is drawn from A5's barangays (EPSG:32651, metres):
      1. the borders of the other 16 cities and of the 142 barangays cut NCR into pieces;
      2. a piece inside a barangay goes to that barangay; any other piece to the city it lies
         in (an overlap goes to the first of the two, by PSGC);
      3. a piece in neither (a gap) goes to the neighbouring city it shares the longest border
         with, or failing one, to the neighbouring barangay; a piece with neither lies outside
         NCR and is dropped;
      4. each city and barangay is its pieces joined, and all of them are simplified together
         (GeoPandas simplify_coverage, Visvalingam-Whyatt): a point goes when the triangle it
         makes with its two neighbours is smaller than about config.MAP_SIMPLIFY_M squared,
         and a border two shapes share is simplified once, so it stays one line;
      5. Quezon City is its simplified barangays joined, so the city and barangay maps line up exactly.
    Returns two GeoDataFrames in EPSG:4326: cities (psgc, name, has_data) and barangays (psgc, name).
    """
    others = cities[cities["psgc"] != config.QC_CITY_PSGC].to_crs(config.CRS_OVERLAY).reset_index(drop=True)
    flat_barangays = barangays.to_crs(config.CRS_OVERLAY)
    keys = [("city", psgc) for psgc in others["psgc"]] + [("barangay", psgc) for psgc in flat_barangays["psgc"]]
    shapes = [*others.geometry, *flat_barangays.geometry]
    lines = shapely.union_all([shape.boundary for shape in shapes])
    pieces = list(shapely.get_parts(shapely.polygonize([lines])))
    in_shape = shapely.STRtree(shapes)
    owner = []
    for piece in pieces:
        hits = sorted(in_shape.query(piece.point_on_surface(), predicate="within"))
        hits = [i for i in hits if keys[i][0] == "barangay"] or hits   # a barangay wins over a city
        owner.append(keys[hits[0]] if hits else None)
    next_to = shapely.STRtree(pieces)
    for kind in ("city", "barangay"):
        allowed = {key for key in keys if key[0] == kind}
        while True:   # a gap next to another gap gets an owner once that one has one
            found = {i: biggest_neighbour(i, pieces, next_to, owner, allowed) for i, who in enumerate(owner) if who is None}
            found = {i: who for i, who in found.items() if who is not None}
            if not found:
                break
            for i, who in found.items():
                owner[i] = who
    by_owner = {}
    for piece, who in zip(pieces, owner):
        by_owner.setdefault(who, []).append(piece)
    joined = gpd.GeoSeries([shapely.union_all(by_owner.get(key, [])) for key in keys], crs=config.CRS_OVERLAY)
    union = joined.union_all()
    gaps = sum(len(polygon.interiors) for polygon in shapely.get_parts(union))
    if joined.is_empty.any() or gaps or abs(joined.area.sum() - union.area) > 1:
        raise ValueError(f"NCR's outlines could not be cleaned: {gaps} gaps left, "
                         f"{joined.area.sum() - union.area:,.0f} m2 of overlap")

    simple = joined.simplify_coverage(config.MAP_SIMPLIFY_M)
    city_shapes, barangay_shapes = simple.iloc[:len(others)], simple.iloc[len(others):]
    qc = cities.set_index("psgc").loc[config.QC_CITY_PSGC]
    out_cities = gpd.GeoDataFrame(
        {"psgc": [*others["psgc"], config.QC_CITY_PSGC], "name": [*others["name"], qc["name"]],
         "has_data": [False] * len(others) + [True]},
        geometry=[*city_shapes, shapely.coverage_union_all(list(barangay_shapes))], crs=config.CRS_OVERLAY)
    out_barangays = gpd.GeoDataFrame(flat_barangays[["psgc", "name"]], geometry=list(barangay_shapes),
                                     crs=config.CRS_OVERLAY)
    return (out_cities.to_crs(config.CRS_LONLAT).sort_values("psgc", ignore_index=True),
            out_barangays.to_crs(config.CRS_LONLAT))


def faeldon_file(path):
    """One of faeldon's files (config.FAELDON_URL), downloaded once into data/raw/ph_cities/, unchanged.

    The address names one commit, so the file never changes; a download that is not whole
    JSON (cut off) is not kept.
    """
    config.PH_CITIES_RAW.mkdir(parents=True, exist_ok=True)
    local = config.PH_CITIES_RAW / path.rsplit("/", 1)[1]
    if not local.exists():
        for attempt in range(DOWNLOAD_ATTEMPTS):   # a slow line drops a connection now and then
            try:
                reply = requests.get(config.FAELDON_URL.format(path=path), timeout=DOWNLOAD_TIMEOUT_S)
                break
            except (requests.ConnectionError, requests.Timeout):
                if attempt == DOWNLOAD_ATTEMPTS - 1:
                    raise
        reply.raise_for_status()
        json.loads(reply.content)
        part = local.with_name(local.name + ".part")
        part.write_bytes(reply.content)
        part.replace(local)
        print(f"downloaded {local.name}")
    return local


def download_province_cities():
    """F14: every province's file of city and municipality outlines but NCR's, as the region files list them.

    Returns (paths, province names by PSGC). NCR's four district files come from
    download_ncr_cities, so the Metro Manila outlines are made as before.
    """
    paths, provinces = [], {}
    for region in config.PH_REGIONS:
        listing = gpd.read_file(faeldon_file(f"regions/lowres/provdists-region-{region}.0.001.json"),
                                ignore_geometry=True)
        for psgc, name in zip(listing["adm2_psgc"].astype("int64").astype(str), listing["adm2_en"]):
            provinces[psgc.zfill(10)] = name
            if psgc.zfill(10) not in config.NCR_DISTRICTS:
                paths.append(faeldon_file(f"provdists/hires/municities-provdist-{psgc}.0.1.json"))
    return paths, provinces


def province_cities(paths, provinces):
    """F14: the cities and municipalities outside NCR, each province simplified on its own (EPSG:4326).

    Within a province the outlines are one coverage, so they are simplified together, as
    map_shapes does for NCR (simplify_coverage, about config.PH_SIMPLIFY_M): a border two
    towns share stays one line. Provinces are simplified apart, since faeldon's files do not
    quite meet at province borders.
    """
    parts = []
    for path in paths:
        raw = gpd.read_file(path)
        if "adm3_psgc" not in raw:   # BARMM's Special Geographic Area: an empty file, no municipalities of its own until 2024
            continue
        raw = raw.to_crs(config.CRS_OVERLAY)
        shapes = gpd.GeoDataFrame({"psgc": raw["adm3_psgc"].astype("int64").astype(str).str.zfill(10),
                                   "name": raw["adm3_en"],
                                   "province": raw["adm2_psgc"].astype("int64").astype(str).str.zfill(10).map(provinces)},
                                  geometry=raw.geometry.make_valid().simplify_coverage(config.PH_SIMPLIFY_M),
                                  crs=config.CRS_OVERLAY)
        parts.append(shapes[~shapes.is_empty])
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=config.CRS_OVERLAY).to_crs(config.CRS_LONLAT)


def towns_apart():
    """F14: the towns no province file holds (config.PH_TOWNS_APART), each its barangays joined and simplified (EPSG:4326)."""
    rows = []
    for psgc, (name, province) in config.PH_TOWNS_APART.items():
        barangays = gpd.read_file(faeldon_file(f"municities/hires/bgysubmuns-municity-{int(psgc)}.0.1.json"))
        shape = shapely.union_all(barangays.to_crs(config.CRS_OVERLAY).geometry.make_valid().values)
        rows.append({"psgc": psgc, "name": name, "province": province,
                     "geometry": shape.simplify(config.PH_SIMPLIFY_M)})
    return gpd.GeoDataFrame(rows, crs=config.CRS_OVERLAY).to_crs(config.CRS_LONLAT)


def country_cities(ncr_cities, others):
    """F14: every city and municipality of the Philippines: NCR's from map_shapes, the others from province_cities.

    Stops unless there are config.PH_CITY_COUNT of them, one PSGC each.
    """
    ncr = ncr_cities.assign(province="National Capital Region")
    cities = gpd.GeoDataFrame(pd.concat([ncr, others.assign(has_data=False)], ignore_index=True),
                              crs=config.CRS_LONLAT)
    if len(cities) != config.PH_CITY_COUNT or not cities["psgc"].is_unique:
        raise ValueError(f"expected {config.PH_CITY_COUNT} cities and municipalities, one PSGC each; got {len(cities)}")
    return cities[["psgc", "name", "province", "has_data", "geometry"]].sort_values("psgc", ignore_index=True)


def label_points(cities):
    """Where the map writes each city's name (F4): cities with label_lon and label_lat added.

    The point is the one farthest inside the city's largest part (shapely's polylabel, found
    to within config.MAP_SIMPLIFY_M), so the name sits inside even a thin or curved city,
    where its centre point might fall outside. A city smaller than config.APP_LABEL_MIN_KM2
    gets none (empty), as in Figma. F14: only a city with data gets one; the street map writes
    the others' names.
    """
    points = []
    for shape, has_data in zip(cities.to_crs(config.CRS_OVERLAY).geometry, cities["has_data"]):   # in metres
        largest = max(shapely.get_parts(shape), key=lambda part: part.area)
        big_enough = has_data and shape.area / 1e6 >= config.APP_LABEL_MIN_KM2
        points.append(shapely.ops.polylabel(largest, tolerance=config.MAP_SIMPLIFY_M) if big_enough else None)
    lonlat = gpd.GeoSeries(points, crs=config.CRS_OVERLAY).to_crs(config.CRS_LONLAT)
    return cities.assign(label_lon=lonlat.x.round(config.APP_COORD_DECIMALS),
                         label_lat=lonlat.y.round(config.APP_COORD_DECIMALS))


def island_outlines(cities):
    """F14: the coastline of every island, which the map draws zoomed out (EPSG:4326).

    Every city and municipality joined into land. faeldon's province files do not quite meet,
    so the gaps between them are closed first: the land grown by config.PH_ISLANDS_GAP_M, then
    shrunk by as much. Each island keeps only its outer coast. The holes left inside are lakes,
    which the street map already draws as water, or gaps in faeldon's maps (221 km2 inside
    Zamboanga City), which would draw lines across the land. Islands under
    config.PH_ISLANDS_MIN_KM2 are left out, and the coasts simplified to
    config.PH_ISLANDS_SIMPLIFY_M: the map draws these lines only between the country's view and
    the towns' borders (app/src/map/borders.ts), where both are under a pixel.
    """
    land = shapely.union_all(cities.to_crs(config.CRS_OVERLAY).geometry.make_valid().values)   # in metres
    gap = config.PH_ISLANDS_GAP_M
    closed = land.buffer(gap, join_style="mitre").buffer(-gap, join_style="mitre")
    islands = [shapely.Polygon(part.exterior).simplify(config.PH_ISLANDS_SIMPLIFY_M)
               for part in shapely.get_parts(closed) if part.area >= config.PH_ISLANDS_MIN_KM2 * 1e6]
    return gpd.GeoDataFrame(geometry=islands, crs=config.CRS_OVERLAY).to_crs(config.CRS_LONLAT)


def write_geojson(shapes, path):
    """Write shapes as GeoJSON (RFC 7946), coordinates to config.APP_COORD_DECIMALS, via a .part file."""
    part = path.with_name(path.name + ".part")
    part.unlink(missing_ok=True)
    shapes.to_file(part, driver="GeoJSON", layer=path.stem, RFC7946="YES",
                   COORDINATE_PRECISION=config.APP_COORD_DECIMALS)
    part.replace(path)


# ---------------------------------------------------------------------------
# Layer 2: storms, barangays and health centers (C8, C9)
# ---------------------------------------------------------------------------

def run_slug(run):
    """A run's name in file names: "observed", "lead1", "lead2" or "lead3"."""
    return run.replace(" ", "")


def barangay_file_name(storm, run):
    """Where one run's barangay file goes under app/public/data/, e.g. barangays/kristine_2024_lead1.json."""
    return f"{config.APP_BARANGAY_RUNS.name}/{storm}_{run_slug(run)}.json"


def flood_key(days):
    """A flood's key in the app's files: "D1" for a 1-day flood, "D7" for 7 days."""
    return f"D{int(days)}"


def app_floods(table):
    """The rows of a C9 table that the app shows: a short flood at w = 0.5, a long one at any w.

    A flood of D >= config.CONTINUOUS_EXPOSURE_DAYS has one row, since w does not matter
    there (every exposed adult is high risk, C5); a shorter one has a row per w, and the
    app shows config.APP_SHORT_FLOOD_W.
    """
    long_flood = table["D"] >= config.CONTINUOUS_EXPOSURE_DAYS
    return table[long_flood | np.isclose(table["w"], config.APP_SHORT_FLOOD_W)]


def share_classes():
    """The map's five classes of share, light to dark: index, legend text and the shares each runs from and to."""
    edges = [0.0, *config.APP_SHARE_BREAKS, 1.0]
    labels = layer2_results.class_labels(config.APP_SHARE_BREAKS, lambda share: f"{100 * share:.0f}%")
    return [{"class": i, "label": label, "from": low, "to": high}
            for i, (label, low, high) in enumerate(zip(labels, edges, edges[1:]))]


def flood_entry(row):
    """One flood of a run in storms.json: its key, D and w (empty when w does not matter), people and units."""
    short = row["D"] < config.CONTINUOUS_EXPOSURE_DAYS
    return {"key": flood_key(row["D"]), "flood": row["flood"], "D": int(row["D"]),
            "w": float(row["w"]) if short else None, "exposed": whole(row["exposed"]), **units_of(row)}


def run_entry(rows):
    """One run of a storm in storms.json: the rain, where it falls, EI and the flags, then each flood."""
    first = rows.iloc[0]
    start, end = (pd.Timestamp(day) for day in first["window"].split(" to "))
    lead = None if first["run"] == OBSERVED else int(first["lead_days"])
    return {
        "run": first["run"],
        "file": barangay_file_name(first["storm"], first["run"]),
        "rain_product": first["product"],
        "levels_product": "IMERG" if first["run"] == OBSERVED else "ERA5",   # each product on its own levels (rule 3, as D7)
        "lead_days": lead,
        # a lead-L forecast comes from model runs started L days before the window (C9)
        "issued": None if lead is None else f"{start - pd.Timedelta(days=lead):%Y-%m-%d}",
        "window": {"start": f"{start:%Y-%m-%d}", "end": f"{end:%Y-%m-%d}"},
        "rain_mm": round(float(first["rain_mm"]), 1),
        "levels_mm": {"R0": round(float(first["r0"]), 1), "R(5)": round(float(first["r5"]), 1),
                      "R(25)": round(float(first["r25"]), 1), "R(100)": round(float(first["r100"]), 1)},
        "levels_years": int(first["levels_years"]),
        "position": first["position"],
        "ei_pct": round(float(first["ei_pct"]), 2),
        "flagged": int(first[FLAG_COLUMN]),
        "floods": [flood_entry(row) for _, row in rows.iterrows()],
    }


def storms_file(c9_runs):
    """storms.json: every storm C9 ran, in config.STORMS' order, each with its runs (observed first, then leads)."""
    shown = layer2_results.in_order(app_floods(c9_runs), by=["D"])
    storms = []
    for storm, storm_rows in shown.groupby("storm", sort=False):
        facts = config.STORMS[storm]
        runs = []
        for run, rows in storm_rows.groupby("run", sort=False):
            if not rows["D"].is_unique:
                raise ValueError(f"{storm}, {run}: two floods with the same D: rerun python -m src.forecast_run")
            runs.append(run_entry(rows))
        storms.append({"storm": storm, "name": layer2_results.STORM_NAMES.get(storm, storm),
                       "start_date": f"{facts['start_date']:%Y-%m-%d}", "end_date": f"{facts['end_date']:%Y-%m-%d}",
                       "D": facts["D"], "runs": runs})
    return {"label": doses.LABEL, "source": "C9, results/c9_forecast_runs.csv", "units": dict(doses.UNITS),
            "counting": counting_rules(), "flag_share": config.APP_FLAG_SHARE, "classes": share_classes(),
            "storms": storms}


def counting_rules():
    """F15: how C6 counts units per person, which the app's barangay report explains (config.py's values).

    doxy100_low, doxy100_moderate: capsules per adult at low and moderate risk;
    doxy100_high_per_week: per high-risk adult and week of flooding (week_days days, rounded
    up); amox500_pregnant: tablets per pregnant woman; high_risk_days: a flood this long or
    longer makes every exposed adult high risk. Children get one course per week of flooding,
    at least one.
    """
    return {"doxy100_low": config.DOXY_CAPS_LOW, "doxy100_moderate": config.DOXY_CAPS_MOD,
            "doxy100_high_per_week": config.DOXY_CAPS_HIGH_PER_WEEK, "amox500_pregnant": config.AMOX_TABS_PREG,
            "week_days": config.DOSE_WEEK_DAYS, "high_risk_days": config.CONTINUOUS_EXPOSURE_DAYS}


def barangay_population():
    """Each barangay's name and 2024 residents, from C8's main run; stops unless there is one value per barangay."""
    c8 = pd.read_csv(config.C8_BARANGAYS, dtype={"psgc": str})
    main = c8[c8["test"] == observed_run.MAIN]
    pop = main.drop_duplicates("psgc").set_index("psgc")[["adm4_name", "pop_2024"]]
    if len(pop) != config.QC_BARANGAYS or main.groupby("psgc")["pop_2024"].nunique().max() != 1:
        raise ValueError(f"C8's barangay file must give one 2024 population for each of the "
                         f"{config.QC_BARANGAYS} barangays: rerun python -m src.observed_run")
    return pop


def barangay_file(rows, pop, storm, run):
    """One run's barangay file: each barangay's residents exposed, share, class, flag and units per flood.

    rows: C9's barangay rows of the run, for the floods the app shows. The residents in
    flood zones (and so the share, class and flag) depend on the rain only, so every flood
    of a run must have the same; the units differ by flood.
    """
    floods = {flood_key(days): part.set_index("psgc") for days, part in rows.groupby("D")}
    first = next(iter(floods.values()))
    for part in floods.values():
        if set(part.index) != set(pop.index) or not part.index.is_unique:
            raise ValueError(f"{storm}, {run}: C9 needs one row for each of the {config.QC_BARANGAYS} barangays")
        if not np.allclose(part["residents"].reindex(first.index), first["residents"]):
            raise ValueError(f"{storm}, {run}: two floods of one run have different residents in flood zones")
    share = first["residents"] / pop["pop_2024"].reindex(first.index)
    classes = pd.Series(layer2_results.classes(share, config.APP_SHARE_BREAKS), index=share.index)
    flagged = forecast_run.flagged(first.reset_index()[["psgc", "residents"]], pop, config.APP_FLAG_SHARE)
    barangays = [{"psgc": psgc, "name": pop.at[psgc, "adm4_name"], "pop_2024": int(pop.at[psgc, "pop_2024"]),
                  "exposed": whole(first.at[psgc, "exposed"]), "share": round(float(share[psgc]), 4),
                  "class": int(classes[psgc]), "flagged": psgc in flagged,
                  "units": {key: units_of(part.loc[psgc]) for key, part in floods.items()}}
                 for psgc in sorted(first.index)]
    return {"label": doses.LABEL, "source": "C9, results/c9_forecast_barangays.csv; 2024 residents from C8",
            "storm": storm, "run": run, "barangays": barangays}


def center_list():
    """A10's health centers (config.CENTER_FACILITY_TYPES), by name: those C7 sends stock to, and any it left out, with why.

    Each center's barangay is named as on the map, A5's name for its PSGC: A10's registry
    names lose the ñ ("DO?A IMELDA").
    """
    barangays = allocation.load_barangays()
    placed, left_out = allocation.load_centers(barangays)
    facilities = pd.read_csv(config.FACILITIES_QC, dtype={"psgc": str, "facility_code": str})
    centers = facilities[facilities["facility_type"].isin(config.CENTER_FACILITY_TYPES)].sort_values("name")
    barangay_names = barangays.set_index("psgc")["adm4_name"]
    unknown = sorted(set(centers["psgc"]) - set(barangay_names.index))
    if unknown:
        raise ValueError(f"health centers in barangays A5 does not have: {unknown}: rerun python -m src.facilities")
    reasons = left_out.set_index("facility_code")["reason"]
    stocked = set(placed["facility_code"])
    if stocked | set(reasons.index) != set(centers["facility_code"]):
        raise ValueError("C7's placed and left-out health centers are not A10's centers: check allocation.load_centers")
    digits = config.APP_COORD_DECIMALS
    return [{"facility_code": code, "name": name, "type": kind,
             "lat": None if pd.isna(lat) else round(float(lat), digits),
             "lon": None if pd.isna(lon) else round(float(lon), digits),
             "psgc": psgc, "barangay": barangay_names[psgc],
             "gets_stock": code in stocked, "left_out": reasons.get(code)}
            for code, name, kind, lat, lon, psgc in centers[
                ["facility_code", "name", "facility_type", "lat", "lon", "psgc"]].itertuples(index=False)]


def center_needs(c9_centers, c9_runs):
    """Each run's need per health center and flood: {storm: {run: {flood key: {facility_code: units}}}}.

    Each pool's three tiers are added up, then rounded up to whole units (as D7). Stops
    unless every center has all three pools and, before rounding, the centers add up to
    C9's QC totals (C9 saved each tier to 2 decimals, so up to 0.005 per tier and center apart).
    """
    rows = app_floods(c9_centers)
    need = rows.assign(units=rows[exposed.TIERS].sum(axis=1)).pivot(
        index=["storm", "run", "D", "facility_code"], columns="pool", values="units")
    if set(need.columns) != set(UNITS) or need.isna().any().any():
        raise ValueError(f"C9's center table needs {UNITS} for every health center: rerun python -m src.forecast_run")
    by_run = need.groupby(level=["storm", "run", "D"])
    totals = app_floods(c9_runs).set_index(["storm", "run", "D"])[UNITS].reindex(by_run.size().index)
    slack = 0.005 * len(exposed.TIERS) * by_run.size()
    gap = (by_run[UNITS].sum() - totals).abs()
    if gap.isna().any().any() or gap.gt(slack, axis=0).any().any():
        raise ValueError("C9's health centers do not add up to its QC totals: rerun python -m src.forecast_run")
    out = {}
    for (storm, run, days, code), row in allocation.round_up(need[UNITS]).astype(int).iterrows():
        out.setdefault(storm, {}).setdefault(run, {}).setdefault(flood_key(days), {})[code] = {
            unit: int(row[unit]) for unit in UNITS}
    return out


def barangay_centers(stocked):
    """F15: each barangay's health centers, as C7 sends its need: {psgc: [center, ...]}, the barangay report's stock.

    Each center is {facility_code, rule, share, km}. rule is C7's: "own" (the barangay's one
    health center), "split" (one of its several centers, which takes the share of its
    residents who live nearest it) or "nearest" (a barangay with none sends all of its need
    to the nearest center, km from the barangay's centroid; km is null for the other rules).
    The largest share comes first. Stops unless each of the 142 barangays has centers whose
    shares add up to 1, and the centers named are exactly those C7 sends stock to (`stocked`).
    """
    table = allocation.load_center_shares()
    if table["psgc"].nunique() != config.QC_BARANGAYS or not set(table["rule"]) <= {"own", "split", "nearest"}:
        raise ValueError(f"C7's shares must name each of the {config.QC_BARANGAYS} barangays, by its rules: "
                         "rerun python -m src.allocation")
    if not np.allclose(table.groupby("psgc")["share"].sum(), 1):
        raise ValueError("C7's shares of a barangay's need do not add up to 1: rerun python -m src.allocation")
    if set(table["facility_code"]) != stocked:
        raise ValueError("C7's shares name other health centers than the ones it places: rerun python -m src.allocation")
    ordered = table.sort_values(["psgc", "share", "facility_code"], ascending=[True, False, True])
    return {psgc: [{"facility_code": code, "rule": rule, "share": round(float(share), 4),
                    "km": None if pd.isna(km) else round(float(km), 2)}
                   for code, rule, share, km in rows[["facility_code", "rule", "share", "distance_km"]].itertuples(index=False)]
            for psgc, rows in ordered.groupby("psgc", sort=True)}


def centers_file(c9_centers, c9_runs):
    """centers.json: the health centers, each run's need per center and flood (whole units, rounded up), and each barangay's centers."""
    centers = center_list()
    needs = center_needs(c9_centers, c9_runs)
    stocked = {center["facility_code"] for center in centers if center["gets_stock"]}
    for storm, runs in needs.items():
        for run, floods in runs.items():
            for key, per_center in floods.items():
                if set(per_center) != stocked:
                    raise ValueError(f"{storm}, {run}, {key}: C9's health centers are not the ones C7 places now "
                                     f"(A10's file changed?): rerun python -m src.allocation and python -m src.forecast_run")
    return {"label": doses.LABEL,
            "source": "A10's health_facilities_qc.csv; need from C9, results/c9_forecast_centers.csv; "
                      "each barangay's centers from C7, center_shares_qc.csv",
            "units": dict(doses.UNITS), "centers": centers, "needs": needs,
            "barangay_centers": barangay_centers(stocked)}


def layer2_files():
    """storms.json, centers.json and one barangay file per run, from C8's and C9's results: {name: content}.

    Stops unless each run's barangay file flags as many barangays as C9 counted.
    """
    c9_runs = pd.read_csv(config.C9_RUNS)
    c9_barangays = pd.read_csv(config.C9_BARANGAYS, dtype={"psgc": str})
    c9_centers = pd.read_csv(config.C9_CENTERS, dtype={"facility_code": str})
    pop = barangay_population()
    files = {"storms.json": storms_file(c9_runs)}
    flagged = app_floods(c9_runs).drop_duplicates(["storm", "run"]).set_index(["storm", "run"])[FLAG_COLUMN]
    for (storm, run), rows in app_floods(c9_barangays).groupby(["storm", "run"]):
        content = barangay_file(rows, pop, storm, run)
        count = sum(barangay["flagged"] for barangay in content["barangays"])
        if count != flagged[(storm, run)]:
            # Either the two files are from different C9 runs, or a barangay sits on the flag
            # line, where the barangay file's 2-decimal residents decide differently.
            raise ValueError(f"{storm}, {run}: {count} barangays flagged from C9's barangay file, "
                             f"{flagged[(storm, run)]} in its runs file: rerun python -m src.forecast_run; if "
                             f"that does not help, a barangay sits on the {config.APP_FLAG_SHARE:.0%} line and "
                             f"C9's barangay file needs its own flag column")
        files[barangay_file_name(storm, run)] = content
    files["centers.json"] = centers_file(c9_centers, c9_runs)
    return files


# ---------------------------------------------------------------------------
# Layer 1: the city forecast (B10) and its scores (D1-D3, D5)
# ---------------------------------------------------------------------------

def load_forecasts():
    """B10's forecasts and where they came from: (table, simulated, path), or (None, None, None).

    results/forecasts.csv, the real run, once it exists; until then the made-up-count run
    (config.FORECASTS_SIMULATED). Model names follow D6 (MODEL_NAMES).
    """
    for path, simulated in ((config.FORECASTS, False), (config.FORECASTS_SIMULATED, True)):
        if path.exists():
            table = pd.read_csv(path)
            return table.assign(model=table["model"].replace(MODEL_NAMES)), simulated, path
    return None, None, None


def city_forecast(table, simulated, path):
    """city_forecast.json: per target week its dates, count y, threshold and breach, then each model's forecast.

    A model's forecast is its mean mu, the 90% range (the 5% and 95% quantiles of
    NB(mu, theta), B6) and Pr(breach) (B7). The forecast for week i was made at week
    i - config.FORECAST_HORIZON_WEEKS. Stops unless every model has a forecast for exactly
    the same weeks (rule 5) and the models agree on each week's y and threshold, and on a
    missing value in a column it reads (rule 5).
    The map (F4) colors Quezon City by config.APP_LEVEL_MODEL's Pr(breach): "levels" lists
    each outbreak level with the Pr(breach) it starts at (config.APP_LEVELS).
    """
    scores.check_same_weeks(table)
    unknown = sorted(set(table["model"]) - set(MODELS))
    if unknown:
        raise ValueError(f"{path.name}: models {unknown} are not B10's")
    models = [model for model in MODELS if model in set(table["model"])]
    if config.APP_LEVEL_MODEL not in models:
        raise ValueError(f"{path.name} has no {config.APP_LEVEL_MODEL} forecasts, the model the map shows")
    low, high = (f"q{q:.3f}" for q in (config.RANGE_LOW_Q, config.RANGE_HIGH_Q))
    blank = [col for col in ("y", "threshold", "breached", "mu", low, high, "p_breach") if table[col].isna().any()]
    if blank:
        raise ValueError(f"{path.name} has missing values in {blank}: rerun B10 (rule 5)")
    weeks_out = []
    for index, rows in table.groupby("week_index"):
        if rows[["y", "threshold"]].nunique().max() > 1:
            raise ValueError(f"{path.name}, week index {index}: the models disagree on y or the threshold")
        first = rows.iloc[0]
        start = weeks.week_start(index)
        by_model = rows.set_index("model")
        weeks_out.append({
            "week_index": int(index), "year": int(first["year"]), "week": int(first["week"]),
            "start": f"{start:%Y-%m-%d}", "end": f"{start + timedelta(days=config.DAYS_PER_WEEK - 1):%Y-%m-%d}",
            "y": int(first["y"]), "threshold": round(float(first["threshold"]), 2), "breached": bool(first["breached"]),
            "forecasts": {model: {"mu": round(float(by_model.at[model, "mu"]), 2),
                                  "low": int(by_model.at[model, low]), "high": int(by_model.at[model, high]),
                                  "p_breach": round(float(by_model.at[model, "p_breach"]), 4)}
                          for model in models},
        })
    return {"simulated": simulated, "note": SIMULATED_NOTE if simulated else None, "source": path.name,
            "option": str(table["option"].iloc[0]), "g": int(table["g"].iloc[0]),
            "horizon_weeks": config.FORECAST_HORIZON_WEEKS, "models": models,
            "map_model": config.APP_LEVEL_MODEL,
            "levels": [{"level": level, "from": start} for level, start in config.APP_LEVELS],
            "range": [config.RANGE_LOW_Q, config.RANGE_HIGH_Q], "covid_years": list(config.COVID_YEARS),
            "weeks": weeks_out}


def scores_file(table, cases):
    """scores.json, from the real run only: each model's D1-D3 scores and D5's primary endpoint.

    MAE and MASE over config.MAE_YEARS; WIS, 90% coverage and the Brier score over
    config.PROB_SCORE_YEARS (the plan's windows, which leave out the COVID years and, for
    the range scores, theta's warm-up). D5: the mean of |error M4| - |error M3| with its
    95% block-bootstrap interval, the 8-week row of compare.primary_endpoint (and of D8's
    figure 2); below 0 means M4 misses less.
    cases: A13's weekly counts, for MASE's fixed denominator (D2).
    """
    point = scores.add_mase(scores.score_models(table, config.MAE_YEARS), scores.mase_denominator(cases))
    probability = scores.score_models(table, config.PROB_SCORE_YEARS)
    window = table[table["year"].isin(config.PROB_SCORE_YEARS)]
    brier = {model: breach_scores.brier(rows["p_breach"], rows["breached"].astype(float))
             for model, rows in window.groupby("model")}
    head = compare.primary_endpoint(table).iloc[0]   # the 8-week row, D5's headline
    models = {model: {"mae": round(float(point.at[model, "mae"]), 4), "mase": round(float(point.at[model, "mase"]), 4),
                      "wis": round(float(probability.at[model, "wis"]), 4),
                      "coverage_90": round(float(probability.at[model, "coverage_90"]), 4),
                      "brier": round(float(brier[model]), 4)}
              for model in MODELS if model in point.index}
    return {"source": config.FORECASTS.name,
            "windows": {"mae_mase": list(config.MAE_YEARS), "wis_coverage_brier": list(config.PROB_SCORE_YEARS)},
            "models": models,
            "primary": {"comparison": head["comparison"], "block_weeks": int(head["block_weeks"]),
                        "weeks": int(head["weeks"]), "mean_diff": round(float(head["mean_diff"]), 4),
                        "low": round(float(head["low"]), 4), "high": round(float(head["high"]), 4),
                        "verdict": head["verdict"]}}


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def write_json(content, path):
    """Write content as compact UTF-8 JSON via a .part file. Stops on a NaN or infinity (rule 5)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    try:
        with open(part, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except Exception:
        part.unlink(missing_ok=True)   # never leave half a file where the app's files live
        raise
    part.replace(path)


def remove_stale_runs(names):
    """Delete barangay files of runs no longer in C9's results, so the app cannot load an old run."""
    for path in sorted(config.APP_BARANGAY_RUNS.glob("*.json")):
        if f"{config.APP_BARANGAY_RUNS.name}/{path.name}" not in names:
            path.unlink()
            print(f"removed {path.name}: no such run in C9's results")


def write_layer1():
    """city_forecast.json from B10's forecasts, and scores.json beside the real run only; returns what it did.

    Both files are made before either is written, so a failure leaves the old pair as it was.
    Without A13's cases_weekly.csv (scores.json's MASE needs it) both are left as they were:
    a copy without QC's case data still runs (E10).
    """
    table, simulated, path = load_forecasts()
    if table is None:
        return ("city_forecast.json left as it was: no B10 forecasts on this computer (results/forecasts.csv, "
                "or run python -m src.backtest --simulate --option C)")
    if not simulated and not config.CASES_WEEKLY.exists():
        return (f"city_forecast.json and scores.json left as they were: scores.json's MASE needs "
                f"{config.CASES_WEEKLY.name} (run task A13, python -m src.cases, or copy the file from the team drive)")
    forecast = city_forecast(table, simulated, path)
    scores_content = None if simulated else scores_file(table, backtest.load_cases())
    write_json(forecast, config.APP_DATA / "city_forecast.json")
    scores_path = config.APP_DATA / "scores.json"
    if simulated:
        scores_path.unlink(missing_ok=True)
        return f"city_forecast.json from {path.name}: SIMULATED (made-up counts), so no scores.json"
    write_json(scores_content, scores_path)
    return f"city_forecast.json and scores.json from {path.name}"


def report(storms, layer1):
    """Print each run's flags and QC totals as the app shows them, the files written, and the label."""
    for storm in storms["storms"]:
        print(f"\n{storm['name']}:")
        for run in storm["runs"]:
            floods = "; ".join(f"{flood['key']}: {flood['exposed']:,} exposed, {flood['doxy100']:,} capsules, "
                               f"{flood['courses']:,} courses, {flood['amox500']:,} tablets" for flood in run["floods"])
            print(f"  {run['run']:<9} {run['rain_mm']:6.1f} mm, {run['position']:<14} {run['flagged']:>3} flagged | {floods}")
    written = sorted(path for path in config.APP_DATA.rglob("*") if path.is_file())
    size = sum(path.stat().st_size for path in written) / 1024
    print(f"\n{layer1}")
    print(f"{len(written)} files in {config.APP_DATA.relative_to(config.ROOT)} ({size:,.0f} KB); "
          f"commit them so the deployed app gets them")
    print(doses.LABEL)


def main():
    check_inputs()
    config.APP_BARANGAY_RUNS.mkdir(parents=True, exist_ok=True)
    cities, barangays = map_shapes(load_cities(download_ncr_cities()), load_barangays())
    others = pd.concat([province_cities(*download_province_cities()), towns_apart()], ignore_index=True)
    country = country_cities(cities, gpd.GeoDataFrame(others, crs=config.CRS_LONLAT))
    write_geojson(label_points(country), config.APP_DATA / config.APP_CITIES_FILE)
    write_geojson(island_outlines(country), config.APP_DATA / config.APP_ISLANDS_FILE)
    for old in ("ncr_cities.geojson", *(f"noah_{t}yr.json" for t in config.NOAH_RETURN_PERIODS)):
        (config.APP_DATA / old).unlink(missing_ok=True)   # F14: ph_cities.json and NOAH's national tiles replace them
    write_geojson(barangays, config.APP_DATA / "qc_barangays.geojson")
    files = layer2_files()
    for name, content in files.items():
        write_json(content, config.APP_DATA / name)
    remove_stale_runs(files)
    layer1 = write_layer1()
    report(files["storms.json"], layer1)


if __name__ == "__main__":
    main()

"""Quezon City health centers from the DOH National Health Facility Registry."""

import html
import re
import time

import geopandas as gpd
import pandas as pd
import requests

import config

NHFR = "https://nhfr.doh.gov.ph"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TIMEOUT_S = 120

# Detail-page fields kept, and their column names in the table
FIELDS = {
    "hfhudcode": "facility_code",
    "hfhudname": "name",
    "factype": "facility_type",
    "ownercode": "ownership",
    "fhudaddress": "street",
    "hfhbldgname": "building",
    "bgycode": "barangay_name",
    "bgycodepsgc": "psgc",
    "ctymuncodepsgc": "city_psgc",
    "license": "license_status",
    "license_validitydate": "license_valid_until",
    "north_coord": "lat",
    "east_coord": "lon",
}


def get_page(session, url, path, params=None):
    """Return the page at url as text, saving it unchanged to path (or reading path if there)."""
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    r = session.get(url, params=params, timeout=TIMEOUT_S)
    r.raise_for_status()
    if "Attention Required! | Cloudflare" in r.text:
        raise IOError(f"the registry's firewall blocked {url}; try again later or from another network")
    path.write_bytes(r.content)
    time.sleep(config.NHFR_PAUSE_S)
    return path.read_text(encoding="utf-8", errors="replace")


def cell_text(fragment):
    """Plain text of an HTML fragment: tags removed, entities decoded, spaces collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def list_rows(page):
    """(facility code, province name, facility type) for every row of the list page."""
    rows = []
    for row in re.findall(r'<tr\s+data-rowindex="\d+"[^>]*>(.*?)</tr>', page, re.S):
        code = re.search(r"VActivefacilitiesView/(DOH\d+)", row)
        cells = {name: cell_text(value) for name, value in
                 re.findall(r'<td data-name="([a-z_]+)"[^>]*>(.*?)</td>', row, re.S)}
        if code:
            rows.append((code.group(1), cells.get("provcode"), cells.get("factype")))
    return rows


def detail_fields(page):
    """The FIELDS of one facility's detail page, as {column: text}."""
    found = {}
    for name, row in re.findall(r'<tr id="r_([a-z_]+)"[^>]*>(.*?)</tr>', page, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if name in FIELDS and len(cells) >= 2:
            found[FIELDS[name]] = cell_text(cells[1])
    missing = set(FIELDS.values()) - set(found)
    if missing:
        raise ValueError(f"detail page lacks {sorted(missing)}")
    return found


def qc_facility_codes(session):
    """Codes of QC's facilities of the kept types, from one list request over NCR."""
    params = {
        "cmd": "search",
        "x_factype": ",".join(config.NHFR_FACILITY_TYPES),
        "z_factype": "LIKE",
        "x_regcode": config.NHFR_REGION_NCR,
        "z_regcode": "LIKE",
        "recperpage": "ALL",
    }
    page = get_page(session, f"{NHFR}/VActivefacilitiesList", config.NHFR_RAW / "list_ncr.html", params)
    rows = list_rows(page)
    if not rows:
        raise ValueError("the list page has no rows; the registry's page layout may have changed")
    kept_types = set(config.NHFR_FACILITY_TYPES.values())
    codes = [code for code, prov, ftype in rows if prov == config.NHFR_QC_NAME and ftype in kept_types]
    print(f"list: {len(rows)} NCR facilities of the kept types, {len(codes)} in QC")
    return codes


def clean_table(records):
    """One row per facility: coordinates as numbers, license date as a date, sorted by code."""
    table = pd.DataFrame(records)
    for col in ("lat", "lon"):
        table[col] = pd.to_numeric(table[col], errors="coerce")
    unknown = (table["lat"] == 0) & (table["lon"] == 0)
    table.loc[unknown, ["lat", "lon"]] = float("nan")
    table["license_valid_until"] = pd.to_datetime(table["license_valid_until"], format="%m/%d/%Y",
                                                  errors="coerce").dt.date
    table["license_status"] = table["license_status"].str.replace("Licensing Status:", "").str.strip()
    return table.sort_values("facility_code").reset_index(drop=True)


def check_table(table):
    """Stop if a facility is outside QC or has no coordinates; print anything to inspect."""
    if table["facility_code"].duplicated().any():
        raise ValueError("a facility appears twice")
    outside = table[~table["psgc"].str.startswith(config.QC_PSGC_PREFIX)]
    if len(outside):
        raise ValueError(f"barangay PSGC outside QC:\n{outside[['facility_code', 'name', 'psgc']]}")
    no_coords = table[table["lat"].isna() | table["lon"].isna()]
    if len(no_coords):
        print(f"NOTE: {len(no_coords)} facilities without coordinates:")
        print(no_coords[["facility_code", "name", "barangay_name"]].to_string(index=False))
    lon_min, lat_min, lon_max, lat_max = config.IMERG_BOX
    far = table[~table["lon"].between(lon_min, lon_max) | ~table["lat"].between(lat_min, lat_max)]
    far = far.dropna(subset=["lat", "lon"])
    if len(far):
        print(f"NOTE: {len(far)} facilities with coordinates outside the rain box (lat/lon swapped?):")
        print(far[["facility_code", "name", "lat", "lon"]].to_string(index=False))


def check_barangays(table):
    """Stop if a facility's barangay is not one of the; list facilities outside their barangay."""
    if not config.BARANGAYS_QC.exists():
        raise FileNotFoundError(f"{config.BARANGAYS_QC} not found: run task A5 first (python -m src.census)")
    barangays = gpd.read_file(config.BARANGAYS_QC, layer="barangays", columns=["psgc"])
    unknown = table[~table["psgc"].isin(barangays["psgc"])]
    if len(unknown):
        raise ValueError(f"barangay PSGC not among A5's {len(barangays)} barangays:\n"
                         f"{unknown[['facility_code', 'name', 'barangay_name', 'psgc']]}")

    located = table.dropna(subset=["lat", "lon"])
    points = gpd.GeoSeries(gpd.points_from_xy(located["lon"], located["lat"]), index=located.index,
                           crs="EPSG:4326").to_crs(config.CRS_OVERLAY)
    shapes = barangays.set_index("psgc").geometry.to_crs(config.CRS_OVERLAY)
    own = gpd.GeoSeries(located["psgc"].map(shapes), crs=config.CRS_OVERLAY)
    metres = points.distance(own).round()          # 0 when inside its own barangay
    outside = located.assign(metres=metres)[metres > 0]
    if len(outside):
        print(f"NOTE: {len(outside)} facilities lie outside their own barangay (inspect the far ones):")
        print(outside.sort_values("metres", ascending=False)
              [["facility_code", "name", "barangay_name", "metres"]].to_string(index=False))


def main():
    config.NHFR_RAW.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    records = []
    for code in qc_facility_codes(session):
        page = get_page(session, f"{NHFR}/VActivefacilitiesView/{code}",
                        config.NHFR_RAW / f"{code}.html", {"showdetail": ""})
        records.append(detail_fields(page))
    table = clean_table(records)
    check_table(table)
    check_barangays(table)

    table.to_csv(config.FACILITIES_QC, index=False)
    print(table["facility_type"].value_counts().to_string())
    print(f"{table['psgc'].nunique()} barangays have a facility; "
          f"{table[['lat', 'lon']].notna().all(axis=1).sum()} of {len(table)} have coordinates")
    print(f"wrote {config.FACILITIES_QC}")


if __name__ == "__main__":
    main()

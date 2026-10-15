"""Quezon City health centers from the DOH National Health Facility Registry (task A10).

C7 assigns each barangay's prophylaxis need to a health center, so it needs every QC
public health facility with its location. This script gets them from the registry
(https://nhfr.doh.gov.ph, "Active facilities") in two steps:
1. One list request: every NCR facility of the types in config.NHFR_FACILITY_TYPES
   (Rural Health Unit, Barangay Health Station, City Health Office); keep QC's rows.
   QC's health centers are registered as "Rural Health Unit".
2. One request per QC facility for its detail page, which holds the coordinates
   (north_coord = latitude, east_coord = longitude) and the barangay's 10-digit PSGC.
Every page is saved unchanged in data/raw/nhfr/; a page already there is not fetched
again (delete the folder to refresh). The table is written to
data/clean/health_facilities_qc.csv.

The registry's list and CSV export have no coordinates, which is why step 2 exists.
Facility heads' names and e-mail addresses are on the detail pages; they are not
needed and are left out of the table.

The registry sits behind a firewall that refuses requests without a browser's
User-Agent, so requests send one, and wait config.NHFR_PAUSE_S between pages.

Run from the repository root:
    python -m src.facilities
"""

import html
import re
import time

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
    """Return the page at url as text, saving it unchanged to path (or reading path if there).

    The registry itself sends "?" for "Ñ" (e.g. "DO?A IMELDA"), so names can be off by a
    letter; join on the PSGC code, never the name. Any byte that is not valid UTF-8 is
    read as a replacement character so it cannot stop the run.
    """
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
    """One row per facility: coordinates as numbers, license date as a date, sorted by code.

    The registry writes 0, 0 when it has no location; those become missing (NaN).
    """
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

    table.to_csv(config.FACILITIES_QC, index=False)
    print(table["facility_type"].value_counts().to_string())
    print(f"{table['psgc'].nunique()} barangays have a facility; "
          f"{table[['lat', 'lon']].notna().all(axis=1).sum()} of {len(table)} have coordinates")
    print(f"wrote {config.FACILITIES_QC}")


if __name__ == "__main__":
    main()

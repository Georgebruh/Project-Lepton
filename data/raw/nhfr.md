Source URL: https://nhfr.doh.gov.ph (DOH National Health Facility Registry, "Active facilities")
List: https://nhfr.doh.gov.ph/VActivefacilitiesList?cmd=search&x_factype=17,20,21&z_factype=LIKE&x_regcode=13&z_regcode=LIKE&recperpage=ALL
Detail pages: https://nhfr.doh.gov.ph/VActivefacilitiesView/<facility code>?showdetail=
Downloaded on (YYYY-MM-DD): 2026-10-15
Downloaded by: a team member
Version / release: the live registry, no version number; this copy is as of the download date.
Notes: Made by `python -m src.facilities` (task A10). Saved in data/raw/nhfr/, unchanged:
list_ncr.html (559 NCR facilities of types Rural Health Unit 17, Barangay Health Station 20,
City Health Office 21) and one detail page per QC facility (69 pages), 9.8 MB in all.
The list and its CSV export have no coordinates; only the detail pages do (north_coord =
latitude, east_coord = longitude), with the barangay's 10-digit PSGC (bgycodepsgc).
Table: data/clean/health_facilities_qc.csv (config.FACILITIES_QC), 69 rows: 67 health centers
(registered as "Rural Health Unit"), 1 Barangay Health Station (Villamor BHS), 1 City Health
Office (Quezon City Health Department); all government; 58 of the 142 barangays have one.
68 have coordinates, all inside QC (checked against the OpenStreetMap outline of QC).
Bago Bantay Health Center (DOH000000000008298, barangay Alicia) has 0, 0 in the registry,
kept as missing: C7 must place it by hand or by its barangay.
Checked 2026-10-18: it is the same center as DOH000000000001842 (same name and barangay,
Bukidnon St., with coordinates but no licence data). QC's own health-center directory lists
one Bago Bantay Health Center, at 84 Sto. Niño St., Alicia, which is 8298's address
(https://quezoncity.gov.ph/qcitizen-guides/quezon-city-health-centers/). So 1842 is the
center's older entry. C7 places the center at 1842's point, inside Alicia; leaving 8298 out
changes no barangay's need.
Checked 2026-10-18 (A10's barangay check on this table): every facility's psgc is one of
A5's 142. One lies outside its own barangay: Villamor Barangay Health Station, registered in
Doña Imelda, 11.0 km away (C7 leaves it out).
The registry sends "?" for "Ñ" (e.g. "DO?A IMELDA"): join on psgc, never on names.
Facility heads' names and e-mails are on the raw pages but left out of the table.
The site's firewall blocks requests without a browser User-Agent; the script sends one and
waits 1 second between pages.
Cite: Department of Health, National Health Facility Registry, https://nhfr.doh.gov.ph,
accessed 2026-10-15.

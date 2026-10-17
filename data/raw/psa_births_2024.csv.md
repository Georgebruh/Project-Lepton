Source URL: https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1A/VS/BI/0011A1ABIB8.px
  (PSA OpenSTAT, Vital Statistics > Births, table 1A1ABIB8; table list at
  https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1A__VS__BI/?tablelist=true)
Downloaded on (YYYY-MM-DD): 2026-10-17
Downloaded by: Hans
Version / release: "Number of Registered Live Births by Place of Occurence, Usual Residence of
  Mother, Sex of the Child, and by Region, Province, and City/Municipality, Philippines: 2024",
  PSA Vital Statistics Division. Data last updated 2026-03-12, table created 2026-07-01,
  listed on OpenSTAT as updated 2026-07-17. PSA's next update (2025 births) is due 2027-07-01,
  so 2024 is the latest year available on the download date.
Notes: Task A12, for the pregnant count in C4. Year used: 2024, the same year as the census
  totals C1 and C4 use.
  The whole table, unchanged, as OpenSTAT's CSV (Windows-1252: read with encoding="cp1252").
  1,736 rows: the Philippines, regions, provinces and cities/municipalities (names indented
  with 4 or 6 dots by level) and "FOREIGN COUNTRY". Columns: Geolocation, then
  Place of Occurrence and Usual Residence, each Both Sexes / Male / Female.
  The CSV has no codes; QC is the one row named "Quezon City" (PSGC 1381300000 in the PX file).
  Seven other rows contain "Quezon" (Quezon province and towns named Quezon): match the
  whole name.
  QC, 2024: 32,578 births to mothers who live in QC (Usual Residence, Both Sexes): use this one.
  By place of occurrence it is 37,024, because QC's hospitals also deliver babies of mothers
  from other cities. With C4's factor 0.75 (config.PREG_BIRTHS_FACTOR): 24,434 pregnant women,
  0.79% of QC's 2024 census total (the plan's upper bound is 3.5%).
  Checked: the Philippines 1,358,989 and NCR 152,638 (by residence) match PSA's 2024 national
  and NCR releases. QC by mother's residence (OpenSTAT table 0221A1ABIR0 for 2013-2023):
  2019 48,459; 2020 44,445; 2021 35,045; 2022 33,630; 2023 34,784; 2024 32,578. 2024 is 6.3%
  below 2023, like the national fall (6.2%); QC stays 21.0-21.3% of NCR since 2022. The 39,347
  for QC in 2023 quoted in some releases is by place of occurrence, not residence.
  PSA's notes: counts of actual registrations, not adjusted for under-registration; births
  registered after PSA's data cut are not included.
  psa.gov.ph and rssoncr.psa.gov.ph block scripts (Cloudflare); the OpenSTAT API does not.
  To download again (Git Bash), 72,702 bytes:
    curl -X POST -H "Content-Type: application/json" -o psa_births_2024.csv \
      https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1A/VS/BI/0011A1ABIB8.px \
      -d '{"query":[{"code":"Geolocation","selection":{"filter":"all","values":["*"]}},{"code":"Place","selection":{"filter":"all","values":["*"]}},{"code":"Sex","selection":{"filter":"all","values":["*"]}}],"response":{"format":"csv"}}'
Cite: Philippine Statistics Authority (2026). Number of Registered Live Births by Place of
  Occurrence, Usual Residence of Mother, Sex of the Child, and by Region, Province, and
  City/Municipality, Philippines: 2024 [OpenSTAT table 1A1ABIB8]. https://openstat.psa.gov.ph,
  accessed 2026-10-17.

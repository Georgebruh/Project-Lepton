Source URL: none; sent by e-mail by the Quezon City Epidemiology and Surveillance Division
  (QCESD, QC Health Department), in reply to the team's A1 request sent by George for the team.
Downloaded on (YYYY-MM-DD): 2026-10-20 (saved from the e-mail; confirm the date QCESD replied)
Downloaded by: Ryan
Version / release: QCESD's case list as extracted for us, no version number. Latest date in it:
  2026-10-18 (an admission), so the extract is from that day or later.
Notes: Task A13. CASE-LEVEL RECORDS: saved unchanged in data/raw/qcesd/ (config.QCESD_CASES_RAW),
  which git ignores. Never commit it, never copy rows from it into the repository, results/ or
  the app, and share it only through the team drive (rule 11). Ethics (E2): the adviser
  approved aggregating it to weekly counts (2026-10-20); file the formal request or exemption
  and record its date in E2.
  Publishing: QCESD gave permission to publish the weekly city totals, 2015-2026 (the counts
  in cases_weekly.csv, which appear as `y` in results/forecasts*.csv and in
  app/public/data/city_forecast.json). Nothing else from the list may be published. Confirmed
  by Dexter for G11 on 2026-10-22 (GitHub #83). QCESD's e-mail or letter is kept on the team
  drive beside the case list.
  File: U.P Cebu Data Request.xlsx, 191,344 bytes, SHA-256
    c37cf6e28a705abcc78b47fd83b314ff30b844770b14367f13d93eaaf6f617d7.
  Layout: one sheet per year, 2026 down to 2015, one row per case, no names. Columns
    Year_of_onset, Date_of_onset, Morbidity_week, Date_of_Admission, District (1-6), Barangay
    (names, not PSGC codes). 4,953 cases; onset 2015-01-30 to 2026-10-14.
  Checked 2026-10-20 (src/cases.py reads only the two dates):
  - Morbidity_week changes meaning between years: the MMWR week of onset in 2024-2026, of
    admission in 2018, 2020, 2022 and 2023, and the month of admission (1-12) in 2015-2017,
    2019 and 2021 (at least 98% of each year's rows). Year_of_onset (= the sheet) follows the
    same date. So weeks are taken from Date_of_onset, never from Morbidity_week.
  - Every case has an onset date; 203 (all in 2026) have no admission date.
  - Onset to admission: median 4 days, 95% within 10, 99% within 17
    (config.CASES_COMPLETE_DAYS). 27 cases were admitted before onset or over 30 days after,
    likely a typo in one of the dates (often day and month swapped); kept as given.
  - 136 rows repeat another row in all six columns. Kept: with them the list gives QCESD's
    published totals (cases admitted 1 Jan to 31 Aug 2025: 535, as published to 1 Sep), so
    they are separate cases with the same dates and barangay.
  - QCESD's published 2025 totals (config.CASES_PUBLISHED): 510 from 1 Jan to 20 Aug (DZRH,
    25 Aug 2025) and 535 from 1 Jan to 1 Sep (MesVaccins, 3 Sep 2025, citing Outbreak News
    Today). The list has 522 and 553 by onset, 514 and 538 by admission. Earlier totals were
    published mid-surge and are lower than the list: 207 to 3 Aug (Outbreak News Today, 8 Aug
    2025), against 264 admitted by then. Reports were still arriving: the delay the guard g
    stands for.
  Table: data/clean/cases_weekly.csv (config.CASES_WEEKLY), by `python -m src.cases`: one row
    per MMWR week from 2015 week 1 to 2026 week 42, cases by onset week, final to 2026 week 38
    (weeks 39-42 missing, still filling in). Weekly totals only: no barangay, no dates.
Cite: Quezon City Health Department, Epidemiology and Surveillance Division (2026).
  Leptospirosis case list, Quezon City, 2015-2026 [unpublished data, received 2026-10-20].

Source URL: https://data.mendeley.com/datasets/v98325dpxv/1
  (S. J. Parreño, "Philippine Epidemiological Data", Mendeley Data, v1, Dec. 2023;
  DOI 10.17632/v98325dpxv.1)
Downloaded on (YYYY-MM-DD): 2026-10-17
Downloaded by: Russel
Version / release: v1 (Dec. 2023). File: Diseases Data (for NBL).xlsx, saved unchanged in
  data/raw/parreno/ (config.PARRENO_RAW).
Notes: Task A9, then B3 (national weekly leptospirosis, 2019 to week 43 of 2023).
  DOI check: matches ref. 9 in Latigay & Gonzaga (2026); the paper writes it
  10.17632/v98325dpxv1, without the dot before the version.
  Layout: one row per week number (1-52), one column per disease and year, e.g.
  "Leptospirosis - 2019".
  Cleaned by: python -m src.benchmark -> data/clean/parreno_national_weekly.csv
  (252 ISO weeks, 25 empty, all in 2020; one of them is 2020 week 53, which the file has
  no row for: see the top of src/benchmark.py).

Source URL: https://github.com/faeldon/philippines-json-maps (MIT License, (c) James Faeldon),
  pinned to commit 8eeead560246863c8c820c31ca6fbca81a279477 (17 Sep 2024), folder
  2023/geojson/provdists/hires/; the full URL pattern is config.NCR_CITIES_URL.
Downloaded on (YYYY-MM-DD): 2026-10-19
Downloaded by: George (by python -m src.app_data, which fetches them if they are missing)
Version / release: the repository's 2023 maps: PSGC as of 31 December 2023 (PSA's 4Q 2023
  summary), simplified by the author with mapshaper at 10% ("hires"), longitude/latitude.
Notes: Task F2. Four files, saved unchanged in data/raw/ncr_cities/ (config.NCR_CITIES_RAW),
  one per NCR district (config.NCR_DISTRICTS): municities-provdist-1303900000.0.1.json
  (City of Manila), -1307400000 (Mandaluyong, Marikina, Pasig, Quezon City, San Juan),
  -1307500000 (Caloocan, Malabon, Navotas, Valenzuela) and -1307600000 (Las Piñas, Makati,
  Muntinlupa, Parañaque, Pasay, Taguig, Pateros): NCR's 17 cities and municipality.
  Fields used: adm3_psgc (10-digit PSGC; Quezon City is 1381300000) and adm3_en (name).
  The app's ncr_cities.geojson is made from them by src/app_data.py (map_shapes): the
  districts' borders do not quite meet (about 90 slivers of gap and 0.2 km2 of overlap), so
  the outlines are cleaned into one coverage, Quezon City's outline is replaced by A5's
  barangays joined (faeldon's lies up to 161 m from them), and all are simplified together
  (config.MAP_SIMPLIFY_M). Credit the source on the app's footer and How it works (U8).

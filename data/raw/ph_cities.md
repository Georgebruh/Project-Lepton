Source URL: https://github.com/faeldon/philippines-json-maps (MIT License, (c) James Faeldon),
  pinned to commit 8eeead560246863c8c820c31ca6fbca81a279477 (17 Sep 2024), as data/raw/ncr_cities/;
  the full URL pattern is config.FAELDON_URL.
Downloaded on (YYYY-MM-DD): 2026-10-22
Downloaded by: a team member (by python -m src.app_data, which fetches them if they are missing)
Version / release: the repository's 2023 maps: PSGC as of 31 December 2023, longitude/latitude.
Notes: Task F14 (the app's map of the whole Philippines). Saved unchanged in data/raw/ph_cities/
  (config.PH_CITIES_RAW):
  - regions/lowres/provdists-region-<PSGC>.0.001.json, faeldon's 17 regions (config.PH_REGIONS):
    only their province PSGCs (adm2_psgc) and names (adm2_en) are read;
  - provdists/hires/municities-provdist-<PSGC>.0.1.json, one per province, 84 files (NCR's four
    districts come from data/raw/ncr_cities/ instead); 1909900000, BARMM's Special Geographic
    Area, is an empty GeometryCollection (its 8 municipalities date from 2024);
  - municities/hires/bgysubmuns-municity-<PSGC>.0.1.json for the 24 towns no province file holds
    (the 16 highly urbanized cities outside NCR and the Special Geographic Area's 8): each is its
    barangays joined. faeldon gives these no town name, so config.PH_TOWNS_APART names them and the
    province they lie in, checked against OpenStreetMap (Nominatim) on 2026-10-22.
  Fields used: adm3_psgc (10-digit PSGC), adm3_en (name), adm2_psgc (province). 1,642 towns in all
  (config.PH_CITY_COUNT). src/app_data.py writes app/public/data/ph_cities.json from them.
  Credit the source on the app's footer and How it works (U8), as for the NCR files.

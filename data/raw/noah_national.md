Source URL: https://noah.up.edu.ph ("Downloads"), the public Google Drive folder
  https://drive.google.com/drive/folders/1ALE4-E9c-4AGjm1fqiPprWHrLUskeY9o -> Flood -> 5yr / 25yr / 100yr
  (folder ids in config.NOAH_NATIONAL_FOLDERS), one zip per province, as A8's Metro Manila maps.
Downloaded on (YYYY-MM-DD): 2026-10-22
Script: python -m src.noah_national
Version / release: NOAH gives no version number; each province's Drive date is its version, listed
  in data/clean/noah_national/manifest.csv (return_period, province, file_name, drive_id,
  drive_modified, shapefiles, features, patches, area_km2, prepared_on). Where NOAH's folder holds a
  province twice (Misamis Oriental: "Misamis Oriental.zip" of 2024-10-29 and "MisamisOriental.zip"
  of 2021-11-11), the newer file is used. On 2026-10-22: 66 provinces in the 5-year folder, 71 in
  the 25-year, 79 in the 100-year, dated 2021-11-07 to 2026-09-27. Two of NOAH's files are empty:
  the 100-year TawiTawi.zip (22 bytes, no shapefile) and the 5-year Masbate shapefile (no shapes);
  the manifest lists both with 0 features, and those maps have no flood zones there.
  The tiles: 5-year 60 MB, 25-year 65 MB, 100-year 54 MB (its densest tiles thinned to 300 KB
  each to stay under GitHub's limit: config.NOAH_TILE_LIMITS).
Notes: Task F14, the app's NOAH layer for the whole country. 6 to 8 GB in all, so the zips are NOT
  kept: each is read, prepared into data/clean/noah_national/<T>yr/<province>.fgb and deleted.
  The app's tiles (app/public/data/noah_flood_<T>yr.pmtiles) are made from those files with
  tippecanoe. On 2026-10-22 each map's prepared files were deleted once its tiles were written
  (the laptop had under 5 GB free); manifest.csv stays. For looking at only: every LEPTON number
  uses A8's Metro Manila maps (C2).
  Licence: ODC-ODbL (NOAH's metadata_flood.txt); the tiles are shared under the same licence.
  Cite: UP Resilience Institute / NOAH Center, Project NOAH flood hazard maps (5-, 25-, 100-year
  rain return), https://noah.up.edu.ph

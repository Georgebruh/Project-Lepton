Source URL: https://noah.up.edu.ph ("Downloads" button), which links the public Google Drive folder
https://drive.google.com/drive/folders/1ALE4-E9c-4AGjm1fqiPprWHrLUskeY9o -> Flood -> 5yr / 25yr / 100yr
(file ids in config.NOAH_FLOOD_FILES and config.NOAH_METADATA_FILES)
Downloaded on (YYYY-MM-DD): 2026-10-15
Version / release: NOAH gives no version number, so each map's version is its two dates:
| Map | Saved as | Drive file, last modified | Shapefile inside, dated | Bytes |
| 5-year | MetroManila_5yr.zip (Drive name MetroManila.zip) | 2021-11-11 | MetroManila_Flood_5year.shp, 2021-11-09 | 33,382,053 |
| 25-year | MetroManila_25yr.zip (Drive name MetroManila.zip) | 2021-11-11 | MetroManila_Flood_25year.shp, 2021-07-22 | 36,248,349 |
| 100-year | MetroManila_100yr.zip (Drive name "Metro Manila.zip") | 2025-11-06 | MetroManila_Flood_100year.shp, 2022-11-28 | 24,855,864 |
Also kept: metadata_flood.txt (Drive 2024-08-28), 01ReadMe_Flood.pdf (2022-01-20),
NOAH_License.pdf (2021-10-21).
Notes: Made by `python -m src.noah` (task A8). Saved in data/raw/noah/, contents unchanged;
only the zip names differ, because all three are called MetroManila.zip on Drive.
Each map: EPSG:4326, 3 MultiPolygon rows, one per Var (1 low 0-0.5 m, 2 medium >0.5-1.5 m,
3 high >1.5 m, per metadata_flood.txt), and all 3 rows invalid as published.
The script reprojects to EPSG:32651, runs make_valid (keeping polygon parts), dissolves
by Var and removes the overlaps between levels (the higher level keeps the area) into
data/clean/noah_flood_mm.gpkg (config.NOAH_FLOOD), 9 rows: return_period, var,
area_km2, geometry. Areas as published (km2), Var 1 / 2 / 3, all:
5-year 83.37 / 71.66 / 27.20, 182.22; 25-year 82.36 / 105.96 / 46.93, 235.26;
100-year 71.60 / 112.72 / 63.76, 248.08.
make_valid keeps these areas (checked 2026-10-15 against shapely's "structure" repair:
same areas to 0.01 km2; the shapes are invalid because rings cross or touch themselves).
Hazard levels of the same map overlap in NOAH's own shapes: 5-year 0, 25-year 0.0003 km2,
100-year 0.80 km2 in all (Var 1/2 0.41, 1/3 0.08, 2/3 0.30). C2 adds the levels up, so
the higher level keeps that area. In the clean file the 100-year map is then
71.10 / 112.42 / 63.76, 247.28 km2; the other two are unchanged at 2 decimals.
The maps reach lon 121.135, lat 14.785, which covers QC (OSM outline to 121.134, 14.776),
so the Rizal and Bulacan maps are not needed for QC.
S8 inspection (2026-10-18): in 11 barangays the exposed count falls from the 5-year map to a
rarer one. In 10 of them (Bayanihan, Malaya, Marilag, Pag-ibig Sa Nayon, Sacred Heart,
San Jose, San Martin de Porres, Sikatuna Village, Teachers Village West, Villa Maria Clara;
0.06-0.57 km2 each, around Project 4, Cubao and Diliman) the 25-year map floods more than
the 5-year one, but the 100-year map floods less: its flood shapes are thinner and in places
shifted by a pixel or two. The 100-year shapefile is a later NOAH release (dated 2022-11-28;
the other two 2021) and all three come in EPSG:4326 and go through the same steps, so the
difference is in NOAH's maps, not in A8 or C2. The largest drop is San Jose, 2,064 residents
on the 5-year map against 1,522 on the 100-year (542 people, 9% of its population). Batasan
Hills falls 0.2% from the 5- to the 25-year map, then rises. QC's total still rises
(675,551, 860,921, 893,375). The maps are used as published; the paper names this as a
limitation.
Licence: ODC-ODbL (metadata_flood.txt); anything built from the maps is shared under ODbL.
Cite: UP Resilience Institute / NOAH Center, Project NOAH flood hazard maps (5-, 25-, 100-year
rain return), Metro Manila, https://noah.up.edu.ph

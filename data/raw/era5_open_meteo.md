Source URL: https://archive-api.open-meteo.com/v1/archive (Open-Meteo Historical Weather API;
  docs https://open-meteo.com/en/docs/historical-weather-api)
Downloaded on (YYYY-MM-DD): 2026-10-17
Downloaded by: a team member
Version / release: the live archive, no version number. Model ERA5 (models=era5, the plain
  ECMWF ERA5 reanalysis at 0.25 degree, not Open-Meteo's ERA5-Land or blended "best match"),
  variable precipitation (mm, hourly).
Notes: Made by `python -m src.era5` (task A14). Saved in data/raw/era5_open_meteo/, unchanged:
  one JSON reply per year, named era5_<year>.json, 2000 to 2025 (26 files, about 21 MB).
  Request: the same 4 grid points as A15 (lat 14.50 / 14.75, lon 121.00 / 121.25; the 0.25
  degree cells that overlap the A7 catchments, catchments.grid_cells), cell_selection=nearest
  (the grid point itself), timezone=GMT. 2000 starts on 1 June 2000, IMERG's first day
  (config.ERA5_START), so the ERA5 and IMERG fits use the same years. Each year runs to
  1 January of the next year, for the 00:00 value (the last hour of 31 December).
  Each hour is labelled by its end (01:00 = rain from 00:00 to 01:00 UTC), so src/era5.py
  shifts labels back 1 hour before summing UTC days, as A15 does.
  Check on 2026-10-17: every hour present at all 4 points, no negative values. Carina
  (2024-07-23, 193.5 mm over the catchments) and Ulysses (2020-11-11, 236.5 mm) are their
  years' wettest UTC days; Ondoy is 142.6 mm on 2009-09-26 UTC. The 2012 habagat
  (6-8 Aug PHT) peaks at only 53.7 mm: ERA5 smooths out heavy monsoon rain, which is why
  C9 matches forecasts on ERA5's own return levels and never on IMERG's (rule 3).
  Table: data/clean/era5_daily.csv (config.ERA5_DAILY), one row per UTC day and cell:
  date, lat, lon, weight, rain_mm; catchment rain = sum(weight x rain_mm).
Cite: Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software]. Zenodo.
  https://doi.org/10.5281/zenodo.7970649. Hersbach, H. et al. (2020). The ERA5 global
  reanalysis. Q. J. R. Meteorol. Soc. 146, 1999-2049. https://doi.org/10.1002/qj.3803.
  "Weather data by Open-Meteo.com" (CC BY 4.0); ERA5 contains modified Copernicus Climate
  Change Service information.

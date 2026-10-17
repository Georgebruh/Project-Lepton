Source URL: https://previous-runs-api.open-meteo.com/v1/forecast (Open-Meteo Previous Runs API;
  docs https://open-meteo.com/en/docs/previous-runs-api)
Downloaded on (YYYY-MM-DD): 2026-10-16
Downloaded by: George
Version / release: the live archive, no version number. Model ECMWF IFS 0.25 degree
  (models=ecmwf_ifs025), variables precipitation_previous_day1, _day2 and _day3 (mm, hourly).
Notes: Made by `python -m src.ecmwf` (task A15). Saved in data/raw/ecmwf_previous_runs/,
  unchanged: one JSON reply per storm, named <storm>_<model>_<first day>_<last day>.json.
  Request: the 4 grid points of the 0.25 degree cells that overlap the A7 catchments
  (lat 14.50 / 14.75, lon 121.00 / 121.25; catchments.grid_cells), cell_selection=nearest
  (the grid point itself), timezone=GMT, from the storm's first wettest UTC day to the day
  after its last (for that day's 00:00 value).
  previous_dayN: for each hour, the value from a run started at least 24 x N hours before
  it (Open-Meteo drops each run's first 24 x N hours and joins the runs into one series).
  ECMWF's 3-hour totals are spread evenly over their 3 hours, and each hour is labelled
  by its end (01:00 = rain from 00:00 to 01:00 UTC), so src/ecmwf.py shifts labels back
  1 hour before summing UTC days.
  Archive check (2026-10-16): day 1 starts at 2024-02-03 22:00 UTC (day 2 and day 3 one
  and two days later), with no missing hour up to 2024-08-31. 2025-07-01 to 2025-08-31
  and 2026-07-15 to 2026-09-15 have every hour at all 4 points for all 3 leads.
  Files so far: carina_2024_ecmwf_ifs025_20240723_20240725.json (Carina, 23-25 July 2024;
  covered). Renamed on 2026-10-17 to add the model (was carina_2024_20240723_20240725.json);
  contents unchanged.
  The 2025 and 2026 storms are fetched once A11's dates are in config.STORMS.
  Table: data/clean/forecasts_storms.csv (config.FORECASTS_STORMS).
Cite: Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software]. Zenodo.
  https://doi.org/10.5281/zenodo.7970649. Forecast data: ECMWF IFS open data, CC BY 4.0;
  "Weather data by Open-Meteo.com" (CC BY 4.0).

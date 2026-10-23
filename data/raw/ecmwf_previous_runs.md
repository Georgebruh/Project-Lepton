Source URL: https://previous-runs-api.open-meteo.com/v1/forecast (Open-Meteo Previous Runs API;
  docs https://open-meteo.com/en/docs/previous-runs-api)
Downloaded on (YYYY-MM-DD): 2026-10-16 (Carina, previous days 1-3); 2026-10-18 (all four
  storms, previous days 1-5)
Downloaded by: a team member
Version / release: the live archive, no version number. Model ECMWF IFS 0.25 degree
  (models=ecmwf_ifs025), variables precipitation_previous_day1 to _day5 (mm, hourly;
  config.FORECAST_PREVIOUS_DAYS). The 2026-10-16 file has _day1 to _day3 only.
Notes: Made by `python -m src.ecmwf` (task A15). Saved in data/raw/ecmwf_previous_runs/,
  unchanged: one JSON reply per storm, named <storm>_<model>_<first day>_<last day>.json.
  Request: the 4 grid points of the 0.25 degree cells that overlap the A7 catchments
  (lat 14.50 / 14.75, lon 121.00 / 121.25; catchments.grid_cells), cell_selection=nearest
  (the grid point itself), timezone=GMT, from 2 days before the storm's first wettest UTC
  day (config.RAIN_ACCUM_DAYS - 1, so a 3-day window ending on that day is covered) to the
  day after its last (for that day's 00:00 value).
  previous_dayN: for each hour, the value from a run started at least 24 x N hours before
  it (Open-Meteo drops each run's first 24 x N hours and joins the runs into one series).
  ECMWF's 3-hour totals are spread evenly over their 3 hours, and each hour is labelled
  by its end (01:00 = rain from 00:00 to 01:00 UTC), so src/ecmwf.py shifts labels back
  1 hour before summing UTC days.
  Why days 1-5: C9 forecasts 3-day totals 1, 2 and 3 days before the window. A forecast
  made L days before takes the window's days 1, 2 and 3 from previous_day L, L + 1 and
  L + 2, so leads 1-3 need previous days 1-5.
  Archive check (2026-10-16): day 1 starts at 2024-02-03 22:00 UTC (day 2 and day 3 one
  and two days later), with no missing hour up to 2024-08-31. 2025-07-01 to 2025-08-31
  and 2026-07-15 to 2026-09-15 have every hour at all 4 points for all 3 leads.
  Files:
    carina_2024_ecmwf_ifs025_20240723_20240725.json (2026-10-16; 23-25 July 2024, days 1-3).
      Renamed on 2026-10-17 to add the model (was carina_2024_20240723_20240725.json);
      contents unchanged. No longer read by the code; kept as downloaded.
    carina_2024_ecmwf_ifs025_20240721_20240725.json (2026-10-18; 21-25 July 2024, days 1-5;
      covered). Its days 1-3 for 23-25 July match the 2026-10-16 file in every hour.
    floods_2025_ecmwf_ifs025_20250719_20250723.json (2026-10-18; 19-23 July 2025, days 1-5;
      covered). Fetched for the first 2025 wettest days (21-23 July); A11 moved them to
      17-19 July (commit f62bbb7), so it is no longer read by the code; kept as downloaded.
    floods_2025_ecmwf_ifs025_20250715_20250719.json (2026-10-18; 15-19 July 2025, days 1-5;
      covered).
    habagat_2026_ecmwf_ifs025_20260806_20260810.json (2026-10-18; 6-10 August 2026, days 1-5;
      covered).
    kristine_2024_ecmwf_ifs025_20241020_20241024.json (2026-10-18; 20-24 October 2024, days
      1-5; covered). Severe Tropical Storm Kristine (Trami), added by A11 in f62bbb7.
  Check on 2026-10-18: every hour of every day at all 4 points for previous days 1-5, all
  four storms. Carina, 23 July 2024, previous day 1: 91.7 mm over the catchments
  (recomputed by hand from the reply: 55.2, 62.1, 63.6 and 119.4 mm at the 4 points).
  Table: data/clean/forecasts_storms.csv (config.FORECASTS_STORMS), 400 rows: 4 storms x
  5 previous days x 5 UTC days x 4 cells.
Cite: Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software]. Zenodo.
  https://doi.org/10.5281/zenodo.7970649. Forecast data: ECMWF IFS open data, CC BY 4.0;
  "Weather data by Open-Meteo.com" (CC BY 4.0).

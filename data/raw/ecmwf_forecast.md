Source URL: https://api.open-meteo.com/v1/forecast (Open-Meteo Forecast API, https://open-meteo.com,
  CC BY 4.0), model ecmwf_ifs025 (ECMWF IFS 0.25 degree, config.FORECAST_MODEL), hourly
  precipitation, UTC, cell_selection=nearest; the request is app_simulation.forecast_params.
Downloaded on (YYYY-MM-DD): 2026-10-22 (one reply per day the simulation is run)
Downloaded by: a team member (by python -m src.app_simulation, which fetches the day's reply if it is missing)
Version / release: the forecast as Open-Meteo served it that day: its past days (the model's
  recent runs) back to 2 days before the first week B4's features lack, and its forecast to the
  day after the end of that week. Each reply is saved unchanged in data/raw/ecmwf_forecast/ as
  ecmwf_ifs025_<day>_<points>points_<first day>.json.
Notes: Task F14, the app's Simulation mode. Points: B4's IMERG cells with QC residents (weekly
  rain over QC, weighted by residents) and A15's four 0.25 degree cells over the catchments (EI,
  against ERA5's return levels, rule 3). Not a result: only the made-up Simulation mode uses it.
  Credit Open-Meteo (CC BY 4.0) wherever the simulated forecast is shown.

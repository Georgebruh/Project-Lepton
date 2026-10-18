# Project-Lepton
Leptospirosis Exposure Prediction &amp; Targeting Operational Network

A few days’ warning before a storm lets health offices send doxycycline to the barangays most likely to flood, and a week’s warning lets hospitals prepare for the cases that follow. Project LEPTON will give Local Government Units both warnings. Standard forecasting models smooth over the sharp post-typhoon spikes that define leptospirosis outbreaks, so health offices cannot position prophylaxis where needed. Project LEPTON will run on one shared flood computation combining NASA IMERG rainfall, Project NOAH flood hazard maps and WorldPop population data to estimate how many residents of each barangay a storm exposes. Layer 1, a negative binomial regression on season, recent cases, two weeks of rainfall and a flood exposure index, will forecast next week’s city-level cases with a 90% range and the probability of crossing the epidemic threshold. Layer 2 will convert 1- to 3-day rain forecasts into barangay-level prophylaxis stock under DOH Memorandum 2023-0309, serving the high-risk tier first when supplies run short. Layer 1 will be tested in a weekly rolling-origin backtest (2018 to 2026) against two seasonal baselines and the published Prophet-XGBoost hybrid, with mean absolute error as the primary endpoint. Layer 2 will be tested on Typhoon Carina (2024) and the 2025 and 2026 floods against flood reports.

Read `Notes.md` first: the open decisions, the changes from the plan, and what the paper
must say about them.

## Setup

1. Install Python 3.13, the version `requirements.txt` is pinned for.
2. From the repository root, make a virtual environment and install the packages:

   ```
   python -m venv .venv
   .venv\Scripts\activate            (Windows; on macOS or Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   ```

3. Copy the data files from the team drive into `data/raw/` and `data/clean/`. They are not in
   git. Each file in `data/raw/` has a note, `<file>.md`, saying where it was downloaded from.
4. Run the sanity checks:

   ```
   python -m src.checks
   ```

   Each check prints PASS, SKIP (its task is not built yet, or its data file is not on this
   computer) or FAIL. A FAIL stops work until it is fixed. Rerun the checks after any change.

## Rebuilding the data (Workstream A)

Run from the repository root, in this order (A4's box and the A14 and A15 grid cells come from A7's
catchments; A10 checks its facilities against A5's barangays):

| Task | Command | Writes |
| --- | --- | --- |
| A3 | `python -m src.weeks` | `data/clean/calendar_weeks.csv` |
| A7 | `python -m src.catchments` | `data/clean/catchments_qc.gpkg`, `results/catchments_qc.png` |
| A4 | `python -m src.imerg` | `data/raw/imerg_daily.nc`; needs a NASA Earthdata login (steps at the top of `src/imerg.py`) |
| A5 | `python -m src.census` | `data/clean/barangays_qc.gpkg`, `census_qc.csv`, `age_sex_2020_qc.csv` |
| A6 | `python -m src.worldpop` | `data/raw/phl_pop_2024_CN_100m_R2025A_v1.tif`, `data/clean/worldpop_2024_box.tif` |
| A8 | `python -m src.noah` | `data/raw/noah/` (the three maps and NOAH's notes), `data/clean/noah_flood_mm.gpkg`; can take over an hour |
| A10 | `python -m src.facilities` | `data/raw/nhfr/` (the registry pages), `data/clean/health_facilities_qc.csv` |
| A14 | `python -m src.era5` | `data/raw/era5_open_meteo/` (one reply per year), `data/clean/era5_daily.csv`; about 5 minutes |
| A9 | `python -m src.benchmark` | `data/clean/parreno_national_weekly.csv`; needs the Mendeley file in `data/raw/parreno/`, downloaded by hand (link in `data/raw/parreno.md`) |
| A11 | by hand: dates, D and flooded barangays in `config.STORMS`, with sources in `data/raw/storm-facts.md` | nothing; check "A11 storm facts" in `python -m src.checks` |
| A12 | by hand: the `curl` command in `data/raw/psa_births_2024.csv.md` | `data/raw/psa_births_2024.csv` |
| A15 | `python -m src.ecmwf` | `data/raw/ecmwf_previous_runs/` (one reply per storm), `data/clean/forecasts_storms.csv` (previous days 1-5 for C9's 3-day totals at leads 1-3, from 2 days before each storm's wettest days); storms without A11's dates in `config.STORMS` are skipped |

## Layer 1: city forecast (Workstream B)

| Task | Command | Writes |
| --- | --- | --- |
| B1 | `python -m src.population` | `data/clean/pop_weekly.csv`; needs only `config.py` (A5's census totals are in it) |
| B2 | none: `cutoff`, `visible`, `training_rows` and `prediction_row` in `src/view.py`, used by B5, B9 and B10. Set `config.DATA_OPTION` from A13's row first: option B sees every week up to forecast day T, option C up to T − g (`config.DELAY_GUARD_G`) | nothing; check "B2 view" in `python -m src.checks` |
| B7 | none: functions in `src/thresholds.py` (and `forecast_dist` in `src/forecast_range.py`), used by B8 and B10 | nothing; check S7 in `python -m src.checks` |
| B8 | none: functions in `src/baselines.py`, used by B10 | nothing; check "B8 M0 and M1" in `python -m src.checks` |
| B6 | none: `estimate_theta` and `theta_for` in `src/forecast_range.py`, used by B10 for every model's 90% range and breach probability | nothing; check S6 in `python -m src.checks` |
| B3 | `python -m src.m3` (then `--diagnose`) | `results/m3_reproduction.csv`, `m3_forecasts.csv`, `m3_diagnostics.csv`; needs A9's file; about a minute. Findings: `results/m3_reproduction.md` |
| B9 | none: `m3_forecast` in `src/m3_port.py`, used by B10 (M3 refitted on the weeks it may see, about 0.5 s a forecast day) | nothing; check "B9 M3" in `python -m src.checks` |
| B5 | none: `model_rows`, `fit_m4` (M4, and M4 without EI2 with `with_ei=False`) and `predict_m4` in `src/m4.py`, used by B10 at every forecast day; `plot_residual_acf` draws v2's residual check once case data exist (`results/m4_residual_acf.png`). Inputs: B2's rows, B4's weekly `rcum2` and `ei2`, B1's population | nothing; check S5 in `python -m src.checks` (50 made-up datasets, a few seconds) |
| B10 | `python -m src.backtest` (option from `config.DATA_OPTION`, or `--option B`/`C`; `--g 1` and `--g 3` for the guard reruns). Before A13: `python -m src.backtest --simulate --option C` on made-up QC-shaped counts | `results/forecasts.csv`: one row per model (M0, M1, M3, M4, M4_noEI) and forecast day, 2018 week 1 on, with mu, theta, the 23 WIS quantiles, the threshold, Pr(breach), y and breached. Guard reruns write `forecasts_g1.csv`, simulated runs `forecasts_simulated_B.csv` / `_C.csv`. Needs B1, B4 (`features_weekly.csv`) and A13; about 12 minutes (M3 refits Prophet every week). Check S11 in `python -m src.checks` |

## Layer 2: barangay doses (Workstream C)

Run after Workstream A, in this order:

| Task | Command | Writes |
| --- | --- | --- |
| C1 | `python -m src.rescale` | `data/clean/worldpop_scale_qc.csv`; needs A5 and A6 |
| C2 | `python -m src.overlay` | `data/clean/overlay_qc.csv`; needs A5, A8 and C1's file (team drive, or run C1 first); about a minute |
| C3 | `python -m src.flood_exposure` | `data/clean/ei_weekly.csv` (one EI series per forecast year, 2018–2026, on 3-day rain totals, `config.RAIN_ACCUM_DAYS`); needs A3, A4, A7, A5 and C2's file; seconds. Prints each year's return levels and where the storms fall. Comparison runs: `--days 1` (single wettest day) writes `ei_weekly_1day.csv`; `--without-2000` (refit without June–December 2000) writes `ei_weekly_no2000.csv` |
| C4 | `python -m src.shares` | `data/clean/shares_qc.csv`; needs A5 and A12's `data/raw/psa_births_2024.csv` |
| C5 | `python -m src.exposed` | no file: prints QC's exposed people and adult risk tiers at each map's own rain; needs C2 and C4. C8 and C9 call its `exposed_with_tiers` |
| C6 | `python -m src.doses` | no file: prints QC's stock (doxycycline, children's courses, amoxicillin) at each map's own rain; needs C2 and C4. C7, C8 and C9 call its `barangay_doses`. Stock planning, not prescriptions |
| C7 | `python -m src.allocation` | `data/clean/center_shares_qc.csv` (each barangay's need to its health centers); needs A5, A10 and C1, and C2 and C4 for its preview of stock per health center and `allocate`; a few seconds |
| C8 | `python -m src.observed_run` | `results/c8_observed_runs.csv` (per storm, test, D, cut-off and w: IMERG's 3-day rain against IMERG's return levels fitted on years before the storm, its return period, EI, flagged-versus-flooded shares, QC's exposed people, tiers and units), `c8_observed_barangays.csv` and `c8_observed_centers.csv` (the main run, per barangay and per health center); each storm on observed rain with A11's D, rerun with the continuous-exposure cut-off at 1 and 3 days and with D ± 1 day; needs A4, A7, A5, C2, C4 and C7's files; a few seconds. Stock planning, not prescriptions |
| C9 | `python -m src.forecast_run` | `results/c9_forecast_runs.csv` (per storm, run, D and w: rain against the return levels, EI, flagged-versus-flooded shares, QC's units), `c9_forecast_barangays.csv`, `c9_forecast_centers.csv`; ECMWF 3-day forecasts at leads 1-3 on ERA5's return levels, beside the observed IMERG run; needs A4, A7, A14, A15, A5, C2, C4 and C7's files; a few seconds. Stock planning, not prescriptions |


## Evaluation (Workstream D)

| Task | Command | Writes |
| --- | --- | --- |
| D1 | none: `point_scores`, `wis`, `covered` and `score_models` in `src/scores.py`, used on B10's forecasts (columns model, week_index, year, y, mu, theta) | nothing; check "S7 scores" in `python -m src.checks` |
| D2 | none: `mase_denominator` and `add_mase` in `src/scores.py`: `add_mase(score_models(table, config.MAE_YEARS), mase_denominator(cases))` | nothing; check "D2 MASE" in `python -m src.checks` |
| D3 | none: `brier`, `base_rate`, `brier_skill_score`, `reliability`, `alarm_test`, `episodes` and `caught_share` in `src/breach_scores.py` | nothing; check "S7 scores" in `python -m src.checks` |
| D7 | `python -m src.layer2_results` | `results/d7_map_<storm>.png` (one per storm, C8's main run: share of each barangay's residents in flood zones, and doxycycline capsules; A11's flooded barangays outlined), `d7_centers.csv` (doses per health center, whole units), `d7_flags.csv` (flagged versus flooded, observed run and each lead), `d7_tests.csv` (the cut-off test and D ± 1), `d7_forecast_vs_observed.csv` (C9's doses at each lead beside C8's observed doses); reads C8's and C9's results files and A5's `barangays_qc.gpkg`, and stops if C8's main run and C9's observed run disagree; a few seconds. No validation regression: no barangay case counts. Stock planning, not prescriptions |

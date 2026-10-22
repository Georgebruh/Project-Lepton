# Project-Lepton
Leptospirosis Exposure Prediction &amp; Targeting Operational Network

A few days’ warning before a storm lets health offices send doxycycline to the barangays most likely to flood, and a week’s warning lets hospitals prepare for the cases that follow. Project LEPTON will give Local Government Units both warnings. Standard forecasting models smooth over the sharp post-typhoon spikes that define leptospirosis outbreaks, so health offices cannot position prophylaxis where needed. Project LEPTON will run on one shared flood computation combining NASA IMERG rainfall, Project NOAH flood hazard maps and WorldPop population data to estimate how many residents of each barangay a storm exposes. Layer 1, a negative binomial regression on season, recent cases, two weeks of rainfall and a flood exposure index, will forecast next week’s city-level cases with a 90% range and the probability of crossing the epidemic threshold. Layer 2 will convert 1- to 3-day rain forecasts into barangay-level prophylaxis stock under DOH Memorandum 2023-0309, serving the high-risk tier first when supplies run short. Layer 1 will be tested in a weekly rolling-origin backtest (2018 to 2026) against two seasonal baselines and the published Prophet-XGBoost hybrid, with mean absolute error as the primary endpoint. Layer 2 will be tested on Typhoon Carina (2024) and the 2025 and 2026 floods against flood reports.

## Submission rules (task E1)

From the 2026 PJDSC Event Primer (pages 8–15), read on October 18, 2026. The primer says exact
dates may change: check PJDSC's Facebook page before the deadline.

**Due Saturday, October 24, 2026, 11:59 PM** (not October 23), through
bit.ly/pjdsc2026FinalProjectSubmission. The primer asks for no written paper (the team's paper in
`paper/` is extra, not a required item). The final submission is:

| Item | Limit | Penalty for going over |
| --- | --- | --- |
| Slide deck, PDF | 20 slides, counting the title slide, references and appendices | 1 point for every 1–2 slides over, at most 10 |
| Recorded demonstration video | 3 minutes | 1 point for every 15 seconds over, at most 10 |
| Link to the complete code repository | none given | none |

Results are expected: "Findings and Analysis" is a judging criterion. The judging criteria:

- **Project rationale and design:** problem statement and motivation; data sources and acquisition; methodology and approach.
- **Execution and impact:** findings and analysis; challenges and mitigation strategies; future directions and real-world application.
- **Code repository:** code structure and documentation; functional execution and reproducibility; dependencies and data management.
- **Demonstration video:** communication quality and clarity; technical content and functional showcase; how much it helps the audience understand.
- **Technical rigor and innovation:** validity and appropriateness of techniques; novelty and creativity; analytical depth.
- **Sources:** reliable, up to date, APA 7th edition.

After the deadline:

- The top 10 teams are announced on November 4, 2026. Finalists present on November 14, 2026, in
  Quezon City: a live demonstration of the working product, a 10-minute talk (stopped at 10
  minutes) and 10 minutes of questions. Finals are judged on functionality and technical
  robustness (including code quality and reproducibility), real-world impact, user experience and
  design, presentation, and sources.
- **The whole project, "including the code and datasets," is published on UP Data Science
  Society's GitHub.** Anything in this repository at submission time should be fit to publish:
  no case-level records (rule 11), and weekly case counts only if their source allows it.

Read `Notes.md` first: the open decisions, the changes from the plan, and what the paper
must say about them.

## Data sources and licenses

The code is under the [LICENSE](LICENSE) file's terms (MIT). The data keep their sources'
licenses. Files in `data/` are not in git (share them through the team drive); each has a note
in `data/raw/<file>.md` with its source, date and citation. Files the repository does ship that
are built from these sources (in `results/` and `app/public/data/`) keep the same terms.

| Data | Source | License | Credit |
| --- | --- | --- | --- |
| Flood hazard maps, 5-, 25- and 100-year, Metro Manila | [Project NOAH](https://noah.up.edu.ph), UP Resilience Institute | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) | UP Resilience Institute / NOAH Center. `app/public/data/noah_*yr.json` are derived from these maps and shared under the ODbL |
| Population, 100 m, 2024 (R2025A) | [WorldPop](https://hub.worldpop.org) | CC BY 4.0 | Bondarenko et al. (2025), WorldPop, University of Southampton |
| Barangay boundaries (COD-AB v03) | NAMRIA and PSA via [OCHA on HDX](https://data.humdata.org/dataset/cod-ab-phl) | CC BY-IGO | OCHA Philippines, from NAMRIA and PSA |
| Population by single-year age and sex, 2020 census | PSA via [OCHA on HDX](https://data.humdata.org/dataset/popn-single-year-age-sex-and-barangay-census-2020) | CC BY | OCHA Philippines, from PSA |
| Barangay population, 2024 census | [Philippine Statistics Authority](https://psa.gov.ph) | PSA terms of use | Philippine Statistics Authority, 2024 Census of Population |
| Registered live births, 2024 | [PSA OpenSTAT](https://openstat.psa.gov.ph) | CC BY ([OpenSTAT terms](https://openstat.psa.gov.ph/Terms)) | Philippine Statistics Authority |
| Health facilities | [DOH National Health Facility Registry](https://nhfr.doh.gov.ph) | No license stated (public registry) | Department of Health. Only facility names, codes and coordinates are kept; the registry's staff names and e-mails are not |
| Daily rain, IMERG Late V07 | [NASA GES DISC](https://doi.org/10.5067/GPM/IMERGDL/DAY/07) | NASA open data, no restrictions | Huffman et al. (2024), NASA/GSFC, archived at GES DISC |
| ERA5 hourly rain | ECMWF via the [Open-Meteo](https://open-meteo.com) Historical Weather API | CC BY 4.0 | Weather data by Open-Meteo.com (Zippenfenig, 2023); contains modified Copernicus Climate Change Service information (Hersbach et al., 2020) |
| ECMWF IFS archived forecasts | ECMWF via the [Open-Meteo](https://open-meteo.com) Previous Runs API | CC BY 4.0 | Weather data by Open-Meteo.com; ECMWF IFS open data |
| Sub-basins (HydroBASINS v1c, level 12) | [HydroSHEDS](https://www.hydrosheds.org) | HydroSHEDS license: free for scientific, educational and commercial use | Lehner & Grill (2013), Hydrological Processes 27(15) |
| National weekly cases, 2019–2023 | [Parreño (2023), Mendeley Data](https://doi.org/10.17632/v98325dpxv.1) | CC BY 4.0 | S. J. Parreño, Philippine Epidemiological Data, v1 |
| NCR city outlines | [faeldon/philippines-json-maps](https://github.com/faeldon/philippines-json-maps) | MIT | (c) James Faeldon |
| QC leptospirosis cases, 2015–2026 | Quezon City Epidemiology and Surveillance Division (shared on request) | Not public | The case list never enters this repository (rule 11). Only weekly city totals are published, with QCESD's permission |
| App base maps | OpenFreeMap / OpenStreetMap; EOX Sentinel-2 cloudless 2024 | ODbL; CC BY-NC-SA 4.0 | © OpenStreetMap contributors; EOX IT Services, contains modified Copernicus Sentinel data |

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

## Rebuild everything (task E10)

One command reruns every task below in order, from the files in `data/raw/`, then the checks:

```
python -m src.run_all --list          # the steps, and which are skipped and why
python -m src.run_all                 # run them all, then python -m src.checks
python -m src.run_all --from C3       # resume at a task after fixing a failed step
python -m src.run_all --only B3 D7    # just these tasks
python -m src.run_all --simulate      # Layer 1 on B10's made-up counts, without QC's case data
```

- It stops at the first failed step and says how to resume. Before the first step it checks
  the files saved by hand (HydroBASINS, the census files, the Mendeley file, PSA births) and
  `data/raw/imerg_daily.nc`, and lists any that are missing: copy them from the team drive.
- Downloads: A6, A8, A10, A14 and A15 fetch only files not already in `data/raw/`. A4
  (IMERG) always fetches up to today and needs an Earthdata login, so it runs only with
  `--fetch-imerg`.
- QC's case data: A13 runs only when QCESD's case list is in `data/raw/qcesd/`. The list is
  case-level and stays on the team drive (rule 11), so in any other copy A13 is skipped, not
  stopped. B10 then runs on `data/clean/cases_weekly.csv` if it was copied from the drive, and
  is skipped if not; its guard reruns (g = 1 and 3) run in option C only. D8 draws figures 4
  and 5 every run, and all five once B10's `results/forecasts.csv` exists; B5's residual check
  (`python -m src.m4`) and E6's score tables (`python -m src.score_tables`) wait for it and for
  `cases_weekly.csv`, and F2 then leaves `city_forecast.json` and `scores.json` as they were. A
  task not built yet is skipped.
- `--simulate` skips A13, B5's residual check and E6 and runs B10 on its made-up counts (`--simulate --option C`) and D8's figures 1–3 as
  previews from them (`results/d8_preview_*`). F2 still exports the committed
  `results/forecasts.csv`; only a copy without that file gets a `city_forecast.json` marked
  `"simulated": true`. It tests the whole chain; none of it is a result.
- The check "E10 package" confirms what the repository ships: every package pinned in
  `requirements.txt` and installed at that version, nothing tracked under `data/` but the
  notes, and no tracked table with a person's columns (rule 11).

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
| A13 | `python -m src.cases` | `data/clean/cases_weekly.csv` (week_index, year, week, cases: QC cases by MMWR week of onset, 2015 week 1 on; the last weeks, still filling in, are missing, not 0); needs QCESD's case list in `data/raw/qcesd/` (team drive; case-level records, never commit them: note in `data/raw/qcesd.md`). Decision-tree row: onset weeks, no report dates, so `config.DATA_OPTION = "C"`. Check S4 in `python -m src.checks` |

## Layer 1: city forecast (Workstream B)

| Task | Command | Writes |
| --- | --- | --- |
| B1 | `python -m src.population` | `data/clean/pop_weekly.csv`; needs only `config.py` (A5's census totals are in it) |
| B4 | `python -m src.features` | `data/clean/imerg_weights_qc.csv` (WorldPop QC weights per IMERG cell), `rain_weekly.csv` (weekly QC rain R and Rcum2), `features_weekly.csv` (R, Rcum2, EI and EI2 per fit year, read by B10); needs A3, A4, A5, A6 and C3's file |
| B2 | none: `cutoff`, `visible`, `training_rows` and `prediction_row` in `src/view.py`, used by B5, B9 and B10. Set `config.DATA_OPTION` from A13's row first: option B sees every week up to forecast day T, option C up to T − g (`config.DELAY_GUARD_G`) | nothing; check "B2 view" in `python -m src.checks` |
| B7 | none: functions in `src/thresholds.py` (and `forecast_dist` in `src/forecast_range.py`), used by B8 and B10 | nothing; check S7 in `python -m src.checks` |
| B8 | none: functions in `src/baselines.py`, used by B10 | nothing; check "B8 M0 and M1" in `python -m src.checks` |
| B6 | none: `estimate_theta` and `theta_for` in `src/forecast_range.py`, used by B10 for every model's 90% range and breach probability | nothing; check S6 in `python -m src.checks` |
| B3 | `python -m src.m3` (then `--diagnose`) | `results/m3_reproduction.csv`, `m3_forecasts.csv`, `m3_diagnostics.csv`; needs A9's file; about a minute. Findings: `results/m3_reproduction.md` |
| B9 | none: `m3_forecast` in `src/m3_port.py`, used by B10 (M3 refitted on the weeks it may see, about 0.5 s a forecast day) | nothing; check "B9 M3" in `python -m src.checks` |
| B5 | `python -m src.m4` (after B10): v2's residual check, on M4's fit at the last forecast day of B10's run (its data option, g and rows). `model_rows`, `fit_m4` (M4, and M4 without EI2 with `with_ei=False`) and `predict_m4` in `src/m4.py` are used by B10 at every forecast day. Inputs: B2's rows, B4's weekly `rcum2` and `ei2`, B1's population | `results/m4_residual_acf.png` and `m4_residual_acf.csv` (how much one week's miss says about the miss 1 to 26 weeks later, with the 95% band for independent weeks); seconds. Check S5 in `python -m src.checks` (50 made-up datasets, a few seconds) |
| B10 | `python -m src.backtest` (option from `config.DATA_OPTION`, or `--option B`/`C`; `--g 1` and `--g 3` for the guard reruns). To test without QC's counts: `python -m src.backtest --simulate --option C` on made-up QC-shaped counts | `results/forecasts.csv`: one row per model (M0, M1, M3, M4, M4_no_EI2) and forecast day, 2018 week 1 on, with mu, theta, the 23 WIS quantiles, the threshold, Pr(breach), y and breached. Guard reruns write `forecasts_g1.csv`, simulated runs `forecasts_simulated_B.csv` / `_C.csv`. Needs B1, B4 (`features_weekly.csv`) and A13; about 12 minutes (M3 refits Prophet every week). Check S11 in `python -m src.checks` |

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
| D4 | none: `lead_times` and `caught_in_advance` in `src/breach_scores.py`: `caught_in_advance(lead_times(forecasts, p_star))`, one model at a time (columns week_index, year, p, breached), with D3's p* from the first half of forecast days and scored on the second half | nothing; check "D4 lead time" in `python -m src.checks` |
| D7 | `python -m src.layer2_results` | `results/d7_map_<storm>.png` (one per storm, C8's main run: share of each barangay's residents in flood zones, and doxycycline capsules; A11's flooded barangays outlined), `d7_centers.csv` (doses per health center, whole units), `d7_flags.csv` (flagged versus flooded, observed run and each lead), `d7_tests.csv` (the cut-off test and D ± 1), `d7_forecast_vs_observed.csv` (C9's doses at each lead beside C8's observed doses); reads C8's and C9's results files and A5's `barangays_qc.gpkg`, and stops if C8's main run and C9's observed run disagree; a few seconds. No validation regression: no barangay case counts. Stock planning, not prescriptions |
| D5 | none: `primary_endpoint(table)` in `src/compare.py` (M4 vs M3 over the MAE window: mean of \|error M4\| − \|error M3\|, 95% moving-block bootstrap interval with 8-, 4- and 13-week blocks, and the Diebold–Mariano test), on B10's forecasts (columns model, week_index, year, y, mu) | nothing; check "D5 primary endpoint" in `python -m src.checks` |
| D6 | none: `flood_and_practical_tests(table)` and `flood_finding(result)` in `src/compare.py` (M4 vs M4 without EI2, no Diebold–Mariano since the models are nested; M4 vs M1 with it; same bootstrap as D5) | nothing; check "D6 flood test" in `python -m src.checks` |
| D1–D6 tables | `python -m src.score_tables` (after B10; also reads B10's guard reruns `forecasts_g1.csv` and `forecasts_g3.csv` when they are there). D1–D6's functions applied to `results/forecasts.csv`, so every score the paper's results (E6) quote is in `results/` | `results/d1_scores.csv` (each model's MAE, RMSE, bias, MASE, WIS, 50% and 90% coverage, Brier and Brier skill score, over the MAE years, 2022–2026 and all years), `d1_mae_by_year.csv`, `d3_alarms.csv` (D3's p*, precision and sensitivity on each half; D4's episodes caught and lead time), `d3_precision_recall.csv` (the full curve behind p*), `d5_d6_all_years.csv` (D5 and D6 over 2018–2026, COVID years in), `d5_guard_reruns.csv` (MAE and D5/D6 with g = 1, 2 and 3); seconds. Check "E6 score tables" in `python -m src.checks` |
| D8 | `python -m src.paper_figures` (all five; needs B10's `results/forecasts.csv`). Without B10's run: `--layer2` (figures 4 and 5 only). To try figures 1–3 on B10's made-up counts: `python -m src.backtest --simulate --option C`, then `--preview results/forecasts_simulated_C.csv` (writes `results/d8_preview_*`, kept out of git, not for the paper) | `results/d8_fig1_forecasts.png` (QC weekly cases, M4's and M3's forecasts, M4's 90% range), `d8_fig2_mae.png` and `.csv` (MAE by model with 95% block-bootstrap intervals, beside D5's and D6's differences), `d8_fig3_reliability.png` and `.csv` (CORP reliability of M4's and M3's breach probabilities, forecasts per step), `d8_fig4_exposure_map.png` (share of residents in flood zones, C8's main run, Carina and Kristine; `config.D8_MAP_STORMS`), `d8_fig5_doses.png` and `.csv` (QC's doses table on observed rain, whole units). Reads B10's forecasts, C8's results files and A5's `barangays_qc.gpkg`; a few seconds. Stock planning, not prescriptions |

## Paper (Workstream E)

The paper's LaTeX source is in `paper/`; its README says how to build it (Overleaf, or
`latexmk -pdf main.tex` in `paper/`) and which file holds which task.

| Task | Command | Writes |
| --- | --- | --- |
| E3 | none: `sections/objectives.tex` in `paper/`, the proposal's four objectives worded as they were tested (the last is D5's primary endpoint, M4 against M3); build as for E4 | `paper/main.pdf` (not in git) |
| E4 | none: `sections/background.tex`, `problem.tex` and `scope.tex`, and the assumptions table `tables/assumptions.tex`, in `paper/`; build the whole paper with `latexmk -pdf main.tex` there | `paper/main.pdf` (not in git) |
| E5 | none: `sections/methodology.tex` (no formulas in its text) and its formulas appendix `tables/formulas.tex` (Table B1, each formula with the `src/` file that computes it), in `paper/`; build as for E4 | `paper/main.pdf` (not in git) |
| E6 | none: `sections/results.tex` in `paper/`, with D8's figures 1-4 copied into `paper/figures/`. Its numbers come from `results/`: B10's guard reruns (`python -m src.backtest --g 1`, `--g 3`), then `python -m src.score_tables` (D1–D6 tables) and `python -m src.paper_figures` (D8); build as for E4 | `paper/main.pdf` (not in git) |
| E9 | none: `sections/summary.tex` in `paper/`, the executive summary under the title (under 250 words, with D5's primary result). Its numbers are E6's, from `results/forecasts.csv`, `d8_fig2_mae.csv`, `d1_scores.csv` and `c9_forecast_runs.csv`; build as for E4 | `paper/main.pdf` (not in git) |

## App (Workstream F)

The web app lives in `app/`. Its README has the details: the screens, the design tokens, maps
and the Vercel setup.

| Task | Command | Writes |
| --- | --- | --- |
| F1 | `cd app`, then `npm install` once and `npm run dev` (http://localhost:5173). Needs Node.js 22.12 or newer | nothing; `npm run build` writes `app/dist/` (not in git). `app/src/styles/tokens.css` holds the Figma file's colors, corners, spacing and text styles |
| F2 | `python -m src.app_data` (repository root, after C8 and C9; downloads NCR's city outlines once into `data/raw/ncr_cities/`). In a copy without `results/forecasts.csv`, run `python -m src.backtest --simulate --option C` first to test the city forecast on made-up counts | `app/public/data/`: `ncr_cities.geojson`, `qc_barangays.geojson`, `storms.json`, `barangays/<storm>_<run>.json` (one per run), `centers.json`, `city_forecast.json` (B10's `forecasts.csv`, or in a copy without it the made-up-count run, marked `"simulated": true`) and, beside a real run only, `scores.json`. Commit them: Vercel builds from git. Needs C8, C9, A5 and A10; seconds. Stock planning, not prescriptions. Check "F2 app data" in `python -m src.checks` |
| F4 | none: the map's first two levels in `app/` (`npm run dev`, then http://localhost:5173/map and `/map/quezon-city`). They read F2's files: `ncr_cities.geojson` now carries each city's label point (`config.APP_LABEL_MIN_KM2`), and `city_forecast.json` the map's model and outbreak levels (`config.APP_LEVEL_MODEL`, `config.APP_LEVELS`); rerun `python -m src.app_data` after changing them | nothing; check "F2 app data" in `python -m src.checks` also checks the label points and the levels |
| F5 | none: the map's level 3, the prophylaxis plan, in `app/` (`npm run dev`, then http://localhost:5173/map/quezon-city/prophylaxis?date=2024-10-22). It reads F2's `storms.json`, `centers.json`, `qc_barangays.geojson` and one `barangays/<storm>_<run>.json` per forecast shown | nothing; its Export stock list button saves `lepton-stock-list_<storm>_lead<n>.csv` in the browser. Stock planning, not prescriptions |
| F6 | none: Home in `app/` (`npm run dev`, then http://localhost:5173/). It reads F2's `storms.json`, `centers.json`, `qc_barangays.geojson`, `barangays/kristine_2024_lead1.json` (the plan's preview, Kristine 1 day ahead) and `city_forecast.json` (the chart); its four photos are real and licensed, in `app/src/assets/home/`, credited in the footer (`app/src/home/photos.ts`) | nothing. Stock planning, not prescriptions |
| F7 | none: the Leptospirosis page for residents in `app/` (`npm run dev`, then http://localhost:5173/leptospirosis). Text only, each medical fact linked to its DOH source (DM 2023-0309 and DOH advisories); no doses | nothing |
| F8 | none: the "I have been exposed to floodwater" guide in `app/` (`npm run dev`, then http://localhost:5173/exposed). Its last step reads F2's `centers.json` and `qc_barangays.geojson` | nothing: answers and location stay in the page's memory, never stored or sent |
| F9 | none: Compare models in `app/` (`npm run dev`, then http://localhost:5173/compare; `?period=12w`, `?period=2024` or `?period=all`). It reads F2's `city_forecast.json` and `storms.json`, and `scores.json` beside B10's real run only; until then every score shows "—" | nothing; check "F9 scores" in `python -m src.checks`: after B10's real run, the page's scores (`scores.json`) equal D8's `d8_fig2_mae.csv` |
| F10 | none: the How it works page in `app/` (`npm run dev`, then http://localhost:5173/how-it-works). Text only, in `app/src/howItWorks/content.ts`: the pipeline, models (formulas behind "Show the formula"), testing, limits and sources; check it against the paper's final text (E4, E5, E7) | nothing |
| F11 | none: motion, accessibility and small screens across `app/` (its README, "Motion, accessibility and small screens"): the map's keyboard lists, one focus ring, live updates, text contrast to WCAG AA, and layouts at 1440, 1024 and 390 px (the map panel a bottom sheet on a phone) | nothing; Lighthouse accessibility 100 on every route. Figma's Theme collection needs the three darker Clinic colors in `app/src/styles/tokens.css` |
| F12 | `python -m src.app_data` on the latest results, then in `app/`: `npm run build`, `npm run preview` and the app checks U1–U8 (`app/README.md`, "Deploy and checks"); Vercel deploys `main` | the production link, at the top of this README once Vercel is set up (`app/README.md`, "Deploy (Vercel)"). Checked October 21 on B10's real run: U1–U8 pass after two fixes (U7: `/kit` in `npm run dev` only; U8: the footer and How it works credit every source); still by hand: two phones and two laptops, a teammate's keyboard run |

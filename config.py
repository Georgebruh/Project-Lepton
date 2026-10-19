from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"        # downloads, never edited
DATA_CLEAN = ROOT / "data" / "clean"    # processed files
RESULTS = ROOT / "results"

CALENDAR = DATA_CLEAN / "calendar_weeks.csv"          # A3
IMERG_DAILY = DATA_RAW / "imerg_daily.nc"             # A4
ERA5_DAILY = DATA_CLEAN / "era5_daily.csv"            # A14
ERA5_RAW = DATA_RAW / "era5_open_meteo"               # A14: Open-Meteo's replies, one JSON file per year
FORECASTS_STORMS = DATA_CLEAN / "forecasts_storms.csv"  # A15
ECMWF_RAW = DATA_RAW / "ecmwf_previous_runs"          # A15: Open-Meteo's replies, one JSON file per storm
CATCHMENTS = DATA_CLEAN / "catchments_qc.gpkg"        # A7
WORLDPOP = DATA_RAW / "phl_pop_2024_CN_100m_R2025A_v1.tif"  # A6: whole country, unchanged
WORLDPOP_BOX = DATA_CLEAN / "worldpop_2024_box.tif"   # A6: clipped to IMERG_BOX; C1 starts here
WORLDPOP_SCALE_QC = DATA_CLEAN / "worldpop_scale_qc.csv"  # C1: census scale factor per barangay
OVERLAY = DATA_CLEAN / "overlay_qc.csv"               # C2
EI_WEEKLY = DATA_CLEAN / "ei_weekly.csv"              # C3
CASES_WEEKLY = DATA_CLEAN / "cases_weekly.csv"        # A13
POP_WEEKLY = DATA_CLEAN / "pop_weekly.csv"            # B1: QC population for every week
FORECASTS = RESULTS / "forecasts.csv"                 # B10
IMERG_WEIGHTS_QC = DATA_CLEAN / "imerg_weights_qc.csv"  # B4: WorldPop QC weights per IMERG cell
RAIN_WEEKLY = DATA_CLEAN / "rain_weekly.csv"            # B4: weekly QC rain R(t) and Rcum2(t)
FEATURES_WEEKLY = DATA_CLEAN / "features_weekly.csv"    # B4: weekly rain and exposure (R, Rcum2, EI, EI2)
C8_RUNS = RESULTS / "c8_observed_runs.csv"            # C8: one row per storm, test, D, cut-off and w
C8_BARANGAYS = RESULTS / "c8_observed_barangays.csv"  # C8: the main run, one row per barangay
C8_CENTERS = RESULTS / "c8_observed_centers.csv"      # C8: the main run, need per health center and pool
C9_RUNS = RESULTS / "c9_forecast_runs.csv"            # C9: one row per storm, run (observed or lead), D and w
C9_BARANGAYS = RESULTS / "c9_forecast_barangays.csv"  # C9: the same runs, one row per barangay
C9_CENTERS = RESULTS / "c9_forecast_centers.csv"      # C9: the same runs, need per health center and pool
D7_FORECAST_VS_OBSERVED = RESULTS / "d7_forecast_vs_observed.csv"  # D7: C9's doses at each lead beside C8's observed doses
D7_FLAGS = RESULTS / "d7_flags.csv"                   # D7: flagged versus flooded, per storm, run and flag share
D7_TESTS = RESULTS / "d7_tests.csv"                   # D7: C8's cut-off test (and D +/- 1): QC's adult tiers and units
D7_CENTERS = RESULTS / "d7_centers.csv"               # D7: doses per health center, C8's main run, whole units
D7_MAP_NAME = "d7_map_{storm}.png"                    # D7: one barangay map per storm, in RESULTS
# D8: the paper's five figures, drawn by src/paper_figures.py from the files above. Each chart
# has a CSV beside it holding the numbers it shows. Stock planning, not prescriptions.
D8_FIG1_FORECASTS = RESULTS / "d8_fig1_forecasts.png"      # D8 (1): weekly cases, M4 and M3, M4's 90% range
D8_FIG2_MAE = RESULTS / "d8_fig2_mae.png"                  # D8 (2): MAE by model, and D5's and D6's differences
D8_FIG2_TABLE = RESULTS / "d8_fig2_mae.csv"                # D8 (2): the numbers in figure 2
D8_FIG3_RELIABILITY = RESULTS / "d8_fig3_reliability.png"  # D8 (3): reliability of the breach probabilities
D8_FIG3_TABLE = RESULTS / "d8_fig3_reliability.csv"        # D8 (3): the reliability steps, forecasts per step
D8_FIG4_MAP = RESULTS / "d8_fig4_exposure_map.png"         # D8 (4): share of residents in flood zones, per storm
D8_FIG5_DOSES = RESULTS / "d8_fig5_doses.png"              # D8 (5): the doses table as a picture
D8_FIG5_TABLE = RESULTS / "d8_fig5_doses.csv"              # D8 (5): the doses table
D8_PREVIEW_PREFIX = "d8_preview_"                          # D8 --preview: figures 1-3 from another B10 file; not for the paper

# Benchmark data (A9)
PARRENO_RAW = DATA_RAW / "parreno" / "Diseases Data (for NBL).xlsx"        # A9: Mendeley file, unchanged
PARRENO_WEEKLY = DATA_CLEAN / "parreno_national_weekly.csv"      # A9: national leptospirosis by ISO week, for B3

# Boundaries and census (A5)
BOUNDARIES_ZIP = DATA_RAW / "phl_admin_boundaries.gdb.zip"           # HDX COD-AB v03
CENSUS_2024_XLSX = DATA_RAW / "NCR - Table C - Population by Barangay.xlsx"  # PSA 2024 POPCEN
CENSUS_2020_AGE_XLSX = DATA_RAW / "2020 Census Total Popn_Single Age_MaleFemale_Admin4.xlsx"  # HDX
BARANGAYS_QC = DATA_CLEAN / "barangays_qc.gpkg"       # A5: 142 polygons with both census totals
CENSUS_QC = DATA_CLEAN / "census_qc.csv"              # A5: same table without the shapes
AGE_SEX_2020_QC = DATA_CLEAN / "age_sex_2020_qc.csv"  # A5: psgc, sex, age, pop (age 80 = 80 and over)
BIRTHS_2024 = DATA_RAW / "psa_births_2024.csv"        # A12: PSA OpenSTAT table 1A1ABIB8, unchanged
SHARES_QC = DATA_CLEAN / "shares_qc.csv"              # C4: child, pregnant and adult shares per barangay

# Health facilities (A10)
NHFR_RAW = DATA_RAW / "nhfr"                          # A10: registry pages as downloaded
FACILITIES_QC = DATA_CLEAN / "health_facilities_qc.csv"  # A10: one row per QC facility, with coordinates
CENTER_SHARES = DATA_CLEAN / "center_shares_qc.csv"   # C7: the share of each barangay's need each health center gets
# NOAH flood hazard maps (A8)
NOAH_RAW = DATA_RAW / "noah"                          # A8: the zips as downloaded, plus NOAH's metadata
NOAH_FLOOD = DATA_CLEAN / "noah_flood_mm.gpkg"        # A8: 9 rows (3 maps x Var 1-3), EPSG:32651

# ---------------------------------------------------------------------------
# Calendar and periods
# ---------------------------------------------------------------------------
FIRST_WEEK_START = date(2015, 1, 4)        # 2015 week 1 (CDC/MMWR), A3
BURN_IN_YEARS = (2015, 2016, 2017)
BACKTEST_FIRST_YEAR = 2018                 # first forecast day: first week of 2018
BACKTEST_LAST_YEAR = 2026                  # to the last complete week of 2026
COVID_YEARS = (2020, 2021)
WEEKS_PER_YEAR = 52.18                     # period of the M4 season terms, B5
MAX_WEEK = 52                              # week 53 is mapped to 52
DAYS_PER_WEEK = 7                          # UTC days in one complete morbidity week, B4

# Scoring windows (Workstream D)
MAE_YEARS = (2018, 2019, 2022, 2023, 2024, 2025, 2026)
PROB_SCORE_YEARS = (2022, 2023, 2024, 2025, 2026)
MASE_DENOM_YEARS = (2016, 2017)            # fixed denominator, D2

# Gates
GATE_A = date(2026, 10, 16)
GATE_BC = date(2026, 10, 19)
GATE_D = date(2026, 10, 21)
SUBMIT = date(2026, 10, 23)

# ---------------------------------------------------------------------------
# Data products
# ---------------------------------------------------------------------------
IMERG_PRODUCT = "GPM_3IMERGDL"
IMERG_VERSION = "07"
IMERG_START = date(2000, 6, 1)             # NASA's catalogue lists Late daily files from 1998-01-01; the plan starts here
IMERG_SUBSETS = DATA_RAW / "imerg_daily"   # A4: one small file per UTC day, stacked into IMERG_DAILY
IMERG_VARIABLES = ("precipitation", "precipitation_cnt")  # rain in mm/day; valid half-hours (of 48) behind it
IMERG_DOWNLOAD_WORKERS = 4                 # downloads at once; keep it small, NASA's server is shared
EARTHDATA_TOKEN_FILE = Path.home() / "earthdata_token.txt"  # A4: your NASA login token; outside the repo, never share it
IMERG_KEEP_2000 = True                     # assumption: keep Jun-Dec 2000; refit once without it
ERA5_YEARS = (2000, 2025)                  # assumption: same years as IMERG, A14
ERA5_START = IMERG_START                   # A14: start on IMERG's first day, so both fits use the same years
ERA5_MODEL = "era5"                        # A14: Open-Meteo Historical Weather, plain ERA5 reanalysis at 0.25 deg
OPEN_METEO_HOUR_SHIFT = -1                 # shift hourly totals back 1 h before summing UTC days
FORECAST_MODEL = "ecmwf_ifs025"            # assumption: ECMWF IFS 0.25 deg, A15
FORECAST_LEADS_DAYS = (1, 2, 3)            # C9: the n-day total forecast 1, 2 and 3 days before its first day

# Catchments (A7). The Philippines is in HydroSHEDS' Australasia region ("au"), not Asia.
HYDROBASINS_SHP = DATA_RAW / "hydrobasins" / "hybas_au_lev12_v1c.shp"
# One point on each river; the sub-basin holding it is the start of the upstream trace.
CATCHMENT_OUTLETS = {
    "marikina": {"lon": 121.093, "lat": 14.636, "trace_upstream": True},   # Sto. Nino gauge, Marikina City
    "san_juan": {"lon": 121.017, "lat": 14.589, "trace_upstream": False},  # mouth at the Pasig; see note below
    "tullahan": {"lon": 121.030, "lat": 14.690, "trace_upstream": True},   # Novaliches, QC
}
# San Juan: its sub-basin is the Pasig's last one, which also receives Laguna de Bay
# (4,034 km2 upstream). Tracing upstream would add the whole lake basin, which does not
# drain into the San Juan River, so it keeps its own sub-basin only.
# WorldPop (A6): constrained 2024 counts, 100 m, R2025A v1. Catalogue page
# https://hub.worldpop.org/geodata/summary?id=74942 (the plan's id=78816 is the 2026 1 km grid).
WORLDPOP_URL = ("https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2024/"
                "PHL/v1/100m/constrained/phl_pop_2024_CN_100m_R2025A_v1.tif")
WORLDPOP_BYTES = 63_493_139                # size of the copy used (its note); R2025A is an alpha release

IMERG_CELL_DEG = 0.1
IMERG_BOX = (120.7, 14.4, 121.5, 15.0)     # (lon_min, lat_min, lon_max, lat_max); printed by src/catchments.py
# ERA5 (A14) and ECMWF IFS 0.25 (A15) grid points sit on multiples of 0.25 degrees.
# Both use every cell that overlaps the catchments, weighted by area (catchments.grid_cells):
# 4 cells; only one grid point, (14.75, 121.25), lies inside the catchments.
GRID_025_DEG = 0.25
GRID_EDGE_POINTS = 25                      # points per cell edge before reprojecting (catchments.grid_cells)
GRID_AREA_TOLERANCE = 1e-3                 # the cells must hold the catchment area to within 0.1%

CRS_LONLAT = "EPSG:4326"                   # longitude/latitude degrees: catchments_qc.gpkg and the rain grids
CRS_OVERLAY = "EPSG:32651"                 # overlays
CRS_EXACTEXTRACT = "EPSG:4326"             # convert to this before exactextract
QC_BARANGAYS = 142                         # check S3
QC_HDX_ADM3_PCODE = "PH1307404"            # QC in the HDX boundaries (A5)
QC_PSGC_PREFIX = "13813"                   # QC in the official 10-digit PSGC: 13813xxxxx (A5)
QC_SHEET_2024 = "Quezon City"              # QC's sheet in the PSA 2024 workbook (A5)
# A10: DOH National Health Facility Registry (https://nhfr.doh.gov.ph), list "Active facilities".
NHFR_REGION_NCR = "13"
NHFR_QC_NAME = "QUEZON CITY (HUC)"         # QC in the registry's Province Name column
# Registry facility types kept. QC's health centers are registered as "Rural Health Unit"
# (2026-10-15: 67 of them, 1 Barangay Health Station, 1 City Health Office).
NHFR_FACILITY_TYPES = {"17": "Rural Health Unit", "20": "Barangay Health Station", "21": "City Health Office"}
NHFR_PAUSE_S = 1.0                         # wait between page requests; the registry is a shared server
NOAH_RETURN_PERIODS = (5, 25, 100)
NOAH_HAZARD_LEVELS = (1, 2, 3)             # the `Var` field
NOAH_OVERLAP_TOLERANCE_KM2 = 1e-6          # C2: levels of one map may share at most 1 m2 in a barangay (rounding)
# A8: Google Drive file ids of NOAH's Metro Manila flood maps. NOAH's download page
# (https://noah.up.edu.ph, "Downloads") links the public folder
# https://drive.google.com/drive/folders/1ALE4-E9c-4AGjm1fqiPprWHrLUskeY9o
# -> Flood -> 5yr / 25yr / 100yr -> MetroManila.zip ("Metro Manila.zip" for 100yr).
NOAH_FLOOD_FILES = {
    5: "1IC5LnscUt7D_5c1BvlwcngR3cFKgDshV",
    25: "1VAcWkVeY2uXWhZVvDYh5viedhihwBBci",
    100: "1n-IrwfWqLRDyDg-wmt68luk_DU5Xzg9S",
}
NOAH_METADATA_FILES = {                    # A8: NOAH's own notes, kept beside the maps
    "metadata_flood.txt": "1qbOoN_CZ6AUIk22owtJxRFENALIWCszq",
    "01ReadMe_Flood.pdf": "1Z6gT7FDUCMps-qHT5Jiy7nwCdaH0rhwR",
    "NOAH_License.pdf": "1z6MH_QI6gU_e2gNnhIMsKkENugHscNl9",
}

# Census reference days for pop_at (B1). src/population.py turns them into decimal
# years (1 Aug 2015 = 2015.58, 1 May 2020 = 2020.33, 1 Jul 2024 = 2024.50).
CENSUS_DAYS = {2015: date(2015, 8, 1), 2020: date(2020, 5, 1), 2024: date(2024, 7, 1)}
# A5: PSA official totals, from Table B of the PSA 2024 NCR workbook (census days
# 1 Aug 2015, 1 May 2020, 1 Jul 2024). src/census.py stops if the workbook disagrees.
CENSUS_POP_QC = {2015: 2_936_116, 2020: 2_960_048, 2024: 3_084_270}

# ---------------------------------------------------------------------------
# Layer 1: case data view (B2)
# ---------------------------------------------------------------------------
DATA_OPTION = None                         # "A", "B" or "C"; set by the A13 decision
DELAY_GUARD_G = 2                          # assumption, option C only
DELAY_GUARD_G_TESTS = (1, 3)
FORECAST_HORIZON_WEEKS = 1                 # B2, B10: forecast day T forecasts week T + 1 (the B11 stretch: 2)
REPORTED_SHARE_CUTOFF = 0.50               # assumption, option A only
REPORTED_SHARE_CUTOFF_TEST = 0.80

# ---------------------------------------------------------------------------
# Layer 1: models
# ---------------------------------------------------------------------------
M0_LAG_WEEKS = 52                          # M0: the count 52 weeks before the target week (B8)
FOURIER_K = 3                              # M4 sin/cos pairs
RAIN_SCALE_MM = 50                         # M4 uses Rcum2 / 50
RAIN_EI_MAX_CORR = 0.8                     # above this, keep EI2 alone (B5)
# B5: statsmodels' optimizers for the negative binomial fit, in order. Newton is fast and
# exact, but can break down to NaN coefficients still flagged "converged" (seen on made-up
# data, 2026-10-18); BFGS then reaches the same maximum. Both failing stops the run.
M4_FIT_METHODS = ("newton", "bfgs")
M4_MAX_ITER = 100                          # B5: iterations before a fit counts as not converged
M4_RESIDUAL_ACF = RESULTS / "m4_residual_acf.png"  # B5: v2's residual autocorrelation check
M4_ACF_LAGS = 26                           # B5: lags plotted, half a year

# M3 benchmark (B3), read from Latigay & Gonzaga (2026)
M3_DATA_YEARS = (2019, 2023)
M3_CHANGEPOINT_PRIOR = 0.55
M3_SEASONALITY_MODE = "multiplicative"
M3_FIRST_WINDOW = 115
M3_HORIZON = 2
M3_STEP = 16
M3_FOLDS = 9
M3_COVID_GAP_FACTOR = 0.5                  # missing lockdown weeks get 0.5 x seasonal mean
M3_RAINY_GAP_FACTOR = 1.0                  # missing Jun-Nov weeks get 1.0 x seasonal mean
M3_XGB_PARAMS = {}                         # assumption: xgboost defaults
M3_XGB_PARAMS_TEST = {"max_depth": 2}
M3_XGB_ROUNDS = 100                        # assumption: XGBRegressor's default n_estimators (xgb.train alone uses 10)
M3_TARGET_MAE = {"hybrid": 16.72, "prophet": 23.68}
M3_TOLERANCE = 0.10
# B3: the paper's Table I, all 18 forecast weeks (SARIMA not reproduced: R auto.arima)
M3_TABLE_I = {
    "hybrid": {"mae": 16.7237, "rmse": 21.9313, "smape": 38.7985, "bias": -0.7196},
    "prophet": {"mae": 23.6831, "rmse": 28.1622, "smape": 50.6627, "bias": 1.0455},
    "snaive": {"mae": 64.1782, "rmse": 97.5642, "smape": 93.6468, "bias": -34.4746},
}
M3_PEAK_CASES = 186                        # Table II: weeks with more than 186 cases (90th percentile)
M3_TABLE_II = {
    "hybrid": {"mae": 7.7409, "rmse": 7.8965, "smape": 2.8187, "bias": -1.5596},
    "prophet": {"mae": 51.6640, "rmse": 52.5004, "smape": 19.1135, "bias": -9.3342},
    "snaive": {"mae": 180.5000, "rmse": 218.1433, "smape": 103.8144, "bias": -122.5000},
}
M3_TABLE_III_DM = {"stat": -1.8242, "p": 0.04287}   # Hybrid vs Prophet
# B3 diagnostics (python -m src.m3 --diagnose): XGBoost settings tried when the hybrid misses
M3_DIAG_MAX_DEPTH = (1, 2, 3, 4, 6)
M3_DIAG_ROUNDS = (10, 25, 50, 100, 200)
M3_DIAG_ETA = (0.05, 0.1, 0.3)
M3_DIAGNOSTICS = RESULTS / "m3_diagnostics.csv"       # B3: hybrid scores for every setting tried
M3_SEASONAL_PERIOD = 52                    # seasonal naive: the value 52 rows earlier
M3_RAINY_MONTHS = (6, 11)                  # "monsoon season (June-November)"
# Assumption: the paper cites a news timeline but gives no dates. "Lockdown" read as
# ECQ and MECQ in Metro Manila / Luzon; a week counts if its Thursday falls inside.
M3_LOCKDOWNS = ((date(2020, 3, 15), date(2020, 5, 31)), (date(2020, 8, 4), date(2020, 8, 18)))
M3_LOCKDOWNS_TEST = ((date(2020, 3, 15), date(2020, 12, 31)),)   # any community quarantine in 2020
# Assumption: the paper counts 260 weeks = 5 x 52, so its series has no ISO 2020 week 53
# row. True drops that (empty) row; False keeps A9's full ISO grid. Both are run.
M3_DROP_WEEK_53 = True
M3_RESULTS = RESULTS / "m3_reproduction.csv"          # B3: scores of every run beside Table I
M3_FORECASTS = RESULTS / "m3_forecasts.csv"           # B3: the 18 forecast weeks of every run

# A9: layout of the Mendeley file. One row per week number; one column per disease and year,
# named like "<Disease> - <year>" (e.g. "Acute Flaccid Paralysis (AFP) - 2019").
PARRENO_URL = "https://data.mendeley.com/datasets/v98325dpxv/1"   # DOI matches Latigay & Gonzaga's ref. 9 (data/raw/parreno.md)
PARRENO_SHEET = 0                          # sheet name or position
PARRENO_WEEK_COL = "Week"                  # the column holding the week number
PARRENO_DISEASE_KEY = "Leptospirosis"      # columns whose name contains this (any case) and ends in a year

# Forecast range (B6)
THETA_WINDOW = 104                         # last 104 non-COVID past forecasts
THETA_MIN_FORECASTS = 26                   # fewer -> training fit's theta
RANGE_LOW_Q = 0.05                         # 90% range
RANGE_HIGH_Q = 0.95
WIS_ALPHAS = (0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)  # 11 central ranges; S7's WIS values (2.12, 32.0) need all 11

# Threshold (B7)
THRESHOLD_SD = 2                           # assumption: mean + 2 SD
THRESHOLD_MAX_YEARS = 5
THRESHOLD_MIN_YEARS = 3

# ---------------------------------------------------------------------------
# Layer 2: rain and exposure (C3)
# ---------------------------------------------------------------------------
GUMBEL_MIN_YEARS = 10                      # assumption: fit on >= 10 years before the forecast year
# Assumption: the trigger rain is the wettest 3-day total (3 consecutive UTC days), for the
# return levels, the storms and the weekly EI alike; C9 uses the same on ERA5 and the ECMWF
# forecasts. 1 = the plan's single wettest day, kept as the comparison run. The single day
# missed the long habagat floods of 2025 and 2026 (C9 test run, 2026-10-18).
RAIN_ACCUM_DAYS = 3
RAIN_ACCUM_DAYS_TEST = 1
# A15: a lead-L forecast of an n-day total takes day i of the window (i = 0 .. n-1) from
# Open-Meteo's precipitation_previous_day(L + i), so every hour comes from runs started L
# days before the window. Leads 1-3 with n = 3 need previous days 1-5. A15 also fetches the
# n - 1 days before each storm's first wettest day, for windows that start there.
FORECAST_PREVIOUS_DAYS = tuple(range(1, max(FORECAST_LEADS_DAYS) + RAIN_ACCUM_DAYS))
R0_FACTOR = 0.5                            # assumption: R0 = 0.5 x R(5)

# ---------------------------------------------------------------------------
# Layer 2: people and doses (C4-C7)
# ---------------------------------------------------------------------------
PREG_BIRTHS_FACTOR = 0.75                  # assumption: pregnant = births x 0.75
PREG_UPPER_SHARE = 0.035                   # test: 3.5% of population as upper bound
# C4 groups from the 2020 census by single-year age (first and last age both included)
CHILD_AGES = (0, 17)                       # children under 18
WOMEN_AGES = (15, 49)                      # women 15-49; the city's pregnant count is split by them (assumption)
GIRLS_AGES = (15, 17)                      # women 15-17: their pregnant share moves out of the child group
# A12's births file: OpenSTAT's CSV is Windows-1252 and has no codes. Seven other rows
# contain "Quezon" (Quezon province, towns named Quezon), so the whole name must match.
BIRTHS_ENCODING = "cp1252"
BIRTHS_QC_ROW = "Quezon City"
BIRTHS_COLUMN = "Usual Residence Both Sexes"  # mothers who live in QC, not births in QC's hospitals
CONTACT_SHARE_Q = 1.0                      # assumption: reported at full coverage
UPTAKE_U = 1.0
CONTACT_BY_LEVEL = {1: 1.0, 2: 1.0, 3: 1.0}  # assumption: r_k = 1 for every level
WOUND_SHARE_W = (0.0, 0.5, 1.0)            # assumption: illustrative grid; 0 and 1 are bounds
CONTINUOUS_EXPOSURE_DAYS = 2               # assumption: D >= 2 -> every exposed adult high risk
CONTINUOUS_EXPOSURE_DAYS_TESTS = (1, 3)    # C8 reruns each storm with these cut-offs
MODERATE_COURSE_DAYS = 5                   # assumption: upper end of 3-5 days

# Units (DOH DM 2023-0309; stock planning, not prescriptions)
DOXY_CAPS_LOW = 2                          # 200 mg once = 2 x 100 mg
DOXY_CAPS_MOD = 2 * MODERATE_COURSE_DAYS   # 200 mg daily for 5 days = 10
DOXY_CAPS_HIGH_PER_WEEK = 2                # 200 mg once a week
AMOX_TABS_PREG = 6                         # 500 mg twice a day for 3 days
DOSE_WEEK_DAYS = 7                         # ceil(D / 7) weeks: high-risk adults' weekly dose; children's course repeats after 1 week

# Stock per health center (C7)
# Assumption: stock goes to health centers ("Rural Health Unit" in the registry) and barangay
# health stations; the City Health Office runs the city's stock rather than handing it out.
CENTER_FACILITY_TYPES = ("Rural Health Unit", "Barangay Health Station")
ALLOCATE_PREVIEW_STOCK_SHARE = 0.5         # preview only (python -m src.allocation): stock covering half of each pool's need

FORECAST_RUN_D = (1, 7)                    # assumption: C9 flood durations
STORM_D_TEST_DAYS = 1                      # assumption test: C8 reruns each storm with A11's D +/- 1 day
# Assumption (C8, C9): a barangay is "flagged" when at least this share of its 2024
# residents live in zones the storm's rain floods (C3's graded exposure). Every barangay
# has some residents in the 5-year zones, so "anyone exposed" would flag all 142 once the
# rain passes R0. Reported at both values; the team confirms the rule (Notes.md 1.2).
FLAG_EXPOSED_SHARES = (0.25, 0.50)

# Storms (A11: start_date, end_date, wettest_days UTC range, D, and flooded barangays by PSGC).
# Sources and the rules below: data/raw/storm-facts.md.
# - wettest_days: 3 consecutive UTC days. C3 and C8 take the storm's wettest n-day total among
#   the windows ending on these days, and A15 fetches the forecasts for them and the n - 1
#   days before. So they must hold the last day of IMERG's wettest n-day window during the
#   flood (catchment rain, checked 2026-10-18; the peak is noted on each storm).
# - flooded_psgc: a barangay is listed only if a source from the storm names it as flooded,
#   affected, or with its residents evacuated, rescued or made homeless. Not counted: a road
#   that shares a barangay's name (E. Rodriguez, Don Manuel, N.S. Amoranto are also streets),
#   a barangay that only hosts an evacuation center, and reports from other surges.
#   C8 compares the barangays its run flags with these lists.
STORMS = {
    "carina_2024": {
        "year": 2024,
        "start_date": date(2024, 7, 23),
        "end_date": date(2024, 7, 25),
        "wettest_days": (date(2024, 7, 23), date(2024, 7, 25)),  # IMERG peak: 22-24 Jul, 120.0 mm
        "D": 3,
        "flooded_psgc": (
            "1381300003",  # Apolonio Samson
            "1381300010",  # Bagong Silangan
            "1381300028",  # Damayang Lagi
            "1381300029",  # Del Monte
            "1381300031",  # Doña Imelda
            "1381300064",  # Masambong
            "1381300065",  # Santo Domingo (Matalahib)
            "1381300068",  # Nagkaisang Nayon
            "1381300090",  # Roxas
            "1381300097",  # San Bartolome
            "1381300118",  # Talayan
            "1381300121",  # Tatalon
        ),
    },
    "floods_2025": {
        "year": 2025,
        "start_date": date(2025, 7, 19),
        "end_date": date(2025, 7, 24),
        "wettest_days": (date(2025, 7, 17), date(2025, 7, 19)),  # IMERG peak: 17-19 Jul, 191.0 mm
        "D": 6,
        "flooded_psgc": (
            "1381300003",  # Apolonio Samson
            "1381300027",  # Damayan
            "1381300028",  # Damayang Lagi
            "1381300029",  # Del Monte
            "1381300031",  # Doña Imelda
            "1381300049",  # Katipunan
            "1381300060",  # Mariana
            "1381300065",  # Santo Domingo (Matalahib)
            "1381300067",  # Milagrosa
            "1381300090",  # Roxas
            "1381300112",  # Sienna
            "1381300121",  # Tatalon
            "1381300138",  # Payatas
            "1381300142",  # North Fairview
        ),
    },
    "habagat_2026": {
        "year": 2026,
        "start_date": date(2026, 8, 8),
        "end_date": date(2026, 8, 11),
        "wettest_days": (date(2026, 8, 8), date(2026, 8, 10)),  # IMERG peak: 7-9 Aug, 140.9 mm
        "D": 4,
        "flooded_psgc": (
            "1381300003",  # Apolonio Samson
            "1381300010",  # Bagong Silangan
            "1381300011",  # Bagumbayan
            "1381300027",  # Damayan
            "1381300028",  # Damayang Lagi
            "1381300029",  # Del Monte
            "1381300031",  # Doña Imelda
            "1381300043",  # Gulod
            "1381300054",  # Lourdes
            "1381300065",  # Santo Domingo (Matalahib)
            "1381300090",  # Roxas
            "1381300104",  # Santa Cruz
            "1381300105",  # Santa Lucia
            "1381300112",  # Sienna
            "1381300120",  # Tandang Sora
            "1381300121",  # Tatalon
            "1381300129",  # Vasra
        ),
    },
    # Added 2026-10-18 (not in the proposal): a storm IMERG registers, beside Carina, which
    # IMERG reads near R0. STS Kristine (Trami); QC declared a state of calamity on 25 Oct.
    # The reports found show QC flooding on 24 Oct only, so D = 1 (the +/- 1 day test gives 2).
    "kristine_2024": {
        "year": 2024,
        "start_date": date(2024, 10, 24),
        "end_date": date(2024, 10, 24),
        "wettest_days": (date(2024, 10, 22), date(2024, 10, 24)),  # IMERG peak: 22-24 Oct, 195.1 mm
        "D": 1,
        "flooded_psgc": (
            "1381300010",  # Bagong Silangan
            "1381300022",  # Commonwealth
            "1381300064",  # Masambong
            "1381300065",  # Santo Domingo (Matalahib)
            "1381300112",  # Sienna
            "1381300121",  # Tatalon
            "1381300138",  # Payatas
            "1381300139",  # Batasan Hills
        ),
    },
}

# ---------------------------------------------------------------------------
# Sanity checks (src/checks.py)
# ---------------------------------------------------------------------------
S2_CARINA_TOP_SHARE = 0.05                 # S2: Carina's wettest day must be in 2024's wettest 5% of days
S2_KNOWN_STORMS_TOP_SHARE = 0.01           # S2: each storm below must have a day in the record's wettest 1%
# Metro Manila's worst rain events as UTC days: from the day before the Philippine dates
# (00:00-08:00 PHT falls in the previous UTC day) to the last Philippine date.
S2_KNOWN_STORMS = {
    "ondoy_2009": (date(2009, 9, 25), date(2009, 9, 26)),      # PHT 26 Sep 2009 (Ketsana)
    "habagat_2012": (date(2012, 8, 5), date(2012, 8, 8)),      # PHT 6-8 Aug 2012 (with Saola/Gener)
    "maring_2013": (date(2013, 8, 17), date(2013, 8, 21)),     # PHT 18-21 Aug 2013 (habagat with Trami/Maring)
    "ulysses_2020": (date(2020, 11, 10), date(2020, 11, 12)),  # PHT 11-12 Nov 2020 (Vamco)
}
# S5 (B5): made-up datasets that follow M4, fitted to see if M4 gets the true values back.
S5_DATASETS = 50                           # the plan: 50 datasets...
S5_WEEKS = 400                             # ...of 400 target weeks each
S5_TRUE = {"rho": 0.30, "beta1": 0.15, "beta2": 0.05, "delta": -0.40}   # the plan's true values
S5_THETA = 5                               # the plan's true theta
# Our choice (the plan gives none): about 20-60 cases a week, a June-November wet season.
S5_BASE = {"Intercept": -13.0, "sin1": 0.4, "cos1": -0.3, "sin2": 0.1, "cos2": 0.05, "sin3": 0.0, "cos3": 0.0}
S5_SIM = {
    "start_cases": 20,                     # mean count of the 2 weeks before the first target (y~ needs them)
    "rain_shape": 2.0,                     # weekly rain ~ gamma with this shape...
    "rain_mean_dry_mm": 30,                # ...and this mean outside the wet season...
    "rain_mean_wet_mm": 120,               # ...and this mean in it
    "wet_weeks": (23, 48),                 # MMWR weeks of the wet season (about June to November)
    "flood_chance": 0.15,                  # chance a wet-season week has a flood (EI above 0)
    "ei_range": (1.0, 20.0),               # a flood week's EI, % of residents, drawn evenly in this range
}
# Mean of 50 fits within this of the truth. rho leans about 0.02 low at 400 weeks: a model fed
# its own past counts is biased in short series (0.273 at 400 weeks, 0.298 at 1,600, 0.299 at
# 3,000 in a 30-dataset test on 2026-10-18), so 0.03 leaves room for that lean, not for a bug.
S5_TOLERANCE = {"rho": 0.03, "beta1": 0.03, "beta2": 0.01, "delta": 0.06}
S5_THETA_RANGE = (4.5, 5.75)               # mean fitted theta in this range (the plan's run: 5.25)
S5_PREDICTION_TOLERANCE = 0.10             # median |forecast / true mean - 1| below this
S6_DRAWS = 20_000                          # S6: draws from forecast_dist(20, 5)...
S6_THETA_RANGE = (4.8, 5.2)                # ...whose estimate_theta must land in this range
B9_FIT_THETA_RANGE = (4.0, 6.5)            # B9 check: M3's fit_theta on simulated NB counts with theta 5 (run: 5.26)
S8_CENSUS_TOLERANCE = 0.001                # S8: each barangay's rescaled pixels within 0.1% of its census total
S9_SAMPLES = 500                           # S9: fit this many samples...
S9_SAMPLE_YEARS = 25                       # ...of this many annual maxima each
S9_FIT_TOLERANCE_MM = 5                    # S9: median and 5th/95th percentile of fitted R(25) within 5 mm of 191, 164, 224
S10_SHARE_TOLERANCE = 1e-9                 # S10: the three shares add to 1 up to rounding
S11_HIDDEN_COUNT = -999                    # S11: counts a model may not see are overwritten with this (rule 1)

# ---------------------------------------------------------------------------
# Evaluation (D1, D3, D5, D6)
# ---------------------------------------------------------------------------
COVERAGE_LEVELS = (0.5, 0.9)               # D1: how often the central 50% and 90% ranges hold the truth
EPISODE_GAP_WEEKS = 2                      # D3, assumption: a breach week at most 2 weeks after the last one joins its episode (S7: [3, 4, 6] is one)
EPISODE_CI_METHOD = "beta"                 # D3: exact (Clopper-Pearson) 95% interval for "k of n episodes caught"
LEAD_TIME_IN_ADVANCE_WEEKS = 1             # D4: an episode is caught in advance if its lead time is at least 1 week
BOOT_BLOCK_WEEKS = 8                       # assumption
BOOT_BLOCK_WEEKS_TESTS = (4, 13)
BOOT_RESAMPLES = 2000
BOOT_INTERVAL = 0.95                       # D5, D6: the bootstrap interval runs from the 2.5% to the 97.5% point
RANDOM_SEED = 2026
# D5: the primary endpoint, model a against model b. Names as in B10's forecasts table (column model).
PRIMARY_COMPARISON = ("M4", "M3")
FLOOD_TEST = ("M4", "M4_no_EI2")           # D6: does the flood exposure index help? (nested: no DM)
PRACTICAL_TEST = ("M4", "M1")              # D6: does M4 beat the same-week average health offices use?

# Layer 2 results (D7): maps and tables from C8 and C9. Stock planning, not prescriptions.
# Map classes, the same for every storm so the maps compare. A value on a break goes to
# the class above it, so the classes from FLAG_EXPOSED_SHARES up are exactly the
# barangays C8 flags.
D7_MAP_SHARE_BREAKS = (0.01, 0.05, 0.10, *FLAG_EXPOSED_SHARES)    # share of a barangay's residents in flood zones
D7_MAP_DOXY_BREAKS = (100, 1_000, 5_000, 10_000, 25_000, 50_000)  # doxycycline 100 mg capsules per barangay
D7_MAP_W = 0.5                             # a short flood's dose map shows w = 0.5, the middle of WOUND_SHARE_W; the tables give every w
D7_RUNS_TOLERANCE = 0.01                   # C8's main run and C9's observed run must agree to 0.01 people or units (both files keep 4 decimals)

# Paper figures (D8). Stock planning, not prescriptions.
# Assumption: figure 4, the plan's "Carina exposure map", also shows Kristine on the same
# scale. Carina's IMERG rain sits at R0, so its map is almost empty (Notes.md 1.1); Kristine
# shows what a storm IMERG registers looks like. If the team does not confirm Kristine,
# set this to ("carina_2024",).
D8_MAP_STORMS = ("carina_2024", "kristine_2024")
D8_RELIABILITY_YEARS = PROB_SCORE_YEARS    # figure 3 scores the breach probabilities on D3's window (2022-2026)

# ---------------------------------------------------------------------------
# App data (F2): the files the web app (app/) reads. Stock planning, not prescriptions.
# ---------------------------------------------------------------------------
APP_DATA = ROOT / "app" / "public" / "data"    # served to the app as /data/<file>; committed, so Vercel ships it
APP_BARANGAY_RUNS = APP_DATA / "barangays"     # one file per storm and run
FORECASTS_SIMULATED = RESULTS / "forecasts_simulated_C.csv"   # B10 --simulate --option C: the app's Layer 1 until A13
# NCR's 17 cities and municipalities (PSGC as of 31 Dec 2023) from faeldon/philippines-json-maps
# (MIT): its four NCR district files at "hires" (mapshaper's 10%), pinned to one commit.
NCR_CITIES_RAW = DATA_RAW / "ncr_cities"
NCR_CITIES_URL = ("https://raw.githubusercontent.com/faeldon/philippines-json-maps/"
                  "8eeead560246863c8c820c31ca6fbca81a279477/2023/geojson/provdists/hires/"
                  "municities-provdist-{district}.0.1.json")
NCR_DISTRICTS = ("1303900000", "1307400000", "1307500000", "1307600000")   # Manila, then the 2nd (with QC), 3rd and 4th districts
NCR_CITIES_BYTES = {"1303900000": 29_016, "1307400000": 23_439, "1307500000": 45_025, "1307600000": 78_208}   # the pinned files' sizes
NCR_CITY_COUNT = 17
QC_CITY_PSGC = QC_PSGC_PREFIX + "00000"        # Quezon City's own 10-digit PSGC: the only city with data
# Assumption: shape detail kept for the web, in metres (about a pixel at the city's view). One
# value for cities and barangays, which are simplified together so their borders stay one line.
MAP_SIMPLIFY_M = 10
APP_COORD_DECIMALS = 5                         # about 1 m
APP_FLAG_SHARE = FLAG_EXPOSED_SHARES[0]        # the app flags a barangay at 25% (Notes.md 1.2)
APP_SHARE_BREAKS = (0.05, 0.15, *FLAG_EXPOSED_SHARES)   # the map's five classes: under 5%, 5-15%, 15-25%, 25-50%, 50% or more
APP_SHORT_FLOOD_W = D7_MAP_W                   # a short flood is shown at w = 0.5, as on D7's maps

# The map (F4). A city's color on the map and its panel's outbreak level come from one model's
# chance of an outbreak next week, Pr(breach) (B7). Assumption (app plan, open question 3):
# Low below 10%, Watch from 10% to under 50%, High from 50%, so the design's 22% reads Watch.
APP_LEVEL_MODEL = "M4"                         # LEPTON's model fills the map and the city panel
APP_LEVELS = (("low", 0.0), ("watch", 0.10), ("high", 0.50))   # each level and the Pr(breach) it starts at
# Assumption: a city smaller than this gets no name written on the map, as in Figma (only
# Pateros, 1.6 km2; the next smallest, San Juan, is 5.8 km2). Its name still shows on hover.
APP_LABEL_MIN_KM2 = 3
from datetime import date
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"        # downloads, never edited
DATA_CLEAN = ROOT / "data" / "clean"    # processed files
RESULTS = ROOT / "results"

CALENDAR = DATA_CLEAN / "calendar_weeks.csv"
IMERG_DAILY = DATA_RAW / "imerg_daily.nc"
ERA5_DAILY = DATA_CLEAN / "era5_daily.csv"
ERA5_RAW = DATA_RAW / "era5_open_meteo"               # Open-Meteo's replies, one JSON file per year
FORECASTS_STORMS = DATA_CLEAN / "forecasts_storms.csv"
ECMWF_RAW = DATA_RAW / "ecmwf_previous_runs"          # Open-Meteo's replies, one JSON file per storm
CATCHMENTS = DATA_CLEAN / "catchments_qc.gpkg"
WORLDPOP = DATA_RAW / "phl_pop_2024_CN_100m_R2025A_v1.tif"  # whole country, unchanged
WORLDPOP_BOX = DATA_CLEAN / "worldpop_2024_box.tif"   # clipped to IMERG_BOX; the census rescale starts here
WORLDPOP_SCALE_QC = DATA_CLEAN / "worldpop_scale_qc.csv"  # census scale factor per barangay
OVERLAY = DATA_CLEAN / "overlay_qc.csv"
EI_WEEKLY = DATA_CLEAN / "ei_weekly.csv"
CASES_WEEKLY = DATA_CLEAN / "cases_weekly.csv"        # QC weekly counts by onset week
# QCESD's case list, unchanged. Case-level records: never commit or share it.
QCESD_CASES_RAW = DATA_RAW / "qcesd" / "qcesd_case_list.xlsx"
POP_WEEKLY = DATA_CLEAN / "pop_weekly.csv"            # QC population for every week
FORECASTS = RESULTS / "forecasts.csv"
IMERG_WEIGHTS_QC = DATA_CLEAN / "imerg_weights_qc.csv"  # WorldPop QC weights per IMERG cell
RAIN_WEEKLY = DATA_CLEAN / "rain_weekly.csv"            # weekly QC rain R(t) and Rcum2(t)
FEATURES_WEEKLY = DATA_CLEAN / "features_weekly.csv"    # weekly rain and exposure (R, Rcum2, EI, EI2)
C8_RUNS = RESULTS / "c8_observed_runs.csv"            # one row per storm, test, D, cut-off and w
C8_BARANGAYS = RESULTS / "c8_observed_barangays.csv"  # the main run, one row per barangay
C8_CENTERS = RESULTS / "c8_observed_centers.csv"      # the main run, need per health center and pool
C9_RUNS = RESULTS / "c9_forecast_runs.csv"            # one row per storm, run (observed or lead), D and w
C9_BARANGAYS = RESULTS / "c9_forecast_barangays.csv"  # the same runs, one row per barangay
C9_CENTERS = RESULTS / "c9_forecast_centers.csv"      # the same runs, need per health center and pool
D7_FORECAST_VS_OBSERVED = RESULTS / "d7_forecast_vs_observed.csv"  # the doses at each lead beside the observed doses
D7_FLAGS = RESULTS / "d7_flags.csv"                   # flagged versus flooded, per storm, run and flag share
D7_TESTS = RESULTS / "d7_tests.csv"                   # the cut-off test (and D +/- 1): QC's adult tiers and units
D7_CENTERS = RESULTS / "d7_centers.csv"               # doses per health center, the main run, whole units
D7_MAP_NAME = "d7_map_{storm}.png"                    # one barangay map per storm, in RESULTS
# The score tables the paper's results quote, written by src/score_tables.py from the forecasts.
D_SCORES = RESULTS / "d1_scores.csv"                  # every score per window and model
D_MAE_BY_YEAR = RESULTS / "d1_mae_by_year.csv"        # each model's MAE in each target year
D_ALARMS = RESULTS / "d3_alarms.csv"                  # alarm cut-off p*, precision, sensitivity, episodes, lead time
D_PRECISION_RECALL = RESULTS / "d3_precision_recall.csv"  # the precision-recall curve behind p*, 2022-2026
D_TESTS_ALL_YEARS = RESULTS / "d5_d6_all_years.csv"   # the all-years check, COVID years in
D_GUARD_RERUNS = RESULTS / "d5_guard_reruns.csv"      # MAE and the three comparisons with g = 1, 2 and 3
# The paper's five figures, drawn by src/paper_figures.py from the files above.
D8_FIG1_FORECASTS = RESULTS / "d8_fig1_forecasts.png"      # weekly cases, M4 and M3, M4's 90% range
D8_FIG2_MAE = RESULTS / "d8_fig2_mae.png"                  # MAE by model, and the differences
D8_FIG2_TABLE = RESULTS / "d8_fig2_mae.csv"                # the numbers in figure 2
D8_FIG3_RELIABILITY = RESULTS / "d8_fig3_reliability.png"  # reliability of the breach probabilities
D8_FIG3_TABLE = RESULTS / "d8_fig3_reliability.csv"        # the reliability steps, forecasts per step
D8_FIG4_MAP = RESULTS / "d8_fig4_exposure_map.png"         # share of residents in flood zones, per storm
D8_FIG5_DOSES = RESULTS / "d8_fig5_doses.png"              # the doses table as a picture
D8_FIG5_TABLE = RESULTS / "d8_fig5_doses.csv"              # the doses table
D8_PREVIEW_PREFIX = "d8_preview_"                          # --preview: figures 1-3 from another forecasts file; not for the paper
# The paper's two design diagrams (Appendix A), drawn by src/diagrams.py from config.py alone.
E8_FIG_DESIGN = RESULTS / "e8_fig_design.png"              # the study design, one flood computation, two layers
E8_FIG_LAYER1 = RESULTS / "e8_fig_layer1.png"              # the six steps behind every Layer 1 forecast

# Benchmark data
PARRENO_RAW = DATA_RAW / "parreno" / "Diseases Data (for NBL).xlsx"        # Mendeley file, unchanged
PARRENO_WEEKLY = DATA_CLEAN / "parreno_national_weekly.csv"      # national leptospirosis by ISO week, for the M3 reproduction

# Boundaries and census
BOUNDARIES_ZIP = DATA_RAW / "phl_admin_boundaries.gdb.zip"           # HDX COD-AB v03
CENSUS_2024_XLSX = DATA_RAW / "NCR - Table C - Population by Barangay.xlsx"  # PSA 2024 POPCEN
CENSUS_2020_AGE_XLSX = DATA_RAW / "2020 Census Total Popn_Single Age_MaleFemale_Admin4.xlsx"  # HDX
BARANGAYS_QC = DATA_CLEAN / "barangays_qc.gpkg"       # 142 polygons with both census totals
CENSUS_QC = DATA_CLEAN / "census_qc.csv"              # same table without the shapes
AGE_SEX_2020_QC = DATA_CLEAN / "age_sex_2020_qc.csv"  # psgc, sex, age, pop (age 80 = 80 and over)
BIRTHS_2024 = DATA_RAW / "psa_births_2024.csv"        # PSA OpenSTAT table 1A1ABIB8, unchanged
SHARES_QC = DATA_CLEAN / "shares_qc.csv"              # child, pregnant and adult shares per barangay

# Health facilities
NHFR_RAW = DATA_RAW / "nhfr"                          # registry pages as downloaded
FACILITIES_QC = DATA_CLEAN / "health_facilities_qc.csv"  # one row per QC facility, with coordinates
CENTER_SHARES = DATA_CLEAN / "center_shares_qc.csv"   # the share of each barangay's need each health center gets
# NOAH flood hazard maps
NOAH_RAW = DATA_RAW / "noah"                          # the zips as downloaded, plus NOAH's metadata
NOAH_FLOOD = DATA_CLEAN / "noah_flood_mm.gpkg"        # 9 rows (3 maps x Var 1-3), EPSG:32651

# Calendar and periods
FIRST_WEEK_START = date(2015, 1, 4)        # 2015 week 1 (CDC/MMWR)
BURN_IN_YEARS = (2015, 2016, 2017)
BACKTEST_FIRST_YEAR = 2018                 # first forecast day: first week of 2018
BACKTEST_LAST_YEAR = 2026                  # to the last complete week of 2026
COVID_YEARS = (2020, 2021)
WEEKS_PER_YEAR = 52.18                     # period of the M4 season terms
MAX_WEEK = 52                              # week 53 is mapped to 52
DAYS_PER_WEEK = 7                          # UTC days in one complete morbidity week

# Scoring windows (Workstream D)
MAE_YEARS = (2018, 2019, 2022, 2023, 2024, 2025, 2026)
PROB_SCORE_YEARS = (2022, 2023, 2024, 2025, 2026)
ALL_YEARS = tuple(range(BACKTEST_FIRST_YEAR, BACKTEST_LAST_YEAR + 1))   # every score again, COVID years in: a check (D)
MASE_DENOM_YEARS = (2016, 2017)            # fixed denominator

# Gates
GATE_A = date(2026, 10, 16)
GATE_BC = date(2026, 10, 19)
GATE_D = date(2026, 10, 21)
SUBMIT = date(2026, 10, 24)                # Sat, Oct 24, 11:59 PM (README)

# Data products
IMERG_PRODUCT = "GPM_3IMERGDL"
IMERG_VERSION = "07"
IMERG_START = date(2000, 6, 1)             # NASA's catalogue lists Late daily files from 1998-01-01; the plan starts here
IMERG_SUBSETS = DATA_RAW / "imerg_daily"   # one small file per UTC day, stacked into IMERG_DAILY
IMERG_VARIABLES = ("precipitation", "precipitation_cnt")  # rain in mm/day; valid half-hours (of 48) behind it
IMERG_DOWNLOAD_WORKERS = 4                 # downloads at once; keep it small, NASA's server is shared
EARTHDATA_TOKEN_FILE = Path.home() / "earthdata_token.txt"  # your NASA login token; outside the repo, never share it
IMERG_KEEP_2000 = True                     # assumption: keep Jun-Dec 2000; refit once without it
ERA5_YEARS = (2000, 2025)                  # assumption: same years as IMERG
ERA5_START = IMERG_START                   # start on IMERG's first day, so both fits use the same years
ERA5_MODEL = "era5"                        # Open-Meteo Historical Weather, plain ERA5 reanalysis at 0.25 deg
OPEN_METEO_HOUR_SHIFT = -1                 # shift hourly totals back 1 h before summing UTC days
FORECAST_MODEL = "ecmwf_ifs025"            # assumption: ECMWF IFS 0.25 deg
FORECAST_LEADS_DAYS = (1, 2, 3)            # the n-day total forecast 1, 2 and 3 days before its first day

# Catchments. The Philippines is in HydroSHEDS' Australasia region ("au"), not Asia.
HYDROBASINS_SHP = DATA_RAW / "hydrobasins" / "hybas_au_lev12_v1c.shp"
# One point on each river; the sub-basin holding it is the start of the upstream trace.
CATCHMENT_OUTLETS = {
    "marikina": {"lon": 121.093, "lat": 14.636, "trace_upstream": True},   # Sto. Nino gauge, Marikina City
    "san_juan": {"lon": 121.017, "lat": 14.589, "trace_upstream": False},  # mouth at the Pasig; see note below
    "tullahan": {"lon": 121.030, "lat": 14.690, "trace_upstream": True},   # Novaliches, QC
}
# San Juan: its sub-basin is the Pasig's last one, which also receives Laguna de Bay (4,034 km2 upstream).
WORLDPOP_URL = ("https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2024/"
                "PHL/v1/100m/constrained/phl_pop_2024_CN_100m_R2025A_v1.tif")
WORLDPOP_BYTES = 63_493_139                # size of the copy used (its note); R2025A is an alpha release

IMERG_CELL_DEG = 0.1
IMERG_BOX = (120.7, 14.4, 121.5, 15.0)     # (lon_min, lat_min, lon_max, lat_max); printed by src/catchments.py
# ERA5 and ECMWF IFS 0.25 grid points sit on multiples of 0.25 degrees.
GRID_025_DEG = 0.25
GRID_EDGE_POINTS = 25                      # points per cell edge before reprojecting (catchments.grid_cells)
GRID_AREA_TOLERANCE = 1e-3                 # the cells must hold the catchment area to within 0.1%

CRS_LONLAT = "EPSG:4326"                   # longitude/latitude degrees: catchments_qc.gpkg and the rain grids
CRS_OVERLAY = "EPSG:32651"                 # overlays
CRS_EXACTEXTRACT = "EPSG:4326"             # convert to this before exactextract
QC_BARANGAYS = 142                         # check S3
QC_HDX_ADM3_PCODE = "PH1307404"            # QC in the HDX boundaries
QC_PSGC_PREFIX = "13813"                   # QC in the official 10-digit PSGC: 13813xxxxx
QC_SHEET_2024 = "Quezon City"              # QC's sheet in the PSA 2024 workbook
# DOH National Health Facility Registry (https://nhfr.doh.gov.ph), list "Active facilities".
NHFR_REGION_NCR = "13"
NHFR_QC_NAME = "QUEZON CITY (HUC)"         # QC in the registry's Province Name column
# Registry facility types kept.
NHFR_FACILITY_TYPES = {"17": "Rural Health Unit", "20": "Barangay Health Station", "21": "City Health Office"}
NHFR_PAUSE_S = 1.0                         # wait between page requests; the registry is a shared server
NOAH_RETURN_PERIODS = (5, 25, 100)
NOAH_HAZARD_LEVELS = (1, 2, 3)             # the `Var` field
NOAH_OVERLAP_TOLERANCE_KM2 = 1e-6          # levels of one map may share at most 1 m2 in a barangay (rounding)
# Google Drive file ids of NOAH's Metro Manila flood maps.
NOAH_FLOOD_FILES = {
    5: "1IC5LnscUt7D_5c1BvlwcngR3cFKgDshV",
    25: "1VAcWkVeY2uXWhZVvDYh5viedhihwBBci",
    100: "1n-IrwfWqLRDyDg-wmt68luk_DU5Xzg9S",
}
NOAH_METADATA_FILES = {                    # NOAH's own notes, kept beside the maps
    "metadata_flood.txt": "1qbOoN_CZ6AUIk22owtJxRFENALIWCszq",
    "01ReadMe_Flood.pdf": "1Z6gT7FDUCMps-qHT5Jiy7nwCdaH0rhwR",
    "NOAH_License.pdf": "1z6MH_QI6gU_e2gNnhIMsKkENugHscNl9",
}

# Census reference days for pop_at.
CENSUS_DAYS = {2015: date(2015, 8, 1), 2020: date(2020, 5, 1), 2024: date(2024, 7, 1)}
# PSA official totals from Table B of the 2024 NCR workbook; src/census.py stops if it disagrees.
CENSUS_POP_QC = {2015: 2_936_116, 2020: 2_960_048, 2024: 3_084_270}

# Layer 1: case data view
# The case list has onset dates but no report dates, so option C: the delay guard.
DATA_OPTION = "C"                          # "A", "B" or "C"; set by the case-data decision
DELAY_GUARD_G = 2                          # assumption, option C only
DELAY_GUARD_G_TESTS = (1, 3)
FORECAST_HORIZON_WEEKS = 1                 # forecast day T forecasts week T + 1
REPORTED_SHARE_CUTOFF = 0.50               # assumption, option A only
REPORTED_SHARE_CUTOFF_TEST = 0.80

# Layer 1: case data
# QCESD's case list: one sheet per year, one row per case, these columns.
QCESD_COLUMNS = ("Year_of_onset", "Date_of_onset", "Morbidity_week", "Date_of_Admission", "District", "Barangay")
QCESD_ONSET = "Date_of_onset"
QCESD_ADMISSION = "Date_of_Admission"
# Assumption: a week's count is final 17 days after it ends; later weeks are missing, not zero.
CASES_COMPLETE_DAYS = 17
CASES_COMPLETE_SHARE = 0.99                # S4: at least this share of onset-to-admission delays within CASES_COMPLETE_DAYS
CASES_DELAY_FLAG_DAYS = 30                 # an admission before onset or over 30 days after it is a likely date typo, counted, kept as given
# S4: QCESD totals published during 2025, reproduced from the list by onset date.
CASES_PUBLISHED = (
    {"start": date(2025, 1, 1), "end": date(2025, 8, 20), "cases": 510,
     "source": "https://www.dzrh.com.ph/post/leptospirosis-cases-in-quezon-city-rise-to-510-deaths-double-in-just-over-a-month-to-55"},
    # The plan's example. Found only second-hand (MesVaccins, 3 Sep 2025, citing Outbreak News Today).
    {"start": date(2025, 1, 1), "end": date(2025, 9, 1), "cases": 535,
     "source": "https://www.mesvaccins.net/web/news/23425-philippines-leptospirose-a-quezon-city"},
)
S4_PUBLISHED_TOLERANCE = 0.05              # S4: "reproduced closely" = within 5% of the published total

# Layer 1: models
M0_LAG_WEEKS = 52                          # M0: the count 52 weeks before the target week
FOURIER_K = 3                              # M4 sin/cos pairs
RAIN_SCALE_MM = 50                         # M4 uses Rcum2 / 50
RAIN_EI_MAX_CORR = 0.8                     # above this, keep EI2 alone
# statsmodels' optimizers for the negative binomial fit, in order.
M4_FIT_METHODS = ("newton", "bfgs")
M4_MAX_ITER = 100                          # iterations before a fit counts as not converged
M4_RESIDUAL_ACF = RESULTS / "m4_residual_acf.png"  # the residual autocorrelation check
M4_RESIDUAL_ACF_TABLE = RESULTS / "m4_residual_acf.csv"  # the numbers in that plot, one row per lag
M4_ACF_LAGS = 26                           # lags plotted, half a year
M4_ACF_ALPHA = 0.05                        # the plot's shaded band holds 95% of the autocorrelations of independent weeks

# M3 benchmark, read from Latigay & Gonzaga (2026)
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
# The paper's Table I, all 18 forecast weeks (SARIMA not reproduced).
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
# M3 diagnostics (python -m src.m3 --diagnose): XGBoost settings tried when the hybrid misses
M3_DIAG_MAX_DEPTH = (1, 2, 3, 4, 6)
M3_DIAG_ROUNDS = (10, 25, 50, 100, 200)
M3_DIAG_ETA = (0.05, 0.1, 0.3)
M3_DIAGNOSTICS = RESULTS / "m3_diagnostics.csv"       # hybrid scores for every setting tried
M3_SEASONAL_PERIOD = 52                    # seasonal naive: the value 52 rows earlier
M3_RAINY_MONTHS = (6, 11)                  # "monsoon season (June-November)"
# Assumption: the paper cites a news timeline but gives no dates.
M3_LOCKDOWNS = ((date(2020, 3, 15), date(2020, 5, 31)), (date(2020, 8, 4), date(2020, 8, 18)))
M3_LOCKDOWNS_TEST = ((date(2020, 3, 15), date(2020, 12, 31)),)   # any community quarantine in 2020
# Assumption: the paper counts 260 weeks = 5 x 52, so its series has no ISO 2020 week 53 row.
M3_DROP_WEEK_53 = True
M3_RESULTS = RESULTS / "m3_reproduction.csv"          # scores of every run beside Table I
M3_FORECASTS = RESULTS / "m3_forecasts.csv"           # the 18 forecast weeks of every run

# Layout of the Mendeley file.
PARRENO_URL = "https://data.mendeley.com/datasets/v98325dpxv/1"   # DOI matches Latigay & Gonzaga's ref. 9 (data/raw/parreno.md)
PARRENO_SHEET = 0                          # sheet name or position
PARRENO_WEEK_COL = "Week"                  # the column holding the week number
PARRENO_DISEASE_KEY = "Leptospirosis"      # columns whose name contains this (any case) and ends in a year

# Forecast range
THETA_WINDOW = 104                         # last 104 non-COVID past forecasts
THETA_MIN_FORECASTS = 26                   # fewer -> training fit's theta
RANGE_LOW_Q = 0.05                         # 90% range
RANGE_HIGH_Q = 0.95
WIS_ALPHAS = (0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)  # 11 central ranges; S7's WIS values (2.12, 32.0) need all 11

# Threshold
THRESHOLD_SD = 2                           # assumption: mean + 2 SD
THRESHOLD_MAX_YEARS = 5
THRESHOLD_MIN_YEARS = 3

# Layer 2: rain and exposure
GUMBEL_MIN_YEARS = 10                      # assumption: fit on >= 10 years before the forecast year
# Assumption: the trigger rain is the wettest 3-day total (3 consecutive UTC days).
RAIN_ACCUM_DAYS = 3
RAIN_ACCUM_DAYS_TEST = 1
# A lead-L forecast takes day i of the window from precipitation_previous_day(L + i).
FORECAST_PREVIOUS_DAYS = tuple(range(1, max(FORECAST_LEADS_DAYS) + RAIN_ACCUM_DAYS))
R0_FACTOR = 0.5                            # assumption: R0 = 0.5 x R(5)

# Layer 2: people and doses
PREG_BIRTHS_FACTOR = 0.75                  # assumption: pregnant = births x 0.75
PREG_UPPER_SHARE = 0.035                   # test: 3.5% of population as upper bound
# Age groups from the 2020 census by single-year age (first and last age both included)
CHILD_AGES = (0, 17)                       # children under 18
WOMEN_AGES = (15, 49)                      # women 15-49; the city's pregnant count is split by them (assumption)
GIRLS_AGES = (15, 17)                      # women 15-17: their pregnant share moves out of the child group
# The births file: OpenSTAT's CSV is Windows-1252 and has no codes.
BIRTHS_ENCODING = "cp1252"
BIRTHS_QC_ROW = "Quezon City"
BIRTHS_COLUMN = "Usual Residence Both Sexes"  # mothers who live in QC, not births in QC's hospitals
CONTACT_SHARE_Q = 1.0                      # assumption: reported at full coverage
UPTAKE_U = 1.0
CONTACT_BY_LEVEL = {1: 1.0, 2: 1.0, 3: 1.0}  # assumption: r_k = 1 for every level
WOUND_SHARE_W = (0.0, 0.5, 1.0)            # assumption: illustrative grid; 0 and 1 are bounds
CONTINUOUS_EXPOSURE_DAYS = 2               # assumption: D >= 2 -> every exposed adult high risk
CONTINUOUS_EXPOSURE_DAYS_TESTS = (1, 3)    # each storm is rerun with these cut-offs
MODERATE_COURSE_DAYS = 5                   # assumption: upper end of 3-5 days

# Units (DOH DM 2023-0309; stock planning, not prescriptions)
DOXY_CAPS_LOW = 2                          # 200 mg once = 2 x 100 mg
DOXY_CAPS_MOD = 2 * MODERATE_COURSE_DAYS   # 200 mg daily for 5 days = 10
DOXY_CAPS_HIGH_PER_WEEK = 2                # 200 mg once a week
AMOX_TABS_PREG = 6                         # 500 mg twice a day for 3 days
DOSE_WEEK_DAYS = 7                         # ceil(D / 7) weeks: high-risk adults' weekly dose; children's course repeats after 1 week

# Stock per health center
# Assumption: stock goes to health centers and barangay health stations, not the City Health Office.
CENTER_FACILITY_TYPES = ("Rural Health Unit", "Barangay Health Station")
ALLOCATE_PREVIEW_STOCK_SHARE = 0.5         # preview only (python -m src.allocation): stock covering half of each pool's need

FORECAST_RUN_D = (1, 7)                    # assumption: flood durations for the forecast runs
STORM_D_TEST_DAYS = 1                      # assumption test: each storm is rerun with D +/- 1 day
# Assumption: a barangay is flagged when at least this share of its residents live in flooded zones.
FLAG_EXPOSED_SHARES = (0.25, 0.50)

# Storms.
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
    # Added 2026-10-18: a storm IMERG registers, beside Carina, which IMERG reads near R0.
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

# Sanity checks (src/checks.py)
S2_CARINA_TOP_SHARE = 0.05                 # S2: Carina's wettest day must be in 2024's wettest 5% of days
S2_KNOWN_STORMS_TOP_SHARE = 0.01           # S2: each storm below must have a day in the record's wettest 1%
# Metro Manila's worst rain events as UTC days (00:00-08:00 PHT falls in the previous UTC day).
S2_KNOWN_STORMS = {
    "ondoy_2009": (date(2009, 9, 25), date(2009, 9, 26)),      # PHT 26 Sep 2009 (Ketsana)
    "habagat_2012": (date(2012, 8, 5), date(2012, 8, 8)),      # PHT 6-8 Aug 2012 (with Saola/Gener)
    "maring_2013": (date(2013, 8, 17), date(2013, 8, 21)),     # PHT 18-21 Aug 2013 (habagat with Trami/Maring)
    "ulysses_2020": (date(2020, 11, 10), date(2020, 11, 12)),  # PHT 11-12 Nov 2020 (Vamco)
}
# S5: made-up datasets that follow M4, fitted to see if M4 gets the true values back.
S5_DATASETS = 50                           # the plan: 50 datasets...
S5_WEEKS = 400                             # ...of 400 target weeks each
S5_TRUE = {"rho": 0.30, "beta1": 0.15, "beta2": 0.05, "delta": -0.40}   # the plan's true values
S5_THETA = 5                               # the plan's true theta
# Our choice: about 20-60 cases a week, a June-November wet season.
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
# Mean of 50 fits within this of the truth; rho runs about 0.02 low at 400 weeks.
S5_TOLERANCE = {"rho": 0.03, "beta1": 0.03, "beta2": 0.01, "delta": 0.06}
S5_THETA_RANGE = (4.5, 5.75)               # mean fitted theta in this range
S5_PREDICTION_TOLERANCE = 0.10             # median |forecast / true mean - 1| below this
S6_DRAWS = 20_000                          # S6: draws from forecast_dist(20, 5)...
S6_THETA_RANGE = (4.8, 5.2)                # ...whose estimate_theta must land in this range
B9_FIT_THETA_RANGE = (4.0, 6.5)            # M3 check: fit_theta on simulated NB counts with theta 5
S8_CENSUS_TOLERANCE = 0.001                # S8: each barangay's rescaled pixels within 0.1% of its census total
S9_SAMPLES = 500                           # S9: fit this many samples...
S9_SAMPLE_YEARS = 25                       # ...of this many annual maxima each
S9_FIT_TOLERANCE_MM = 5                    # S9: median and 5th/95th percentile of fitted R(25) within 5 mm of 191, 164, 224
S10_SHARE_TOLERANCE = 1e-9                 # S10: the three shares add to 1 up to rounding
S11_HIDDEN_COUNT = -999                    # S11: counts a model may not see are overwritten with this
S11_REAL_DAYS = ((2018, 30), (2023, 30))   # S11 on the real counts: forecast days (year, week), each at g = 2, 1 and 3

# Evaluation
COVERAGE_LEVELS = (0.5, 0.9)               # how often the central 50% and 90% ranges hold the truth
EPISODE_GAP_WEEKS = 2                      # assumption: a breach week at most 2 weeks after the last one joins its episode
EPISODE_CI_METHOD = "beta"                 # exact (Clopper-Pearson) 95% interval for "k of n episodes caught"
LEAD_TIME_IN_ADVANCE_WEEKS = 1             # an episode is caught in advance if its lead time is at least 1 week
BOOT_BLOCK_WEEKS = 8                       # assumption
BOOT_BLOCK_WEEKS_TESTS = (4, 13)
BOOT_RESAMPLES = 2000
BOOT_INTERVAL = 0.95                       # the bootstrap interval runs from the 2.5% to the 97.5% point
RANDOM_SEED = 2026
# The primary endpoint, model a against model b, named as in the forecasts table.
PRIMARY_COMPARISON = ("M4", "M3")
FLOOD_TEST = ("M4", "M4_no_EI2")           # does the flood exposure index help? (nested: no DM)
PRACTICAL_TEST = ("M4", "M1")              # does M4 beat the same-week average health offices use?

# Layer 2 results: maps and tables from the storm runs.
D7_MAP_SHARE_BREAKS = (0.01, 0.05, 0.10, *FLAG_EXPOSED_SHARES)    # share of a barangay's residents in flood zones
D7_MAP_DOXY_BREAKS = (100, 1_000, 5_000, 10_000, 25_000, 50_000)  # doxycycline 100 mg capsules per barangay
D7_MAP_W = 0.5                             # a short flood's dose map shows w = 0.5, the middle of WOUND_SHARE_W; the tables give every w
D7_RUNS_TOLERANCE = 0.01                   # the main run and the observed run must agree to 0.01 people or units (both files keep 4 decimals)

# Paper figures.
D8_MAP_STORMS = ("carina_2024", "kristine_2024")
D8_RELIABILITY_YEARS = PROB_SCORE_YEARS    # figure 3 scores the breach probabilities on the window (2022-2026)

# App data: the files the web app (app/) reads. Stock planning, not prescriptions.
APP_DATA = ROOT / "app" / "public" / "data"    # served to the app as /data/<file>; committed, so Vercel ships it
APP_BARANGAY_RUNS = APP_DATA / "barangays"     # one file per storm and run
FORECASTS_SIMULATED = RESULTS / "forecasts_simulated_C.csv"   # backtest --simulate --option C: the app's Layer 1 without case data
# NCR's 17 cities and municipalities from faeldon/philippines-json-maps (MIT), pinned to one commit.
NCR_CITIES_RAW = DATA_RAW / "ncr_cities"
NCR_CITIES_URL = ("https://raw.githubusercontent.com/faeldon/philippines-json-maps/"
                  "8eeead560246863c8c820c31ca6fbca81a279477/2023/geojson/provdists/hires/"
                  "municities-provdist-{district}.0.1.json")
NCR_DISTRICTS = ("1303900000", "1307400000", "1307500000", "1307600000")   # Manila, then the 2nd (with QC), 3rd and 4th districts
NCR_CITIES_BYTES = {"1303900000": 29_016, "1307400000": 23_439, "1307500000": 45_025, "1307600000": 78_208}   # the pinned files' sizes
NCR_CITY_COUNT = 17
QC_CITY_PSGC = QC_PSGC_PREFIX + "00000"        # Quezon City's own 10-digit PSGC: the only city with data
# The map shows every city and municipality of the Philippines, from the same commit of faeldon's maps.
FAELDON_URL = NCR_CITIES_URL.split("provdists/")[0] + "{path}"   # the same commit's 2023/geojson/ folder
PH_CITIES_RAW = DATA_RAW / "ph_cities"
PH_REGIONS = ("100000000", "200000000", "300000000", "400000000", "500000000", "600000000",
              "700000000", "800000000", "900000000", "1000000000", "1100000000", "1200000000",
              "1300000000", "1400000000", "1600000000", "1700000000", "1900000000")   # faeldon's 17 regions, NCR is 1300000000
PH_CITY_COUNT = 1642                           # cities and municipalities in faeldon's 2023 maps, one file each
# The towns no province file holds: each outline is built by joining its barangays.
PH_TOWNS_APART = {
    "0330100000": ("City of Angeles", "Pampanga"),
    "0331400000": ("City of Olongapo", "Zambales"),
    "0431200000": ("City of Lucena", "Quezon"),
    "0630200000": ("City of Bacolod", "Negros Occidental"),
    "0631000000": ("City of Iloilo", "Iloilo"),
    "0730600000": ("City of Cebu", "Cebu"),
    "0731100000": ("City of Lapu-Lapu", "Cebu"),
    "0731300000": ("City of Mandaue", "Cebu"),
    "0831600000": ("City of Tacloban", "Leyte"),
    "0931700000": ("City of Zamboanga", "Zamboanga del Sur"),
    "1030500000": ("City of Cagayan de Oro", "Misamis Oriental"),
    "1030900000": ("City of Iligan", "Lanao del Norte"),
    "1230800000": ("City of General Santos", "South Cotabato"),
    "1430300000": ("City of Baguio", "Benguet"),
    "1630400000": ("City of Butuan", "Agusan del Norte"),
    "1731500000": ("City of Puerto Princesa", "Palawan"),
    "1999901000": ("Kapalawan", "Special Geographic Area"),
    "1999902000": ("Old Kaabakan", "Special Geographic Area"),
    "1999903000": ("Kadayangan", "Special Geographic Area"),
    "1999904000": ("Nabalawag", "Special Geographic Area"),
    "1999905000": ("Pahamuddin", "Special Geographic Area"),
    "1999906000": ("Malidegao", "Special Geographic Area"),
    "1999907000": ("Ligawasan", "Special Geographic Area"),
    "1999908000": ("Tugunan", "Special Geographic Area"),
}
# Assumption: outlines outside NCR keep detail to about 100 m.
PH_SIMPLIFY_M = 100
APP_CITIES_FILE = "ph_cities.json"             # .json, not .geojson, so the web host sends it compressed
# The islands' coastlines, which the map draws between the country view and the town borders.
PH_ISLANDS_GAP_M = 150
PH_ISLANDS_MIN_KM2 = 1
PH_ISLANDS_SIMPLIFY_M = 250
APP_ISLANDS_FILE = "ph_islands.json"
# The app's Simulation mode (src/app_simulation.py).
SIM_FORECAST_API = "https://api.open-meteo.com/v1/forecast"
SIM_FORECAST_RAW = DATA_RAW / "ecmwf_forecast"   # each day's reply, unchanged
APP_SIMULATION_FILE = "city_simulation.json"
SIM_MAX_PAST_DAYS = 92                           # the most past days Open-Meteo's forecast API gives
# A prophylaxis plan for every day of the app's timeline, not only the four storms (src/app_days.py).
FORECAST_ARCHIVE_START = date(2024, 2, 1)        # the archive's first hour is 3 Feb 2024; earlier days come back empty
APP_DAYS = APP_DATA / "days"                     # one file per year: each day's plan
APP_DAY_RUNS = APP_BARANGAY_RUNS / "days"        # one barangay file per day and run that exposes anyone
# Assumption: shape detail kept for the web, in metres (about a pixel at the city's view).
MAP_SIMPLIFY_M = 10
APP_COORD_DECIMALS = 5                         # about 1 m
APP_FLAG_SHARE = FLAG_EXPOSED_SHARES[0]        # the app flags a barangay at 25%
APP_SHARE_BREAKS = (0.05, 0.15, *FLAG_EXPOSED_SHARES)   # the map's five classes: under 5%, 5-15%, 15-25%, 25-50%, 50% or more
APP_SHORT_FLOOD_W = D7_MAP_W                   # a short flood is shown at w = 0.5, as on the maps

# The map.
APP_LEVEL_MODEL = "M4"                         # LEPTON's model fills the map and the city panel
APP_LEVELS = (("low", 0.0), ("watch", 0.10), ("high", 0.50))   # each level and the Pr(breach) it starts at
# Assumption: a city smaller than this gets no name on the map (only Pateros).
APP_LABEL_MIN_KM2 = 3

# NOAH's flood patches on the map.
APP_NOAH_MIN_M2 = 400
# While a barangay is open, the map draws only its own flood zones (src/noah_barangays.py), one file per map and barangay.
APP_NOAH_BARANGAYS = APP_DATA / "noah_barangays"
# Assumption: a barangay's flood zones keep detail to about 10 m, one cell of NOAH's grid: it smooths the cells'
# steps, a third as many points and 0.1% of the area lost (25-year map).
APP_NOAH_BARANGAY_SIMPLIFY_M = 10
# About 0.1 m, not APP_COORD_DECIMALS: rounded to 1 m, patches that meet at a corner of NOAH's cells overlap
# by up to 1.2 m2 (at 0.1 m, none), for 9% more bytes.
APP_NOAH_BARANGAY_DECIMALS = 6

# The map shows NOAH's flood maps for the whole country (src/noah_national.py), as vector tiles.
NOAH_NATIONAL_FOLDERS = {
    5: "17ecJuf2vnkrpCzNVLes0fI08XFsR1x8N",
    25: "1PYdJFtfxzmAwk1gIgn8wYLh8WPkiZvOf",
    100: "10pCWTfU-gVuAbdx4gdUGaDcNrSzMz0Mm",
}
NOAH_NATIONAL_CLEAN = DATA_CLEAN / "noah_national"   # one FlatGeobuf per province and map, and manifest.csv
# Assumption: before tiling, outlines drop points that move them less than 5 m.
NOAH_NATIONAL_PRESIMPLIFY_M = 5
# Assumption: tiles from zoom 4 (the whole country) to 11 (a city), 2^11 units across.
NOAH_TILE_ZOOMS = (4, 11)
NOAH_TILE_DETAIL = 11
# Assumption: each map uses the largest tile size limit that keeps its file under APP_NOAH_TILES_MAX_BYTES.
NOAH_TILE_LIMITS = (500_000, 300_000, 200_000)
APP_NOAH_TILES = "noah_flood_{return_period}yr.pmtiles"
APP_NOAH_TILES_MAX_BYTES = 95_000_000
# The NOAH tiles check: each file must reach at least this far (west, south, east, north).
APP_NOAH_TILES_REACH = (120.0, 7.5, 125.5, 18.0)
TIPPECANOE_WSL_DIR = "$HOME/tools/tippecanoe"   # Windows only: the WSL folder tippecanoe was built in (make)
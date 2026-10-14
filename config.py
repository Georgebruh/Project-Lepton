"""Project LEPTON settings (task A2).

Every date, path and assumption value lives here; no magic numbers elsewhere.
Values marked "assumption" are choices, not sourced facts: each one goes in the
paper's assumptions table with the test written beside it.
Values set to None are not known yet; the task named beside them fills them in.
"""

from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"        # downloads, never edited
DATA_CLEAN = ROOT / "data" / "clean"    # processed files
RESULTS = ROOT / "results"

IMERG_DAILY = DATA_RAW / "imerg_daily.nc"             # A4
ERA5_DAILY = DATA_CLEAN / "era5_daily.csv"            # A14
FORECASTS_STORMS = DATA_CLEAN / "forecasts_storms.csv"  # A15
CATCHMENTS = DATA_CLEAN / "catchments_qc.gpkg"        # A7
WORLDPOP = DATA_RAW / "phl_pop_2024_CN_100m_R2025A_v1.tif"  # A6
OVERLAY = DATA_CLEAN / "overlay_qc.csv"               # C2
EI_WEEKLY = DATA_CLEAN / "ei_weekly.csv"              # C3
CASES_WEEKLY = DATA_CLEAN / "cases_weekly.csv"        # A13
FORECASTS = RESULTS / "forecasts.csv"                 # B10

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
IMERG_START = date(2000, 6, 1)
IMERG_KEEP_2000 = True                     # assumption: keep Jun-Dec 2000; refit once without it
ERA5_YEARS = (2000, 2025)                  # assumption: same years as IMERG, A14
OPEN_METEO_HOUR_SHIFT = -1                 # shift hourly totals back 1 h before summing UTC days
FORECAST_MODEL = "ecmwf_ifs025"            # assumption: ECMWF IFS 0.25 deg, A15
FORECAST_LEADS_DAYS = (1, 2, 3)

CRS_OVERLAY = "EPSG:32651"                 # overlays
CRS_EXACTEXTRACT = "EPSG:4326"             # convert to this before exactextract
QC_BARANGAYS = 142                         # check S3
NOAH_RETURN_PERIODS = (5, 25, 100)
NOAH_HAZARD_LEVELS = (1, 2, 3)             # the `Var` field

# Census reference dates as decimal years for pop_at (B1)
CENSUS_T = {2015: 2015.58, 2020: 2020.33, 2024: 2024.50}  # 2015 = 1 Aug 2015; confirm with PSA
CENSUS_POP_QC = {2015: None, 2020: None, 2024: None}      # A5 fills these in

# ---------------------------------------------------------------------------
# Layer 1: case data view (B2)
# ---------------------------------------------------------------------------
DATA_OPTION = None                         # "A", "B" or "C"; set by the A13 decision
DELAY_GUARD_G = 2                          # assumption, option C only
DELAY_GUARD_G_TESTS = (1, 3)
REPORTED_SHARE_CUTOFF = 0.50               # assumption, option A only
REPORTED_SHARE_CUTOFF_TEST = 0.80

# ---------------------------------------------------------------------------
# Layer 1: models
# ---------------------------------------------------------------------------
FOURIER_K = 3                              # M4 sin/cos pairs
RAIN_SCALE_MM = 50                         # M4 uses Rcum2 / 50
RAIN_EI_MAX_CORR = 0.8                     # above this, keep EI2 alone (B5)

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
M3_TARGET_MAE = {"hybrid": 16.72, "prophet": 23.68}
M3_TOLERANCE = 0.10

# Forecast range (B6)
THETA_WINDOW = 104                         # last 104 non-COVID past forecasts
THETA_MIN_FORECASTS = 26                   # fewer -> training fit's theta
RANGE_LOW_Q = 0.05                         # 90% range
RANGE_HIGH_Q = 0.95
WIS_ALPHAS = (0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)  # 11 central ranges; confirm against v2's ALPHAS

# Threshold (B7)
THRESHOLD_SD = 2                           # assumption: mean + 2 SD
THRESHOLD_MAX_YEARS = 5
THRESHOLD_MIN_YEARS = 3

# ---------------------------------------------------------------------------
# Layer 2: rain and exposure (C3)
# ---------------------------------------------------------------------------
GUMBEL_MIN_YEARS = 10                      # assumption: fit on >= 10 years before the forecast year
R0_FACTOR = 0.5                            # assumption: R0 = 0.5 x R(5)

# ---------------------------------------------------------------------------
# Layer 2: people and doses (C4-C7)
# ---------------------------------------------------------------------------
PREG_BIRTHS_FACTOR = 0.75                  # assumption: pregnant = births x 0.75
PREG_UPPER_SHARE = 0.035                   # test: 3.5% of population as upper bound
CONTACT_SHARE_Q = 1.0                      # assumption: reported at full coverage
UPTAKE_U = 1.0
CONTACT_BY_LEVEL = {1: 1.0, 2: 1.0, 3: 1.0}  # assumption: r_k = 1 for every level
WOUND_SHARE_W = (0.0, 0.5, 1.0)            # assumption: illustrative grid; 0 and 1 are bounds
CONTINUOUS_EXPOSURE_DAYS = 2               # assumption: D >= 2 -> every exposed adult high risk
CONTINUOUS_EXPOSURE_DAYS_TESTS = (1, 3)
MODERATE_COURSE_DAYS = 5                   # assumption: upper end of 3-5 days

# Units (DOH DM 2023-0309; stock planning, not prescriptions)
DOXY_CAPS_LOW = 2                          # 200 mg once = 2 x 100 mg
DOXY_CAPS_MOD = 2 * MODERATE_COURSE_DAYS   # 200 mg daily for 5 days = 10
DOXY_CAPS_HIGH_PER_WEEK = 2                # 200 mg once a week
AMOX_TABS_PREG = 6                         # 500 mg twice a day for 3 days

FORECAST_RUN_D = (1, 7)                    # assumption: C9 flood durations
STORM_D_TEST_DAYS = 1                      # D +/- 1 day

# Storms (A11 fills in dates and D)
STORMS = {
    "carina_2024": {"year": 2024, "wettest_days": (date(2024, 7, 23), date(2024, 7, 25)), "D": None},
    "floods_2025": {"year": 2025, "wettest_days": None, "D": None},
    "habagat_2026": {"year": 2026, "wettest_days": None, "D": None},
}

# ---------------------------------------------------------------------------
# Evaluation (D5, D6)
# ---------------------------------------------------------------------------
BOOT_BLOCK_WEEKS = 8                       # assumption
BOOT_BLOCK_WEEKS_TESTS = (4, 13)
BOOT_RESAMPLES = 2000
RANDOM_SEED = 2026

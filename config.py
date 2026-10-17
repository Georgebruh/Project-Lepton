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
OPEN_METEO_HOUR_SHIFT = -1                 # shift hourly totals back 1 h before summing UTC days
FORECAST_MODEL = "ecmwf_ifs025"            # assumption: ECMWF IFS 0.25 deg, A15
FORECAST_LEADS_DAYS = (1, 2, 3)

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
REPORTED_SHARE_CUTOFF = 0.50               # assumption, option A only
REPORTED_SHARE_CUTOFF_TEST = 0.80

# ---------------------------------------------------------------------------
# Layer 1: models
# ---------------------------------------------------------------------------
M0_LAG_WEEKS = 52                          # M0: the count 52 weeks before the target week (B8)
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
CONTINUOUS_EXPOSURE_DAYS_TESTS = (1, 3)
MODERATE_COURSE_DAYS = 5                   # assumption: upper end of 3-5 days

# Units (DOH DM 2023-0309; stock planning, not prescriptions)
DOXY_CAPS_LOW = 2                          # 200 mg once = 2 x 100 mg
DOXY_CAPS_MOD = 2 * MODERATE_COURSE_DAYS   # 200 mg daily for 5 days = 10
DOXY_CAPS_HIGH_PER_WEEK = 2                # 200 mg once a week
AMOX_TABS_PREG = 6                         # 500 mg twice a day for 3 days

FORECAST_RUN_D = (1, 7)                    # assumption: C9 flood durations
STORM_D_TEST_DAYS = 1                      # D +/- 1 day

# Storms (A11: start_date, end_date, wettest_days UTC range, D, and flooded barangays by PSGC)
STORMS = {
    "carina_2024": {
        "year": 2024,
        "start_date": date(2024, 7, 23),
        "end_date": date(2024, 7, 25),
        "wettest_days": (date(2024, 7, 23), date(2024, 7, 25)),
        "D": 3,
        "flooded_psgc": (
            "1381300003",  # Apolonio Samson
            "1381300010",  # Bagong Silangan
            "1381300013",  # Balingasa
            "1381300028",  # Damayang Lagi
            "1381300029",  # Del Monte
            "1381300031",  # Doña Imelda
            "1381300033",  # Don Manuel
            "1381300035",  # E. Rodriguez
            "1381300041",  # Fairview
            "1381300042",  # N.S. Amoranto (Gintong Silahis)
            "1381300047",  # Kalusugan
            "1381300048",  # Kamuning
            "1381300060",  # Mariana
            "1381300061",  # Mariblo
            "1381300064",  # Masambong
            "1381300065",  # Santo Domingo (Matalahib)
            "1381300068",  # Nagkaisang Nayon
            "1381300070",  # Novaliches Proper
            "1381300076",  # Paltok
            "1381300081",  # Phil-Am
            "1381300085",  # Quirino 2-A
            "1381300090",  # Roxas
            "1381300097",  # San Bartolome
            "1381300116",  # South Triangle
            "1381300118",  # Talayan
            "1381300121",  # Tatalon
        ),
    },
    "floods_2025": {
        "year": 2025,
        "start_date": date(2025, 7, 19),
        "end_date": date(2025, 7, 24),
        "wettest_days": (date(2025, 7, 21), date(2025, 7, 23)),
        "D": 6,
        "flooded_psgc": (
            "1381300003",  # Apolonio Samson
            "1381300010",  # Bagong Silangan
            "1381300022",  # Commonwealth
            "1381300029",  # Del Monte
            "1381300031",  # Doña Imelda
            "1381300041",  # Fairview
            "1381300042",  # N.S. Amoranto (Gintong Silahis)
            "1381300043",  # Gulod
            "1381300055",  # Loyola Heights
            "1381300059",  # Mangga
            "1381300065",  # Santo Domingo (Matalahib)
            "1381300080",  # Pasong Tamo
            "1381300090",  # Roxas
            "1381300104",  # Santa Cruz
            "1381300105",  # Santa Lucia
            "1381300112",  # Sienna
            "1381300120",  # Tandang Sora
            "1381300121",  # Tatalon
        ),
    },
    "habagat_2026": {
        "year": 2026,
        "start_date": date(2026, 8, 8),
        "end_date": date(2026, 8, 11),
        "wettest_days": (date(2026, 8, 8), date(2026, 8, 10)),
        "D": 4,
        "flooded_psgc": (
            "1381300003",  # Apolonio Samson
            "1381300010",  # Bagong Silangan
            "1381300011",  # Bagumbayan
            "1381300012",  # Bahay Toro
            "1381300025",  # Culiat
            "1381300027",  # Damayan
            "1381300028",  # Damayang Lagi
            "1381300029",  # Del Monte
            "1381300031",  # Doña Imelda
            "1381300033",  # Don Manuel
            "1381300035",  # E. Rodriguez
            "1381300042",  # N.S. Amoranto (Gintong Silahis)
            "1381300043",  # Gulod
            "1381300048",  # Kamuning
            "1381300049",  # Katipunan
            "1381300054",  # Lourdes
            "1381300060",  # Mariana
            "1381300062",  # Marilag
            "1381300063",  # Masagana
            "1381300065",  # Santo Domingo (Matalahib)
            "1381300071",  # Obrero
            "1381300073",  # Paang Bundok
            "1381300080",  # Pasong Tamo
            "1381300082",  # Pinyahan
            "1381300084",  # Project 6
            "1381300089",  # Ramon Magsaysay
            "1381300090",  # Roxas
            "1381300102",  # San Roque
            "1381300104",  # Santa Cruz
            "1381300105",  # Santa Lucia
            "1381300112",  # Sienna
            "1381300115",  # Socorro
            "1381300118",  # Talayan
            "1381300119",  # Talipapa
            "1381300120",  # Tandang Sora
            "1381300121",  # Tatalon
            "1381300129",  # Vasra
            "1381300142",  # North Fairview
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
S8_CENSUS_TOLERANCE = 0.001                # S8: each barangay's rescaled pixels within 0.1% of its census total
S10_SHARE_TOLERANCE = 1e-9                 # S10: the three shares add to 1 up to rounding
S11_HIDDEN_COUNT = -999                    # S11: counts a model may not see are overwritten with this (rule 1)

# ---------------------------------------------------------------------------
# Evaluation (D5, D6)
# ---------------------------------------------------------------------------
BOOT_BLOCK_WEEKS = 8                       # assumption
BOOT_BLOCK_WEEKS_TESTS = (4, 13)
BOOT_RESAMPLES = 2000
RANDOM_SEED = 2026
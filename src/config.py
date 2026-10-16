"""Single source of project constants; all date bounds are inclusive.

Keep configuration in this module and use ``config.CONSTANT_NAME`` in each
source module. Paths are anchored to the project, regardless of the working
directory used to launch Python.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLIMATE_DATA_DIR = RAW_DATA_DIR / "climate"
FIRE_DATA_DIR = RAW_DATA_DIR / "fire"
GEOLOGICAL_DATA_DIR = RAW_DATA_DIR / "geological"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CLEAN_DATA_DIR = DATA_DIR / "clean"
CLEAN_MERGED_FILENAME = "merged.nc"

RANDOM_SEED = 42
TRAIN_FRACTION = 0.8
VALIDATION_FRACTION = 0.2

# Geographic grid spacing in degrees; pandas/xarray daily frequency alias.
TARGET_LATITUDE_RESOLUTION_DEGREES = 1.0
TARGET_LONGITUDE_RESOLUTION_DEGREES = 1.0
TARGET_FREQUENCY = "D"

# Fixed user-requested exclusions: the 109 cells missing land cover in the
# original grid. IDs use the configured globally anchored one-degree grid.
EXCLUDED_CELL_IDS = (
    50159, 52653, 52654, 52655, 52656, 52657, 52658, 53011, 53012, 53013,
    53014, 53015, 53016, 53017, 53018, 53368, 53369, 53370, 53371, 53372,
    53373, 53374, 53375, 53376, 53377, 53726, 53727, 53728, 53729, 53730,
    53731, 53732, 53733, 53734, 53735, 53736, 53737, 53752, 54087, 54088,
    54089, 54090, 54091, 54092, 54093, 54094, 54095, 54096, 54097, 54098,
    54113, 54448, 54449, 54450, 54451, 54452, 54453, 54454, 54455, 54456,
    54457, 54458, 54471, 54472, 54810, 54811, 54812, 54813, 54814, 55185,
    55540, 55898, 55899, 55900, 56259, 56260, 56261, 56262, 56263, 56264,
    56620, 57653, 57656, 57658, 57659, 57660, 57661, 57681, 58013, 58036,
    58037, 58048, 58396, 58747, 58750, 58756, 59103, 59117, 59118, 59454,
    59455, 59456, 59828, 60191, 60192, 60193, 60551, 60552, 60553,
)
# Omit these daily historical CSVs; retain source time coordinates and fire reports.
EXCLUDED_HISTORICAL_DATES = ("2025-05-26", "2026-03-17", "2026-04-13", "2026-04-14")

TRAIN_VALIDATION_START_DATE = "2020-09-01"
TRAIN_VALIDATION_END_DATE = "2025-08-31"
TEST_START_DATE = "2025-09-01"
TEST_END_DATE = "2026-08-31"
FORECAST_START_DATE = "2026-09-01"
FORECAST_END_DATE = "2027-08-31"

# ISO dates also support inclusive, whole-day slicing in xarray.
TIME_WINDOWS = {
    "training_validation": (TRAIN_VALIDATION_START_DATE, TRAIN_VALIDATION_END_DATE),
    "testing": (TEST_START_DATE, TEST_END_DATE),
    "forecasting": (FORECAST_START_DATE, FORECAST_END_DATE),
}

CLIMATE_VARIABLES = ("hurs", "pr", "sfcWind", "tas")
SECONDS_PER_DAY = 86_400
KELVIN_TO_CELSIUS_OFFSET = 273.15
METRES_TO_MILLIMETRES = 1_000

# Predictor source paths and field names follow data/raw/README.md.
TARGET_CRS = "EPSG:4326"
ECODISTRICTS_PATH = GEOLOGICAL_DATA_DIR / "National Ecological Framework" / "ecodistricts.shp"
ELEVATION_PATH = ECODISTRICTS_PATH.with_name("dt_elevation.dbf")
ELEVATION_FIELDS = ("MIN_ELEV", "MAX_ELEV", "MEAN_ELEV", "ELEVDIFF")
GEOLOGICAL_RASTERS = {
    "landcover": GEOLOGICAL_DATA_DIR / "2020 Land Cover of Canada" / "landcover-2020-classification.tif",
    "fuel_type": GEOLOGICAL_DATA_DIR / "FBPfueltypes" / "FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif",
}
NETCDF_SOURCE_PATTERNS = {
    "ORRC": "ORRC v1.0_{variable}/{variable}_day_NAM_Ouranos_ORRC_v10_*.nc",
    "CanESM5": "CanESM5_{variable}/{variable}_day_CanESM5_ssp585_r1i1p1f1_gn_*_v2.0.nc",
}
FORECAST_ONLY_SOURCES = ("CanESM5", "CanSIPSv3")
CLIMATE_UNITS = {
    "hurs": "%", "pr": "mm day-1", "sfcWind": "m s-1", "tas": "degC",
    "tdps": "degC", "uas": "m s-1", "vas": "m s-1",
}
CANSIPS_PARAMETERS = {167: "tas", 168: "tdps", 165: "uas", 166: "vas", 228: "pr"}
CANSIPS_MODELS = {4: "CanESM5.1p1bc", 5: "GEM5.2-NEMO"}
CANSIPS_FILE_KINDS = ("6hourly", "total_precipitation")
CANSIPS_SAMPLE_HOURS = 6
CANSIPS_PRECIPITATION_HOURS = 24

# Bound memory use without changing the source or target data resolutions.
PROCESSING_TIME_CHUNK = 32

# CIFFC is the selected fire source; retain IDs and report dates, never status dates.
LARGE_FIRE_THRESHOLD_HA = 1_000
FIRE_OUTPUT_COLUMNS = (
    "fire_id", "latitude", "longitude", "report_date", "size_ha", "is_large_fire",
)
FIRE_SOURCES = {
    "CIFFC": {
        "pattern": "CIFFC/ciffc.csv",
        "header": None,
        "columns": {0: "fire_id", 8: "latitude", 9: "longitude", 2: "report_date", 7: "size_ha"},
    },
}

# Daily historical modelling tables: chronological splitting and eight neighbours.
HISTORICAL_CLIMATE_SOURCE = "ORRC"
MERGE_STATIC_PREDICTORS = {
    "ecodistrict_elevation": ELEVATION_FIELDS,
    "landcover": ("landcover",),
}
FIRE_NEIGHBOUR_OFFSETS = tuple(
    (row, column)
    for row in (-1, 0, 1)
    for column in (-1, 0, 1)
    if (row, column) != (0, 0)
)

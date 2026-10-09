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

RANDOM_SEED = 42
TRAIN_FRACTION = 0.8
VALIDATION_FRACTION = 0.2

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

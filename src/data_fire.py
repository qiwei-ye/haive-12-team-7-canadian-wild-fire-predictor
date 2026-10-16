"""Standardise fire records and flag reported areas at or above the threshold.

Outputs use CIFFC report dates within the configured historical training/testing
period. No grid aggregation, deduplication, or predictor merging is performed.
Records with unknown dates are excluded; unknown locations and areas remain
missing. Indicators are 0/1 for known areas and missing for unknown areas.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .preprocessing import cell_ids


LOGGER = logging.getLogger(__name__)


def standardize_records(records):
    """Keep six fields for report dates within the inclusive historical period."""
    result = records[[name for name in config.FIRE_OUTPUT_COLUMNS if name != "is_large_fire"]].copy()
    result["fire_id"] = result.fire_id.astype("string").str.strip().replace("", pd.NA)
    # Read the ISO date portion without converting time zones or using status dates.
    dates = result.report_date.astype("string").str.strip().str.slice(0, 10)
    valid_dates = dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    valid_dates &= pd.to_datetime(dates, format="%Y-%m-%d", errors="coerce").notna()
    result["report_date"] = dates.where(valid_dates)
    start = config.TIME_WINDOWS["training_validation"][0]
    end = config.TIME_WINDOWS["testing"][1]
    result = result.loc[result.report_date.between(start, end).fillna(False)].copy()
    for name, bounds in (("latitude", (-90, 90)), ("longitude", (-180, 180))):
        values = pd.to_numeric(result[name], errors="coerce").astype("Float64")
        result[name] = values.where(values.between(*bounds))
    areas = pd.to_numeric(result.size_ha, errors="coerce").astype("Float64")
    result["size_ha"] = areas.where(np.isfinite(areas) & areas.ge(0))
    result["is_large_fire"] = result.size_ha.ge(config.LARGE_FIRE_THRESHOLD_HA).astype("Int8")
    located = result.latitude.notna() & result.longitude.notna()
    excluded = pd.Series(False, index=result.index)
    excluded.loc[located] = np.isin(
        cell_ids(result.loc[located, "latitude"].to_numpy(dtype=float),
                 result.loc[located, "longitude"].to_numpy(dtype=float)),
        config.EXCLUDED_CELL_IDS,
    )
    result = result.loc[~excluded]
    return result.loc[:, config.FIRE_OUTPUT_COLUMNS]


def preprocess(output_dir=None):
    """Write one CSV per input under <processed root>/fire; raw files stay intact."""
    root = Path(output_dir) if output_dir is not None else config.PROCESSED_DATA_DIR
    destination = root / "fire"
    if destination.resolve().is_relative_to(config.RAW_DATA_DIR.resolve()):
        raise ValueError("Fire outputs must not be written inside the raw input directory")
    outputs = []
    for source, settings in config.FIRE_SOURCES.items():
        paths = sorted(config.FIRE_DATA_DIR.glob(settings["pattern"]))
        if not paths:
            LOGGER.warning("Missing %s fire inputs: %s", source, config.FIRE_DATA_DIR / settings["pattern"])
            continue
        for path in paths:
            records = pd.read_csv(
                path, header=settings["header"], usecols=list(settings["columns"]),
                dtype="string", keep_default_na=False,
            ).rename(columns=settings["columns"])
            result = standardize_records(records)
            LOGGER.info("%s: kept %s of %s records after cell exclusions and report-date filtering, %s to %s inclusive", path.name,
                        len(result), len(records), config.TIME_WINDOWS["training_validation"][0],
                        config.TIME_WINDOWS["testing"][1])
            for field in ("latitude", "longitude", "report_date", "size_ha"):
                missing = int(result[field].isna().sum())
                if missing:
                    LOGGER.warning("%s: %s missing or invalid %s values retained as blanks", path.name, missing, field)
            destination.mkdir(parents=True, exist_ok=True)
            output = destination / path.name
            temporary = output.with_suffix(".partial.csv")
            try:
                result.to_csv(temporary, index=False, na_rep="", encoding="utf-8")
                temporary.replace(output)
            finally:
                temporary.unlink(missing_ok=True)
            LOGGER.info("Saved %s (%s records; %s fires at least %s ha)", output, len(result),
                        int(result.is_large_fire.eq(1).sum()), config.LARGE_FIRE_THRESHOLD_HA)
            outputs.append(output)
    return outputs

"""Standardise fire records and flag reported areas at or above the threshold.

Outputs use CWFIS dates with matched January 1 placeholders replaced by official
NWT estimated start dates. Repeated national IDs retain their earliest annual
snapshot. Both steps precede historical date filtering, so later carryover reports
cannot create another event or move its date.
No grid aggregation or predictor merging is performed.
Records with unknown dates are excluded; unknown locations and areas remain
missing. Indicators are 0/1 for known areas and missing for unknown areas.
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .preprocessing import cell_ids


LOGGER = logging.getLogger(__name__)


def calendar_dates(values):
    """Validate the supplied calendar portion without timezone conversion."""
    dates = values.astype("string").str.strip().str.slice(0, 10)
    valid = dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    valid &= pd.to_datetime(dates, format="%Y-%m-%d", errors="coerce").notna()
    return dates.where(valid)


def correct_january_1_dates(records):
    """Return records and a log; change only dates supported by exact NWT IDs."""
    result = records.copy()
    dates = calendar_dates(result.report_date)
    january = dates.str.endswith("-01-01", na=False)
    log = result.loc[january, ["fire_id"]].copy()
    log["original_report_date"] = dates.loc[january]
    log["corrected_report_date"] = dates.loc[january]
    log["date_source"] = "CWFIS.situation_report_date"
    log["status"] = "unmatched"
    log["nwt_estimated_start_date"] = pd.Series(pd.NA, index=log.index, dtype="string")
    log["nwt_discovery_date"] = pd.Series(pd.NA, index=log.index, dtype="string")
    log["start_discovery_dates_differ"] = pd.Series(pd.NA, index=log.index, dtype="boolean")
    settings = config.FIRE_DATE_REFERENCE
    prefix = f"{settings['year']}_{settings['agency']}_"
    eligible = january & result.fire_id.str.startswith(prefix, na=False)
    if eligible.any():
        path = config.FIRE_DATA_DIR / settings["relative_path"]
        reference = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
        required = [settings[name] for name in ("id_column", "date_column", "discovery_column",
                                               "latitude_column", "longitude_column")]
        missing = set(required) - set(reference.columns)
        if missing:
            raise ValueError(f"NWT date reference fields are missing: {sorted(missing)}")
        identifiers = reference[settings["id_column"]].astype("string").str.strip()
        if identifiers.isna().any() or identifiers.eq("").any() or identifiers.duplicated().any():
            raise ValueError("Missing or duplicate NWT fire identifiers")
        reference.index = prefix + identifiers
        matched = result.index[eligible & result.fire_id.isin(reference.index)]
        selected = reference.reindex(result.loc[matched, "fire_id"]).set_axis(matched)
        replacement = calendar_dates(selected[settings["date_column"]])
        if replacement.isna().any():
            raise ValueError("Missing or invalid matched NWT estimated start dates")
        tolerance = 0.5 * 10 ** -settings["coordinate_decimal_places"]
        for name in ("latitude", "longitude"):
            original = pd.to_numeric(result.loc[matched, name], errors="coerce").to_numpy(dtype=float)
            proposed = pd.to_numeric(selected[settings[f"{name}_column"]], errors="coerce").to_numpy(dtype=float)
            if not (np.isfinite(original).all() and np.isfinite(proposed).all()
                    and np.all(np.abs(original - proposed) <= tolerance + 1e-8)):
                raise ValueError(f"CWFIS/NWT {name} coordinates disagree for matched January 1 fires")
        discovery = calendar_dates(selected[settings["discovery_column"]])
        result.loc[matched, "report_date"] = replacement
        log.loc[matched, "corrected_report_date"] = replacement
        log.loc[matched, "date_source"] = f"{settings['relative_path']}:{settings['date_column']}"
        log.loc[matched, "status"] = "corrected"
        log.loc[matched, "nwt_estimated_start_date"] = replacement
        log.loc[matched, "nwt_discovery_date"] = discovery
        log.loc[matched, "start_discovery_dates_differ"] = replacement.ne(discovery)
        LOGGER.info("Replaced %s January 1 dates using %s", len(matched), path)
    unmatched = log.loc[log.status.eq("unmatched"), "fire_id"]
    if not unmatched.empty:
        LOGGER.warning("%s January 1 fires have no NWT date match; dates retained: %s",
                       len(unmatched), unmatched.tolist()[:10])
    return result, log


def standardize_records(records):
    """Keep six fields for processed fire dates within the historical period."""
    result = records[[name for name in config.FIRE_OUTPUT_COLUMNS if name != "is_large_fire"]].copy()
    result["fire_id"] = result.fire_id.astype("string").str.strip().replace("", pd.NA)
    # Read the ISO date portion without converting time zones or using status dates.
    result["report_date"] = calendar_dates(result.report_date)
    start = config.FIRE_START_DATE
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
    """Consolidate annual snapshots into one CSV per configured fire source."""
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
        frames = []
        for path in paths:
            records = pd.read_csv(
                path, header=settings["header"], usecols=list(settings["columns"]),
                dtype="string", keep_default_na=False,
            ).rename(columns=settings["columns"])
            records["fire_id"] = records.fire_id.str.strip()
            if records.fire_id.eq("").any() or records.fire_id.isna().any():
                raise ValueError(f"Missing national fire identifiers in {path}")
            if records.fire_id.duplicated().any():
                raise ValueError(f"Duplicate national fire identifiers within {path}")
            frames.append(records)
            LOGGER.info("Read %s: %s records", path.name, len(records))
        records = pd.concat(frames, ignore_index=True)
        # Filenames sort by snapshot year; keep the original snapshot, including
        # its date, location and area, rather than a later carryover/reset record.
        unique = records.drop_duplicates("fire_id", keep="first")
        LOGGER.info("%s: removed %s repeated annual-snapshot records", source, len(records) - len(unique))
        unique, _ = correct_january_1_dates(unique)
        result = standardize_records(unique).sort_values(["report_date", "fire_id"], kind="stable").reset_index(drop=True)
        LOGGER.info("%s: kept %s of %s unique records after cell exclusions and historical date filtering", source,
                    len(result), len(unique))
        for field in ("latitude", "longitude", "report_date", "size_ha"):
            missing = int(result[field].isna().sum())
            if missing:
                LOGGER.warning("%s: %s missing or invalid %s values retained as blanks", source, missing, field)
        destination.mkdir(parents=True, exist_ok=True)
        output = destination / settings["output_filename"]
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

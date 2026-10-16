"""Daily historical predictor/CIFFC tables, with strictly earlier fire history.

Zero labels mean no *reported* large fire, not verified absence of fire. Unknown
reported sizes remain missing unless another known large fire establishes a 1.
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
import xarray as xr

from . import config
from .preprocessing import cell_ids, load_boundary, validate_grid, validate_output


LOGGER = logging.getLogger(__name__)


def partition_dates():
    """Reserve testing; split the earlier window by whole dates, without shuffle."""
    if not (0 < config.TRAIN_FRACTION < 1 and 0 < config.VALIDATION_FRACTION < 1
            and np.isclose(config.TRAIN_FRACTION + config.VALIDATION_FRACTION, 1)):
        raise ValueError("Training and validation fractions must be positive and sum to one")
    dates = pd.date_range(*config.TIME_WINDOWS["training_validation"], freq=config.TARGET_FREQUENCY)
    cut = int(len(dates) * config.TRAIN_FRACTION)
    if not 0 < cut < len(dates):
        raise ValueError("The configured window cannot supply both training and validation dates")
    testing = pd.date_range(*config.TIME_WINDOWS["testing"], freq=config.TARGET_FREQUENCY)
    if testing.empty or dates[-1] >= testing[0]:
        raise ValueError("Testing must follow training/validation without overlapping dates")
    excluded = pd.to_datetime(config.EXCLUDED_HISTORICAL_DATES)
    # Preserve the established split boundaries when excluding individual dates.
    partitions = {"training": dates[:cut], "validation": dates[cut:], "test": testing}
    partitions = {name: days[~days.isin(excluded)] for name, days in partitions.items()}
    if any(days.empty for days in partitions.values()):
        raise ValueError("Date exclusions leave an empty temporal partition")
    return partitions


def connecting_cells(grid):
    """Indices of retained side/corner neighbours; -1 marks absent grid cells."""
    if not np.array_equal(grid.cell.values, cell_ids(grid.lat.values, grid.lon.values)):
        raise ValueError("Grid identifiers do not match the configured grid coordinates")
    width = round(360 / config.TARGET_LONGITUDE_RESOLUTION_DEGREES)
    height = round(180 / config.TARGET_LATITUDE_RESOLUTION_DEGREES)
    positions = {divmod(int(identifier), width): index
                 for index, identifier in enumerate(grid.cell.values)}
    neighbours = np.full((grid.sizes["cell"], len(config.FIRE_NEIGHBOUR_OFFSETS)), -1, dtype=int)
    for (row, column), index in positions.items():
        for offset, (dy, dx) in enumerate(config.FIRE_NEIGHBOUR_OFFSETS):
            candidate = row + dy, column + dx
            if 0 <= candidate[0] < height and 0 <= candidate[1] < width:
                neighbours[index, offset] = positions.get(candidate, -1)
    return neighbours


def assign_fire_cells(records, grid, boundary):
    """Map actual containing cells; return excluded records with explicit reasons."""
    missing = set(config.FIRE_OUTPUT_COLUMNS) - set(records.columns)
    if missing:
        raise ValueError(f"Processed fire fields are missing: {sorted(missing)}")
    records = records.copy().reset_index(drop=True)
    dates = pd.to_datetime(records.report_date, format="%Y-%m-%d", errors="coerce")
    latitude = pd.to_numeric(records.latitude, errors="coerce").to_numpy(dtype=float)
    longitude = pd.to_numeric(records.longitude, errors="coerce").to_numpy(dtype=float)
    indicators = pd.to_numeric(records.is_large_fire.replace("", np.nan), errors="coerce")
    supplied = records.is_large_fire.notna() & records.is_large_fire.astype(str).str.strip().ne("")
    if (supplied & ~indicators.isin([0, 1])).any():
        raise ValueError("Processed is_large_fire must contain only 0, 1, or missing values")
    valid = (np.isfinite(latitude) & np.isfinite(longitude)
             & (np.abs(latitude) <= 90) & (np.abs(longitude) <= 180))
    inside = np.zeros(len(records), dtype=bool)
    inside[valid] = shapely.intersects_xy(boundary, longitude[valid], latitude[valid])
    positions = np.full(len(records), -1, dtype=int)
    positions[valid] = grid.cell.to_index().get_indexer(cell_ids(latitude[valid], longitude[valid]))
    reasons = np.select(
        [dates.isna(), ~dates.between(config.TIME_WINDOWS["training_validation"][0],
                                     config.TIME_WINDOWS["testing"][1]),
         ~valid, ~inside, positions < 0],
        ["invalid_report_date", "outside_historical_window", "missing_or_invalid_coordinates",
         "outside_canadian_boundary", "containing_cell_not_in_retained_grid"],
        default="",
    )
    excluded = records.loc[reasons != ""].copy()
    excluded["exclusion_reason"] = reasons[reasons != ""]
    retained = records.loc[reasons == ""].copy()
    retained["report_date"] = dates[reasons == ""]
    retained["is_large_fire"] = indicators[reasons == ""]
    retained["_cell_index"] = positions[reasons == ""]
    return retained, excluded


def daily_fire_fields(records, dates, neighbours):
    """Use earlier reports, including reports on dates without an output CSV."""
    count = len(neighbours)
    first_report = np.full(count, np.datetime64("NaT"), dtype="datetime64[ns]")
    first = records.groupby("_cell_index").report_date.min()
    first_report[first.index.to_numpy(dtype=int)] = first.to_numpy(dtype="datetime64[ns]")
    reports = dict(tuple(records.groupby("report_date", sort=True)))
    for day in dates:
        seen = first_report < day.to_datetime64()
        connected = (seen[np.maximum(neighbours, 0)] & (neighbours >= 0)).any(axis=1)
        target = np.zeros(count, dtype=np.float32)
        today = reports.get(day)
        if today is not None:
            unknown = today.loc[today.is_large_fire.isna(), "_cell_index"].to_numpy(dtype=int)
            large = today.loc[today.is_large_fire.eq(1), "_cell_index"].to_numpy(dtype=int)
            target[unknown] = np.nan
            target[large] = 1
        yield day, {
            "previous_fire": seen.astype(np.int8),
            "previous_fire_neighbour": connected.astype(np.int8),
            "is_large_fire": target,
        }


def load_predictors(root, grid, split):
    """Load configured historical variables on the exact common grid, without fill."""
    fields = {}
    for variable in config.CLIMATE_VARIABLES:
        path = root / "climate" / config.HISTORICAL_CLIMATE_SOURCE / split / f"{variable}.nc"
        with xr.open_dataset(path) as dataset:
            validate_output(dataset, grid, source=config.HISTORICAL_CLIMATE_SOURCE, split=split)
            if dataset.attrs.get("source", config.HISTORICAL_CLIMATE_SOURCE) != config.HISTORICAL_CLIMATE_SOURCE:
                raise ValueError(f"Unexpected historical climate source: {path}")
            if variable not in dataset or set(dataset[variable].dims) != {"time", "cell"}:
                raise ValueError(f"Expected daily {variable}(time, cell) in {path}")
            if dataset[variable].attrs.get("units") != config.CLIMATE_UNITS[variable]:
                raise ValueError(f"Unexpected {variable} units in {path}")
            if not pd.DatetimeIndex(dataset.time.values).equals(pd.DatetimeIndex(dataset.time.values).normalize()):
                raise ValueError(f"Daily times must be midnight dates in {path}")
            fields[variable] = dataset[variable].transpose("time", "cell").load()
    # Exact merging catches inconsistent dates instead of silently shifting rows.
    dataset = xr.merge([field.to_dataset(name=name) for name, field in fields.items()],
                       join="exact", compat="no_conflicts")
    dates = pd.date_range(*config.TIME_WINDOWS[split], freq=config.TARGET_FREQUENCY)
    if not pd.DatetimeIndex(dataset.time.values).equals(dates):
        LOGGER.warning("%s: unavailable predictor dates will remain missing", split)
    return dataset.reindex(time=dates)


def merge(processed_dir=None, output_dir=None, boundary_path=None):
    """Write one all-cell CSV per historical day, keeping original inputs intact."""
    root = Path(processed_dir) if processed_dir is not None else config.PROCESSED_DATA_DIR
    destination = Path(output_dir) if output_dir is not None else config.CLEAN_DATA_DIR
    if (destination.resolve().is_relative_to(config.RAW_DATA_DIR.resolve())
            or destination.resolve().is_relative_to(root.resolve())):
        raise ValueError("Clean outputs must be separate from raw and processed input directories")
    if config.HISTORICAL_CLIMATE_SOURCE in config.FORECAST_ONLY_SOURCES:
        raise ValueError("Forecast-only climate sources cannot be merged as historical predictors")
    partitions = partition_dates()
    required = [root / "grid.nc"]
    for split in ("training_validation", "testing"):
        required.extend(root / "climate" / config.HISTORICAL_CLIMATE_SOURCE / split / f"{variable}.nc"
                        for variable in config.CLIMATE_VARIABLES)
    required.extend(root / "static" / source / "predictors.nc" for source in config.MERGE_STATIC_PREDICTORS)
    fire_paths = [root / "fire" / Path(settings["pattern"]).name for settings in config.FIRE_SOURCES.values()]
    required.extend(fire_paths)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required processed inputs are missing:\n" + "\n".join(missing))
    with xr.open_dataset(root / "grid.nc") as dataset:
        grid = dataset.load()
    boundary = load_boundary(boundary_path)
    validate_grid(grid, boundary)
    base = pd.DataFrame({"cell": grid.cell.values, "lat": grid.lat.values, "lon": grid.lon.values})
    units = {"lat": "degrees_north", "lon": "degrees_east"}
    for source, variables in config.MERGE_STATIC_PREDICTORS.items():
        path = root / "static" / source / "predictors.nc"
        with xr.open_dataset(path) as dataset:
            validate_output(dataset, grid, static=True)
            for variable in variables:
                if variable not in dataset or dataset[variable].dims != ("cell",):
                    raise ValueError(f"Expected static {variable}(cell) in {path}")
                values = dataset[variable].values
                if variable == "landcover":
                    finite = np.isfinite(values)
                    if not np.equal(values[finite], np.rint(values[finite])).all():
                        raise ValueError("Land cover must retain integer category codes")
                    base[variable] = pd.array(values, dtype="Int64")
                else:
                    base[variable] = values
                units[variable] = dataset[variable].attrs.get("units", "unspecified")
    climate = {split: load_predictors(root, grid, split) for split in ("training_validation", "testing")}
    units.update({name: config.CLIMATE_UNITS[name] for name in config.CLIMATE_VARIABLES})
    records = pd.concat([pd.read_csv(path, dtype={"fire_id": "string"}, keep_default_na=False)
                         for path in fire_paths], ignore_index=True)
    fires, excluded = assign_fire_cells(records, grid, boundary)
    if len(excluded):
        LOGGER.warning("Excluded %s fire records: %s", len(excluded), excluded.exclusion_reason.value_counts().to_dict())
    LOGGER.warning("CIFFC reporting is incomplete: zero means no reported large fire, not verified absence. "
                   "Unknown reported sizes remain missing; history uses available reports only.")
    all_dates = partitions["training"].append(partitions["validation"]).append(partitions["test"])
    membership = {day: name for name, dates in partitions.items() for day in dates}
    neighbours = connecting_cells(grid)
    # Remove only the explicitly excluded CSV dates, including stale prior runs.
    for date in config.EXCLUDED_HISTORICAL_DATES:
        filename = f"{pd.Timestamp(date).date().isoformat()}.csv"
        for name in partitions:
            (destination / name / filename).unlink(missing_ok=True)
    outputs = []
    counts = {name: {"positive_targets": 0, "missing_targets": 0} for name in partitions}
    for day, fire_fields in daily_fire_fields(fires, all_dates, neighbours):
        partition = membership[day]
        split = "testing" if partition == "test" else "training_validation"
        daily = base.copy()
        daily.insert(0, "date", day.date().isoformat())
        for variable in config.CLIMATE_VARIABLES:
            daily[variable] = climate[split][variable].sel(time=day).values
        for name, values in fire_fields.items():
            daily[name] = pd.array(values, dtype="Int8")
        counts[partition]["positive_targets"] += int(daily.is_large_fire.eq(1).sum())
        counts[partition]["missing_targets"] += int(daily.is_large_fire.isna().sum())
        path = destination / partition / f"{day.date().isoformat()}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".partial.csv")
        try:
            daily.to_csv(temporary, index=False, na_rep="", encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        outputs.append(path)
        if len(outputs) % 365 == 0:
            LOGGER.info("Saved %s daily tables", len(outputs))
    summary = {
        "spatial_cells_per_day": grid.sizes["cell"],
        "spatial_resolution_degrees": [config.TARGET_LATITUDE_RESOLUTION_DEGREES,
                                       config.TARGET_LONGITUDE_RESOLUTION_DEGREES],
        "crs": config.TARGET_CRS,
        "frequency": config.TARGET_FREQUENCY,
        "split_method": "chronological whole dates; floor(days * TRAIN_FRACTION) for training",
        "excluded_cell_ids": list(config.EXCLUDED_CELL_IDS),
        "excluded_historical_dates": list(config.EXCLUDED_HISTORICAL_DATES),
        "date_exclusion_rule": "Original chronological split boundaries are preserved; only excluded CSV dates are omitted",
        "partitions": {name: {"start": dates[0].date().isoformat(), "end": dates[-1].date().isoformat(),
                              "days": len(dates), "rows": len(dates) * grid.sizes["cell"], **counts[name]}
                       for name, dates in partitions.items()},
        "climate_source": config.HISTORICAL_CLIMATE_SOURCE,
        "fire_sources": list(config.FIRE_SOURCES),
        "fire_reporting_date_range": [None if records.empty else str(records.report_date.min()),
                                      None if records.empty else str(records.report_date.max())],
        "retained_fire_records": len(fires),
        "excluded_fire_records": json.loads(excluded.to_json(orient="records")),
        "columns": list(daily.columns),
        "units": units,
        "definitions": {
            "previous_fire": "1 if any available fire report in this cell strictly precedes the row date; otherwise 0",
            "previous_fire_neighbour": "1 if any available earlier report is in a retained connecting cell; otherwise 0",
            "neighbour_offsets": config.FIRE_NEIGHBOUR_OFFSETS,
            "is_large_fire": f"1 if any reported fire in this cell on this report date is >= {config.LARGE_FIRE_THRESHOLD_HA} ha; "
                             "missing if no known large fire but a reported size is unknown; otherwise 0 (no reported large fire)",
            "missing_values": "Empty CSV fields remain unknown; predictors are not imputed",
            "fire_history_coverage": "Available CIFFC reports only; missing historical reporting does not establish absence",
            "omitted_date_history": "Fire reports on omitted CSV dates still contribute to strictly later fire-history indicators",
            "cell_assignment": "Containing regular grid cell; outside-boundary or unretained-cell records excluded, never relocated",
        },
    }
    (destination / "merge_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Saved %s daily tables (%s rows) under %s", len(outputs), len(outputs) * grid.sizes["cell"], destination)
    return outputs

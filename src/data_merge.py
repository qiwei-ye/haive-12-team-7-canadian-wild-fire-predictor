"""Daily historical predictor/fire tables, with strictly earlier fire history.

Zero labels mean no *reported* large fire, not verified absence of fire. Missing
cleaned indicators use 0; a known large fire in the cell/day still establishes 1.
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


def _clean_target_definitions():
    return {
        "is_large_fire": f"1 if any reported fire in this cell on this processed fire date is >= {config.LARGE_FIRE_THRESHOLD_HA} ha; "
                         "otherwise 0, including missing indicators and unknown reported fire sizes",
        "missing_values": "Missing is_large_fire indicators are replaced with 0; historical tas uses the configured centered mean fill before weather features; other missing predictor values remain unknown",
        "fire_date": config.FIRE_DATE_DEFINITION,
    }


def feature_definitions():
    window = (f"[{config.FIRE_HISTORY_YEARS + config.FIRE_HISTORY_LAG_YEARS} calendar years before the row date, "
              f"{config.FIRE_HISTORY_LAG_YEARS} calendar year(s) before the row date)")
    result = {
        "tas": config.TAS_FILL_DEFINITION,
        "previous_large_fire": f"1 if a known large fire occurred in this cell in {window}; otherwise 0",
        "previous_large_fire_neighbour": f"1 if a known large fire occurred in a retained surrounding cell in {window}; otherwise 0",
        "previous_small_fire_neighbour": f"1 if a known non-large fire occurred in a retained surrounding cell in {window}; otherwise 0; unknown sizes do not count",
    }
    for name, settings in config.ROLLING_WEATHER_FEATURES.items():
        result[name] = (f"{settings['aggregation']} of {settings['variable']} over {settings['days']} consecutive calendar days "
                        "ending on and including the row date; missing if any required observation is unavailable")
    return result


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
        [dates.isna(), ~dates.between(config.FIRE_START_DATE,
                                     config.TIME_WINDOWS["testing"][1]),
         ~valid, ~inside, positions < 0],
        ["invalid_report_date", "outside_fire_processing_window", "missing_or_invalid_coordinates",
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


def fire_history_bounds(day):
    """Inclusive/exclusive calendar bounds for the configured lagged history."""
    day = pd.Timestamp(day)
    return (day - pd.DateOffset(years=config.FIRE_HISTORY_LAG_YEARS + config.FIRE_HISTORY_YEARS),
            day - pd.DateOffset(years=config.FIRE_HISTORY_LAG_YEARS))


def daily_fire_fields(records, dates, neighbours):
    """Use known-size reports in the configured lagged two-year history window."""
    count = len(neighbours)
    dates = pd.DatetimeIndex(dates)
    if dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("Fire history dates must be unique and increasing")
    if config.FIRE_HISTORY_YEARS <= 0 or config.FIRE_HISTORY_LAG_YEARS < 0:
        raise ValueError("Fire history duration must be positive and its lag nonnegative")
    history = records.loc[records.is_large_fire.notna()].sort_values("report_date", kind="stable")
    event_dates = history.report_date.to_numpy(dtype="datetime64[ns]")
    cells = history._cell_index.to_numpy(dtype=int)
    large = history.is_large_fire.to_numpy(dtype=np.int8)
    large_counts = np.zeros(count, dtype=np.int64)
    small_counts = np.zeros_like(large_counts)
    left = right = 0
    reports = dict(tuple(records.groupby("report_date", sort=True)))
    for day in dates:
        window_start, window_end = fire_history_bounds(day)
        end = int(np.searchsorted(event_dates, window_end.to_datetime64(), side="left"))
        start = int(np.searchsorted(event_dates, window_start.to_datetime64(), side="left"))
        np.add.at(large_counts, cells[right:end], large[right:end])
        np.add.at(small_counts, cells[right:end], 1 - large[right:end])
        np.add.at(large_counts, cells[left:start], -large[left:start])
        np.add.at(small_counts, cells[left:start], -(1 - large[left:start]))
        left, right = start, end
        seen_large, seen_small = large_counts > 0, small_counts > 0
        connected_large = (seen_large[np.maximum(neighbours, 0)] & (neighbours >= 0)).any(axis=1)
        connected_small = (seen_small[np.maximum(neighbours, 0)] & (neighbours >= 0)).any(axis=1)
        target = np.zeros(count, dtype=np.float32)
        today = reports.get(day)
        if today is not None:
            large_today = today.loc[today.is_large_fire.eq(1), "_cell_index"].to_numpy(dtype=int)
            target[large_today] = 1
        yield day, {
            "previous_large_fire": seen_large.astype(np.int8),
            "previous_large_fire_neighbour": connected_large.astype(np.int8),
            "previous_small_fire_neighbour": connected_small.astype(np.int8),
            "is_large_fire": target,
        }


def rolling_weather_features(climate):
    """Calculate complete daily windows before output-date exclusions or splitting."""
    fields = {}
    for name, settings in config.ROLLING_WEATHER_FEATURES.items():
        rolling = climate[settings["variable"]].astype("float64").rolling(
            time=settings["days"], min_periods=settings["days"])
        fields[name] = getattr(rolling, settings["aggregation"])()
        fields[name].attrs = {"units": settings["units"], "description": feature_definitions()[name]}
    return xr.Dataset(fields)


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


def merge_csvs_to_netcdf(output_dir=None):
    """Combine existing CSVs, with partition(time), preserving values and gaps.

    Static columns must agree across CSVs and are stored once per cell.
    Continuous values use float64 to preserve the precision read from CSVs.
    Missing target indicators are replaced with 0 in both CSVs and NetCDF.
    """
    directory = Path(output_dir) if output_dir is not None else config.CLEAN_DATA_DIR
    if any(directory.resolve().is_relative_to(path.resolve())
           for path in (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR)):
        raise ValueError("Merged NetCDF must be separate from raw and processed inputs")
    summary_path = directory / "merge_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Clean CSV metadata is missing: {summary_path}; run the merge stage first")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["definitions"].update(_clean_target_definitions())
    partitions = partition_dates()
    entries = [(day, name, directory / name / f"{day.date().isoformat()}.csv")
               for name, days in partitions.items() for day in days]
    expected_paths = {path for _, _, path in entries}
    actual_paths = {path for name in partitions for path in (directory / name).glob("*.csv")}
    missing, extra = expected_paths - actual_paths, actual_paths - expected_paths
    if missing:
        raise FileNotFoundError(f"{len(missing)} daily CSVs are missing; examples: {sorted(map(str, missing))[:5]}")
    if extra:
        raise ValueError(f"Unexpected CSV dates outside configured partitions: {sorted(map(str, extra))[:5]}")
    columns = summary["columns"]
    static_names = [name for names in config.MERGE_STATIC_PREDICTORS.values() for name in names]
    binary_names = (*config.FIRE_HISTORY_VARIABLES, "is_large_fire")
    dynamic_names = [name for name in columns if name not in ("date", "cell", "lat", "lon", *static_names)]
    if set(columns) != {"date", "cell", "lat", "lon", *static_names, *config.CLIMATE_VARIABLES,
                        *config.ROLLING_WEATHER_FEATURES, *binary_names}:
        raise ValueError("Clean CSV metadata does not match the configured predictor schema")
    target_counts = {name: {"positive_targets": 0, "missing_targets": 0} for name in partitions}
    for index, (day, partition, path) in enumerate(entries):
        frame = pd.read_csv(path, keep_default_na=False, na_values=[""], float_precision="round_trip")
        if list(frame.columns) != columns or not frame.date.eq(day.date().isoformat()).all():
            raise ValueError(f"Inconsistent columns or row dates in {path}")
        if frame.cell.isna().any() or frame.cell.duplicated().any():
            raise ValueError(f"Missing or duplicate cell identifiers in {path}")
        missing_target = frame.is_large_fire.isna()
        if missing_target.any():
            # Preserve other fields' original text when updating legacy CSVs.
            text = pd.read_csv(path, dtype="string", keep_default_na=False)
            text.loc[missing_target, "is_large_fire"] = "0"
            temporary_csv = path.with_suffix(".partial.csv")
            try:
                text.to_csv(temporary_csv, index=False, encoding="utf-8")
                temporary_csv.replace(path)
            finally:
                temporary_csv.unlink(missing_ok=True)
            frame["is_large_fire"] = frame.is_large_fire.fillna(0)
            LOGGER.info("%s: replaced %s missing large-fire indicators with 0", path, int(missing_target.sum()))
        target_counts[partition]["positive_targets"] += int(frame.is_large_fire.eq(1).sum())
        frame = frame.set_index("cell").sort_index()
        if index == 0:
            cells = frame.index.to_numpy()
            if len(cells) != summary["spatial_cells_per_day"] or np.isin(cells, config.EXCLUDED_CELL_IDS).any():
                raise ValueError("Clean CSV cells do not match the retained grid")
            latitude, longitude = frame.lat.to_numpy(), frame.lon.to_numpy()
            if not (np.isfinite(latitude).all() and np.isfinite(longitude).all()
                    and np.array_equal(cells, cell_ids(latitude, longitude))):
                raise ValueError("Clean CSV coordinates do not match their grid identifiers")
            static = {name: frame[name].to_numpy(dtype=np.float64) for name in static_names}
            dynamic = {name: np.empty((len(entries), len(cells)), dtype=np.float64) for name in dynamic_names}
        if not (np.array_equal(frame.index.to_numpy(), cells)
                and np.array_equal(frame.lat.to_numpy(), latitude)
                and np.array_equal(frame.lon.to_numpy(), longitude)):
            raise ValueError(f"CSV spatial grid differs from the common grid: {path}")
        for name in static_names:
            if not np.array_equal(frame[name].to_numpy(dtype=np.float64), static[name], equal_nan=True):
                raise ValueError(f"Static predictor {name} changes between CSVs: {path}")
        for name in dynamic_names:
            values = frame[name].to_numpy(dtype=np.float64)
            if name in binary_names and not np.isin(values[~np.isnan(values)], [0, 1]).all():
                raise ValueError(f"Non-binary {name} values in {path}")
            dynamic[name][index] = values
        if (index + 1) % 365 == 0:
            LOGGER.info("Combined %s daily CSVs", index + 1)
    landcover = static["landcover"]
    finite = landcover[~np.isnan(landcover)]
    if not (np.equal(finite, np.rint(finite)).all()
            and ((finite >= 0) & (finite <= np.iinfo(np.int16).max)).all()):
        raise ValueError("Land cover must contain integer category codes or missing values")
    dynamic["is_large_fire"] = dynamic["is_large_fire"].astype(np.int8)
    dataset = xr.Dataset(
        {**{name: ("cell", values) for name, values in static.items()},
         **{name: (("time", "cell"), values) for name, values in dynamic.items()},
         "partition": ("time", np.asarray([name for _, name, _ in entries], dtype=str))},
        coords={"time": pd.DatetimeIndex([day for day, _, _ in entries]), "cell": cells,
                "lat": ("cell", latitude), "lon": ("cell", longitude)},
        attrs={"crs": config.TARGET_CRS, "source_csv_count": len(entries),
               "source_csv_layout": "<partition>/YYYY-MM-DD.csv", "source_columns": json.dumps(columns),
               "latitude_resolution_degrees": config.TARGET_LATITUDE_RESOLUTION_DEGREES,
               "longitude_resolution_degrees": config.TARGET_LONGITUDE_RESOLUTION_DEGREES,
               "time_sampling": "Daily observations; configured excluded dates are omitted",
               "excluded_historical_dates": ",".join(config.EXCLUDED_HISTORICAL_DATES),
               "excluded_cell_ids": ",".join(map(str, config.EXCLUDED_CELL_IDS)),
               "target_definition": summary["definitions"]["is_large_fire"],
               "fire_history_coverage": summary["definitions"]["fire_history_coverage"],
               "fire_sources": ",".join(summary["fire_sources"]),
               "fire_date_definition": summary["definitions"]["fire_date"],
               "tas_fill_definition": config.TAS_FILL_DEFINITION},
    )
    dataset.time.attrs = {"standard_name": "time", "long_name": "Daily CSV date"}
    dataset.lat.attrs = {"standard_name": "latitude", "units": summary["units"]["lat"]}
    dataset.lon.attrs = {"standard_name": "longitude", "units": summary["units"]["lon"]}
    dataset.partition.attrs = {"long_name": "Temporal partition inherited from the CSV folder",
                               "labels": ",".join(partitions), "applies_to": "Every cell at this time"}
    for name in (*static_names, *dynamic_names):
        dataset[name].attrs["units"] = summary["units"].get(name, "1")
        if name in summary["definitions"]:
            dataset[name].attrs["description"] = summary["definitions"][name]
    dataset.landcover.attrs["variable_type"] = "categorical"
    encoding = {name: {"zlib": True, "complevel": 4} for name in (*static_names, *dynamic_names)}
    for name in binary_names:
        encoding[name].update(dtype="int8", _FillValue=np.int8(-1))
    encoding["is_large_fire"]["_FillValue"] = None
    encoding["landcover"].update(dtype="int16", _FillValue=np.int16(-32768))
    encoding["time"] = {"dtype": "int32", "units": f"days since {config.TRAIN_VALIDATION_START_DATE}",
                        "calendar": "proleptic_gregorian"}
    path = directory / config.CLEAN_MERGED_FILENAME
    temporary = path.with_suffix(".partial.nc")
    try:
        dataset.to_netcdf(temporary, engine="netcdf4", encoding=encoding)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    summary["merged_netcdf"] = {"file": path.name, "dimensions": dict(dataset.sizes),
                                "partition_variable": "partition", "partition_labels": list(partitions),
                                "static_variables": static_names, "csv_date_coordinate": "time"}
    for name, counts in target_counts.items():
        summary["partitions"][name].update(counts)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Saved %s (%s dates by %s cells)", path, len(entries), len(cells))
    return path


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
    for split in ("history", "training_validation", "testing"):
        required.extend(root / "climate" / config.HISTORICAL_CLIMATE_SOURCE / split / f"{variable}.nc"
                        for variable in config.CLIMATE_VARIABLES)
    required.extend(root / "static" / source / "predictors.nc" for source in config.MERGE_STATIC_PREDICTORS)
    fire_paths = [root / "fire" / settings["output_filename"] for settings in config.FIRE_SOURCES.values()]
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
    climate_parts = [load_predictors(root, grid, split) for split in ("history", "training_validation", "testing")]
    climate = xr.concat(climate_parts, dim="time", join="exact").sortby("time")
    if climate.indexes["time"].has_duplicates:
        raise ValueError("Historical predictor windows overlap")
    climate = climate.reindex(time=pd.date_range(config.TIME_WINDOWS["history"][0],
                                                config.TIME_WINDOWS["testing"][1], freq=config.TARGET_FREQUENCY))
    weather = rolling_weather_features(climate)
    units.update({name: config.CLIMATE_UNITS[name] for name in config.CLIMATE_VARIABLES})
    units.update({name: settings["units"] for name, settings in config.ROLLING_WEATHER_FEATURES.items()})
    records = pd.concat([pd.read_csv(path, dtype={"fire_id": "string"}, keep_default_na=False)
                         for path in fire_paths], ignore_index=True)
    fires, excluded = assign_fire_cells(records, grid, boundary)
    if len(excluded):
        LOGGER.warning("Excluded %s fire records: %s", len(excluded), excluded.exclusion_reason.value_counts().to_dict())
    source_names = ", ".join(config.FIRE_SOURCES)
    LOGGER.warning("%s coverage can be incomplete: zero means no reported large fire, not verified absence. "
                   "Missing cleaned large-fire indicators use 0; history uses available reports only.", source_names)
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
        daily = base.copy()
        daily.insert(0, "date", day.date().isoformat())
        for variable in config.CLIMATE_VARIABLES:
            daily[variable] = climate[variable].sel(time=day).values
        for name in config.ROLLING_WEATHER_FEATURES:
            daily[name] = weather[name].sel(time=day).values
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
            **feature_definitions(),
            "neighbour_offsets": config.FIRE_NEIGHBOUR_OFFSETS,
            **_clean_target_definitions(),
            "fire_history_coverage": f"Available {source_names} reports from {config.FIRE_START_DATE}; missing historical reporting does not establish absence",
            "omitted_date_history": "Fire reports on omitted CSV dates still contribute when they fall inside a later row's lagged history window",
            "cell_assignment": "Containing regular grid cell; outside-boundary or unretained-cell records excluded, never relocated",
        },
    }
    (destination / "merge_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    merge_csvs_to_netcdf(destination)
    LOGGER.info("Saved %s daily tables (%s rows) under %s", len(outputs), len(outputs) * grid.sizes["cell"], destination)
    return outputs

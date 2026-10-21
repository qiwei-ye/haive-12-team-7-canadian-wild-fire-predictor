"""Daily Canadian predictors from ORRC, CanESM5 and CanSIPSv3."""

from contextlib import ExitStack
from datetime import datetime
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from . import config
from .preprocessing import mean_weights, normalize_longitudes, save_dataset, spatial_mean, spatial_sums


LOGGER = logging.getLogger(__name__)


def source_splits(source):
    """Never allow model projections/forecasts into historical partitions."""
    return ("forecasting",) if source in config.FORECAST_ONLY_SOURCES else tuple(
        name for name in config.TIME_WINDOWS if name != "forecasting"
    )


def convert_units(array, variable):
    """Convert documented input units, rejecting unrecognised units."""
    units = str(array.attrs.get("units", "")).strip()
    attrs = dict(array.attrs)
    if variable in ("tas", "tdps"):
        if units == "K":
            array = array - config.KELVIN_TO_CELSIUS_OFFSET
        elif units not in ("degC", "degree_Celsius", "degrees_Celsius"):
            raise ValueError(f"Unsupported {variable} units: {units!r}")
    elif variable == "pr":
        if units in ("kg m-2 s-1", "kg m**-2 s**-1"):
            array = array * config.SECONDS_PER_DAY
        elif units == "m":
            array = array * config.METRES_TO_MILLIMETRES
        elif units != config.CLIMATE_UNITS[variable]:
            raise ValueError(f"Unsupported precipitation units: {units!r}")
        attrs["standard_name"] = "lwe_precipitation_rate"
    elif variable in ("sfcWind", "uas", "vas") and units in ("m s-1", "m s**-1"):
        pass
    elif units != config.CLIMATE_UNITS[variable]:
        raise ValueError(f"Unsupported {variable} units: {units!r}")
    attrs.pop("grid_mapping", None)
    attrs.pop("_FillValue", None)
    attrs["units"] = config.CLIMATE_UNITS[variable]
    array.attrs = attrs
    return array


def daily_partitions(array, source):
    """Normalise date labels, retain gaps as NaN, and apply inclusive windows."""
    # Conversion retains calendar dates, not day offsets. No interpolation of Feb 29.
    if isinstance(array.indexes["time"], xr.CFTimeIndex):
        array = array.convert_calendar("proleptic_gregorian", use_cftime=False)
    array = array.sortby("time")
    if array.indexes["time"].has_duplicates:
        raise ValueError(f"Duplicate observations in {source}; refusing to average duplicate records")
    for split in source_splits(source):
        start, end = config.TIME_WINDOWS[split]
        selected = array.sel(time=slice(start, end))
        if selected.sizes["time"]:
            daily = selected.resample(time=config.TARGET_FREQUENCY).mean(keep_attrs=True)
            yield split, daily


def tiled_spatial_mean(array, spatial_dims, weights, grid):
    """Read each ORRC native tile once, even when it contains years of times."""
    array = array.transpose("time", *spatial_dims)
    total = np.zeros((array.sizes["time"], grid.sizes["cell"]), dtype=np.float64)
    count = np.zeros_like(total)
    rows = np.cumsum((0,) + array.data.chunks[array.get_axis_num(spatial_dims[0])])
    columns = np.cumsum((0,) + array.data.chunks[array.get_axis_num(spatial_dims[1])])
    width = array.sizes[spatial_dims[1]]
    for row_start, row_end in zip(rows[:-1], rows[1:]):
        for column_start, column_end in zip(columns[:-1], columns[1:]):
            source_indices = (np.arange(row_start, row_end)[:, None] * width
                              + np.arange(column_start, column_end)).ravel()
            tile_weights = weights[:, source_indices]
            target_indices = np.flatnonzero(tile_weights.getnnz(axis=1))
            if not target_indices.size:
                continue
            tile = array.isel({spatial_dims[0]: slice(row_start, row_end),
                               spatial_dims[1]: slice(column_start, column_end)}).compute(scheduler="synchronous")
            values = tile.values.reshape(array.sizes["time"], -1)
            tile_total, tile_count = spatial_sums(values, tile_weights[target_indices])
            total[:, target_indices] += tile_total
            count[:, target_indices] += tile_count
    result = np.full(total.shape, np.nan, dtype=np.float32)
    np.divide(total, count, out=result, where=count > 0)
    return xr.DataArray(result, dims=("time", "cell"),
                        coords={"time": array.time, **grid.coords}, attrs=array.attrs, name=array.name)


def regrid_netcdf(array, grid, boundary):
    """Mean of source grid centres in each target cell, using actual lat/lon."""
    if array.lat.ndim == array.lon.ndim == 1:
        array = array.assign_coords(lon=normalize_longitudes(array.lon.values)).sortby("lon").sortby("lat")
        dx = config.TARGET_LONGITUDE_RESOLUTION_DEGREES / 2
        dy = config.TARGET_LATITUDE_RESOLUTION_DEGREES / 2
        array = array.sel(
            lon=slice(float(grid.lon.min()) - dx, float(grid.lon.max()) + dx),
            lat=slice(float(grid.lat.min()) - dy, float(grid.lat.max()) + dy),
        )
        longitude, latitude = np.meshgrid(array.lon.values, array.lat.values)
        spatial_dims = (array.lat.dims[0], array.lon.dims[0])
    else:
        latitude, longitude = array.lat.values, array.lon.values
        spatial_dims = array.lat.dims
        if array.lon.dims != spatial_dims or len(spatial_dims) != 2:
            raise ValueError("Expected matching two-dimensional geographic coordinates")
    weights = mean_weights(latitude, longitude, grid, boundary)
    if weights.shape[1] == 0:
        raise ValueError("No source coordinates overlap the target grid extent")
    # Geographic coordinates have served their purpose; do not reread them per tile.
    array = array.reset_coords(drop=True)

    def aggregate(values):
        return spatial_mean(values.reshape(values.shape[:-2] + (-1,)), weights)

    if array.chunks is not None and max(array.data.chunks[array.get_axis_num("time")]) > config.PROCESSING_TIME_CHUNK:
        result = tiled_spatial_mean(array, spatial_dims, weights, grid)
    else:
        array = array.chunk({"time": config.PROCESSING_TIME_CHUNK, **{dimension: -1 for dimension in spatial_dims}})
        result = xr.apply_ufunc(
            aggregate, array, input_core_dims=[list(spatial_dims)], output_core_dims=[["cell"]],
            exclude_dims=set(spatial_dims), dask="parallelized", output_dtypes=[np.float32],
            dask_gufunc_kwargs={"output_sizes": {"cell": grid.sizes["cell"]}}, keep_attrs=True,
        )
    result = result.assign_coords(grid.coords)
    result.attrs["spatial_aggregation"] = "mean of valid Canadian source grid centres within each cell"
    return result


def process_netcdf_source(source, grid, boundary, output_dir=None, splits=None):
    output_dir = Path(output_dir) if output_dir is not None else config.PROCESSED_DATA_DIR
    outputs = []
    splits = source_splits(source) if splits is None else tuple(splits)
    if not splits or not set(splits).issubset(source_splits(source)):
        raise ValueError(f"Invalid {source} processing splits: {splits}")
    windows = [config.TIME_WINDOWS[name] for name in splits]
    first, last = min(window[0] for window in windows), max(window[1] for window in windows)
    for variable in config.CLIMATE_VARIABLES:
        pattern = config.NETCDF_SOURCE_PATTERNS[source].format(variable=variable)
        paths = sorted(config.CLIMATE_DATA_DIR.glob(pattern))
        if not paths:
            LOGGER.warning("Missing %s %s inputs: %s", source, variable, config.CLIMATE_DATA_DIR / pattern)
            continue
        with ExitStack() as stack:
            pieces = []
            for path in paths:
                LOGGER.info("Reading %s", path.name)
                dataset = stack.enter_context(xr.open_dataset(path, engine="netcdf4", chunks={}))
                if variable not in dataset:
                    LOGGER.warning("Variable %s missing in %s", variable, path)
                    continue
                field = dataset[variable]
                # Some CF files expose 2-D latitude/longitude as data variables.
                field = field.assign_coords(lat=dataset.lat, lon=dataset.lon)
                field = field.sel(time=slice(first, last))
                if field.sizes["time"]:
                    pieces.append(regrid_netcdf(convert_units(field, variable), grid, boundary))
            if not pieces:
                LOGGER.warning("No %s %s observations in configured windows", source, variable)
                continue
            combined = xr.concat(pieces, dim="time", coords="minimal", compat="equals")
            for split, daily in daily_partitions(combined, source):
                if split not in splits:
                    continue
                daily.attrs["source_cell_methods"] = daily.attrs.get("cell_methods", "")
                daily.attrs["cell_methods"] = "area: mean time: mean"
                dataset = daily.to_dataset(name=variable)
                dataset.attrs["input_files"] = "; ".join(path.name for path in paths)
                if source == "CanESM5":
                    dataset.attrs.update(model="CanESM5", ensemble_member="r1i1p1f1", scenario="ssp585")
                path = output_dir / "climate" / source / split / f"{variable}.nc"
                outputs.append(save_dataset(dataset, path, grid, source, split))
    return outputs


def iter_grib_records(path):
    """Stream GRIB messages without creating cfgrib indexes beside raw files."""
    import eccodes as ec

    with Path(path).open("rb") as stream:
        while (message := ec.codes_grib_new_from_file(stream)) is not None:
            try:
                parameter = int(ec.codes_get(message, "paramId"))
                if parameter not in config.CANSIPS_PARAMETERS:
                    LOGGER.warning("Skipping undocumented GRIB parameter %s in %s", parameter, path)
                    continue
                values = ec.codes_get_values(message)
                if ec.codes_get(message, "numberOfMissing"):
                    values[values == ec.codes_get(message, "missingValue")] = np.nan
                reference = datetime.strptime(
                    f'{ec.codes_get(message, "dataDate"):08d}{ec.codes_get(message, "dataTime"):04d}',
                    "%Y%m%d%H%M",
                )
                yield {
                    "parameter": parameter,
                    "reference": reference,
                    "step": pd.to_timedelta(ec.codes_get(message, "endStep"), unit="h"),
                    "model": int(ec.codes_get(message, "systemNumber")),
                    "member": int(ec.codes_get(message, "perturbationNumber")),
                    "units": ec.codes_get(message, "units"),
                    "latitude": ec.codes_get_array(message, "latitudes"),
                    "longitude": ec.codes_get_array(message, "longitudes"),
                    "values": values,
                }
            finally:
                ec.codes_release(message)


def daily_cansips(records, grid, boundary):
    """Process each model/initialisation/member separately, preserving uncertainty."""
    # Entries are source samples, not statistical ensemble averages.
    groups = {}
    weights = None
    coordinates = None
    for record in records:
        key = (record["model"], pd.Timestamp(record["reference"]), record["member"])
        variable = config.CANSIPS_PARAMETERS[record["parameter"]]
        group = groups.setdefault(key, {})
        samples = group.setdefault(variable, {})
        step = pd.Timedelta(record["step"])
        if step in samples:
            raise ValueError(f"Duplicate CanSIPS message for {key}, {variable}, {step}")
        current = (np.asarray(record["latitude"]), normalize_longitudes(record["longitude"]))
        if coordinates is None:
            coordinates = current
            weights = mean_weights(*current, grid, boundary)
        elif not all(np.array_equal(old, new) for old, new in zip(coordinates, current)):
            raise ValueError("CanSIPS messages use inconsistent spatial grids")
        array = xr.DataArray(np.asarray(record["values"], dtype=np.float32), dims="point", attrs={"units": record["units"]})
        # Keep precipitation on the native grid until after deaccumulation.
        samples[step] = convert_units(array, variable).values

    by_model = {}
    offset = pd.tseries.frequencies.to_offset(config.TARGET_FREQUENCY)
    period = pd.Timedelta(offset.nanos, unit="ns")
    sample_interval = pd.Timedelta(hours=config.CANSIPS_SAMPLE_HOURS)
    precipitation_interval = pd.Timedelta(hours=config.CANSIPS_PRECIPITATION_HOURS)
    if period % sample_interval or period < precipitation_interval:
        raise ValueError("Target frequency is incompatible with the documented CanSIPS sampling")
    expected_samples = period // sample_interval
    for (model, reference, member), variables in sorted(groups.items()):
        fields = {}
        # Wind speed must be derived at each subdaily instant before its daily mean.
        if "uas" in variables and "vas" in variables:
            variables["sfcWind"] = {
                step: np.hypot(u, variables["vas"][step])
                for step, u in variables["uas"].items() if step in variables["vas"]
            }
        for variable, samples in variables.items():
            days = {}
            previous_step = pd.Timedelta(0)
            previous = None
            for step, values in sorted(samples.items()):
                if step <= pd.Timedelta(0):
                    if variable == "pr":
                        previous_step, previous = step, values
                    continue
                valid_time = reference + step
                # A midnight endpoint belongs to the preceding (0,24h] forecast day.
                day = (valid_time - pd.Timedelta(1, unit="ns")).floor(config.TARGET_FREQUENCY)
                if variable == "pr":
                    if step - previous_step == precipitation_interval:
                        increment = values if previous is None else values - previous
                        increment = np.where(increment >= 0, increment, np.nan)
                    else:
                        increment = np.full_like(values, np.nan)
                    previous_step, previous = step, values
                    start = valid_time - precipitation_interval
                    if start < day or valid_time > day + period:
                        raise ValueError("Precipitation accumulation does not fit the target time bin")
                    result = spatial_mean(increment, weights)
                else:
                    result = spatial_mean(values, weights)
                days.setdefault(day, []).append(result)
            if not days:
                continue
            times = sorted(days)
            daily = []
            required = period // precipitation_interval if variable == "pr" else expected_samples
            for day in times:
                samples_for_day = np.stack(days[day])
                # An incomplete day stays missing, including per-cell missing samples.
                complete = np.isfinite(samples_for_day).sum(axis=0) == required
                total = np.nansum(samples_for_day, axis=0)
                value = total if variable == "pr" else total / required
                daily.append(np.where(complete, value, np.nan))
            field = xr.DataArray(np.asarray(daily, dtype=np.float32), dims=("time", "cell"),
                                 coords={"time": times, **grid.coords}, name=variable)
            field.attrs = {"units": config.CLIMATE_UNITS[variable], "cell_methods": "time: sum" if variable == "pr" else "time: mean"}
            for split, selected in daily_partitions(field, "CanSIPSv3"):
                fields[variable] = selected
        if not fields:
            continue
        dataset = xr.Dataset(fields).expand_dims(member=[member])
        dataset = dataset.assign_coords(forecast_reference_time=reference)
        by_model.setdefault((model, reference), []).append(dataset)
    for (model, reference), members in sorted(by_model.items()):
        name = config.CANSIPS_MODELS.get(model, f"system{model}")
        dataset = xr.concat(members, dim="member", join="outer").expand_dims(model=[name])
        # Different fields/members may have different coverage. Gaps remain NaN.
        dataset = dataset.reindex(time=pd.date_range(dataset.time.values.min(), dataset.time.values.max(), freq=config.TARGET_FREQUENCY))
        dataset = dataset.assign_coords(lead_time=dataset.time - reference.to_datetime64())
        dataset.attrs.update(system_number=model, precipitation="difference of consecutive 24-hour cumulative totals; labelled by interval start",
                             subdaily_aggregation="complete right-closed daily intervals; no ensemble averaging")
        yield model, reference, dataset


def process_cansips(grid, boundary, output_dir=None):
    output_dir = Path(output_dir) if output_dir is not None else config.PROCESSED_DATA_DIR
    paths = sorted((config.CLIMATE_DATA_DIR / "CanSIPSv3").glob("*.grib"))
    if not paths:
        LOGGER.warning("CanSIPSv3 GRIB inputs missing: %s", config.CLIMATE_DATA_DIR / "CanSIPSv3")
        return []
    outputs = []
    # Process one documented system at a time to bound GRIB message memory.
    for system in config.CANSIPS_MODELS:
        model_paths = [path for path in paths if f"_system{system}_" in path.name]
        if not model_paths:
            LOGGER.warning("Missing CanSIPSv3 inputs for system %s", system)
            continue
        for kind in config.CANSIPS_FILE_KINDS:
            if not any(path.name.endswith(f"_{kind}.grib") for path in model_paths):
                LOGGER.warning("Missing CanSIPSv3 %s input for system %s", kind, system)
        def records():
            for path in model_paths:
                LOGGER.info("Reading %s", path.name)
                yield from iter_grib_records(path)
        for model, reference, dataset in daily_cansips(records(), grid, boundary):
            dataset.attrs["input_files"] = "; ".join(path.name for path in model_paths)
            name = config.CANSIPS_MODELS.get(model, f"system{model}")
            path = output_dir / "climate" / "CanSIPSv3" / "forecasting" / f"{name}_{reference:%Y%m%d}.nc"
            outputs.append(save_dataset(dataset, path, grid, "CanSIPSv3", "forecasting"))
    return outputs


def preprocess(grid, boundary, output_dir=None):
    outputs = []
    for source in config.NETCDF_SOURCE_PATTERNS:
        outputs.extend(process_netcdf_source(source, grid, boundary, output_dir))
    outputs.extend(process_cansips(grid, boundary, output_dir))
    return outputs

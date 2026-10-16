"""Shared Canadian grid, spatial means, and predictor output checks."""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyogrio.errors import DataSourceError
from scipy.sparse import csr_matrix
import shapely
import xarray as xr

from . import config


LOGGER = logging.getLogger(__name__)


def load_boundary(path=None):
    """Dissolve the local Canadian polygons; never substitute a bounding box."""
    path = Path(path) if path is not None else config.ECODISTRICTS_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Canadian boundary polygons missing: {path}")
    try:
        polygons = gpd.read_file(path)
    except (DataSourceError, OSError) as error:
        # Broken shapefile sidecars must be reported as unavailable boundaries.
        raise ValueError(f"Cannot read Canadian boundary polygons: {path}: {error}") from error
    if polygons.crs is None:
        raise ValueError(f"Boundary CRS is missing: {path}")
    polygons = polygons.to_crs(config.TARGET_CRS)
    geometry = shapely.union_all(shapely.make_valid(polygons.geometry.array))
    if geometry.is_empty or geometry.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("Canadian boundary must contain nonempty polygon geometry")
    shapely.prepare(geometry)
    return geometry


def normalize_longitudes(values):
    return (np.asarray(values) + 180) % 360 - 180


def cell_ids(latitude, longitude):
    """Globally stable IDs, with grid edges anchored at -90 and -180 degrees."""
    dy = config.TARGET_LATITUDE_RESOLUTION_DEGREES
    dx = config.TARGET_LONGITUDE_RESOLUTION_DEGREES
    if dy <= 0 or dx <= 0 or not np.isclose(180 / dy, round(180 / dy)) or not np.isclose(360 / dx, round(360 / dx)):
        raise ValueError("Target spacing must be positive and divide 180/360 degrees")
    row = np.floor((np.asarray(latitude) + 90) / dy).astype(np.int64)
    column = np.floor((normalize_longitudes(longitude) + 180) / dx).astype(np.int64)
    return row * round(360 / dx) + column


def create_grid(boundary):
    """Keep only centres in Canada; all sources use these exact cell coordinates."""
    dx = config.TARGET_LONGITUDE_RESOLUTION_DEGREES
    dy = config.TARGET_LATITUDE_RESOLUTION_DEGREES
    west, south, east, north = boundary.bounds
    lon = np.arange(np.floor((west + 180) / dx) * dx - 180 + dx / 2, east, dx)
    lat = np.arange(np.floor((south + 90) / dy) * dy - 90 + dy / 2, north, dy)
    longitude, latitude = np.meshgrid(lon, lat)
    keep = shapely.intersects_xy(boundary, longitude, latitude)
    keep &= ~np.isin(cell_ids(latitude, longitude), config.EXCLUDED_CELL_IDS)
    if not keep.any():
        raise ValueError("No grid centres fall within the supplied Canadian boundary")
    latitude, longitude = latitude[keep], longitude[keep]
    grid = xr.Dataset(coords={
        "cell": cell_ids(latitude, longitude),
        "lat": ("cell", latitude),
        "lon": ("cell", longitude),
    })
    grid.lat.attrs = {"standard_name": "latitude", "units": "degrees_north"}
    grid.lon.attrs = {"standard_name": "longitude", "units": "degrees_east"}
    grid.attrs = {
        "crs": config.TARGET_CRS,
        "latitude_resolution_degrees": dy,
        "longitude_resolution_degrees": dx,
        "boundary_rule": "cell centre intersects Canadian ecodistrict polygons",
        "spatial_support": "regular grid cells; only Canadian centres are retained",
        "excluded_cell_ids": ",".join(map(str, config.EXCLUDED_CELL_IDS)),
    }
    validate_grid(grid, boundary)
    return grid


def validate_grid(grid, boundary):
    if np.isin(grid.cell.values, config.EXCLUDED_CELL_IDS).any():
        raise ValueError("Grid contains a configured excluded cell")
    if not np.all(shapely.intersects_xy(boundary, grid.lon.values, grid.lat.values)):
        raise ValueError("A retained grid centre is outside Canada")
    for name, spacing, origin in (
        ("lat", config.TARGET_LATITUDE_RESOLUTION_DEGREES, -90),
        ("lon", config.TARGET_LONGITUDE_RESOLUTION_DEGREES, -180),
    ):
        indices = (grid[name].values - origin) / spacing - 0.5
        if not np.allclose(indices, np.round(indices)):
            raise ValueError(f"{name} coordinates are not aligned to the target grid")
    if len(np.unique(grid.cell.values)) != grid.sizes["cell"]:
        raise ValueError("Duplicate target grid cells")


def grid_cells(grid, boundary):
    """Actual Canadian portions of cells, for polygon attribute aggregation."""
    dx = config.TARGET_LONGITUDE_RESOLUTION_DEGREES / 2
    dy = config.TARGET_LATITUDE_RESOLUTION_DEGREES / 2
    boxes = shapely.box(grid.lon.values - dx, grid.lat.values - dy,
                        grid.lon.values + dx, grid.lat.values + dy)
    return gpd.GeoDataFrame(
        {"cell": grid.cell.values},
        geometry=shapely.intersection(boxes, boundary), crs=config.TARGET_CRS,
    )


def mean_weights(latitude, longitude, grid, boundary):
    """Membership matrix for means of valid source centres inside Canada."""
    latitude = np.asarray(latitude)
    longitude = normalize_longitudes(longitude)
    if latitude.shape != longitude.shape:
        raise ValueError("Latitude and longitude arrays must have the same shape")
    latitude, longitude = latitude.ravel(), longitude.ravel()
    finite = np.isfinite(latitude) & np.isfinite(longitude)
    columns = np.flatnonzero(finite)
    columns = columns[shapely.intersects_xy(boundary, longitude[columns], latitude[columns])]
    ids = cell_ids(latitude[columns], longitude[columns])
    rows = np.searchsorted(grid.cell.values, ids)
    valid = rows < grid.sizes["cell"]
    valid[valid] &= grid.cell.values[rows[valid]] == ids[valid]
    return csr_matrix((np.ones(valid.sum()), (rows[valid], columns[valid])),
                      shape=(grid.sizes["cell"], latitude.size))


def spatial_sums(values, weights):
    """Sums and valid counts can be accumulated across native spatial tiles."""
    values = np.asarray(values)
    flat = values.reshape(-1, weights.shape[1])
    valid = np.isfinite(flat)
    total = weights.dot(np.where(valid, flat, 0).T).T
    count = weights.dot(valid.astype(np.float32).T).T
    shape = values.shape[:-1] + (weights.shape[0],)
    return total.reshape(shape), count.reshape(shape)


def spatial_mean(values, weights):
    """Ignore missing contributors, while leaving an entirely missing cell NaN."""
    total, count = spatial_sums(values, weights)
    result = np.full(total.shape, np.nan, dtype=np.float32)
    np.divide(total, count, out=result, where=count > 0)
    return result


def validate_output(dataset, grid, source=None, split=None, static=False):
    for name in ("cell", "lat", "lon"):
        if name not in dataset.coords or not np.array_equal(dataset[name].values, grid[name].values):
            raise ValueError(f"Output {name} coordinates differ from the common grid")
    if static:
        if "time" in dataset.dims:
            raise ValueError("Static predictors must not have a time dimension")
        return
    if source in config.FORECAST_ONLY_SOURCES and split != "forecasting":
        raise ValueError(f"{source} is forecast-only")
    if source not in config.FORECAST_ONLY_SOURCES and split == "forecasting":
        raise ValueError(f"Historical source {source} cannot enter the forecast split")
    times = pd.DatetimeIndex(dataset.time.values)
    if times.empty or times.has_duplicates or not times.is_monotonic_increasing:
        raise ValueError("Output dates must be nonempty, unique, and increasing")
    start, end = config.TIME_WINDOWS[split]
    if times.min() < pd.Timestamp(start) or times.max() >= pd.Timestamp(end) + pd.Timedelta(days=1):
        raise ValueError(f"Dates fall outside the {split} window")
    expected = pd.date_range(times.min(), times.max(), freq=config.TARGET_FREQUENCY)
    if not times.equals(expected):
        raise ValueError("Output dates do not follow the configured target frequency")


def save_dataset(dataset, path, grid, source=None, split=None, static=False, encoding=None):
    validate_output(dataset, grid, source, split, static)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = dataset.copy()
    dataset.attrs.update(grid.attrs)
    if source:
        dataset.attrs["source"] = source
    if split:
        dataset.attrs["temporal_split"] = split
        start, end = config.TIME_WINDOWS[split]
        available_start = pd.Timestamp(dataset.time.values[0]).date().isoformat()
        available_end = pd.Timestamp(dataset.time.values[-1]).date().isoformat()
        if available_start != start or available_end != end:
            LOGGER.warning("%s %s coverage is %s to %s; configured window is %s to %s. Unavailable dates are not extrapolated.",
                           source, split, available_start, available_end, start, end)
    options = {name: {"zlib": True, "complevel": 4} for name in dataset.data_vars}
    for name, settings in (encoding or {}).items():
        options.setdefault(name, {}).update(settings)
    temporary = path.with_suffix(".partial.nc")
    try:
        # Single-threaded reads avoid HDF5/netCDF library thread-safety problems.
        import dask
        with dask.config.set(scheduler="synchronous"):
            dataset.to_netcdf(temporary, engine="netcdf4", encoding=options)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    LOGGER.info("Saved %s", path)
    return path

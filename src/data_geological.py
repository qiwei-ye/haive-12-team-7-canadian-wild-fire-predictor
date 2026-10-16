"""Static Canadian categorical rasters and ecodistrict elevation attributes."""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import CRS
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject
import shapely
import xarray as xr

from . import config
from .preprocessing import grid_cells, save_dataset


LOGGER = logging.getLogger(__name__)


def categorical_raster(path, variable, grid):
    """Reproject native classes using mode, excluding the source nodata code."""
    dx = config.TARGET_LONGITUDE_RESOLUTION_DEGREES
    dy = config.TARGET_LATITUDE_RESOLUTION_DEGREES
    west, north = float(grid.lon.min()) - dx / 2, float(grid.lat.max()) + dy / 2
    width = round((float(grid.lon.max()) - float(grid.lon.min())) / dx) + 1
    height = round((float(grid.lat.max()) - float(grid.lat.min())) / dy) + 1
    transform = from_origin(west, north, dx, dy)
    with rasterio.open(path) as source:
        if source.crs is None:
            raise ValueError(f"Missing raster CRS: {path}")
        nodata, dtype = source.nodata, source.dtypes[0]
        # Native integer classes use GDAL's histogram mode kernel. NaN working
        # buffers would force its much slower general floating-point mode kernel.
        destination_nodata = nodata if nodata is not None else np.nan
        destination = np.full((height, width), destination_nodata,
                              dtype=dtype if nodata is not None else "float32")
        LOGGER.info("Aggregating %s with categorical mode; native pixels are read in bounded blocks", path)
        # Passing a band, rather than source.read(), keeps national rasters off the Python heap.
        reproject(
            source=rasterio.band(source, 1), destination=destination,
            src_crs=source.crs, src_transform=source.transform, src_nodata=source.nodata,
            dst_crs=config.TARGET_CRS, dst_transform=transform, dst_nodata=destination_nodata,
            resampling=Resampling.mode,
        )
        boxes = shapely.box(grid.lon.values - dx / 2, grid.lat.values - dy / 2,
                            grid.lon.values + dx / 2, grid.lat.values + dy / 2)
        native_cells = gpd.GeoSeries(boxes, crs=config.TARGET_CRS).to_crs(source.crs)
        overlap = shapely.area(shapely.intersection(native_cells.array, shapely.box(*source.bounds))) > 0
    rows = np.rint((north - grid.lat.values) / dy - 0.5).astype(int)
    columns = np.rint((grid.lon.values - west) / dx - 0.5).astype(int)
    # GDAL mode can include an edge pixel for cells merely touching the footprint.
    values = destination[rows, columns].astype(np.float32)
    valid = overlap & (values != destination_nodata)
    values = np.where(valid, values, np.nan)
    field = xr.DataArray(values, dims="cell", coords=grid.coords, name=variable)
    field.attrs = {"units": "1", "spatial_aggregation": "mode of valid source classes", "source_file": str(path)}
    encoding = {variable: {"dtype": dtype}}
    if nodata is not None:
        encoding[variable]["_FillValue"] = nodata
    else:
        # A float encoding retains missing output cells if the source has no nodata code.
        encoding[variable]["dtype"] = "float32"
    return field.to_dataset(), encoding


def elevation_predictors(polygons, attributes, grid, boundary):
    """Join by district, then average each attribute over Canadian cell overlap."""
    if polygons.crs is None:
        raise ValueError("Ecodistrict polygons have no CRS")
    required = {"DISTRICT", *config.ELEVATION_FIELDS}
    if not required.issubset(attributes.columns) or "ECODISTRIC" not in polygons:
        raise ValueError("Ecodistrict/elevation join fields are missing")
    joined = polygons.to_crs(config.TARGET_CRS).merge(
        attributes[["DISTRICT", *config.ELEVATION_FIELDS]],
        left_on="ECODISTRIC", right_on="DISTRICT", how="left", validate="many_to_one",
    )
    cells = grid_cells(grid, boundary)
    geod = CRS.from_user_input(config.TARGET_CRS).get_geod()
    output = {name: np.full(grid.sizes["cell"], np.nan, dtype=np.float32)
              for name in ("ECODISTRIC", *config.ELEVATION_FIELDS)}
    for index, cell in enumerate(cells.geometry):
        candidates = joined.iloc[joined.sindex.query(cell, predicate="intersects")]
        weights, records = [], []
        for _, row in candidates.iterrows():
            overlap = shapely.intersection(shapely.make_valid(row.geometry), cell)
            if overlap.is_empty or overlap.area == 0:
                continue
            area = abs(geod.geometry_area_perimeter(shapely.orient_polygons(overlap))[0])
            if area > 0:
                weights.append(area)
                records.append(row)
        if not records:
            continue
        weights = np.asarray(weights)
        for name in config.ELEVATION_FIELDS:
            values = np.asarray([row[name] for row in records], dtype=float)
            valid = np.isfinite(values)
            if valid.any():
                output[name][index] = np.average(values[valid], weights=weights[valid])
        # District identifiers are categories: choose the greatest total overlap.
        areas = {}
        for row, area in zip(records, weights):
            identifier = row.ECODISTRIC
            if np.isfinite(identifier):
                areas[identifier] = areas.get(identifier, 0) + area
        if areas:
            output["ECODISTRIC"][index] = min(areas, key=lambda identifier: (-areas[identifier], identifier))
    dataset = xr.Dataset({name: ("cell", values) for name, values in output.items()}, coords=grid.coords)
    for name in config.ELEVATION_FIELDS:
        dataset[name].attrs = {"units": "m", "spatial_aggregation": "area-weighted mean of source district attributes"}
    dataset.ECODISTRIC.attrs = {"units": "1", "spatial_aggregation": "mode by district overlap area"}
    dataset.attrs["elevation_support"] = "ecodistrict summary attributes; no sub-district terrain inferred"
    return dataset


def preprocess(grid, boundary, output_dir=None):
    output_dir = Path(output_dir) if output_dir is not None else config.PROCESSED_DATA_DIR
    outputs = []
    for variable, path in config.GEOLOGICAL_RASTERS.items():
        if not path.is_file():
            LOGGER.warning("Missing %s raster: %s", variable, path)
            continue
        dataset, encoding = categorical_raster(path, variable, grid)
        outputs.append(save_dataset(dataset, output_dir / "static" / variable / "predictors.nc",
                                    grid, source=variable, static=True, encoding=encoding))
    missing = [path for path in (config.ECODISTRICTS_PATH, config.ELEVATION_PATH) if not path.is_file()]
    if missing:
        for path in missing:
            LOGGER.warning("Missing elevation input: %s", path)
    else:
        polygons = gpd.read_file(config.ECODISTRICTS_PATH)
        attributes = gpd.read_file(config.ELEVATION_PATH)
        dataset = elevation_predictors(polygons, attributes, grid, boundary)
        dataset.attrs["input_files"] = f"{config.ECODISTRICTS_PATH.name}; {config.ELEVATION_PATH.name}"
        outputs.append(save_dataset(dataset, output_dir / "static" / "ecodistrict_elevation" / "predictors.nc",
                                    grid, source="National Ecological Framework", static=True))
    # PDF references and shapefile sidecars are not independent predictor datasets.
    return outputs

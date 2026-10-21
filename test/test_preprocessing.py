"""Small synthetic predictor checks; no national raw datasets are required."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
import shapely
from shapely.geometry import box
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, data_climate, data_geological
from src.preprocessing import (
    create_grid, grid_cells, load_boundary, mean_weights, normalize_longitudes,
    save_dataset, spatial_mean, validate_grid, validate_output,
)


class GridFixture(unittest.TestCase):
    def setUp(self):
        self.boundary = box(-100, 50, -98, 52)
        self.grid = create_grid(self.boundary)


class SpatialTests(GridFixture):
    def test_configured_cells_are_excluded_from_every_new_grid(self):
        with patch.object(config, "EXCLUDED_CELL_IDS", (int(self.grid.cell.values[0]),)):
            filtered = create_grid(self.boundary)
            self.assertEqual(filtered.sizes["cell"], 3)
            self.assertNotIn(self.grid.cell.values[0], filtered.cell.values)
            with self.assertRaisesRegex(ValueError, "excluded cell"):
                validate_grid(self.grid, self.boundary)

    def test_grid_excludes_holes_and_clips_coastal_support(self):
        boundary = self.boundary.difference(box(-99.75, 50.25, -99.25, 50.75))
        grid = create_grid(boundary)
        self.assertEqual(grid.sizes["cell"], 3)
        validate_grid(grid, boundary)
        cells = grid_cells(grid, boundary)
        self.assertTrue(all(boundary.covers(cell) for cell in cells.geometry))
        for name, resolution in (("lat", config.TARGET_LATITUDE_RESOLUTION_DEGREES),
                                 ("lon", config.TARGET_LONGITUDE_RESOLUTION_DEGREES)):
            np.testing.assert_allclose(np.diff(np.unique(grid[name])), resolution)
        with self.assertRaisesRegex(ValueError, "outside Canada"):
            validate_grid(self.grid, boundary)

    def test_spatial_means_longitude_conventions_and_missing_values(self):
        latitude = np.array([50.2, 50.8, 50.5, 50.5, 49.9])
        longitude = np.array([260.2, 260.8, 261.2, 261.8, 260.5])
        weights = mean_weights(latitude, longitude, self.grid, self.boundary)
        values = np.array([[2, 4, np.nan, np.nan, 100], [2, np.nan, 8, 10, 100]])
        actual = spatial_mean(values, weights)
        np.testing.assert_allclose(actual[:, 0], [3, 2])
        np.testing.assert_allclose(actual[:, 1], [np.nan, 9], equal_nan=True)
        self.assertTrue(np.isnan(actual[:, 2:]).all())
        np.testing.assert_allclose(normalize_longitudes(longitude), longitude - 360)

    def test_boundary_reprojection_and_missing_boundary(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "canada.gpkg"
            gpd.GeoDataFrame(geometry=[self.boundary], crs=config.TARGET_CRS).to_crs("EPSG:3978").to_file(path)
            actual = load_boundary(path)
            np.testing.assert_allclose(actual.bounds, self.boundary.bounds, atol=1e-6)
            with self.assertRaises(FileNotFoundError):
                load_boundary(Path(directory) / "absent.shp")

    def test_misaligned_output_is_rejected(self):
        bad = self.grid.assign_coords(lon=self.grid.lon + 0.1)
        with self.assertRaisesRegex(ValueError, "coordinates differ"):
            validate_output(bad, self.grid, static=True)


class ClimateTests(GridFixture):
    def test_historical_and_forecast_partitioning_and_gaps(self):
        dates = ["2020-08-31", "2020-09-01", "2025-08-31", "2025-09-01", "2026-08-31", "2026-09-01", "2027-08-31", "2027-09-01"]
        array = xr.DataArray(np.arange(len(dates), dtype=float), dims="time", coords={"time": pd.to_datetime(dates) + pd.Timedelta(hours=12)})
        historical = dict(data_climate.daily_partitions(array, "ORRC"))
        forecast = dict(data_climate.daily_partitions(array, "CanESM5"))
        self.assertEqual(set(historical), {"history", "training_validation", "testing"})
        self.assertEqual(str(historical["history"].time.values[-1])[:10], config.TIME_WINDOWS["history"][1])
        self.assertEqual(set(forecast), {"forecasting"})
        self.assertEqual(str(historical["training_validation"].time.values[0])[:10], config.TRAIN_VALIDATION_START_DATE)
        self.assertEqual(str(historical["testing"].time.values[-1])[:10], config.TEST_END_DATE)
        self.assertFalse(set(historical["training_validation"].time.values) & set(historical["testing"].time.values))
        self.assertTrue(np.isnan(historical["testing"].sel(time="2025-09-02")))
        for source, splits in (("ORRC", historical), ("CanESM5", forecast)):
            for split, daily in splits.items():
                dataset = daily.expand_dims(cell=self.grid.cell).to_dataset(name="tas").assign_coords(self.grid.coords)
                validate_output(dataset, self.grid, source=source, split=split)
        with self.assertRaisesRegex(ValueError, "forecast-only"):
            validate_output(self.grid, self.grid, source="CanSIPSv3", split="testing")

    def test_noleap_calendar_keeps_dates_without_inventing_leap_day(self):
        times = xr.date_range("2024-02-28", periods=2, calendar="noleap", use_cftime=True)
        field = xr.DataArray([1.0, 3.0], dims="time", coords={"time": times})
        daily = dict(data_climate.daily_partitions(field, "ORRC"))["training_validation"]
        self.assertEqual(daily.sizes["time"], 3)
        self.assertTrue(np.isnan(daily.sel(time="2024-02-29")))
        self.assertEqual(float(daily.sel(time="2024-03-01")), 3)

    def test_rotated_coordinates_use_geographic_latitude_longitude(self):
        array = xr.DataArray(
            [[[2.0, 4.0], [np.nan, np.nan]]], dims=("time", "rlat", "rlon"),
            coords={"time": pd.to_datetime(["2025-09-01"]), "rlat": [0, 0.09], "rlon": [0, 0.09],
                    "lat": (("rlat", "rlon"), [[50.2, 50.8], [51.2, 51.8]]),
                    "lon": (("rlat", "rlon"), [[-99.8, -99.2], [-98.8, -98.2]])},
        )
        actual = data_climate.regrid_netcdf(array, self.grid, self.boundary).compute()
        self.assertEqual(float(actual.isel(time=0, cell=0)), 3)
        self.assertTrue(np.isnan(actual.isel(time=0, cell=3)))

    def test_unit_conversions_preserve_missing_values_and_reject_unknown_units(self):
        for variable, units, value, expected in (
            ("tas", "K", 283.15, 10), ("pr", "kg m-2 s-1", 1 / config.SECONDS_PER_DAY, 1),
            ("pr", "m", 0.001, 1), ("uas", "m s**-1", 3, 3),
        ):
            with self.subTest(variable=variable, units=units):
                actual = data_climate.convert_units(xr.DataArray([value, np.nan], attrs={"units": units}), variable)
                np.testing.assert_allclose(actual, [expected, np.nan], atol=1e-4, equal_nan=True)
                self.assertEqual(actual.attrs["units"], config.CLIMATE_UNITS[variable])
        with self.assertRaises(ValueError):
            data_climate.convert_units(xr.DataArray([10], attrs={"units": "unknown"}), "tas")

    def test_native_spatial_tiles_match_the_lazy_mean_with_missing_contributors(self):
        count = config.PROCESSING_TIME_CHUNK + 1
        values = np.repeat(np.array([[[2, 4, np.nan, 8], [np.nan, 6, 10, np.nan]]], dtype=float), count, axis=0)
        field = xr.DataArray(
            values, dims=("time", "lat", "lon"),
            coords={"time": pd.date_range(config.TEST_START_DATE, periods=count),
                    "lat": [50.2, 50.8], "lon": [-99.8, -99.2, -98.8, -98.2]},
        )
        expected = data_climate.regrid_netcdf(field, self.grid, self.boundary).compute()
        tiled = field.chunk({"time": -1, "lat": 1, "lon": 2})
        actual = data_climate.regrid_netcdf(tiled, self.grid, self.boundary)
        xr.testing.assert_allclose(actual, expected)

    def test_netcdf_processing_output_and_missing_inputs(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "raw" / "ORRC v1.0_tas"
            folder.mkdir(parents=True)
            source = folder / "tas_day_NAM_Ouranos_ORRC_v10_fixture.nc"
            dataset = xr.Dataset({"tas": (("time", "lat", "lon"), np.full((2, 2, 2), 283.15))},
                                 coords={"time": pd.to_datetime([config.TRAIN_VALIDATION_END_DATE, config.TEST_START_DATE]),
                                         "lat": [50.5, 51.5], "lon": [260.5, 261.5]})
            dataset.tas.attrs["units"] = "K"
            dataset.to_netcdf(source)
            original = source.read_bytes()
            with patch.object(config, "CLIMATE_DATA_DIR", root / "raw"), self.assertLogs(level="WARNING"):
                outputs = data_climate.process_netcdf_source("ORRC", self.grid, self.boundary, root / "processed")
            self.assertEqual(len(outputs), 2)
            for path in outputs:
                with xr.open_dataset(path) as actual:
                    validate_output(actual, self.grid, "ORRC", path.parent.name)
                    np.testing.assert_allclose(actual.tas, 10, atol=1e-4)
            self.assertEqual(original, source.read_bytes())

    def record(self, parameter, step, value, member=0, model=4, reference=None):
        return {"parameter": parameter, "step": pd.Timedelta(hours=step), "values": np.full(4, value),
                "member": member, "model": model, "reference": pd.Timestamp(reference or config.FORECAST_START_DATE),
                "units": "m" if parameter == 228 else ("m s**-1" if parameter in (165, 166) else "K"),
                "latitude": self.grid.lat.values, "longitude": self.grid.lon.values}

    def test_cansips_leads_precipitation_models_members_and_wind(self):
        records = []
        for model in (4, 5):
            for member in (0, 1):
                for step in (6, 12, 18, 24, 30, 36, 42, 48):
                    records.extend([self.record(167, step, 283.15 + member, member, model),
                                    self.record(165, step, 3 if step % 12 else -3, member, model),
                                    self.record(166, step, 4, member, model)])
                records.extend([self.record(228, 24, 0.001, member, model), self.record(228, 48, 0.003, member, model)])
        outputs = list(data_climate.daily_cansips(iter(records), self.grid, self.boundary))
        self.assertEqual([model for model, _, _ in outputs], [4, 5])
        for model, reference, actual in outputs:
            self.assertEqual(actual.model.item(), config.CANSIPS_MODELS[model])
            np.testing.assert_array_equal(actual.member, [0, 1])
            np.testing.assert_allclose(actual.pr.isel(time=0), 1)
            np.testing.assert_allclose(actual.pr.isel(time=1), 2)
            np.testing.assert_allclose(actual.sfcWind, 5)
            np.testing.assert_allclose(actual.uas, 0)
            self.assertEqual(str(actual.time.values[0])[:10], config.FORECAST_START_DATE)
            self.assertEqual(actual.lead_time.values[0], np.timedelta64(0, "ns"))
            self.assertNotIn("hurs", actual)
            validate_output(actual, self.grid, "CanSIPSv3", "forecasting")

    def test_cansips_incomplete_days_missing_accumulations_and_resets(self):
        records = [self.record(167, step, 280) for step in (6, 12, 18)]
        records.extend([self.record(228, 48, 0.005), self.record(228, 72, np.nan),
                        self.record(228, 96, 0.010), self.record(228, 120, 0.009)])
        actual = list(data_climate.daily_cansips(records, self.grid, self.boundary))[0][2]
        self.assertTrue(np.isnan(actual.tas).all())
        self.assertTrue(np.isnan(actual.pr).all())

    def test_missing_cansips_precipitation_is_reported_without_fabricating_it(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "CanSIPSv3"
            folder.mkdir()
            (folder / "ECCC_system4_fixture_6hourly.grib").touch()
            records = [self.record(167, step, 280) for step in (6, 12, 18, 24)]
            with patch.object(config, "CLIMATE_DATA_DIR", root), patch.object(data_climate, "iter_grib_records", return_value=iter(records)):
                with self.assertLogs(level="WARNING") as logs:
                    outputs = data_climate.process_cansips(self.grid, self.boundary, root / "processed")
            self.assertEqual(len(outputs), 1)
            self.assertIn("Missing CanSIPSv3 total_precipitation input", " ".join(logs.output))
            with xr.open_dataset(outputs[0]) as actual:
                self.assertIn("tas", actual)
                self.assertNotIn("pr", actual)


class GeologicalTests(GridFixture):
    def test_categorical_mode_and_nodata_survive_round_trip(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "classes.tif"
            values = np.array([[1, 2, 2, 0, 0, 0, 0, 0]] * 4, dtype="uint8")
            with rasterio.open(path, "w", driver="GTiff", width=8, height=4, count=1,
                               dtype="uint8", crs=config.TARGET_CRS, nodata=0,
                               transform=from_origin(-100, 51, 0.25, 0.25)) as raster:
                raster.write(values, 1)
            original = path.read_bytes()
            actual, encoding = data_geological.categorical_raster(path, "landcover", self.grid)
            self.assertEqual(actual.landcover.values[0], 2)
            self.assertTrue(np.isnan(actual.landcover.values[1:]).all())
            output = Path(directory) / "result.nc"
            save_dataset(actual, output, self.grid, static=True, encoding=encoding)
            with xr.open_dataset(output) as restored:
                np.testing.assert_allclose(restored.landcover, [2, np.nan, np.nan, np.nan], equal_nan=True)
                self.assertNotIn("time", restored.dims)
            self.assertEqual(original, path.read_bytes())

    def test_elevation_join_uses_overlap_means_and_categorical_districts(self):
        polygons = gpd.GeoDataFrame({"ECODISTRIC": [1, 2]},
                                    geometry=[box(-100, 50, -99.75, 51), box(-99.75, 50, -99, 51)], crs=config.TARGET_CRS)
        attributes = gpd.GeoDataFrame({"DISTRICT": [1, 2], **{name: [100, 200] for name in config.ELEVATION_FIELDS}})
        attributes.loc[0, "MIN_ELEV"] = np.nan
        actual = data_geological.elevation_predictors(polygons, attributes, self.grid, self.boundary)
        self.assertEqual(actual.ECODISTRIC.values[0], 2)
        self.assertAlmostEqual(float(actual.MEAN_ELEV.values[0]), 175, delta=0.01)
        self.assertEqual(actual.MIN_ELEV.values[0], 200)
        self.assertTrue(np.isnan(actual.MEAN_ELEV.values[1:]).all())
        self.assertNotIn("time", actual.dims)


class CommandLineTests(unittest.TestCase):
    def test_missing_boundary_is_reported_without_creating_predictors(self):
        from run_pipeline import main
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertLogs(level="ERROR") as logs:
                result = main(["preprocess", "--boundary", str(root / "missing.shp"),
                               "--output-dir", str(root / "processed")])
            self.assertEqual(result, 1)
            self.assertIn("Canadian boundary polygons missing", " ".join(logs.output))
            self.assertFalse((root / "processed").exists())

    def test_geological_only_does_not_invoke_climate(self):
        from run_pipeline import main
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "boundary.gpkg"
            gpd.GeoDataFrame(geometry=[box(-100, 50, -99, 51)], crs=config.TARGET_CRS).to_file(path)
            with patch.object(data_climate, "preprocess") as climate, patch.object(data_geological, "preprocess", return_value=[]) as geological:
                result = main(["preprocess", "--only", "geological", "--boundary", str(path),
                               "--output-dir", str(root / "processed")])
            self.assertEqual(result, 0)
            climate.assert_not_called()
            geological.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)

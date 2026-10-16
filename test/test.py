"""Configuration and environment checks, without loading the raw datasets.

Run with: .venv/Scripts/python.exe -m unittest discover -s test -v
Or run directly: .venv/Scripts/python.exe test/test.py
"""

from datetime import date, timedelta
import importlib
from importlib import metadata
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config


class ConfigurationTests(unittest.TestCase):
    def test_train_validation_split_is_chronological_and_reproducible(self):
        import pandas as pd
        from src.data_merge import partition_dates

        partitions = partition_dates()
        repeated = partition_dates()
        expected = pd.date_range(*config.TIME_WINDOWS["training_validation"], freq=config.TARGET_FREQUENCY)
        self.assertEqual(len(partitions["training"]), int(len(expected) * config.TRAIN_FRACTION))
        expected = expected[~expected.isin(pd.to_datetime(config.EXCLUDED_HISTORICAL_DATES))]
        self.assertTrue(partitions["training"].append(partitions["validation"]).equals(expected))
        self.assertLess(partitions["training"][-1], partitions["validation"][0])
        self.assertLess(partitions["validation"][-1], partitions["test"][0])
        for name in partitions:
            self.assertTrue(partitions[name].equals(repeated[name]))

    def test_requested_time_windows(self):
        self.assertEqual(
            config.TIME_WINDOWS,
            {
                "training_validation": ("2020-09-01", "2025-08-31"),
                "testing": ("2025-09-01", "2026-08-31"),
                "forecasting": ("2026-09-01", "2027-08-31"),
            },
        )

    def test_time_windows_are_contiguous_and_do_not_overlap(self):
        previous_end = None
        for name, (start_date, end_date) in config.TIME_WINDOWS.items():
            with self.subTest(window=name):
                start = date.fromisoformat(start_date)
                end = date.fromisoformat(end_date)
                self.assertLess(start, end)
                if previous_end is not None:
                    self.assertEqual(start, previous_end + timedelta(days=1))
                previous_end = end

    def test_whole_day_slicing_includes_last_day_at_noon(self):
        import numpy as np
        import pandas as pd
        import xarray as xr

        for name, (start_date, end_date) in config.TIME_WINDOWS.items():
            with self.subTest(window=name):
                times = pd.date_range(
                    pd.Timestamp(start_date) - pd.Timedelta(days=1),
                    pd.Timestamp(end_date) + pd.Timedelta(days=1),
                    freq="D",
                ) + pd.Timedelta(hours=12)
                values = xr.DataArray(
                    np.arange(len(times)), coords={"time": times}, dims="time"
                )
                selected = values.sel(time=slice(start_date, end_date))
                expected_days = (
                    date.fromisoformat(end_date) - date.fromisoformat(start_date)
                ).days + 1
                self.assertEqual(selected.sizes["time"], expected_days)
                self.assertEqual(
                    pd.Timestamp(selected.time.values[0]).date().isoformat(), start_date
                )
                self.assertEqual(
                    pd.Timestamp(selected.time.values[-1]).date().isoformat(), end_date
                )

    def test_project_paths_are_absolute_and_exist(self):
        for path in (
            config.PROJECT_ROOT,
            config.DATA_DIR,
            config.RAW_DATA_DIR,
            config.CLIMATE_DATA_DIR,
            config.FIRE_DATA_DIR,
            config.GEOLOGICAL_DATA_DIR,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_absolute())
                self.assertTrue(path.is_relative_to(config.PROJECT_ROOT))
                self.assertTrue(path.is_dir())


class LibraryTests(unittest.TestCase):
    def test_source_modules_share_configuration(self):
        for module_name in (
            "src",
            "src.data_fire",
            "src.data_climate",
            "src.data_geological",
            "src.data_merge",
        ):
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIs(module.config, config)

    def test_requested_dependencies_are_installed_and_importable(self):
        requirements = (config.PROJECT_ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        for requirement in requirements:
            if not requirement.strip() or requirement.startswith("#"):
                continue
            package = requirement.strip().split("[", 1)[0]
            module_name = {"scikit-learn": "sklearn"}.get(package, package)
            with self.subTest(package=package):
                self.assertTrue(metadata.version(package))
                importlib.import_module(module_name)


class BackendTests(unittest.TestCase):
    def test_netcdf_round_trip_with_both_engines(self):
        import numpy as np
        import pandas as pd
        import xarray as xr

        expected = xr.Dataset(
            {"tas": ("time", np.array([280.0, 281.0, 282.0]))},
            coords={"time": pd.date_range(config.FORECAST_START_DATE, periods=3)},
        )
        with TemporaryDirectory() as directory:
            for engine in ("netcdf4", "h5netcdf"):
                with self.subTest(engine=engine):
                    path = Path(directory) / f"{engine}.nc"
                    expected.to_netcdf(path, engine=engine)
                    with xr.open_dataset(path, engine=engine, chunks={"time": 1}) as actual:
                        xr.testing.assert_allclose(actual.compute(), expected)
                        self.assertAlmostEqual(
                            actual.tas.mean().compute(scheduler="synchronous").item(),
                            281.0,
                        )

    def test_eccodes_grib_round_trip_through_cfgrib(self):
        import eccodes
        import numpy as np
        import xarray as xr

        with TemporaryDirectory() as directory:
            path = Path(directory) / "temperature.grib"
            message = eccodes.codes_grib_new_from_samples("regular_ll_sfc_grib1")
            try:
                eccodes.codes_set(message, "shortName", "2t")
                values = np.full(eccodes.codes_get_size(message, "values"), 280.0)
                eccodes.codes_set_values(message, values)
                with path.open("wb") as stream:
                    eccodes.codes_write(message, stream)
            finally:
                eccodes.codes_release(message)
            with xr.open_dataset(
                path, engine="cfgrib", backend_kwargs={"indexpath": ""}
            ) as dataset:
                self.assertIn("t2m", dataset.data_vars)
                np.testing.assert_allclose(dataset.t2m.values, 280.0)

    def test_vector_io_and_projection(self):
        import geopandas as gpd
        import numpy as np
        from shapely.geometry import Point

        expected = gpd.GeoDataFrame(
            {"fire_id": [1]}, geometry=[Point(-79.38, 43.65)], crs="EPSG:4326"
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fires.gpkg"
            expected.to_file(path, driver="GPKG", engine="pyogrio")
            actual = gpd.read_file(path, engine="pyogrio")
            self.assertEqual(actual.fire_id.tolist(), [1])
            projected = actual.to_crs("EPSG:3978")
            self.assertTrue(np.isfinite(projected.geometry.x).all())
            restored = projected.to_crs("EPSG:4326")
            self.assertAlmostEqual(restored.geometry.x.iloc[0], -79.38, places=6)
            self.assertAlmostEqual(restored.geometry.y.iloc[0], 43.65, places=6)

    def test_raster_io_through_rioxarray(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        import rioxarray

        values = np.array([[1, 2], [3, 4]], dtype="uint8")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "landcover.tif"
            with rasterio.open(
                path, "w", driver="GTiff", height=2, width=2, count=1,
                dtype=values.dtype, crs="EPSG:4326",
                transform=from_origin(-80, 50, 1, 1),
            ) as raster:
                raster.write(values, 1)
            with rioxarray.open_rasterio(path) as raster:
                np.testing.assert_array_equal(raster.values[0], values)
                self.assertEqual(raster.rio.crs.to_epsg(), 4326)

    def test_boosting_libraries_can_fit_and_predict(self):
        from catboost import CatBoostRegressor
        from lightgbm import LGBMRegressor
        import numpy as np
        from xgboost import XGBRegressor

        features = np.arange(40, dtype=float).reshape(20, 2)
        target = features[:, 0] * 0.5 + 1
        models = (
            XGBRegressor(n_estimators=2, max_depth=2, n_jobs=1, random_state=config.RANDOM_SEED),
            LGBMRegressor(
                n_estimators=2, max_depth=2, min_child_samples=2, n_jobs=1,
                verbosity=-1, random_state=config.RANDOM_SEED,
            ),
            CatBoostRegressor(
                iterations=2, depth=2, thread_count=1, verbose=False,
                allow_writing_files=False, random_seed=config.RANDOM_SEED,
            ),
        )
        for model in models:
            with self.subTest(model=type(model).__name__):
                model.fit(features, target)
                predictions = model.predict(features)
                self.assertEqual(predictions.shape, target.shape)
                self.assertTrue(np.isfinite(predictions).all())

    def test_cvxpy_solver_is_usable(self):
        import cvxpy as cp

        value = cp.Variable()
        problem = cp.Problem(cp.Minimize(cp.square(value - 2)), [value >= 0])
        problem.solve(solver="CLARABEL")
        self.assertEqual(problem.status, cp.OPTIMAL)
        self.assertAlmostEqual(float(value.value), 2.0, places=5)


class PipelineTests(unittest.TestCase):
    def test_pipeline_runs_from_command_line(self):
        # Launch outside the project to catch paths that depend on the caller's cwd.
        with TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(config.PROJECT_ROOT / "run_pipeline.py")],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Pipeline failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        for name, (start_date, end_date) in config.TIME_WINDOWS.items():
            self.assertIn(f"{name}: {start_date} to {end_date}", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

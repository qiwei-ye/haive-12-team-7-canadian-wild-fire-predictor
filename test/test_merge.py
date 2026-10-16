"""Synthetic daily merges: spatial assignment, chronology, leakage, and missingness."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, data_merge
from src.preprocessing import create_grid


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.boundary = box(-100, 50, -98, 52)
        self.grid = create_grid(self.boundary)

    def records(self):
        return pd.DataFrame({
            "fire_id": ["a", "b", "c", "d", "e"],
            "latitude": [50.2, 50.2, 50.2, 51.2, 51.2],
            "longitude": [-99.8, -98.8, -98.8, -99.8, -98.8],
            "report_date": ["2020-09-01", "2020-09-02", "2020-09-02", "2020-09-02", "2020-09-06"],
            "size_ha": [1, 1000, np.nan, np.nan, 2000],
            "is_large_fire": [0, 1, np.nan, np.nan, 1],
        })

    def test_fire_history_strictly_precedes_day_and_diagonal_counts(self):
        records, _ = data_merge.assign_fire_cells(self.records(), self.grid, self.boundary)
        days = pd.date_range("2020-09-01", periods=6)
        fields = dict(data_merge.daily_fire_fields(records, days, data_merge.connecting_cells(self.grid)))
        np.testing.assert_array_equal(fields[days[0]]["previous_fire"], [0, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[0]]["previous_fire_neighbour"], [0, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_fire"], [1, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_fire_neighbour"], [0, 1, 1, 1])
        # A known large fire wins over an unknown size in the same cell/day.
        np.testing.assert_allclose(fields[days[1]]["is_large_fire"], [0, 1, np.nan, 0], equal_nan=True)
        np.testing.assert_array_equal(fields[days[2]]["previous_fire"], [1, 1, 1, 0])
        self.assertEqual(fields[days[-1]]["previous_fire"][3], 0)
        self.assertEqual(fields[days[-1]]["is_large_fire"][3], 1)

    def test_history_survives_partition_start_and_missing_neighbours_stay_absent(self):
        grid = self.grid.isel(cell=[0])
        records, _ = data_merge.assign_fire_cells(self.records().iloc[:1], grid, self.boundary)
        fields = next(data_merge.daily_fire_fields(
            records, pd.date_range("2020-09-03", periods=1), data_merge.connecting_cells(grid)))[1]
        np.testing.assert_array_equal(fields["previous_fire"], [1])
        np.testing.assert_array_equal(fields["previous_fire_neighbour"], [0])

    def test_reports_on_omitted_days_still_enter_later_history_without_leakage(self):
        records, _ = data_merge.assign_fire_cells(self.records(), self.grid, self.boundary)
        days = pd.to_datetime(["2020-09-01", "2020-09-03"])
        fields = dict(data_merge.daily_fire_fields(records, days, data_merge.connecting_cells(self.grid)))
        np.testing.assert_array_equal(fields[days[0]]["previous_fire"], [0, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_fire"], [1, 1, 1, 0])
        self.assertEqual(fields[days[1]]["previous_fire_neighbour"][3], 1)

    def test_outside_and_unretained_fires_are_audited_without_relocation(self):
        records = self.records().iloc[[0, 4]].copy()
        records.loc[2] = ["outside", 49.9, -99.8, "2020-09-01", 2000, 1]
        records.loc[3] = ["invalid", np.nan, -99.8, "2020-09-01", 2000, 1]
        original = records.copy(deep=True)
        retained, excluded = data_merge.assign_fire_cells(records, self.grid.isel(cell=[0, 1, 2]), self.boundary)
        self.assertEqual(retained.fire_id.tolist(), ["a"])
        self.assertEqual(set(excluded.exclusion_reason), {
            "outside_canadian_boundary", "missing_or_invalid_coordinates", "containing_cell_not_in_retained_grid"})
        pd.testing.assert_frame_equal(original, records)

    def test_invalid_fire_indicator_and_wrong_grid_are_rejected(self):
        records = self.records()
        records.loc[0, "is_large_fire"] = 2
        with self.assertRaisesRegex(ValueError, "only 0, 1"):
            data_merge.assign_fire_cells(records, self.grid, self.boundary)
        wrong_grid = self.grid.assign_coords(cell=self.grid.cell.values + 1)
        with self.assertRaisesRegex(ValueError, "identifiers do not match"):
            data_merge.connecting_cells(wrong_grid)

    def fixture(self, root):
        processed = root / "processed"
        processed.mkdir()
        self.grid.to_netcdf(processed / "grid.nc")
        windows = {"training_validation": ("2020-09-01", "2020-09-04"),
                   "testing": ("2020-09-05", "2020-09-06"),
                   "forecasting": config.TIME_WINDOWS["forecasting"]}
        for split in ("training_validation", "testing"):
            dates = pd.date_range(*windows[split])
            for variable in config.CLIMATE_VARIABLES:
                path = processed / "climate" / config.HISTORICAL_CLIMATE_SOURCE / split / f"{variable}.nc"
                path.parent.mkdir(parents=True, exist_ok=True)
                values = np.full((len(dates), 4), 10, dtype=np.float32)
                values[0, 2] = np.nan
                dataset = xr.Dataset({variable: (("time", "cell"), values)},
                                     coords={**self.grid.coords, "time": dates})
                dataset[variable].attrs["units"] = config.CLIMATE_UNITS[variable]
                dataset.to_netcdf(path)
        for source, variables in config.MERGE_STATIC_PREDICTORS.items():
            path = processed / "static" / source / "predictors.nc"
            path.parent.mkdir(parents=True, exist_ok=True)
            values = {variable: ("cell", [1, 2, 3, np.nan]) for variable in variables}
            dataset = xr.Dataset(values, coords=self.grid.coords)
            for variable in variables:
                dataset[variable].attrs["units"] = "1" if variable == "landcover" else "m"
            dataset.to_netcdf(path)
        path = processed / "fire" / "ciffc.csv"
        path.parent.mkdir()
        self.records().to_csv(path, index=False)
        boundary = root / "boundary.gpkg"
        gpd.GeoDataFrame(geometry=[self.boundary], crs=config.TARGET_CRS).to_file(boundary)
        return processed, boundary, windows

    def test_daily_csvs_preserve_all_cells_missing_values_categories_and_splits(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            processed, boundary, windows = self.fixture(root)
            original = {path: path.read_bytes() for path in processed.rglob("*") if path.is_file()}
            with patch.object(config, "TIME_WINDOWS", windows), self.assertLogs(level="WARNING"):
                outputs = data_merge.merge(processed, root / "clean", boundary)
            self.assertEqual(len(outputs), 6)
            self.assertEqual([path.parent.name for path in outputs], ["training"] * 3 + ["validation"] + ["test"] * 2)
            for path in outputs:
                frame = pd.read_csv(path)
                self.assertEqual(frame.cell.tolist(), self.grid.cell.values.tolist())
                self.assertEqual(frame.date.unique().tolist(), [path.stem])
                self.assertNotIn("fuel_type", frame)
                self.assertNotIn("ECODISTRIC", frame)
                self.assertNotIn("partition", frame)
                self.assertTrue(frame.landcover.dropna().isin([1, 2, 3]).all())
                self.assertTrue(pd.isna(frame.landcover.iloc[3]))
            first = pd.read_csv(outputs[0])
            self.assertTrue(pd.isna(first.tas.iloc[2]))
            self.assertEqual(first.previous_fire.sum(), 0)
            testing = pd.read_csv(root / "clean" / "test" / "2020-09-05.csv")
            self.assertEqual(testing.previous_fire.tolist(), [1, 1, 1, 0])
            summary = json.loads((root / "clean" / "merge_summary.json").read_text())
            self.assertEqual(summary["partitions"]["training"]["rows"], 12)
            self.assertEqual(summary["partitions"]["training"]["missing_targets"], 1)
            with xr.open_dataset(root / "clean" / config.CLEAN_MERGED_FILENAME) as merged:
                self.assertEqual(dict(merged.sizes), {"cell": 4, "time": 6})
                self.assertEqual(merged.partition.dims, ("time",))
                self.assertEqual(merged.partition.values.tolist(), ["training"] * 3 + ["validation"] + ["test"] * 2)
                self.assertEqual(merged.landcover.dims, ("cell",))
                self.assertEqual(merged.tas.attrs["units"], config.CLIMATE_UNITS["tas"])
                self.assertEqual(merged.landcover.encoding["dtype"], np.dtype("int16"))
                self.assertEqual(merged.is_large_fire.encoding["dtype"], np.dtype("int8"))
                for path in outputs:
                    frame = pd.read_csv(path, float_precision="round_trip")
                    daily = merged.sel(time=path.stem)
                    for column in frame.columns.difference(["date"]):
                        np.testing.assert_equal(daily[column].values, frame[column].values)
                self.assertTrue(np.isnan(merged.is_large_fire.sel(time="2020-09-02").values[2]))
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)

    def test_missing_inputs_fail_before_writing_and_cli_reports_them(self):
        from run_pipeline import main
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "clean"
            with self.assertLogs(level="ERROR") as logs:
                result = main(["merge", "--processed-dir", str(root / "missing"), "--output-dir", str(output)])
            self.assertEqual(result, 1)
            self.assertIn("Required processed inputs are missing", " ".join(logs.output))
            self.assertFalse(output.exists())

    def test_date_exclusions_remove_stale_csvs_without_moving_split_boundaries(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            processed, boundary, windows = self.fixture(root)
            destination = root / "clean"
            stale = [destination / "training" / "2020-09-02.csv", destination / "test" / "2020-09-05.csv"]
            for path in stale:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("stale data", encoding="utf-8")
            exclusions = ("2020-09-02", "2020-09-05")
            with patch.object(config, "TIME_WINDOWS", windows), patch.object(config, "EXCLUDED_HISTORICAL_DATES", exclusions):
                with self.assertLogs(level="WARNING"):
                    outputs = data_merge.merge(processed, destination, boundary)
            self.assertEqual([(path.parent.name, path.stem) for path in outputs], [
                ("training", "2020-09-01"), ("training", "2020-09-03"),
                ("validation", "2020-09-04"), ("test", "2020-09-06")])
            self.assertFalse(any(path.exists() for path in stale))
            later = pd.read_csv(destination / "training" / "2020-09-03.csv")
            self.assertEqual(later.previous_fire.tolist(), [1, 1, 1, 0])
            with xr.open_dataset(destination / config.CLEAN_MERGED_FILENAME) as merged:
                self.assertEqual(pd.DatetimeIndex(merged.time.values).strftime("%Y-%m-%d").tolist(),
                                 ["2020-09-01", "2020-09-03", "2020-09-04", "2020-09-06"])
                self.assertEqual(merged.partition.values.tolist(), ["training", "training", "validation", "test"])

    def test_netcdf_only_aligns_shuffled_cells_without_loading_raw_or_processed_inputs(self):
        from run_pipeline import main
        with TemporaryDirectory() as directory:
            root = Path(directory)
            processed, boundary, windows = self.fixture(root)
            destination = root / "clean"
            with patch.object(config, "TIME_WINDOWS", windows), self.assertLogs(level="WARNING"):
                data_merge.merge(processed, destination, boundary)
            with xr.open_dataset(destination / config.CLEAN_MERGED_FILENAME) as dataset:
                expected = dataset.load()
            path = destination / "training" / "2020-09-02.csv"
            frame = pd.read_csv(path).iloc[::-1]
            frame.to_csv(path, index=False)
            original = {path: path.read_bytes() for path in destination.rglob("*.csv")}
            with patch.object(config, "TIME_WINDOWS", windows), patch.object(data_merge, "merge") as stage:
                result = main(["merge", "--netcdf-only", "--output-dir", str(destination),
                               "--processed-dir", str(root / "missing"), "--boundary", str(root / "missing.shp")])
            self.assertEqual(result, 0)
            stage.assert_not_called()
            with xr.open_dataset(destination / config.CLEAN_MERGED_FILENAME) as actual:
                xr.testing.assert_equal(actual, expected)
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)

    def test_netcdf_rejects_missing_csvs_grid_changes_and_varying_static_values(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            processed, boundary, windows = self.fixture(root)
            destination = root / "clean"
            with patch.object(config, "TIME_WINDOWS", windows), self.assertLogs(level="WARNING"):
                data_merge.merge(processed, destination, boundary)
            path = destination / "training" / "2020-09-02.csv"
            original_csv = path.read_bytes()
            netcdf = destination / config.CLEAN_MERGED_FILENAME
            original_netcdf = netcdf.read_bytes()
            for problem, message in (("missing", "daily CSVs are missing"), ("grid", "spatial grid differs"),
                                     ("static", "Static predictor"), ("binary", "Non-binary")):
                with self.subTest(problem=problem):
                    frame = pd.read_csv(path)
                    if problem == "missing":
                        path.unlink()
                    else:
                        column = {"grid": "lat", "static": "MEAN_ELEV", "binary": "previous_fire"}[problem]
                        frame.loc[0, column] += 2
                        frame.to_csv(path, index=False)
                    with patch.object(config, "TIME_WINDOWS", windows), self.assertRaisesRegex((ValueError, FileNotFoundError), message):
                        data_merge.merge_csvs_to_netcdf(destination)
                    self.assertEqual(netcdf.read_bytes(), original_netcdf)
                    path.write_bytes(original_csv)

    def test_inconsistent_predictor_coordinates_are_rejected_before_writing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            processed, boundary, windows = self.fixture(root)
            path = processed / "climate" / config.HISTORICAL_CLIMATE_SOURCE / "testing" / "tas.nc"
            with xr.open_dataset(path) as dataset:
                shifted = dataset.load().assign_coords(lon=dataset.lon.values + 0.1)
            shifted.to_netcdf(path, mode="w")
            with patch.object(config, "TIME_WINDOWS", windows), self.assertRaisesRegex(ValueError, "coordinates differ"):
                data_merge.merge(processed, root / "clean", boundary)
            self.assertFalse((root / "clean").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

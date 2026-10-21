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
        np.testing.assert_array_equal(fields[days[0]]["previous_large_fire"], [0, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[0]]["previous_large_fire_neighbour"], [0, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_large_fire"], [0, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_small_fire_neighbour"], [0, 1, 1, 1])
        # Unknown indicators use zero; a known large fire in the cell/day wins.
        np.testing.assert_array_equal(fields[days[1]]["is_large_fire"], [0, 1, 0, 0])
        np.testing.assert_array_equal(fields[days[2]]["previous_large_fire"], [0, 1, 0, 0])
        np.testing.assert_array_equal(fields[days[2]]["previous_large_fire_neighbour"], [1, 0, 1, 1])
        self.assertEqual(fields[days[-1]]["previous_large_fire"][3], 0)
        self.assertEqual(fields[days[-1]]["is_large_fire"][3], 1)

    def test_history_survives_partition_start_and_missing_neighbours_stay_absent(self):
        grid = self.grid.isel(cell=[0])
        events = self.records().iloc[:1].copy()
        events.loc[0, ["size_ha", "is_large_fire"]] = [1000, 1]
        records, _ = data_merge.assign_fire_cells(events, grid, self.boundary)
        fields = next(data_merge.daily_fire_fields(
            records, pd.date_range("2020-09-03", periods=1), data_merge.connecting_cells(grid)))[1]
        np.testing.assert_array_equal(fields["previous_large_fire"], [1])
        np.testing.assert_array_equal(fields["previous_large_fire_neighbour"], [0])
        np.testing.assert_array_equal(fields["previous_small_fire_neighbour"], [0])

    def test_reports_on_omitted_days_still_enter_later_history_without_leakage(self):
        records, _ = data_merge.assign_fire_cells(self.records(), self.grid, self.boundary)
        days = pd.to_datetime(["2020-09-01", "2020-09-03"])
        fields = dict(data_merge.daily_fire_fields(records, days, data_merge.connecting_cells(self.grid)))
        np.testing.assert_array_equal(fields[days[0]]["previous_large_fire"], [0, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_large_fire"], [0, 1, 0, 0])
        self.assertEqual(fields[days[1]]["previous_large_fire_neighbour"][3], 1)

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

    def test_two_year_history_expires_includes_anniversary_and_excludes_unknown_sizes(self):
        events = pd.DataFrame({
            "fire_id": ["large", "small", "unknown", "today"],
            "latitude": [50.2, 51.2, 50.2, 51.2], "longitude": [-99.8, -98.8, -98.8, -99.8],
            "report_date": ["2018-09-01", "2018-09-01", "2019-05-01", "2020-09-01"],
            "size_ha": [1000, 999.9, np.nan, 1000], "is_large_fire": [1, 0, np.nan, 1],
        })
        records, excluded = data_merge.assign_fire_cells(events, self.grid, self.boundary)
        self.assertTrue(excluded.empty)
        days = pd.to_datetime(["2020-09-01", "2020-09-02"])
        fields = dict(data_merge.daily_fire_fields(records, days, data_merge.connecting_cells(self.grid)))
        np.testing.assert_array_equal(fields[days[0]]["previous_large_fire"], [1, 0, 0, 0])
        np.testing.assert_array_equal(fields[days[0]]["previous_large_fire_neighbour"], [0, 1, 1, 1])
        np.testing.assert_array_equal(fields[days[0]]["previous_small_fire_neighbour"], [1, 1, 1, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_large_fire"], [0, 0, 1, 0])
        np.testing.assert_array_equal(fields[days[1]]["previous_small_fire_neighbour"], [0, 0, 0, 0])

    def test_calendar_year_lookback_handles_leap_day(self):
        events = self.records().iloc[:1].copy()
        events.loc[0, ["report_date", "size_ha", "is_large_fire"]] = ["2020-02-29", 1000, 1]
        records, _ = data_merge.assign_fire_cells(events, self.grid, self.boundary)
        days = pd.to_datetime(["2022-02-28", "2022-03-01"])
        fields = dict(data_merge.daily_fire_fields(records, days, data_merge.connecting_cells(self.grid)))
        self.assertEqual(fields[days[0]]["previous_large_fire"][0], 1)
        self.assertEqual(fields[days[1]]["previous_large_fire"][0], 0)

    def test_weather_windows_include_today_retain_missing_days_and_recover(self):
        dates = pd.date_range("2020-08-01", periods=70)
        climate = xr.Dataset({"pr": ("time", np.arange(1, 71, dtype=float)),
                              "tas": ("time", np.arange(70, dtype=float))}, coords={"time": dates})
        climate.tas.values[32] = np.nan
        climate.pr.values[35] = np.nan
        features = data_merge.rolling_weather_features(climate)
        self.assertTrue(np.isnan(features["30_day_pr"].isel(time=28)))
        self.assertEqual(float(features["30_day_pr"].isel(time=29)), sum(range(1, 31)))
        self.assertEqual(float(features["30_day_pr"].isel(time=30)), sum(range(2, 32)))
        self.assertTrue(np.isnan(features["30_day_pr"].isel(time=64)))
        self.assertEqual(float(features["30_day_pr"].isel(time=65)), sum(range(37, 67)))
        self.assertEqual(float(features["7_day_min_avg_tas"].isel(time=31)), 25)
        self.assertTrue(np.isnan(features["7_day_min_avg_tas"].isel(time=38)))
        self.assertEqual(float(features["7_day_min_avg_tas"].isel(time=39)), 33)
        self.assertEqual(features["30_day_pr"].attrs["units"], "mm")
        # A missing calendar day must be represented explicitly before rolling.
        reindexed = climate.isel(time=[i for i in range(70) if i != 40]).reindex(time=dates)
        self.assertTrue(np.isnan(data_merge.rolling_weather_features(reindexed)["7_day_min_avg_tas"].isel(time=41)))

    def fixture(self, root):
        processed = root / "processed"
        processed.mkdir()
        self.grid.to_netcdf(processed / "grid.nc")
        windows = {"training_validation": ("2020-09-01", "2020-09-04"),
                   "testing": ("2020-09-05", "2020-09-06"),
                   "history": config.TIME_WINDOWS["history"],
                   "forecasting": config.TIME_WINDOWS["forecasting"]}
        for split in ("history", "training_validation", "testing"):
            dates = pd.date_range(*windows[split])
            for variable in config.CLIMATE_VARIABLES:
                path = processed / "climate" / config.HISTORICAL_CLIMATE_SOURCE / split / f"{variable}.nc"
                path.parent.mkdir(parents=True, exist_ok=True)
                values = np.full((len(dates), 4), 10, dtype=np.float32)
                if split != "history":
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
        path = processed / "fire" / config.FIRE_SOURCES["CWFIS"]["output_filename"]
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
            self.assertEqual(first.previous_large_fire.sum(), 0)
            self.assertEqual(first["30_day_pr"].iloc[0], 300)
            self.assertEqual(first["7_day_min_avg_tas"].iloc[0], 10)
            testing = pd.read_csv(root / "clean" / "test" / "2020-09-05.csv")
            self.assertEqual(testing.previous_large_fire.tolist(), [0, 1, 0, 0])
            self.assertNotIn("previous_fire", testing)
            self.assertNotIn("previous_fire_neighbour", testing)
            summary = json.loads((root / "clean" / "merge_summary.json").read_text())
            self.assertEqual(summary["partitions"]["training"]["rows"], 12)
            self.assertEqual(summary["partitions"]["training"]["missing_targets"], 0)
            self.assertEqual(summary["definitions"]["fire_date"], config.FIRE_DATE_DEFINITION)
            self.assertEqual(summary["definitions"]["tas"], config.TAS_FILL_DEFINITION)
            with xr.open_dataset(root / "clean" / config.CLEAN_MERGED_FILENAME) as merged:
                self.assertEqual(dict(merged.sizes), {"cell": 4, "time": 6})
                self.assertEqual(merged.partition.dims, ("time",))
                self.assertEqual(merged.partition.values.tolist(), ["training"] * 3 + ["validation"] + ["test"] * 2)
                self.assertEqual(merged.landcover.dims, ("cell",))
                self.assertEqual(merged.attrs["fire_date_definition"], config.FIRE_DATE_DEFINITION)
                self.assertEqual(merged.attrs["tas_fill_definition"], config.TAS_FILL_DEFINITION)
                self.assertEqual(merged.tas.attrs["units"], config.CLIMATE_UNITS["tas"])
                self.assertEqual(merged.landcover.encoding["dtype"], np.dtype("int16"))
                self.assertEqual(merged.is_large_fire.encoding["dtype"], np.dtype("int8"))
                for path in outputs:
                    frame = pd.read_csv(path, float_precision="round_trip")
                    daily = merged.sel(time=path.stem)
                    for column in frame.columns.difference(["date"]):
                        np.testing.assert_equal(daily[column].values, frame[column].values)
                self.assertEqual(merged.is_large_fire.sel(time="2020-09-02").values[2], 0)
                self.assertFalse(merged.is_large_fire.isnull().any())
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
            self.assertEqual(later.previous_large_fire.tolist(), [0, 1, 0, 0])
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

    def test_legacy_missing_indicators_become_zero_in_csv_and_netcdf(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            processed, boundary, windows = self.fixture(root)
            destination = root / "clean"
            with patch.object(config, "TIME_WINDOWS", windows), self.assertLogs(level="WARNING"):
                data_merge.merge(processed, destination, boundary)
            path = destination / "training" / "2020-09-02.csv"
            frame = pd.read_csv(path, dtype="string", keep_default_na=False)
            frame.loc[2, "is_large_fire"] = ""
            frame.to_csv(path, index=False)
            original = pd.read_csv(path, dtype="string", keep_default_na=False)
            processed_fire = (processed / "fire" / config.FIRE_SOURCES["CWFIS"]["output_filename"]).read_bytes()
            with patch.object(config, "TIME_WINDOWS", windows):
                data_merge.merge_csvs_to_netcdf(destination)
            actual = pd.read_csv(path, dtype="string", keep_default_na=False)
            pd.testing.assert_frame_equal(actual.drop(columns="is_large_fire"), original.drop(columns="is_large_fire"))
            self.assertEqual(actual.is_large_fire.tolist(), ["0", "1", "0", "0"])
            with xr.open_dataset(destination / config.CLEAN_MERGED_FILENAME) as merged:
                np.testing.assert_array_equal(merged.is_large_fire.sel(time="2020-09-02"), [0, 1, 0, 0])
                self.assertFalse(merged.is_large_fire.isnull().any())
                self.assertEqual(merged.is_large_fire.dtype, np.dtype("int8"))
            summary = json.loads((destination / "merge_summary.json").read_text())
            self.assertEqual(summary["partitions"]["training"]["missing_targets"], 0)
            self.assertEqual(processed_fire, (processed / "fire" / config.FIRE_SOURCES["CWFIS"]["output_filename"]).read_bytes())

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
                        column = {"grid": "lat", "static": "MEAN_ELEV", "binary": "previous_large_fire"}[problem]
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

"""Greedy correlation filtering and unchanged selected values across all splits."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import baseline, config, variable_selection
from src.data_merge import partition_dates


class VariableSelectionTests(unittest.TestCase):
    def test_greedy_filter_uses_absolute_correlation_only_with_retained_predictors(self):
        iv = pd.Series({"a": 4., "b": 3., "c": 2., "d": 1.})
        correlation = pd.DataFrame([[1, -.8, .2, .6], [-.8, 1, .8, 0],
                                    [.2, .8, 1, 0], [.6, 0, 0, 1]], index=iv.index, columns=iv.index)
        result = variable_selection.select_variables(iv, correlation, threshold=.6, nominal_predictors=())
        self.assertEqual(result.selected.tolist(), [True, False, True, True])
        self.assertEqual(result.dropped_for.tolist(), ["", "a", "", ""])
        self.assertEqual(result.correlation_with_retained.iloc[1], -.8)
        self.assertEqual(result.corr_b.iloc[2], .8)

    def test_iv_ties_keep_source_order_and_nominal_codes_bypass_pearson(self):
        iv = pd.Series({"b": 1., "a": 1., "landcover": .5})
        correlation = pd.DataFrame([[1., .9, np.nan], [.9, 1., np.nan], [np.nan] * 3],
                                   index=iv.index, columns=iv.index)
        result = variable_selection.select_variables(iv, correlation, nominal_predictors=("landcover",))
        self.assertEqual(result.variable.tolist(), ["b", "a", "landcover"])
        self.assertEqual(result.selected.tolist(), [True, False, True])
        self.assertTrue(result.corr_landcover.isna().all())

    def test_invalid_threshold_and_undefined_correlations_are_rejected(self):
        iv = pd.Series({"a": 1.})
        for threshold, value in ((1.1, 1.), (.6, np.nan)):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                variable_selection.select_variables(iv, pd.DataFrame([[value]], index=["a"], columns=["a"]),
                                                    threshold=threshold, nominal_predictors=())

    def fixture(self, root):
        clean = root / "clean"
        clean.mkdir()
        dates = pd.date_range("2020-09-01", "2020-09-07")
        partitions = partition_dates()
        labels = np.concatenate([np.repeat(name, len(days)) for name, days in partitions.items()])
        rng = np.random.default_rng(config.RANDOM_SEED)
        target = rng.binomial(1, .3, size=(len(dates), 8)).astype(np.int8)
        fields = {}
        for name, kind in baseline.predictor_types().items():
            if name in config.ELEVATION_FIELDS:
                fields[name] = ("cell", np.linspace(1, 8, 8))
            elif name == "landcover":
                fields[name] = ("cell", np.array([1, 2] * 4, dtype=np.int16))
            else:
                values = rng.binomial(1, .5, size=target.shape).astype(np.int8) if kind == "categorical" else rng.normal(size=target.shape)
                fields[name] = (("time", "cell"), values)
        fields["7_day_min_avg_tas"] = fields["tas"]
        fields[config.FIRE_OUTPUT_COLUMNS[-1]] = (("time", "cell"), target)
        fields["partition"] = ("time", labels)
        dataset = xr.Dataset(fields, coords={"time": dates, "cell": np.arange(8),
                                             "lat": ("cell", np.full(8, 50.5)), "lon": ("cell", np.arange(8) - 100.5)},
                             attrs={"crs": config.TARGET_CRS})
        for name in fields:
            dataset[name].attrs["units"] = config.CLIMATE_UNITS.get(name, "1")
        self.write_clean(clean, dataset, partitions)
        frame, metadata, _ = baseline.load_training_data(clean / config.CLEAN_MERGED_FILENAME)
        # Supplied IV ranks stand in for an existing binning report; selection
        # must consume them without fitting bins or looking at heldout values.
        rows = [{"variable": name, "variable_iv": float(len(baseline.predictor_types()) - i),
                 "iv": float(len(baseline.predictor_types()) - i), "count": len(frame),
                 "event": int(frame[metadata["target"]].sum()),
                 **metadata, "training_events": int(frame[metadata["target"]].sum())}
                for i, name in enumerate(baseline.predictor_types())]
        binning = root / "binning.csv"
        pd.DataFrame(rows).to_csv(binning, index=False)
        return clean, binning, dataset

    def write_clean(self, clean, dataset, partitions):
        dataset.to_netcdf(clean / config.CLEAN_MERGED_FILENAME)
        columns = ["date", "cell", "lat", "lon", *baseline.predictor_types(), config.FIRE_OUTPUT_COLUMNS[-1]]
        for partition, dates in partitions.items():
            (clean / partition).mkdir(exist_ok=True)
            for day in dates:
                daily = dataset.drop_vars("partition").sel(time=day).to_dataframe().reset_index()
                daily["date"] = day.date().isoformat()
                daily[columns].to_csv(clean / partition / f"{day.date().isoformat()}.csv", index=False)
        static = [name for fields in config.MERGE_STATIC_PREDICTORS.values() for name in fields]
        summary = {"columns": columns, "spatial_cells_per_day": 8, "units": {name: "1" for name in columns},
                   "definitions": {name: name for name in baseline.predictor_types()},
                   "partitions": {name: {"rows": len(days) * 8, "days": len(days)} for name, days in partitions.items()},
                   "merged_netcdf": {"static_variables": static, "file": config.CLEAN_MERGED_FILENAME,
                                     "dimensions": dict(dataset.sizes)}}
        (clean / "merge_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    def test_export_matches_clean_columns_values_layout_and_is_unaffected_by_heldout_data(self):
        windows = {**config.TIME_WINDOWS, "training_validation": ("2020-09-01", "2020-09-05"),
                   "testing": ("2020-09-06", "2020-09-07")}
        with TemporaryDirectory() as directory, patch.object(config, "TIME_WINDOWS", windows):
            root = Path(directory)
            clean, binning, dataset = self.fixture(root)
            originals = {path: path.read_bytes() for path in clean.rglob("*") if path.is_file()}
            original_bins = binning.read_bytes()
            destination, report = root / "inputs", root / "selection.csv"
            result = variable_selection.run_selection(clean, destination, binning, report)
            selected = result.loc[result.selected, "variable"].tolist()
            self.assertFalse(result.set_index("variable").loc["7_day_min_avg_tas", "selected"])
            with xr.open_dataset(clean / config.CLEAN_MERGED_FILENAME) as source, xr.open_dataset(destination / config.CLEAN_MERGED_FILENAME) as actual:
                xr.testing.assert_equal(actual, source[[name for name in source.data_vars if name in {*selected, "is_large_fire", "partition"}]])
                self.assertEqual(actual.attrs["crs"], config.TARGET_CRS)
                self.assertEqual(actual.is_large_fire.encoding["dtype"], source.is_large_fire.encoding["dtype"])
            for path in clean.rglob("*.csv"):
                source = pd.read_csv(path, dtype=str, keep_default_na=False)
                expected = source[[name for name in source if name not in baseline.predictor_types() or name in selected]]
                actual = pd.read_csv(destination / path.relative_to(clean), dtype=str, keep_default_na=False)
                pd.testing.assert_frame_equal(actual, expected)
            summary = json.loads((destination / "merge_summary.json").read_text())
            self.assertEqual(summary["variable_selection"]["selected_predictors"], selected)
            self.assertEqual(summary["columns"], actual.columns.tolist())
            for path, contents in originals.items():
                self.assertEqual(path.read_bytes(), contents)
            self.assertEqual(binning.read_bytes(), original_bins)
            self.assertTrue(report.is_file())

            # Change validation/test values, categories, and targets, then rerun.
            heldout = dataset.partition.values != "training"
            for name in config.CLIMATE_VARIABLES:
                dataset[name].values[heldout] = 1e12
            dataset.is_large_fire.values[heldout] = 1 - dataset.is_large_fire.values[heldout]
            self.write_clean(clean, dataset, partition_dates())
            repeated = variable_selection.run_selection(clean, root / "inputs_second", binning, root / "selection_second.csv")
            pd.testing.assert_frame_equal(result, repeated)
            self.assertFalse(list(destination.rglob("*.partial.*")))

    def test_stale_binning_metadata_and_overwriting_sources_are_rejected(self):
        windows = {**config.TIME_WINDOWS, "training_validation": ("2020-09-01", "2020-09-05"),
                   "testing": ("2020-09-06", "2020-09-07")}
        with TemporaryDirectory() as directory, patch.object(config, "TIME_WINDOWS", windows):
            root = Path(directory)
            clean, binning, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "separate from clean"):
                variable_selection.run_selection(clean, clean, binning, root / "selection.csv")
            rows = pd.read_csv(binning)
            rows["training_end"] = "2020-09-05"
            rows.to_csv(binning, index=False)
            with self.assertRaisesRegex(ValueError, "training_end"):
                variable_selection.run_selection(clean, root / "inputs", binning, root / "selection.csv")
            self.assertFalse((root / "inputs").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

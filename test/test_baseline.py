"""Binning constraints, empirical statistics, and training-only selection."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import baseline, config


class BinningTests(unittest.TestCase):
    def test_numerical_has_exactly_five_intervals_with_correct_counts_and_woe(self):
        values = np.repeat(np.arange(20, dtype=float), 100)
        target = np.concatenate([np.r_[np.ones(i % 10 + 1), np.zeros(99 - i % 10)] for i in range(20)])
        table = baseline.fit_variable("tas", values, target, "numerical")
        self.assertEqual(len(table), config.BINNING_NUMERICAL_BINS)
        self.assertTrue(table.solver_status.eq("OPTIMAL").all())
        self.assertTrue(np.isneginf(table.lower_bound.iloc[0]))
        self.assertTrue(np.isposinf(table.upper_bound.iloc[-1]))
        np.testing.assert_equal(table.upper_bound.iloc[:-1].to_numpy(), table.lower_bound.iloc[1:].to_numpy())
        indices = np.searchsorted(table.upper_bound.iloc[:-1].to_numpy(), values, side="right")
        for i, row in table.iterrows():
            selected = indices == i
            self.assertEqual(row["count"], selected.sum())
            self.assertEqual(row.event, target[selected].sum())
            self.assertAlmostEqual(row.woe, np.log((row.non_event / (target == 0).sum()) /
                                                  (row.event / (target == 1).sum())))
        self.assertAlmostEqual(table.iv.sum(), table.variable_iv.iloc[0])

    def test_categories_are_never_merged_and_pure_bins_have_infinite_woe(self):
        table = baseline.fit_variable("landcover", [1, 1, 2, 2, 3, 3, np.nan, np.nan],
                                      [0, 0, 1, 1, 0, 1, 0, 1], "categorical")
        self.assertEqual(table.category.dropna().tolist(), [1, 2, 3])
        self.assertEqual(table.bin_type.tolist(), ["category"] * 3 + ["missing"])
        self.assertEqual(table["count"].tolist(), [2] * 4)
        self.assertTrue(np.isposinf(table.woe.iloc[0]))
        self.assertTrue(np.isneginf(table.woe.iloc[1]))
        self.assertEqual(table.woe.iloc[2], 0)
        self.assertEqual(table.woe_status.tolist(), ["zero_events", "zero_non_events", "finite", "finite"])
        self.assertTrue(np.isposinf(table.variable_iv.iloc[0]))
        self.assertTrue(table.regular_bins.eq(3).all())

    def test_binary_flags_are_categorical_and_identifiers_are_excluded(self):
        types = baseline.predictor_types()
        for name in ("landcover", *config.FIRE_HISTORY_VARIABLES):
            self.assertEqual(types[name], "categorical")
        self.assertEqual(sum(t == "numerical" for t in types.values()), 10)
        for name in ("date", "time", "cell", "lat", "lon", "partition", "is_large_fire", "fuel_type"):
            self.assertNotIn(name, types)

    def test_invalid_inputs_fail_without_silently_reducing_bin_count(self):
        for values, target, message in (
            ([0, 1], [0, 1], "fewer than"),
            ([np.nan, np.nan], [0, 1], "no observed"),
            ([np.inf, 0], [0, 1], "infinite predictor"),
            ([0, 1], [0, np.nan], "Training target"),
            ([0, 1], [0, 0], "Training target"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                baseline.fit_variable("tas", values, target, "numerical")

    def test_training_only_output_ignores_heldout_values_categories_and_targets(self):
        from src.data_merge import partition_dates

        dates_by_partition = partition_dates()
        dates = dates_by_partition["training"].append(dates_by_partition["validation"]).append(dates_by_partition["test"])
        labels = np.concatenate([np.repeat(name, len(days)) for name, days in dates_by_partition.items()])
        train_count = len(dates_by_partition["training"])
        rng = np.random.default_rng(config.RANDOM_SEED)
        values = rng.normal(size=len(dates))
        target = rng.binomial(1, 0.3, size=len(dates))
        category = np.tile([1, 2], (len(dates) + 1) // 2)[:len(dates)]
        # Deliberately invalid heldout targets and unseen categories must never
        # participate in fitting, validation, counts, or category discovery.
        values[train_count:] = 1e12
        target[train_count:] = 2
        category[train_count:] = 99
        ds = xr.Dataset(
            {"tas": (("time", "cell"), values[:, None]),
             "landcover": (("time", "cell"), category[:, None]),
             "is_large_fire": (("time", "cell"), target[:, None]),
             "partition": ("time", labels)},
            coords={"time": dates, "cell": [1]},
        )
        ds.tas.attrs["units"] = config.CLIMATE_UNITS["tas"]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path, output = root / "merged.nc", root / "outputs" / "binning.csv"
            ds.to_netcdf(path)
            original = path.read_bytes()
            types = {"tas": "numerical", "landcover": "categorical"}
            with patch.object(baseline, "predictor_types", return_value=types):
                report = baseline.run_binning(path, output)
                training, metadata, _ = baseline.load_training_data(path)
                expected = baseline.fit_variable("tas", values[:train_count], target[:train_count], "numerical")
                numerical = report.loc[report.variable.eq("tas"), expected.columns].reset_index(drop=True)
                pd.testing.assert_frame_equal(numerical, expected)
                self.assertEqual(len(training), train_count)
                self.assertEqual(metadata["training_end"], dates_by_partition["training"][-1].date().isoformat())
                self.assertEqual(report.loc[report.variable.eq("landcover"), "category"].tolist(), [1, 2])
                self.assertTrue(report.fit_partition.eq("training").all())
                for _, rows in report.groupby("variable"):
                    self.assertEqual(rows["count"].sum(), train_count)
                    self.assertEqual(rows.event.sum(), target[:train_count].sum())
                saved = pd.read_csv(output)
                self.assertEqual(len(saved), len(report))
                self.assertEqual(path.read_bytes(), original)
                ds["partition"] = xr.where(ds.time == dates[train_count], "training", ds.partition)
                ds.to_netcdf(path, mode="w")
                with self.assertRaisesRegex(ValueError, "Training dates"):
                    baseline.load_training_data(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

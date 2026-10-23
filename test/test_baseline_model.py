"""Fixed WoE mapping, training-only C selection, and partition evaluation."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import xarray as xr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import baseline, config


class BaselineModelTests(unittest.TestCase):
    def test_existing_woe_mapping_respects_interval_edges_categories_and_missing_bin(self):
        bins = pd.DataFrame([
            {"variable": "tas", "bin_id": 0, "bin_type": "interval", "lower_bound": -np.inf, "upper_bound": 0, "woe": -2},
            {"variable": "tas", "bin_id": 1, "bin_type": "interval", "lower_bound": 0, "upper_bound": np.inf, "woe": 3},
            {"variable": "tas", "bin_id": 2, "bin_type": "missing", "woe": .25},
            {"variable": "landcover", "bin_id": 0, "bin_type": "category", "category": 1, "woe": -.5},
            {"variable": "landcover", "bin_id": 1, "bin_type": "category", "category": 2, "woe": 1},
        ])
        frame = pd.DataFrame({"tas": [-1, 0, 1, np.nan], "landcover": [1, 2, 1, 2]})
        encoded = baseline.transform_woe(frame, bins)
        np.testing.assert_equal(encoded, [[-2, -.5], [3, 1], [3, -.5], [.25, 1]])
        frame.loc[0, "landcover"] = 99
        with self.assertRaisesRegex(ValueError, "unseen category"):
            baseline.transform_woe(frame, bins)
        frame.loc[0, "landcover"] = 1
        bins.loc[0, "woe"] = np.inf
        with self.assertRaisesRegex(ValueError, "non-finite WoE"):
            baseline.transform_woe(frame, bins)

    def test_c_grid_and_seeded_folds_match_independent_l2_fits(self):
        self.assertEqual(config.BASELINE_CV_FOLDS, 5)
        self.assertEqual(config.BASELINE_C_GRID, tuple(10.0 ** i for i in range(-5, 6)))
        rng = np.random.default_rng(config.RANDOM_SEED)
        features = rng.normal(size=(250, 3))
        target = (features[:, 0] + rng.normal(size=250) > .6).astype(int)
        with patch.object(config, "BASELINE_C_GRID", (0.001, 1., 1000.)):
            model, results = baseline.fit_logistic_regression(features, target)
            expected = np.empty((config.BASELINE_CV_FOLDS, 3))
            folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=config.RANDOM_SEED)
            with threadpool_limits(limits=1):
                for fold, (train, valid) in enumerate(folds.split(features, target)):
                    for index, c in enumerate(config.BASELINE_C_GRID):
                        independent = LogisticRegression(C=c, l1_ratio=0., solver=config.BASELINE_SOLVER,
                            max_iter=config.BASELINE_MAX_ITER, tol=config.BASELINE_TOLERANCE,
                            random_state=config.RANDOM_SEED).fit(features[train], target[train])
                        expected[fold, index] = roc_auc_score(target[valid], independent.predict_proba(features[valid])[:, 1])
                refitted = LogisticRegression(C=model.C, l1_ratio=0., solver=config.BASELINE_SOLVER,
                    max_iter=config.BASELINE_MAX_ITER, tol=config.BASELINE_TOLERANCE,
                    random_state=config.RANDOM_SEED).fit(features, target)
            np.testing.assert_allclose(results.mean_roc_auc, expected.mean(axis=0))
            np.testing.assert_allclose(results.std_roc_auc, expected.std(axis=0))
            self.assertEqual(model.C, config.BASELINE_C_GRID[int(np.argmax(expected.mean(axis=0)))])
            np.testing.assert_allclose(model.coef_, refitted.coef_)
            np.testing.assert_allclose(model.intercept_, refitted.intercept_)

    def test_confusion_matrix_and_probability_based_auc(self):
        metrics, curve = baseline.partition_performance(np.array([0, 0, 1, 1]), [.1, .9, .8, .2], "test", .5)
        self.assertEqual([metrics[name] for name in ("tn", "fp", "fn", "tp")], [1, 1, 1, 1])
        self.assertEqual(metrics["roc_auc"], .5)
        self.assertEqual(metrics["precision"], .5)
        self.assertEqual(metrics["recall"], .5)
        self.assertEqual(metrics["total_cost"], 1051)
        self.assertIsNotNone(curve)
        imbalanced, _ = baseline.partition_performance(np.array([0, 0, 0, 1]), [.1, .9, .2, .8], "test", .5)
        self.assertEqual(imbalanced["precision"], .5)
        self.assertEqual(imbalanced["recall"], 1.)
        self.assertAlmostEqual(imbalanced["specificity"], 2 / 3)
        self.assertEqual(imbalanced["accuracy"], .75)
        self.assertEqual(imbalanced["total_cost"], 51)
        self.assertFalse(any(name.endswith(("_fraction", "_rate")) for name in imbalanced))
        with self.assertRaisesRegex(ValueError, "at least one"):
            baseline.fit_logistic_regression(np.arange(12).reshape(6, 2), [0, 0, 0, 0, 0, 1])

    def test_training_threshold_matches_brute_force_including_tied_scores_and_tp_cost(self):
        self.assertEqual(config.BASELINE_CONFUSION_COSTS, {"tn": 0, "fp": 1, "fn": 1000, "tp": 50})
        rng = np.random.default_rng(config.RANDOM_SEED)
        target = rng.binomial(1, .2, size=100)
        probabilities = np.round(rng.uniform(size=100), 1)
        result = baseline.optimize_threshold(target, probabilities)
        candidates = np.r_[np.nextafter(probabilities.max(), np.inf), np.unique(probabilities)[::-1]]
        costs = [baseline.partition_performance(target, probabilities, "training", threshold)[0]["total_cost"]
                 for threshold in candidates]
        self.assertEqual(result["probability_threshold"], candidates[int(np.argmin(costs))])
        self.assertEqual(result["threshold_training_cost"], min(costs))
        self.assertEqual(result["threshold_fit_partition"], "training")
        with patch.object(config, "BASELINE_CONFUSION_COSTS", {"tn": 0, "fp": 0, "fn": 0, "tp": 0}):
            result = baseline.optimize_threshold(target, probabilities)
            self.assertGreater(result["probability_threshold"], probabilities.max())

    def test_end_to_end_exports_and_heldout_data_cannot_change_coefficients_or_c(self):
        windows = {**config.TIME_WINDOWS, "training_validation": ("2020-09-01", "2020-09-05"),
                   "testing": ("2020-09-06", "2020-09-07")}
        rng = np.random.default_rng(config.RANDOM_SEED)
        dates = pd.date_range("2020-09-01", "2020-09-07")
        values = rng.normal(size=(7, 200))
        category = np.tile([1, 2], 100)
        probabilities = 1 / (1 + np.exp(-(values + .4 * (category - 1) - .5)))
        target = rng.binomial(1, probabilities).astype(np.int8)
        ds = xr.Dataset({"tas": (("time", "cell"), values), "landcover": ("cell", category),
            "is_large_fire": (("time", "cell"), target),
            "partition": ("time", ["training"] * 4 + ["validation"] + ["test"] * 2)},
            coords={"time": dates, "cell": np.arange(200)}, attrs={"selected_predictors": json.dumps(["tas", "landcover"])})
        with TemporaryDirectory() as directory, patch.object(config, "TIME_WINDOWS", windows), patch.object(config, "BASELINE_C_GRID", (.01, 1.)):
            root = Path(directory)
            source, report, output = root / "inputs.nc", root / "binning.csv", root / "outputs"
            ds.to_netcdf(source)
            frame, y, coverage = baseline.load_model_partition(source, "training")
            rows = []
            for name, kind in (("tas", "numerical"), ("landcover", "categorical")):
                rows.append(baseline.fit_variable(name, frame[name], y, kind))
            bins = pd.concat(rows, ignore_index=True)
            for name, value in {"fit_partition": "training", **{"training_" + k: v for k, v in coverage.items()}}.items():
                bins[name] = value
            bins.to_csv(report, index=False)
            original_source, original_bins = source.read_bytes(), report.read_bytes()
            model, coefficients, performance = baseline.run_classifier(source, report, output)
            self.assertEqual(coefficients.variable.tolist(), ["intercept", "tas", "landcover"])
            self.assertEqual(performance.partition.tolist(), ["training", "validation", "test"])
            self.assertTrue(performance.roc_auc.between(0, 1).all())
            self.assertEqual(performance.probability_threshold.nunique(), 1)
            self.assertTrue(performance.threshold_fit_partition.eq("training").all())
            self.assertEqual(performance.total_cost.iloc[0], performance.threshold_training_cost.iloc[0])
            for row in performance.itertuples():
                self.assertEqual(row.tn + row.fp + row.fn + row.tp, row.rows)
                cv = json.loads(row.cv_auc_by_C)
                self.assertEqual(len(cv), 2)
                self.assertEqual(len(cv[0]["fold_roc_auc"]), 5)
                self.assertEqual(row.total_cost, row.fp + 50 * row.tp + 1000 * row.fn)
            self.assertTrue((output / config.BASELINE_COEFFICIENTS_PATH.name).is_file())
            self.assertTrue((output / config.BASELINE_PERFORMANCE_PATH.name).is_file())
            self.assertTrue((output / config.BASELINE_ROC_PATH.name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(source.read_bytes(), original_source)
            self.assertEqual(report.read_bytes(), original_bins)

            ds.tas.values[4:] = 1e9
            ds.is_large_fire.values[4:] = 1 - ds.is_large_fire.values[4:]
            ds.to_netcdf(source, mode="w")
            repeated, coefficients_again, _ = baseline.run_classifier(source, report, root / "second")
            self.assertEqual(model.C, repeated.C)
            pd.testing.assert_frame_equal(coefficients, coefficients_again)
            self.assertFalse(list(output.glob("*.partial.*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)

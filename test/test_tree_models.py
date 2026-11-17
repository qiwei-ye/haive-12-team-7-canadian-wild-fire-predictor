"""Tree model wiring and leakage checks; no forest or XGBoost model is trained."""

from contextlib import ExitStack
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from sklearn.model_selection import ParameterGrid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, randomforest, tree_models, xgboost


class TreeModelTests(unittest.TestCase):
    def test_rf_and_xgboost_specifications_use_configured_seed(self):
        with patch.object(randomforest, "RandomForestClassifier") as factory:
            randomforest.build_estimator()
        factory.assert_called_once_with(n_estimators=300, bootstrap=True, max_samples=.8,
                                       criterion="log_loss", random_state=config.RANDOM_SEED,
                                       n_jobs=config.TREE_MODEL_N_JOBS)
        self.assertEqual(config.RANDOM_FOREST_PARAM_GRID,
                         {"max_depth": (5, 10, 15), "max_features": (2, 3, 4),
                          "min_samples_leaf": (10, 50, 100)})
        self.assertEqual(len(ParameterGrid(config.RANDOM_FOREST_PARAM_GRID)), 27)
        with patch.object(xgboost, "XGBClassifier") as factory:
            xgboost.build_estimator()
        factory.assert_called_once_with(**config.XGBOOST_PARAMETERS, random_state=config.RANDOM_SEED,
                                       n_jobs=config.TREE_MODEL_N_JOBS)
        self.assertEqual(config.XGBOOST_PARAMETERS, {
            "objective": "binary:logistic", "eval_metric": "logloss", "n_estimators": 3_000,
            "early_stopping_rounds": 100, "subsample": .8, "tree_method": "hist",
        })
        self.assertEqual(config.XGBOOST_PARAM_GRID, {
            "learning_rate": (.03, .05, .10), "max_depth": (2, 4, 6),
            "min_child_weight": (1, 5, 10), "colsample_bytree": (.6, .8, 1.),
            "reg_lambda": (1, 10, 50),
        })
        self.assertEqual(len(ParameterGrid(config.XGBOOST_PARAM_GRID)), 243)

    def test_cli_without_fit_never_starts_models(self):
        for module in (randomforest, xgboost):
            with self.subTest(module=module.__name__), patch.object(module, "run_classifier") as run:
                with patch("argparse.ArgumentParser.print_help"):
                    self.assertEqual(module.main([]), 0)
                run.assert_not_called()

    def test_selected_loader_preserves_raw_values_and_rejects_unselected_inputs(self):
        raw = pd.DataFrame({"tas": [3.25, 17.125], "landcover": [1, 18]})
        y = np.array([0, 1])
        source = SimpleNamespace(attrs={"selected_predictors": json.dumps(list(raw))},
                                 data_vars=[*raw, "is_large_fire", "partition"])
        with patch.object(tree_models.xr, "open_dataset") as opened:
            opened.return_value.__enter__.return_value = source
            with patch.object(tree_models, "load_model_partition", return_value=(raw, y, {})):
                frame, target, _ = tree_models.load_selected_partition("selected.nc", "training")
                np.testing.assert_array_equal(frame.to_numpy(), raw.to_numpy())
                np.testing.assert_array_equal(target, y)
                self.assertTrue(all(dtype == np.dtype("float32") for dtype in frame.dtypes))
            source.attrs = {}
            with self.assertRaisesRegex(ValueError, "selected_predictors"):
                tree_models.load_selected_partition("unselected.nc", "training")
            source.attrs = {"selected_predictors": json.dumps([*raw, "is_large_fire"])}
            with self.assertRaisesRegex(ValueError, "Targets and identifiers"):
                tree_models.load_selected_partition("leaky.nc", "training")
            source.attrs = {"selected_predictors": json.dumps(list(raw))}
            raw.loc[0, "tas"] = np.nan
            with patch.object(tree_models, "load_model_partition", return_value=(raw, y, {})):
                with self.assertRaisesRegex(ValueError, "missing/infinite"):
                    tree_models.load_selected_partition("missing.nc", "training")

    def test_cv_receives_only_supplied_training_rows_with_unfitted_fold_encoder(self):
        features = pd.DataFrame({"tas": np.arange(20), "landcover": [1, 2] * 10})
        y = np.array([0, 1] * 10)
        search = Mock(best_estimator_=object(), best_index_=1, best_score_=.8,
                      best_params_={"model__max_depth": 10})
        search.cv_results_ = {
            "params": [{"model__max_depth": 5}, {"model__max_depth": 10}],
            "mean_test_score": [.7, .8], "std_test_score": [.01, .02],
            "rank_test_score": [2, 1],
            **{f"split{fold}_test_score": [.7, .8] for fold in range(config.BASELINE_CV_FOLDS)},
        }
        with patch.object(tree_models, "GridSearchCV", return_value=search) as factory:
            result, cv = tree_models.fit_tree_classifier(features, y, Mock(), {"max_depth": [5, 10]})
        search.fit.assert_called_once_with(features, y)
        self.assertIs(result, search.best_estimator_)
        self.assertEqual(cv.selected.tolist(), [False, True])
        arguments, settings = factory.call_args
        self.assertEqual(arguments[1], {"model__max_depth": [5, 10]})
        self.assertEqual(settings["scoring"], "roc_auc")
        self.assertEqual(settings["cv"].random_state, config.RANDOM_SEED)
        self.assertEqual(settings["cv"].n_splits, config.BASELINE_CV_FOLDS)
        self.assertTrue(settings["cv"].shuffle)
        self.assertEqual(settings["n_jobs"], 1)
        self.assertEqual(settings["error_score"], "raise")
        self.assertFalse(hasattr(arguments[0].named_steps["preprocessing"], "transformers_"))
        with self.assertRaisesRegex(ValueError, "at least one"):
            tree_models.fit_tree_classifier(features.iloc[:6], [0, 0, 0, 0, 0, 1], Mock(), {})

    def test_one_hot_is_training_only_and_importances_aggregate_to_selected_features(self):
        training = pd.DataFrame({"tas": [4., 8., 12.], "previous_large_fire": [0, 1, 0],
                                 "landcover": [1, 2, 1]})
        encoder = tree_models.build_preprocessor(training.columns)
        encoded = encoder.fit_transform(training)
        np.testing.assert_array_equal(encoded[:, :2], training.iloc[:, :2])
        heldout = pd.DataFrame({"tas": [19.], "previous_large_fire": [1], "landcover": [99]})
        np.testing.assert_array_equal(encoder.transform(heldout), [[19., 1., 0., 0.]])
        np.testing.assert_array_equal(encoder.named_transformers_["nominal"].categories_[0], [1, 2])
        pipeline = SimpleNamespace(named_steps={"preprocessing": encoder,
            "model": SimpleNamespace(feature_importances_=np.array([.1, .2, .3, .4]))})
        report = tree_models.feature_importances(pipeline, training.columns.tolist(), "test").set_index("variable")
        self.assertAlmostEqual(report.loc["landcover", "importance"], .7)
        self.assertEqual(report.loc["landcover", "encoded_columns"], 2)
        self.assertEqual(set(report.index), set(training.columns))
        self.assertAlmostEqual(report.importance.sum(), 1.)

    def test_heldout_values_never_reach_fit_or_threshold_selection(self):
        frames = {name: pd.DataFrame({"tas": np.arange(4) + offset, "landcover": [1, 2, 1, 2]})
                  for name, offset in (("training", 0), ("validation", 100), ("test", 200))}
        y = np.array([0, 1, 0, 1])
        coverage = {"start": "2020-09-01", "end": "2020-09-01", "days": 1, "rows": 4, "events": 2}
        pipeline = Mock()
        pipeline.named_steps = {"model": Mock()}
        pipeline.named_steps["model"].get_params.return_value = {"random_state": config.RANDOM_SEED}
        probabilities = np.column_stack(([.9, .1, .8, .2], [.1, .9, .2, .8]))
        pipeline.predict_proba.return_value = probabilities
        cv = pd.DataFrame({"selected": [True], "mean_roc_auc": [.8], "std_roc_auc": [.02], "parameters": ['{}']})
        fit = Mock(return_value=(pipeline, cv))
        threshold_info = {"probability_threshold": .4, "threshold_fit_partition": "training",
                          "threshold_training_cost": 100., "threshold_objective": "test"}
        importance = pd.DataFrame({"variable": ["tas", "landcover"], "importance": [.4, .6]})
        with TemporaryDirectory() as directory, ExitStack() as stack:
            loader = stack.enter_context(patch.object(tree_models, "load_selected_partition",
                side_effect=lambda path, partition: (frames[partition], y, coverage)))
            threshold = stack.enter_context(patch.object(tree_models, "optimize_threshold", return_value=threshold_info))
            stack.enter_context(patch.object(tree_models, "feature_importances", return_value=importance))
            stack.enter_context(patch.object(tree_models, "_save_csv"))
            stack.enter_context(patch.object(tree_models, "_save_roc"))
            stack.enter_context(patch.object(tree_models, "export_probabilities"))
            _, _, performance = tree_models.run_tree_classifier("testmodel", fit, "inputs.nc", directory, "test")
            self.assertFalse(list(Path(directory).iterdir()))
        fit.assert_called_once()
        self.assertIs(fit.call_args.args[0], frames["training"])
        self.assertIs(fit.call_args.args[1], y)
        self.assertEqual([call.args[1] for call in loader.call_args_list], ["training", "validation", "test"])
        threshold.assert_called_once()
        np.testing.assert_array_equal(threshold.call_args.args[0], y)
        np.testing.assert_array_equal(threshold.call_args.args[1], probabilities[:, 1])
        self.assertEqual(performance.partition.tolist(), ["training", "validation", "test"])
        self.assertEqual(performance.probability_threshold.tolist(), [.4, .4, .4])
        self.assertEqual(performance.evaluation.tolist(), ["in_sample", "held_out", "held_out"])

    def test_xgboost_stopping_is_disjoint_from_scoring_and_final_refit_uses_all_training(self):
        features = pd.DataFrame({
            "tas": np.arange(100), "previous_large_fire": np.arange(100) % 2,
            "landcover": np.where(np.arange(100) == 99, 99, 1 + np.arange(100) % 2),
        })
        y = np.arange(100) % 2
        instances, preprocessors = [], []
        fold_counts = {2: 0, 4: 0}
        outer = self

        class FakeXGBClassifier:
            """Record fit arguments and return fixed probabilities; no learning."""

            def __init__(self, **parameters):
                self.parameters = parameters
                instances.append(self)

            def fit(self, x, target, eval_set=None, verbose=False):
                self.fit_ids = set(x[:, 0].astype(int))
                np.testing.assert_array_equal(target, x[:, 0].astype(int) % 2)
                self.stop_ids = None
                if eval_set is not None:
                    outer.assertEqual(len(eval_set), 1)
                    self.stop_ids = set(eval_set[0][0][:, 0].astype(int))
                    np.testing.assert_array_equal(eval_set[0][1], eval_set[0][0][:, 0].astype(int) % 2)
                    depth = self.parameters["max_depth"]
                    fold_counts[depth] += 1
                    self.best_iteration = depth + fold_counts[depth] - 1
                outer.assertFalse(verbose)
                return self

            def predict_proba(self, x, iteration_range=None):
                self.score_ids = set(x[:, 0].astype(int))
                outer.assertEqual(iteration_range, (0, self.best_iteration + 1))
                confidence = .9 if self.parameters["max_depth"] == 4 else .6
                probabilities = np.where(x[:, 0].astype(int) % 2, confidence, 1 - confidence)
                return np.column_stack((1 - probabilities, probabilities))

        def preprocessor(names):
            result = tree_models.build_preprocessor(names)
            preprocessors.append(result)
            return result

        with patch.object(config, "XGBOOST_PARAM_GRID", {"max_depth": (2, 4)}), \
                patch.object(xgboost, "XGBClassifier", FakeXGBClassifier), \
                patch.object(xgboost, "build_preprocessor", side_effect=preprocessor):
            pipeline, cv = xgboost.fit_xgboost(features, y)
        self.assertEqual(len(instances), 2 * config.BASELINE_CV_FOLDS + 1)
        self.assertEqual(len(preprocessors), config.BASELINE_CV_FOLDS + 1)
        self.assertEqual(cv.selected.tolist(), [False, True])
        self.assertEqual(cv["rank"].tolist(), [2, 1])
        self.assertTrue(cv.selection_metric.eq("log_loss").all())
        self.assertTrue(cv.mean_roc_auc.eq(1.).all())  # Log loss breaks the AUC tie.
        scoring_sets = []
        for fold in range(config.BASELINE_CV_FOLDS):
            first, second = instances[fold * 2:fold * 2 + 2]
            for model in (first, second):
                self.assertFalse(model.fit_ids & model.stop_ids)
                self.assertFalse(model.score_ids & (model.fit_ids | model.stop_ids))
                self.assertEqual(model.fit_ids | model.stop_ids | model.score_ids, set(range(100)))
                self.assertEqual(model.parameters["n_estimators"], 3_000)
                self.assertEqual(model.parameters["early_stopping_rounds"], 100)
                self.assertEqual(model.parameters["random_state"], config.RANDOM_SEED)
            self.assertEqual(first.fit_ids, second.fit_ids)
            self.assertEqual(first.stop_ids, second.stop_ids)
            self.assertEqual(first.score_ids, second.score_ids)
            categories = preprocessors[fold].named_transformers_["nominal"].categories_[0]
            np.testing.assert_array_equal(categories, np.sort(features.loc[list(first.fit_ids), "landcover"].unique()))
            self.assertFalse(any(first.score_ids & previous for previous in scoring_sets))
            scoring_sets.append(first.score_ids)
        self.assertEqual(set.union(*scoring_sets), set(range(100)))
        final = pipeline.named_steps["model"]
        self.assertEqual(final.fit_ids, set(range(100)))
        self.assertIsNone(final.stop_ids)
        self.assertIsNone(final.parameters["early_stopping_rounds"])
        self.assertEqual(final.parameters["n_estimators"], 7)  # Median of 5, 6, 7, 8, 9 rounds.
        self.assertEqual(cv.loc[cv.selected, "refit_n_estimators"].item(), 7)

    def test_xgboost_rejects_invalid_stopping_configuration_without_fitting(self):
        features = pd.DataFrame({"tas": np.arange(20)})
        y = np.array([0, 1] * 10)
        with patch.object(xgboost, "XGBClassifier") as factory:
            with patch.object(config, "VALIDATION_FRACTION", 0):
                with self.assertRaisesRegex(ValueError, "fraction"):
                    xgboost.fit_xgboost(features, y)
            with patch.object(config, "XGBOOST_PARAM_GRID", {"n_estimators": (10,)}):
                with self.assertRaisesRegex(ValueError, "round limit"):
                    xgboost.fit_xgboost(features, y)
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

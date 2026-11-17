"""XGBoost on selected raw predictors; no binning or WoE.

Fit explicitly: .venv/Scripts/python.exe -m src.xgboost --fit

The configured 243 candidates use five shuffled stratified training-only folds.
Early stopping monitors log loss on a separate subset of each fold's training
rows; the outer scoring fold and dated validation/test partitions are excluded.
Mean outer-fold log loss selects the candidate; ROC-AUC is reported alongside it.
The final model fits all training rows using the median best fold round count.
Nominal land cover uses fold-fitted one-hot encoding; other values pass through.
No model runs on import or without --fit.
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import ParameterGrid, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from . import config
from .tree_models import build_preprocessor, run_tree_classifier, validate_training_data


LOGGER = logging.getLogger(__name__)


def build_estimator(**parameters):
    return XGBClassifier(
        **{**config.XGBOOST_PARAMETERS, **parameters}, random_state=config.RANDOM_SEED,
        n_jobs=config.TREE_MODEL_N_JOBS,
    )


def fit_xgboost(features, target):
    """Tune with nested training-only stopping sets, then refit every training row.

    Each outer training fold reserves the configured VALIDATION_FRACTION for
    stopping. Encoding learns only from the remaining fitting rows. Predictions
    on the untouched scoring fold use best_iteration + 1 rounds. No heldout
    partition is needed to choose parameters, stopping rounds, or the final fit.
    """
    target = validate_training_data(features, target)
    if not 0 < config.VALIDATION_FRACTION < 1:
        raise ValueError("Early-stopping fraction must be between zero and one")
    if {"random_state", "n_jobs", "n_estimators", "early_stopping_rounds"}.intersection(config.XGBOOST_PARAM_GRID):
        raise ValueError("Set the seed, workers, round limit, and patience in their fixed configuration, not the grid")
    candidates = list(ParameterGrid(config.XGBOOST_PARAM_GRID))
    if not candidates:
        raise ValueError("XGBoost needs at least one parameter configuration")
    max_rounds = config.XGBOOST_PARAMETERS["n_estimators"]
    patience = config.XGBOOST_PARAMETERS["early_stopping_rounds"]
    if max_rounds < 1 or patience < 1:
        raise ValueError("XGBoost round limit and early-stopping patience must be positive")
    folds = StratifiedKFold(n_splits=config.BASELINE_CV_FOLDS, shuffle=True,
                            random_state=config.RANDOM_SEED)
    shape = (len(candidates), config.BASELINE_CV_FOLDS)
    losses, aucs = np.empty(shape), np.empty(shape)
    rounds = np.empty(shape, dtype=int)
    LOGGER.info("XGBoost: %s candidates x %s training-only folds; log-loss ranking and stopping",
                len(candidates), config.BASELINE_CV_FOLDS)
    for fold, (training_rows, scoring_rows) in enumerate(folds.split(features, target)):
        fitting_rows, stopping_rows = train_test_split(
            training_rows, test_size=config.VALIDATION_FRACTION,
            stratify=target[training_rows], random_state=config.RANDOM_SEED,
        )
        if any(np.unique(target[rows]).size != 2 for rows in (fitting_rows, stopping_rows)):
            raise ValueError("Each fitting/early-stopping subset must contain both target classes")
        preprocessing = build_preprocessor(features.columns)
        x_fit = preprocessing.fit_transform(features.iloc[fitting_rows])
        x_stop = preprocessing.transform(features.iloc[stopping_rows])
        x_score = preprocessing.transform(features.iloc[scoring_rows])
        for index, parameters in enumerate(candidates):
            model = build_estimator(**parameters)
            model.fit(x_fit, target[fitting_rows], eval_set=[(x_stop, target[stopping_rows])], verbose=False)
            count = int(model.best_iteration) + 1
            if not 1 <= count <= max_rounds:
                raise ValueError("XGBoost selected an invalid number of boosting rounds")
            probabilities = model.predict_proba(x_score, iteration_range=(0, count))[:, 1]
            losses[index, fold] = log_loss(target[scoring_rows], probabilities, labels=[0, 1])
            aucs[index, fold] = roc_auc_score(target[scoring_rows], probabilities)
            rounds[index, fold] = count
            LOGGER.info("Fold %s/%s, candidate %s/%s: log loss=%.8f; ROC-AUC=%.6f; best rounds=%s",
                        fold + 1, config.BASELINE_CV_FOLDS, index + 1, len(candidates),
                        losses[index, fold], aucs[index, fold], count)
            del model
        del x_fit, x_stop, x_score
    means = losses.mean(axis=1)
    best = int(np.argmin(means))  # Exact ties retain the first grid entry.
    ranks = pd.Series(means).rank(method="min").astype(int).to_numpy()
    records = []
    for index, parameters in enumerate(candidates):
        records.append({
            "candidate": index + 1, **parameters,
            "parameters": json.dumps(parameters, sort_keys=True),
            "selection_metric": "log_loss", "mean_log_loss": means[index],
            "std_log_loss": losses[index].std(),
            "mean_roc_auc": aucs[index].mean(), "std_roc_auc": aucs[index].std(),
            "rank": int(ranks[index]), "selected": index == best,
            "max_n_estimators": max_rounds, "early_stopping_rounds": patience,
            "early_stopping_fraction": config.VALIDATION_FRACTION,
            "refit_n_estimators": int(np.ceil(np.median(rounds[index]))),
            **{f"fold_{fold + 1}_log_loss": losses[index, fold] for fold in range(config.BASELINE_CV_FOLDS)},
            **{f"fold_{fold + 1}_roc_auc": aucs[index, fold] for fold in range(config.BASELINE_CV_FOLDS)},
            **{f"fold_{fold + 1}_best_rounds": int(rounds[index, fold]) for fold in range(config.BASELINE_CV_FOLDS)},
        })
    cv = pd.DataFrame(records)
    best_rounds = int(cv.loc[best, "refit_n_estimators"])
    preprocessing = build_preprocessor(features.columns)
    encoded = preprocessing.fit_transform(features)
    model = build_estimator(**candidates[best], n_estimators=best_rounds, early_stopping_rounds=None)
    model.fit(encoded, target, verbose=False)
    pipeline = Pipeline([("preprocessing", preprocessing), ("model", model)])
    LOGGER.info("Selected parameters %s; CV log loss=%.8f; full-training refit rounds=%s",
                candidates[best], means[best], best_rounds)
    return pipeline, cv


def run_classifier(input_path=None, output_dir=None):
    return run_tree_classifier(
        "xgboost", fit_xgboost,
        input_path if input_path is not None else config.INPUT_DATA_DIR / config.CLEAN_MERGED_FILENAME,
        output_dir if output_dir is not None else config.XGBOOST_OUTPUTS_DIR,
        importance_type="normalized_gain; summed_across_one_hot_columns",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fit", action="store_true", help="Run training-only CV, refit, and export partition results")
    parser.add_argument("--input", type=Path, default=config.INPUT_DATA_DIR / config.CLEAN_MERGED_FILENAME)
    parser.add_argument("--output-dir", type=Path, default=config.XGBOOST_OUTPUTS_DIR)
    args = parser.parse_args(argv)
    if not args.fit:
        parser.print_help()
        return 0
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run_classifier(args.input, args.output_dir)
    except (ValueError, OSError) as error:
        LOGGER.error("XGBoost failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

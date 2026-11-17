"""Shared raw selected-input preparation, CV, and evaluation for tree models.

Only generic input/metric/export helpers are reused from baseline. No binning
report is read and no bin or WoE transformation is performed. Land cover uses
fold-fitted one-hot encoding; numerical and binary predictors pass through.
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from sklearn.compose import ColumnTransformer
from sklearn.metrics import log_loss
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from . import config
from .baseline import (
    export_probabilities, load_model_partition, optimize_threshold,
    partition_performance,
)
from .data_merge import partition_dates


LOGGER = logging.getLogger(__name__)


def load_selected_partition(input_path, partition):
    """Require selection metadata, and keep dates/coordinates/target out of X."""
    target = config.FIRE_OUTPUT_COLUMNS[-1]
    with xr.open_dataset(input_path) as source:
        try:
            selected = json.loads(source.attrs["selected_predictors"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Use selected data/inputs/merged.nc with selected_predictors metadata") from error
        if (not isinstance(selected, list) or not selected
                or any(not isinstance(name, str) for name in selected)
                or len(set(selected)) != len(selected)
                or set(source.data_vars) != {*selected, target, "partition"}):
            raise ValueError("Model input schema must contain exactly the selected predictors, target, and partition")
        if {target, "partition", "date", "time", "cell", "lat", "lon"}.intersection(selected):
            raise ValueError("Targets and identifiers cannot be selected predictors")
    frame, y, coverage = load_model_partition(input_path, partition)
    if set(frame.columns) != set(selected):
        raise ValueError("Selected predictor metadata differs from the model input fields")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError(f"{partition} predictors contain missing/infinite values; no implicit filling is applied")
    for name in set(config.VARIABLE_SELECTION_NOMINAL_PREDICTORS).intersection(frame.columns):
        values = frame[name].to_numpy()
        if not np.equal(values, np.rint(values)).all():
            raise ValueError(f"Nominal predictor {name} must retain integer category codes")
    # Both tree libraries use single-precision predictor values internally.
    frame = frame.astype(np.float32)
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError(f"{partition} predictors exceed the tree models' float32 range")
    return frame, y, coverage


def build_preprocessor(names):
    """Fit nominal categories inside each CV fold; leave other values unbinned."""
    nominal = [name for name in names if name in config.VARIABLE_SELECTION_NOMINAL_PREDICTORS]
    numerical = [name for name in names if name not in nominal]
    transformers = []
    if numerical:
        transformers.append(("numerical", "passthrough", numerical))
    if nominal:
        transformers.append(("nominal", OneHotEncoder(
            handle_unknown="ignore", sparse_output=False, dtype=np.float32,
        ), nominal))
    return ColumnTransformer(transformers, remainder="drop", sparse_threshold=0)


def validate_training_data(features, target):
    """Validate raw named predictors and sufficient binary classes for CV."""
    target = np.asarray(target)
    if (not isinstance(features, pd.DataFrame) or features.empty
            or features.columns.has_duplicates
            or target.shape != (len(features),)
            or not np.isfinite(features.to_numpy(dtype=float)).all()
            or not np.isin(target, [0, 1]).all()):
        raise ValueError("Tree fitting needs finite named predictors and an equally sized binary target")
    if (np.unique(target).size != 2
            or np.bincount(target.astype(int)).min() < config.BASELINE_CV_FOLDS):
        raise ValueError("Each target class needs at least one observation per CV fold")
    return target


def fit_tree_classifier(features, target, estimator, parameter_grid):
    """Search only training folds, then refit the winning pipeline on training."""
    target = validate_training_data(features, target)
    if {"random_state", "n_jobs"}.intersection(parameter_grid):
        raise ValueError("Use the configured shared random seed and worker count, not a grid over them")
    pipeline = Pipeline([
        ("preprocessing", build_preprocessor(features.columns)),
        ("model", estimator),
    ])
    folds = StratifiedKFold(n_splits=config.BASELINE_CV_FOLDS, shuffle=True,
                            random_state=config.RANDOM_SEED)
    search = GridSearchCV(
        pipeline, {f"model__{name}": values for name, values in parameter_grid.items()},
        scoring="roc_auc", cv=folds, refit=True, n_jobs=1, pre_dispatch=1,
        error_score="raise", return_train_score=False, verbose=2,
    )
    search.fit(features, target)
    results = search.cv_results_
    records = []
    for index, parameters in enumerate(results["params"]):
        parameters = {name.removeprefix("model__"): value for name, value in parameters.items()}
        records.append({
            "candidate": index + 1, **parameters,
            "parameters": json.dumps(parameters, sort_keys=True),
            "mean_roc_auc": results["mean_test_score"][index],
            "std_roc_auc": results["std_test_score"][index],
            "rank": results["rank_test_score"][index],
            "selected": index == search.best_index_,
            **{f"fold_{fold + 1}_roc_auc": results[f"split{fold}_test_score"][index]
               for fold in range(config.BASELINE_CV_FOLDS)},
        })
    LOGGER.info("Selected parameters %s; mean CV ROC-AUC=%.6f", search.best_params_, search.best_score_)
    return search.best_estimator_, pd.DataFrame(records)


def feature_importances(pipeline, names, importance_type):
    """Sum one-hot importances back to the original selected predictor names."""
    preprocessing = pipeline.named_steps["preprocessing"]
    importance = np.asarray(pipeline.named_steps["model"].feature_importances_, dtype=float)
    if (importance.shape != (len(preprocessing.get_feature_names_out()),)
            or not np.isfinite(importance).all() or (importance < 0).any()):
        raise ValueError("Model feature importances do not match its encoded predictor schema")
    values, counts = {}, {}
    for group, transformer, columns in preprocessing.transformers_:
        if group == "remainder":
            continue
        selected = importance[preprocessing.output_indices_[group]]
        if group == "numerical":
            values.update(zip(columns, selected))
            counts.update({name: 1 for name in columns})
        elif group == "nominal":
            offset = 0
            for name, categories in zip(columns, transformer.categories_):
                size = len(categories)
                values[name] = selected[offset:offset + size].sum()
                counts[name] = size
                offset += size
    return pd.DataFrame({
        "variable": names, "importance": [values[name] for name in names],
        "encoded_columns": [counts[name] for name in names],
        "importance_type": importance_type,
    }).sort_values("importance", ascending=False, kind="stable").reset_index(drop=True)


def _save_csv(frame, path):
    temporary = path.with_suffix(".partial.csv")
    try:
        frame.to_csv(temporary, index=False, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _save_roc(performance, curves, threshold, model_name, output_path):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    figure = Figure(figsize=(8, 7), layout="constrained")
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    for row in performance.itertuples():
        curve = curves[row.partition]
        if curve is not None:
            label = "Training (in-sample)" if row.partition == "training" else row.partition.capitalize()
            line, = axis.plot(*curve, linewidth=2, label=f"{label}: AUC = {row.roc_auc:.4f}")
            fpr = row.fp / (row.fp + row.tn) if row.fp + row.tn else 0.
            axis.scatter(fpr, row.recall, s=65, color=line.get_color(), edgecolors="white", zorder=4)
    axis.scatter([], [], s=65, color="black", label=f"Cost threshold = {threshold:.6g}")
    axis.plot([0, 1], [0, 1], "--", color="gray", linewidth=1, label="Chance")
    axis.set(xlim=(0, 1), ylim=(0, 1.01), xlabel="False positive rate", ylabel="True positive rate",
             title=f"{model_name}: selected raw predictors\nDots: minimum-cost threshold selected on training predictions")
    axis.legend(loc="lower right")
    axis.grid(alpha=.2)
    temporary = output_path.with_suffix(".partial.png")
    try:
        figure.savefig(temporary, dpi=160, format="png")
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
        figure.clear()


def run_tree_classifier(model_name, fit_function, input_path, output_dir, importance_type):
    """Fit training only, choose its cost threshold, and export heldout results."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    if any(output_dir.resolve().is_relative_to(path.resolve()) for path in
           (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR, config.CLEAN_DATA_DIR, config.INPUT_DATA_DIR)):
        raise ValueError("Model outputs must be separate from all source data directories")
    training, y_train, coverage = load_selected_partition(input_path, "training")
    names = training.columns.tolist()
    pipeline, cv = fit_function(training, y_train)
    training_probabilities = pipeline.predict_proba(training)[:, 1]
    del training
    threshold_info = optimize_threshold(y_train, training_probabilities)
    best = cv.loc[cv.selected].iloc[0]
    estimator = pipeline.named_steps["model"]
    common = {
        "model": model_name, "fit_partition": "training",
        "encoding": "raw_numerical_and_binary; training_fitted_one_hot_nominal",
        "selected_predictors": json.dumps(names),
        "target": config.FIRE_OUTPUT_COLUMNS[-1],
        "random_seed": config.RANDOM_SEED, "cv_folds": config.BASELINE_CV_FOLDS,
        "cv_mean_roc_auc": float(best.mean_roc_auc), "cv_std_roc_auc": float(best.std_roc_auc),
        "cv_selection_metric": best.get("selection_metric", "roc_auc"),
        "best_parameters": best.parameters,
        "model_parameters": json.dumps(estimator.get_params(), sort_keys=True, default=str),
        "cv_scope": "Shuffled stratified training rows; fixed full-training variable selection; encoding fit within folds",
        **{f"training_{name}": value for name, value in coverage.items()},
        **threshold_info,
        **{f"cost_{name}": value for name, value in config.BASELINE_CONFUSION_COSTS.items()},
    }
    if "mean_log_loss" in cv:
        common.update({
            "cv_mean_log_loss": float(best.mean_log_loss),
            "cv_std_log_loss": float(best.std_log_loss),
            "max_n_estimators": int(best.max_n_estimators),
            "refit_n_estimators": int(best.refit_n_estimators),
            "early_stopping_rounds": int(best.early_stopping_rounds),
            "early_stopping_fraction": float(best.early_stopping_fraction),
            "early_stopping_scope": "Within each outer fold's training rows; scoring fold and dated heldout partitions excluded",
            "refit_rounds_rule": "Median of selected candidate's best fold round counts, rounded up; full-training fit without early stopping",
        })
    performance, curves, probabilities_by_partition = [], {}, {}
    threshold = threshold_info["probability_threshold"]
    for partition in partition_dates():
        if partition == "training":
            y, metadata, probabilities = y_train, coverage, training_probabilities
        else:
            frame, y, metadata = load_selected_partition(input_path, partition)
            if frame.columns.tolist() != names:
                raise ValueError(f"Selected predictor order differs in {partition}")
            probabilities = pipeline.predict_proba(frame)[:, 1]
            del frame
        metrics, curves[partition] = partition_performance(y, probabilities, partition, threshold)
        metrics["log_loss"] = log_loss(y, probabilities, labels=[0, 1])
        metrics.update(common)
        metrics.update({"start": metadata["start"], "end": metadata["end"],
                        "evaluation": "in_sample" if partition == "training" else "held_out"})
        performance.append(metrics)
        probabilities_by_partition[partition] = probabilities
        LOGGER.info("%s: ROC-AUC=%.6f; TN=%s FP=%s FN=%s TP=%s", partition,
                    metrics["roc_auc"], metrics["tn"], metrics["fp"], metrics["fn"], metrics["tp"])
    performance = pd.DataFrame(performance)
    importance = feature_importances(pipeline, names, importance_type)
    for name in ("model", "fit_partition", "random_seed", "best_parameters"):
        importance[name] = common[name]
    for name, value in {"fit_partition": "training", "random_seed": config.RANDOM_SEED,
                        "cv_folds": config.BASELINE_CV_FOLDS,
                        **{f"training_{name}": value for name, value in coverage.items()}}.items():
        cv[name] = value
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame, suffix in ((cv, "cv_results.csv"), (importance, "feature_importances.csv"),
                          (performance, "performance.csv")):
        _save_csv(frame, output_dir / f"{model_name}_{suffix}")
    export_probabilities(input_path, probabilities_by_partition,
                         output_dir / f"{model_name}_probabilities.nc", common,
                         title=f"{model_name} fitted cell-day probabilities")
    _save_roc(performance, curves, threshold, model_name, output_dir / f"{model_name}_performance.png")
    LOGGER.info("Saved %s CV, importances, performance, ROC, and probabilities under %s", model_name, output_dir)
    return pipeline, importance, performance

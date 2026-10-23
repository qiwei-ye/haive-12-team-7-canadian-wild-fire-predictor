"""Training-only predictor binning and an L2 logistic regression baseline.

Bin: .venv/Scripts/python.exe -m src.baseline
Fit: .venv/Scripts/python.exe -m src.baseline --fit

Numerical predictors use exactly five OptBinning intervals. Categorical
predictors, including binary fire-history flags, keep one bin per observed
training category. Regression uses selected data/inputs predictors and the
existing WoE values, with five-fold stratified CV to select C. Bins and prior
variable selection are fixed, so CV is conditional on full-training preprocessing.
"""

import argparse
import json
import logging
from pathlib import Path
import warnings

import numpy as np
from optbinning import OptimalBinning
import pandas as pd
import xarray as xr
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits

from . import config
from .data_merge import partition_dates


LOGGER = logging.getLogger(__name__)


def predictor_types():
    """Derive the predictor list from the existing merge configuration."""
    names = (
        *(name for fields in config.MERGE_STATIC_PREDICTORS.values() for name in fields),
        *config.CLIMATE_VARIABLES,
        *config.ROLLING_WEATHER_FEATURES,
        *config.FIRE_HISTORY_VARIABLES,
    )
    return {name: "categorical" if name in config.BINNING_CATEGORICAL_PREDICTORS else "numerical"
            for name in names}


def load_training_data(input_path=None):
    """Select training times before reading any predictor or target values."""
    path = Path(input_path) if input_path is not None else config.CLEAN_DATA_DIR / config.CLEAN_MERGED_FILENAME
    target_name = config.FIRE_OUTPUT_COLUMNS[-1]
    names = [*predictor_types(), target_name]
    if not path.is_file():
        raise FileNotFoundError(f"Clean merged data is missing: {path}; run the merge stage first")
    with xr.open_dataset(path) as source:
        if "partition" not in source or source.partition.dims != ("time",):
            raise ValueError("Merged data must contain partition(time)")
        missing = set(names) - set(source.data_vars)
        if missing:
            raise ValueError(f"Merged data is missing predictors/target: {sorted(missing)}")
        positions = np.flatnonzero(source.partition.values == "training")
        dates = pd.DatetimeIndex(source.time.values[positions])
        if not dates.equals(partition_dates()["training"]):
            raise ValueError("Training dates do not match the configured chronological training partition")
        training = source[names].isel(time=positions)
        target = training[target_name]
        if target.dims != ("time", "cell"):
            raise ValueError(f"Expected {target_name}(time, cell)")
        frame = pd.DataFrame({name: training[name].broadcast_like(target).transpose("time", "cell")
                              .values.reshape(-1) for name in names})
        metadata = {
            "fit_partition": "training", "training_start": dates[0].date().isoformat(),
            "training_end": dates[-1].date().isoformat(), "training_days": len(dates),
            "training_rows": len(frame), "target": target_name,
        }
        units = {name: training[name].attrs.get("units", "1") for name in predictor_types()}
    return frame, metadata, units


def fit_variable(name, values, target, variable_type):
    """Build one predictor's bins, counts, empirical WoE, and IV.

    WoE = log(non-event distribution / event distribution), with target 1
    denoting a large fire. No smoothing or artificial observations are added.
    A populated bin with no events/non-events has +inf/-inf WoE and infinite IV.
    Missing observations, when present, have their own additional bin.
    """
    values = np.asarray(values, dtype=float)
    target = np.asarray(target)
    if values.ndim != 1 or target.ndim != 1 or len(values) != len(target) or not len(values):
        raise ValueError(f"{name}: expected nonempty, equally sized predictor and target vectors")
    if not np.isin(target, [0, 1]).all() or np.unique(target).size != 2:
        raise ValueError("Training target must contain both 0 and 1, without missing values")
    if np.isinf(values).any():
        raise ValueError(f"{name}: infinite predictor values are unsupported")
    observed = values[~np.isnan(values)]
    if not observed.size:
        raise ValueError(f"{name}: no observed training values")

    rows = []
    if variable_type == "numerical":
        count = config.BINNING_NUMERICAL_BINS
        if np.unique(observed).size < count:
            raise ValueError(f"{name}: fewer than {count} distinct values; cannot construct {count} numerical bins")
        model = OptimalBinning(
            name=name, dtype="numerical", min_n_bins=count, max_n_bins=count,
            monotonic_trend=None, random_state=config.RANDOM_SEED,
        ).fit(values, target)
        if model.status != "OPTIMAL" or len(model.splits) + 1 != count:
            raise ValueError(f"{name}: exactly {count} optimal numerical bins unavailable (status={model.status})")
        table = model.binning_table.build(add_totals=False)
        bounds = np.r_[-np.inf, model.splits, np.inf]
        for i in range(count):
            lower, upper = map(float, bounds[i:i + 2])
            rows.append({"bin_type": "interval", "bin": f"[{lower!r}, {upper!r})",
                         "lower_bound": lower, "upper_bound": upper, "category": np.nan,
                         "non_event": int(table.iloc[i]["Non-event"]), "event": int(table.iloc[i]["Event"])})
        method, status = "OptBinning", model.status
    elif variable_type == "categorical":
        # Direct singleton bins prevent OptBinning's pure-bin refinement from
        # merging categories with zero events or zero non-events.
        for category in np.unique(observed):
            selected = values == category
            events = int(target[selected].sum())
            rows.append({"bin_type": "category", "bin": str(category),
                         "lower_bound": np.nan, "upper_bound": np.nan, "category": category,
                         "non_event": int(selected.sum()) - events, "event": events})
        method, status = "one_category_per_bin", "FIXED"
    else:
        raise ValueError(f"Unknown predictor type: {variable_type}")

    missing = np.isnan(values)
    regular_bins = len(rows)
    if missing.any():
        events = int(target[missing].sum())
        rows.append({"bin_type": "missing", "bin": "Missing", "lower_bound": np.nan,
                     "upper_bound": np.nan, "category": np.nan,
                     "non_event": int(missing.sum()) - events, "event": events})
    result = pd.DataFrame(rows)
    result.insert(0, "bin_id", np.arange(len(result)))
    result.insert(0, "variable_type", variable_type)
    result.insert(0, "variable", name)
    result["count"] = result.non_event + result.event
    result["count_fraction"] = result["count"] / len(target)
    result["event_rate"] = result.event / result["count"]
    result["non_event_distribution"] = result.non_event / (target == 0).sum()
    result["event_distribution"] = result.event / (target == 1).sum()
    with np.errstate(divide="ignore"):
        result["woe"] = np.log(result.non_event_distribution / result.event_distribution)
    result["iv"] = (result.non_event_distribution - result.event_distribution) * result.woe
    result["variable_iv"] = result.iv.sum()
    result["woe_status"] = np.select([result.event.eq(0), result.non_event.eq(0)],
                                     ["zero_events", "zero_non_events"], default="finite")
    result["regular_bins"] = regular_bins
    result["method"], result["solver_status"] = method, status
    if result["count"].sum() != len(target):
        raise ValueError(f"{name}: bin counts do not cover every training row")
    return result


def run_binning(input_path=None, output_path=None):
    """Fit on all training rows and write the bin documentation atomically."""
    destination = Path(output_path) if output_path is not None else config.BINNING_OUTPUT_PATH
    if any(destination.resolve().is_relative_to(path.resolve()) for path in
           (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR, config.CLEAN_DATA_DIR)):
        raise ValueError("Binning output must be separate from raw, processed, and cleaned data")
    training, metadata, units = load_training_data(input_path)
    target = training[metadata["target"]].to_numpy()
    LOGGER.info("Fitting bins on %s training rows (%s to %s; %s large-fire targets)",
                len(training), metadata["training_start"], metadata["training_end"], int(target.sum()))
    tables = []
    for name, variable_type in predictor_types().items():
        table = fit_variable(name, training[name].to_numpy(), target, variable_type)
        table["units"] = units[name]
        tables.append(table)
        LOGGER.info("%s: %s %s bins; IV=%s", name, table.regular_bins.iloc[0], variable_type,
                    table.variable_iv.iloc[0])
    result = pd.concat(tables, ignore_index=True)
    for name, value in metadata.items():
        result[name] = value
    result["training_events"] = int(target.sum())
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.csv")
    try:
        result.to_csv(temporary, index=False, encoding="utf-8")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    LOGGER.info("Saved %s (%s predictors, %s bin rows)", destination, len(tables), len(result))
    return result


def load_model_partition(input_path, partition):
    """Read one selected-input partition, keeping metadata out of predictors."""
    target_name = config.FIRE_OUTPUT_COLUMNS[-1]
    with xr.open_dataset(input_path) as source:
        if "partition" not in source or source.partition.dims != ("time",):
            raise ValueError("Model inputs must contain partition(time)")
        names = [name for name in source.data_vars if name in predictor_types()]
        if not names or set(source.data_vars) != {*names, target_name, "partition"}:
            raise ValueError("Model input schema must contain selected predictors, target, and partition")
        if "selected_predictors" in source.attrs and set(json.loads(source.attrs["selected_predictors"])) != set(names):
            raise ValueError("Model inputs disagree with their selected-predictor metadata")
        positions = np.flatnonzero(source.partition.values == partition)
        dates = pd.DatetimeIndex(source.time.values[positions])
        if not dates.equals(partition_dates()[partition]):
            raise ValueError(f"Model input dates differ from the configured {partition} partition")
        subset = source[names + [target_name]].isel(time=positions)
        target = subset[target_name]
        if target.dims != ("time", "cell"):
            raise ValueError(f"Expected {target_name}(time, cell)")
        frame = pd.DataFrame({name: subset[name].broadcast_like(target).transpose("time", "cell")
                              .values.reshape(-1) for name in names})
        y = target.values.reshape(-1)
        if not np.isin(y, [0, 1]).all():
            raise ValueError(f"{partition} target must contain only 0 and 1 without missing values")
        metadata = {"start": dates[0].date().isoformat(), "end": dates[-1].date().isoformat(),
                    "days": len(dates), "rows": len(y), "events": int(y.sum())}
    return frame, y, metadata


def transform_woe(frame, bins):
    """Apply exact existing intervals/categories; never fit or invent a WoE."""
    transformed = np.empty(frame.shape, dtype=np.float64)
    for column, name in enumerate(frame.columns):
        table = bins.loc[bins.variable.eq(name)].sort_values("bin_id")
        if table.empty or table.bin_id.duplicated().any():
            raise ValueError(f"Missing or duplicate WoE bins: {name}")
        regular = table.loc[table.bin_type.ne("missing")]
        if regular.empty:
            raise ValueError(f"No regular WoE bins available: {name}")
        values = frame[name].to_numpy(dtype=float)
        missing = np.isnan(values)
        encoded = np.full(len(values), np.nan)
        if np.isinf(values).any():
            raise ValueError(f"Infinite model predictor: {name}")
        if regular.bin_type.eq("interval").all():
            lower, upper = regular.lower_bound.to_numpy(), regular.upper_bound.to_numpy()
            if (not np.isneginf(lower[0]) or not np.isposinf(upper[-1])
                    or not np.array_equal(lower[1:], upper[:-1]) or not (lower < upper).all()):
                raise ValueError(f"WoE intervals have gaps, overlaps, or invalid bounds: {name}")
            indices = np.searchsorted(upper[:-1], values[~missing], side="right")
            encoded[~missing] = regular.woe.to_numpy()[indices]
        elif regular.bin_type.eq("category").all():
            if regular.category.isna().any() or regular.category.duplicated().any():
                raise ValueError(f"Invalid singleton category bins: {name}")
            lookup = pd.Series(regular.woe.to_numpy(), index=regular.category.to_numpy())
            encoded[~missing] = pd.Series(values[~missing]).map(lookup).to_numpy()
        else:
            raise ValueError(f"Invalid regular WoE bin types: {name}")
        if missing.any():
            missing_bin = table.loc[table.bin_type.eq("missing"), "woe"]
            if len(missing_bin) == 1:
                encoded[missing] = missing_bin.iloc[0]
        if not np.isfinite(encoded).all():
            raise ValueError(f"Unavailable/non-finite WoE or unseen category for {name}; rebuild or review binning")
        transformed[:, column] = encoded
    return transformed


def fit_logistic_regression(features, target):
    """Select C using only stratified training folds, then refit all training rows."""
    features = np.asarray(features, dtype=np.float64, order="C")
    target = np.asarray(target)
    if not np.isfinite(features).all() or not np.isin(target, [0, 1]).all():
        raise ValueError("Logistic regression requires finite WoE and binary targets")
    if np.unique(target).size != 2 or np.bincount(target.astype(int)).min() < config.BASELINE_CV_FOLDS:
        raise ValueError("Each target class must have at least one observation per CV fold")
    candidates = np.asarray(config.BASELINE_C_GRID, dtype=float)
    if not candidates.size or not np.isfinite(candidates).all() or not (candidates > 0).all():
        raise ValueError("The baseline C grid must contain positive finite values")
    candidates = np.sort(np.unique(candidates))
    splitter = StratifiedKFold(n_splits=config.BASELINE_CV_FOLDS, shuffle=True, random_state=config.RANDOM_SEED)
    scores = np.empty((config.BASELINE_CV_FOLDS, len(candidates)))

    def estimator(c, warm_start=False):
        return LogisticRegression(
            C=c, l1_ratio=0.0, solver=config.BASELINE_SOLVER,
            max_iter=config.BASELINE_MAX_ITER, tol=config.BASELINE_TOLERANCE,
            random_state=config.RANDOM_SEED, warm_start=warm_start,
        )

    # One fold at a time avoids duplicating millions of rows in worker processes.
    # Warm starts share coefficients only between C values within the same fold.
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        try:
            for fold, (train, valid) in enumerate(splitter.split(features, target)):
                x_train, x_valid = features[train], features[valid]
                y_train, y_valid = target[train], target[valid]
                model = estimator(candidates[0], warm_start=True)
                for column, c in enumerate(candidates):
                    model.set_params(C=c).fit(x_train, y_train)
                    scores[fold, column] = roc_auc_score(y_valid, model.predict_proba(x_valid)[:, 1])
                    LOGGER.info("CV fold %s/%s: C=%g; ROC-AUC=%.6f", fold + 1, config.BASELINE_CV_FOLDS,
                                c, scores[fold, column])
            means, deviations = scores.mean(axis=0), scores.std(axis=0)
            best = int(np.argmax(means))  # Equal means favour the smallest C.
            fitted = estimator(candidates[best]).fit(features, target)
        except ConvergenceWarning as error:
            raise ValueError(f"Logistic regression did not converge: {error}") from error
    cv = pd.DataFrame({"C": candidates, "mean_roc_auc": means, "std_roc_auc": deviations})
    cv["fold_roc_auc"] = [scores[:, i].tolist() for i in range(len(candidates))]
    LOGGER.info("Selected C=%g; mean CV ROC-AUC=%.6f (+/- %.6f)", fitted.C, means[best], deviations[best])
    return fitted, cv


def optimize_threshold(target, probabilities):
    """Minimize empirical training cost over every distinct probability cutoff.

    Tied predictions enter together under the rule probability >= threshold.
    Include the unflag-everything option; equal costs favour fewer flagged rows.
    """
    target, probabilities = np.asarray(target), np.asarray(probabilities)
    if target.ndim != 1 or probabilities.shape != target.shape or np.unique(target).size != 2 or not np.isin(target, [0, 1]).all():
        raise ValueError("Threshold optimization needs equally sized binary targets containing both classes")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Threshold probabilities must be finite values between 0 and 1")
    costs = config.BASELINE_CONFUSION_COSTS
    if set(costs) != {"tn", "fp", "fn", "tp"} or not all(np.isfinite(v) and v >= 0 for v in costs.values()):
        raise ValueError("Confusion costs must specify finite, nonnegative tn/fp/fn/tp costs")
    fpr, tpr, thresholds = roc_curve(target, probabilities, drop_intermediate=False)
    positives, negatives = int(target.sum()), int((target == 0).sum())
    tp = np.rint(tpr * positives).astype(np.int64)
    fp = np.rint(fpr * negatives).astype(np.int64)
    total = costs["tp"] * tp + costs["fp"] * fp + costs["fn"] * (positives - tp) + costs["tn"] * (negatives - fp)
    best = int(np.argmin(total))
    threshold = thresholds[best]
    if np.isinf(threshold):
        threshold = np.nextafter(probabilities.max(), np.inf)
    return {"probability_threshold": float(threshold), "threshold_fit_partition": "training",
            "threshold_objective": "Minimum training total confusion cost; ties favour fewer flags",
            "threshold_training_cost": float(total[best])}


def partition_performance(target, probabilities, partition, threshold):
    """Return a binary confusion matrix and probability-based ROC-AUC."""
    probabilities = np.asarray(probabilities)
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Predicted probabilities must be finite values between 0 and 1")
    predicted = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(target, predicted, labels=[0, 1]).ravel()
    total_cost = sum(config.BASELINE_CONFUSION_COSTS[name] * count
                     for name, count in zip(("tn", "fp", "fn", "tp"), (tn, fp, fn, tp)))
    both_classes = np.unique(target).size == 2
    auc = roc_auc_score(target, probabilities) if both_classes else np.nan
    return {"partition": partition, "rows": len(target), "actual_positive": int(tp + fn),
            "predicted_positive": int(tp + fp), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "roc_auc": auc, "probability_threshold": threshold,
            "precision": tp / (tp + fp) if tp + fp else 0.,
            "recall": tp / (tp + fn) if tp + fn else 0.,
            "specificity": tn / (tn + fp) if tn + fp else 0.,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.,
            "accuracy": (tp + tn) / len(target),
            "total_cost": total_cost, "cost_per_row": total_cost / len(target),
            "unflagged_cost": config.BASELINE_CONFUSION_COSTS["tn"] * (tn + fp) + config.BASELINE_CONFUSION_COSTS["fn"] * (tp + fn),
            }, (roc_curve(target, probabilities)[:2] if both_classes else None)


def run_classifier(input_path=None, binning_path=None, output_dir=None):
    """Fit selected WoE predictors; export coefficients, partition metrics, and ROC."""
    input_path = Path(input_path) if input_path is not None else config.INPUT_DATA_DIR / config.CLEAN_MERGED_FILENAME
    binning_path = Path(binning_path) if binning_path is not None else config.BINNING_OUTPUT_PATH
    output_dir = Path(output_dir) if output_dir is not None else config.OUTPUTS_DIR
    if any(output_dir.resolve().is_relative_to(path.resolve()) for path in
           (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR, config.CLEAN_DATA_DIR, config.INPUT_DATA_DIR)):
        raise ValueError("Baseline outputs must be separate from source data directories")
    training, y_train, coverage = load_model_partition(input_path, "training")
    names = training.columns.tolist()
    bins = pd.read_csv(binning_path, float_precision="round_trip")
    fit_metadata = {"fit_partition": "training", **{f"training_{name}": value for name, value in coverage.items()}}
    required = {"variable", "bin_id", "bin_type", "woe", "count", "event", *fit_metadata}
    if not required.issubset(bins.columns):
        raise ValueError(f"Existing WoE report fields missing: {sorted(required - set(bins.columns))}")
    selected_bins = bins.loc[bins.variable.isin(names)]
    for name, value in fit_metadata.items():
        if name not in bins or not selected_bins[name].eq(value).all():
            raise ValueError(f"Existing WoE fit metadata differs from training inputs: {name}")
    for name in names:
        table = selected_bins.loc[selected_bins.variable.eq(name)]
        if table["count"].sum() != len(y_train) or table.event.sum() != y_train.sum():
            raise ValueError(f"Existing bin counts differ from training inputs: {name}")
    x_train = transform_woe(training, bins)
    del training
    model, cv = fit_logistic_regression(x_train, y_train)
    coefficients, performance = evaluate_classifier(
        model, cv, names, input_path, bins, output_dir, training_data=(x_train, y_train, coverage))
    return model, coefficients, performance


def evaluate_classifier(model, cv, names, input_path, bins, output_dir, training_data=None):
    """Choose the training-cost threshold, then evaluate all partitions and export."""
    output_dir = Path(output_dir)
    if any(output_dir.resolve().is_relative_to(path.resolve()) for path in
           (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR, config.CLEAN_DATA_DIR, config.INPUT_DATA_DIR)):
        raise ValueError("Baseline outputs must be separate from source data directories")
    if training_data is None:
        training, y_train, coverage = load_model_partition(input_path, "training")
        if training.columns.tolist() != names:
            raise ValueError("Predictor order differs from fitted coefficients")
        x_train = transform_woe(training, bins)
        del training
    else:
        x_train, y_train, coverage = training_data
    with threadpool_limits(limits=1):
        training_probabilities = model.predict_proba(x_train)[:, 1]
    threshold_info = optimize_threshold(y_train, training_probabilities)
    threshold = threshold_info["probability_threshold"]
    LOGGER.info("Training-cost-optimal threshold=%.12g; total cost=%g", threshold, threshold_info["threshold_training_cost"])
    fit_metadata = {"fit_partition": "training", **{f"training_{name}": value for name, value in coverage.items()}}
    best = cv.loc[cv.C.eq(model.C)].iloc[0]
    common = {"C": model.C, "inverse_C": 1 / model.C, "penalty": "l2", "encoding": "existing_training_woe",
              "target": config.FIRE_OUTPUT_COLUMNS[-1],
              "cv_folds": config.BASELINE_CV_FOLDS, "random_seed": config.RANDOM_SEED,
              "cv_mean_roc_auc": best.mean_roc_auc, "cv_std_roc_auc": best.std_roc_auc,
              "cv_scope": "Shuffled stratified training rows; fixed full-training binning and variable selection",
              **fit_metadata, **threshold_info,
              **{"cost_" + name: cost for name, cost in config.BASELINE_CONFUSION_COSTS.items()}}
    coefficients = pd.DataFrame({"variable": ["intercept", *names],
                                 "coefficient": np.r_[model.intercept_, model.coef_[0]]})
    coefficients["odds_ratio"] = np.exp(coefficients.coefficient)
    for name, value in common.items():
        coefficients[name] = value
    performance, curves = [], {}
    for partition in partition_dates():
        if partition == "training":
            y, metadata, probabilities = y_train, coverage, training_probabilities
        else:
            frame, y, metadata = load_model_partition(input_path, partition)
            if frame.columns.tolist() != names:
                raise ValueError(f"Predictor order differs in {partition}")
            x = transform_woe(frame, bins)
            del frame
            with threadpool_limits(limits=1):
                probabilities = model.predict_proba(x)[:, 1]
        metrics, curve = partition_performance(y, probabilities, partition, threshold)
        metrics.update(common)
        metrics.update({"start": metadata["start"], "end": metadata["end"],
                        "evaluation": "in_sample" if partition == "training" else "held_out",
                        "cv_auc_by_C": cv.to_json(orient="records", double_precision=12)})
        performance.append(metrics)
        curves[partition] = curve
        LOGGER.info("%s: ROC-AUC=%.6f; TN=%s FP=%s FN=%s TP=%s", partition, metrics["roc_auc"],
                    metrics["tn"], metrics["fp"], metrics["fn"], metrics["tp"])
    performance = pd.DataFrame(performance)
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame, filename in ((coefficients, config.BASELINE_COEFFICIENTS_PATH.name),
                            (performance, config.BASELINE_PERFORMANCE_PATH.name)):
        path = output_dir / filename
        temporary = path.with_suffix(".partial.csv")
        try:
            frame.to_csv(temporary, index=False, encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

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
            false_positive_rate = row.fp / (row.fp + row.tn) if row.fp + row.tn else 0.
            axis.scatter(false_positive_rate, row.recall, s=65, color=line.get_color(),
                         edgecolors="white", linewidths=.8, zorder=4, clip_on=False)
    axis.scatter([], [], s=65, color="black", edgecolors="white", label=f"Cost threshold = {threshold:.6g}")
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1, label="Chance")
    axis.set(xlim=(0, 1), ylim=(0, 1.01), xlabel="False positive rate", ylabel="True positive rate",
             title=f"L2 logistic regression on selected WoE predictors\nC = {model.C:g}; {config.BASELINE_CV_FOLDS}-fold training CV AUC = {best.mean_roc_auc:.4f}\nDots: minimum-cost threshold selected on training predictions")
    axis.legend(loc="lower right")
    axis.grid(alpha=.2)
    path = output_dir / config.BASELINE_ROC_PATH.name
    temporary = path.with_suffix(".partial.png")
    try:
        figure.savefig(temporary, dpi=160, format="png")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
        figure.clear()
    LOGGER.info("Saved baseline coefficients, performance, and ROC plot under %s", output_dir)
    return coefficients, performance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fit", action="store_true", help="Fit the selected-input L2 logistic regression instead of generating bins")
    parser.add_argument("--input", type=Path, help="Default: data/inputs/merged.nc with --fit; data/clean/merged.nc for binning")
    parser.add_argument("--output", type=Path, default=config.BINNING_OUTPUT_PATH)
    parser.add_argument("--binning", type=Path, default=config.BINNING_OUTPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=config.OUTPUTS_DIR)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        if args.fit:
            run_classifier(args.input, args.binning, args.output_dir)
        else:
            run_binning(args.input, args.output)
    except (FileNotFoundError, ValueError, OSError) as error:
        LOGGER.error("Baseline failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

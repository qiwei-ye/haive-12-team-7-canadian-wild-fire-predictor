"""Fit predictor bins and WoE using only the configured training partition.

Run: .venv/Scripts/python.exe -m src.baseline

Numerical predictors use exactly five OptBinning intervals. Categorical
predictors, including binary fire-history flags, keep one bin per observed
training category. No model is trained and no cleaned data are modified.
"""

import argparse
import logging
from pathlib import Path

import numpy as np
from optbinning import OptimalBinning
import pandas as pd
import xarray as xr

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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=config.CLEAN_DATA_DIR / config.CLEAN_MERGED_FILENAME)
    parser.add_argument("--output", type=Path, default=config.BINNING_OUTPUT_PATH)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run_binning(args.input, args.output)
    except (FileNotFoundError, ValueError, OSError) as error:
        LOGGER.error("Binning failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

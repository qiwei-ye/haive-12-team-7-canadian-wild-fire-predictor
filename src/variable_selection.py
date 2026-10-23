"""Select raw predictors by training IV and correlation, then export data/inputs.

Run: .venv/Scripts/python.exe -m src.variable_selection

Read existing training-only binning statistics; do not refit bins. In descending
IV order, reject a predictor if abs(Pearson r) with an earlier retained predictor
exceeds the configured threshold. Nominal land cover bypasses this filter.
Export the same selected columns for training, validation, and test.
"""

import argparse
import csv
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from . import config
from .baseline import load_training_data, predictor_types
from .data_merge import partition_dates


LOGGER = logging.getLogger(__name__)


def read_iv(path, training, metadata):
    """Check existing IV statistics describe the current training partition."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Binning report missing: {path}; run python -m src.baseline first")
    bins = pd.read_csv(path, float_precision="round_trip")
    required = {"variable", "variable_iv", "iv", "count", "event", *metadata, "training_events"}
    if not required.issubset(bins.columns):
        raise ValueError(f"Binning report fields missing: {sorted(required - set(bins.columns))}")
    if set(bins.variable) != set(predictor_types()):
        raise ValueError("Binning report predictors differ from the configured predictors")
    for name, expected in {**metadata, "training_events": int(training[metadata["target"]].sum())}.items():
        if not bins[name].eq(expected).all():
            raise ValueError(f"Binning report {name} differs from current training data; rebuild binning first")
    result = {}
    for name, rows in bins.groupby("variable", sort=False):
        if (rows.variable_iv.nunique() != 1 or rows.variable_iv.isna().any()
                or (rows.variable_iv < 0).any() or not np.isclose(rows.iv.sum(), rows.variable_iv.iloc[0])
                or rows["count"].sum() != len(training)
                or rows.event.sum() != int(training[metadata["target"]].sum())):
            raise ValueError(f"Invalid or inconsistent training binning statistics: {name}")
        result[name] = rows.variable_iv.iloc[0]
    return pd.Series(result, name="iv", dtype=float)


def select_variables(iv, correlation, threshold=None, nominal_predictors=None):
    """Greedily keep IV-ranked predictors, comparing only with retained ones."""
    threshold = config.VARIABLE_SELECTION_CORRELATION_THRESHOLD if threshold is None else threshold
    nominal = set(config.VARIABLE_SELECTION_NOMINAL_PREDICTORS if nominal_predictors is None else nominal_predictors)
    if not 0 <= threshold <= 1:
        raise ValueError("Correlation threshold must be between 0 and 1")
    if iv.empty or iv.index.has_duplicates or iv.isna().any() or iv.lt(0).any():
        raise ValueError("IV values must have unique predictor names and nonnegative, nonmissing values")
    numeric = [name for name in iv.index if name not in nominal]
    if not set(iv.index).issubset(correlation.index) or not set(iv.index).issubset(correlation.columns):
        raise ValueError("Correlation matrix must include every predictor")
    core = correlation.loc[numeric, numeric].to_numpy()
    if (not np.isfinite(core).all() or not np.allclose(core, core.T)
            or (np.abs(core) > 1 + 1e-12).any() or not np.allclose(np.diag(core), 1)):
        raise ValueError("Training Pearson correlations are undefined or invalid; check constant predictors")
    retained, records = [], []
    for rank, (name, value) in enumerate(iv.sort_values(ascending=False, kind="stable").items(), 1):
        conflicts = [(other, correlation.loc[name, other]) for other in retained
                     if name not in nominal and other not in nominal
                     and abs(correlation.loc[name, other]) > threshold]
        blocker, coefficient = conflicts[0] if conflicts else ("", np.nan)
        selected = not conflicts
        records.append({"rank": rank, "variable": name, "iv": value, "selected": selected,
                        "dropped_for": blocker, "correlation_with_retained": coefficient,
                        "correlation_filter": "nominal_exempt" if name in nominal else "absolute_pearson",
                        "correlation_threshold": threshold})
        if selected:
            retained.append(name)
    result = pd.DataFrame(records)
    for name in result.variable:
        result[f"corr_{name}"] = result.variable.map(correlation[name])
    return result


def export_inputs(clean_dir, output_dir, selection):
    """Project daily CSV text and the matching NetCDF; source files stay intact."""
    clean_dir, output_dir = Path(clean_dir), Path(output_dir)
    if (any(output_dir.resolve().is_relative_to(path.resolve())
            for path in (clean_dir, config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR))
            or clean_dir.resolve().is_relative_to(output_dir.resolve())):
        raise ValueError("Input outputs must be separate from clean, raw, and processed source directories")
    selected = selection.loc[selection.selected, "variable"].tolist()
    dropped = selection.loc[~selection.selected, "variable"].tolist()
    summary = json.loads((clean_dir / "merge_summary.json").read_text(encoding="utf-8"))
    original_columns = summary["columns"]
    predictors = set(selection.variable)
    target = config.FIRE_OUTPUT_COLUMNS[-1]
    if set(original_columns) != {"date", "cell", "lat", "lon", target, *predictors}:
        raise ValueError("Clean CSV schema differs from the variable-selection schema")
    columns = [name for name in original_columns if name not in predictors or name in selected]
    indices = [original_columns.index(name) for name in columns]
    partitions = partition_dates()
    entries = [(partition, day, clean_dir / partition / f"{day.date().isoformat()}.csv")
               for partition, dates in partitions.items() for day in dates]
    expected = {path for _, _, path in entries}
    actual = {path for partition in partitions for path in (clean_dir / partition).glob("*.csv")}
    if actual != expected:
        raise ValueError("Clean CSV inventory differs from the configured partition dates")
    desired = {output_dir / path.relative_to(clean_dir) for path in expected}
    existing = {path for partition in partitions for path in (output_dir / partition).glob("*.csv")}
    if existing - desired:
        raise ValueError("Input destination has unexpected daily CSVs; choose an empty destination")
    with xr.open_dataset(clean_dir / config.CLEAN_MERGED_FILENAME) as source:
        expected_dates = pd.DatetimeIndex(np.concatenate([days.values for days in partitions.values()]))
        expected_labels = np.concatenate([np.repeat(name, len(days)) for name, days in partitions.items()])
        if (not pd.DatetimeIndex(source.time.values).equals(expected_dates)
                or not np.array_equal(source.partition.values, expected_labels)):
            raise ValueError("Clean NetCDF dates/partitions differ from the configured CSV dates")
        if not {target, "partition", *selected}.issubset(source.data_vars):
            raise ValueError("Clean NetCDF is missing a selected predictor, target, or partition")
    for number, (partition, day, path) in enumerate(entries, 1):
        destination = output_dir / partition / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".partial.csv")
        try:
            with path.open("r", newline="", encoding="utf-8") as incoming, temporary.open("w", newline="", encoding="utf-8") as outgoing:
                reader, writer = csv.reader(incoming), csv.writer(outgoing, lineterminator="\n")
                if next(reader) != original_columns:
                    raise ValueError(f"Clean CSV header differs from metadata: {path}")
                writer.writerow(columns)
                rows = 0
                for row in reader:
                    if len(row) != len(original_columns) or row[original_columns.index("date")] != day.date().isoformat():
                        raise ValueError(f"Invalid clean CSV row: {path}")
                    writer.writerow([row[i] for i in indices])
                    rows += 1
                if rows != summary["spatial_cells_per_day"]:
                    raise ValueError(f"Unexpected cell count: {path}")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        if number % 365 == 0:
            LOGGER.info("Exported %s daily input CSVs", number)

    selection_metadata = {
        "method": "Descending training IV; reject when absolute Pearson correlation with an earlier retained predictor exceeds threshold",
        "correlation_threshold": config.VARIABLE_SELECTION_CORRELATION_THRESHOLD,
        "correlation_data": "Raw training predictors; binary flags included; nominal predictors exempt",
        "nominal_predictors": list(config.VARIABLE_SELECTION_NOMINAL_PREDICTORS),
        "selected_predictors": selected, "dropped_predictors": dropped,
        "fit_partition": "training", "source_clean_dir": str(clean_dir.resolve()),
        "value_representation": "Original cleaned values; no WoE transform or further imputation",
    }
    with xr.open_dataset(clean_dir / config.CLEAN_MERGED_FILENAME) as source:
        keep = [name for name in source.data_vars if name in {*selected, target, "partition"}]
        subset = source[keep].copy()
        subset.attrs.update({"source_columns": json.dumps(columns),
                             "selected_predictors": json.dumps(selected), "dropped_predictors": json.dumps(dropped),
                             "variable_selection_method": selection_metadata["method"],
                             "variable_selection_fit_partition": "training",
                             "variable_selection_correlation_threshold": config.VARIABLE_SELECTION_CORRELATION_THRESHOLD})
        temporary = output_dir / "merged.partial.nc"
        try:
            subset.to_netcdf(temporary, engine="netcdf4")
            temporary.replace(output_dir / config.CLEAN_MERGED_FILENAME)
        finally:
            temporary.unlink(missing_ok=True)
    summary["columns"] = columns
    summary["units"] = {name: unit for name, unit in summary["units"].items() if name in columns}
    summary["definitions"] = {name: value for name, value in summary["definitions"].items() if name not in dropped}
    summary["merged_netcdf"]["static_variables"] = [name for name in summary["merged_netcdf"]["static_variables"] if name in selected]
    summary["variable_selection"] = selection_metadata
    temporary = output_dir / "merge_summary.partial.json"
    try:
        temporary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output_dir / "merge_summary.json")
    finally:
        temporary.unlink(missing_ok=True)
    LOGGER.info("Saved %s daily CSVs and merged.nc under %s", len(entries), output_dir)


def run_selection(clean_dir=None, output_dir=None, binning_path=None, report_path=None):
    clean_dir = Path(clean_dir) if clean_dir is not None else config.CLEAN_DATA_DIR
    output_dir = Path(output_dir) if output_dir is not None else config.INPUT_DATA_DIR
    binning_path = Path(binning_path) if binning_path is not None else config.BINNING_OUTPUT_PATH
    report_path = Path(report_path) if report_path is not None else config.VARIABLE_SELECTION_OUTPUT_PATH
    if any(report_path.resolve().is_relative_to(path.resolve())
           for path in (clean_dir, config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR)) or report_path.resolve() == binning_path.resolve():
        raise ValueError("Selection report must be separate from source data and binning statistics")
    training, metadata, _ = load_training_data(clean_dir / config.CLEAN_MERGED_FILENAME)
    iv = read_iv(binning_path, training, metadata)
    numeric = [name for name in iv.index if name not in config.VARIABLE_SELECTION_NOMINAL_PREDICTORS]
    correlation = training[numeric].corr(method="pearson").reindex(index=iv.index, columns=iv.index)
    result = select_variables(iv, correlation)
    for name, value in metadata.items():
        result[name] = value
    result["training_events"] = int(training[metadata["target"]].sum())
    del training
    LOGGER.info("Training-only selection: %s retained; %s dropped", int(result.selected.sum()), int((~result.selected).sum()))
    export_inputs(clean_dir, output_dir, result)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(".partial.csv")
    try:
        result.to_csv(temporary, index=False, encoding="utf-8")
        temporary.replace(report_path)
    finally:
        temporary.unlink(missing_ok=True)
    LOGGER.info("Saved IV rankings, selection decisions, and full training correlation matrix to %s", report_path)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clean-dir", type=Path, default=config.CLEAN_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=config.INPUT_DATA_DIR)
    parser.add_argument("--binning", type=Path, default=config.BINNING_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=config.VARIABLE_SELECTION_OUTPUT_PATH)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run_selection(args.clean_dir, args.output_dir, args.binning, args.report)
    except (FileNotFoundError, ValueError, OSError) as error:
        LOGGER.error("Variable selection failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

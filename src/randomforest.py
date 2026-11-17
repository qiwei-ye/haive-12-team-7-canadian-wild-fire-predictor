"""Random forest on selected raw predictors; no binning or WoE.

Fit explicitly: .venv/Scripts/python.exe -m src.randomforest --fit

The 27 configured combinations use five shuffled stratified training folds and
ROC-AUC scoring. Each tree draws 80% of the current fold's training rows with
replacement. Nominal land cover is one-hot encoded inside each fold; max_features
counts the resulting model input columns. No model runs on import or without --fit.
"""

import argparse
import logging
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier

from . import config
from .tree_models import fit_tree_classifier, run_tree_classifier


LOGGER = logging.getLogger(__name__)


def build_estimator():
    return RandomForestClassifier(
        **config.RANDOM_FOREST_PARAMETERS, random_state=config.RANDOM_SEED,
        n_jobs=config.TREE_MODEL_N_JOBS,
    )


def fit_random_forest(features, target):
    """Choose the configured depth/features/leaf sizes using training folds only."""
    return fit_tree_classifier(features, target, build_estimator(), config.RANDOM_FOREST_PARAM_GRID)


def run_classifier(input_path=None, output_dir=None):
    return run_tree_classifier(
        "randomforest", fit_random_forest,
        input_path if input_path is not None else config.INPUT_DATA_DIR / config.CLEAN_MERGED_FILENAME,
        output_dir if output_dir is not None else config.RANDOM_FOREST_OUTPUTS_DIR,
        importance_type="mean_decrease_impurity; summed_across_one_hot_columns",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fit", action="store_true", help="Run training-only CV, refit, and export partition results")
    parser.add_argument("--input", type=Path, default=config.INPUT_DATA_DIR / config.CLEAN_MERGED_FILENAME)
    parser.add_argument("--output-dir", type=Path, default=config.RANDOM_FOREST_OUTPUTS_DIR)
    args = parser.parse_args(argv)
    if not args.fit:
        parser.print_help()
        return 0
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run_classifier(args.input, args.output_dir)
    except (ValueError, OSError) as error:
        LOGGER.error("Random forest failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

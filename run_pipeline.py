"""Run data preprocessing, historical merging, and tree-ensemble training.

Usage: .venv/Scripts/python.exe run_pipeline.py preprocess [--only climate|geological]
       .venv/Scripts/python.exe run_pipeline.py preprocess --only fire
       .venv/Scripts/python.exe run_pipeline.py merge
       .venv/Scripts/python.exe run_pipeline.py merge --netcdf-only
       .venv/Scripts/python.exe run_pipeline.py train
       .venv/Scripts/python.exe run_pipeline.py train --model randomforest
       .venv/Scripts/python.exe run_pipeline.py train --model xgboost

Outputs are NetCDF files under data/processed/climate/<source>/<split>/ and
data/processed/static/<source>/. grid.nc stores the common Canadian cell centres;
canada_cells.gpkg stores their polygon support clipped to the Canadian boundary.
The default boundary comes from the local ecodistrict polygons; --boundary can
select another local Canadian polygon file. No inputs are downloaded.

Only cell centres inside Canada are retained. Climate means use valid Canadian
source centres; categorical rasters use mode. Historical tas gaps use original
same-cell observations over [t-3, t+3]; other unavailable values remain NaN.
CanSIPS daily intervals include the midnight endpoint and retain every model and
member; unavailable humidity is not inferred from dewpoint. Forecast coverage is
limited to the supplied files. Static elevation remains district-level information.

Fire preprocessing combines CWFIS snapshots into data/processed/fire/cwfis.csv,
using national fire IDs and retaining the earliest snapshot for repeated IDs,
correcting matched January 1 placeholders from NWT estimated start dates before
filtering to the configured historical period. CWFIS locations and valid areas are
preserved; missing 2026 NT areas use exact-ID, coordinate-checked NWT currentsize,
including published zeros. Unmatched January 1 dates are retained and reported in console warnings.
It runs separately with --only fire;
the default 'all' selection continues to process climate/geological predictors.

Merge writes one all-cell CSV per day under data/clean/{training,validation,test}.
It also combines those CSVs in data/clean/merged.nc, with partition(time).
Use merge --netcdf-only to combine existing CSVs without regenerating them.
Training/validation dates are split chronologically using the configured fractions.
Fire processing begins in September 2017; August 2020 climate is stored as history
before the clean modelling window. The two numerical fire-size predictors sum
stored areas across the centre cell and eight retained neighbours over
[t-90 days, t) and [t-2 calendar years, t-90 days). Today is excluded from both;
unknown areas produce missing totals. Future features require observations
covering the relevant windows.
Weather features are inclusive 30-day precipitation sums and 7-day minima of daily
average temperature; incomplete windows remain missing across split boundaries.
Only ORRC climate, elevation, land cover, earlier fire history, and CWFIS targets
are included. Missing predictors remain blank; missing target indicators use 0.
Zero targets mean no reported
large fire, not verified absence; merge_summary.json documents coverage/exclusions.

Train reads existing selected predictors from data/inputs/merged.nc. By default
it runs Random Forest followed by XGBoost, using their configured training-only
CV, cost threshold, and evaluation/export logic. --model selects one ensemble.
Default outputs use the model directories in src/config.py; --output-dir selects
a parent directory containing randomforest/ and xgboost/ subdirectories. Prepare
selected inputs with python -m src.variable_selection before training.
"""

import argparse
import importlib
import logging
from pathlib import Path

from src import config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command")
    preprocess = commands.add_parser("preprocess", help="Prepare predictors or standardise fire records")
    preprocess.add_argument("--only", choices=("all", "climate", "geological", "fire"), default="all",
                            help="Default 'all' processes predictors; select 'fire' for fire records")
    preprocess.add_argument("--boundary", type=Path, default=config.ECODISTRICTS_PATH,
                            help="Local Canadian polygon boundary (defaults to ecodistricts)")
    preprocess.add_argument("--output-dir", type=Path, default=config.PROCESSED_DATA_DIR)
    merge = commands.add_parser("merge", help="Create daily historical training, validation, and test CSVs")
    merge.add_argument("--processed-dir", type=Path, default=config.PROCESSED_DATA_DIR)
    merge.add_argument("--output-dir", type=Path, default=config.CLEAN_DATA_DIR)
    merge.add_argument("--boundary", type=Path, default=config.ECODISTRICTS_PATH)
    merge.add_argument("--netcdf-only", action="store_true", help="Combine existing daily CSVs into merged.nc only")
    train = commands.add_parser("train", help="Fit and evaluate Random Forest and/or XGBoost on selected inputs")
    train.add_argument("--model", choices=("all", "randomforest", "xgboost"), default="all",
                       help="Default 'all' runs Random Forest then XGBoost sequentially")
    train.add_argument("--input", type=Path, default=config.INPUT_DATA_DIR / config.CLEAN_MERGED_FILENAME,
                       help="Selected predictor NetCDF, including targets and temporal partitions")
    train.add_argument("--output-dir", type=Path,
                       help="Parent output directory; each model gets its own subdirectory (defaults to config paths)")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        print("\nConfigured time windows (inclusive):")
        for name, (start_date, end_date) in config.TIME_WINDOWS.items():
            print(f"{name}: {start_date} to {end_date}")
        return 0
    if args.output_dir is not None and args.output_dir.resolve().is_relative_to(config.RAW_DATA_DIR.resolve()):
        parser.error("--output-dir must not be inside the raw input directory")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)
    if args.command == "train":
        destinations = {"randomforest": config.RANDOM_FOREST_OUTPUTS_DIR,
                        "xgboost": config.XGBOOST_OUTPUTS_DIR}
        names = list(destinations) if args.model == "all" else [args.model]
        if args.output_dir is not None:
            destinations = {name: args.output_dir / name for name in names}
        for name in names:
            output = destinations[name]
            if any(output.resolve().is_relative_to(path.resolve()) for path in
                   (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR, config.CLEAN_DATA_DIR, config.INPUT_DATA_DIR)):
                parser.error("Tree-model outputs must be separate from raw, processed, clean, and input data")
        if not args.input.is_file():
            logger.error("Selected model input missing: %s; prepare inputs with python -m src.variable_selection", args.input)
            return 1
        for name in names:
            try:
                module = importlib.import_module(f"src.{name}")
                logger.info("Starting %s: selected inputs %s; outputs %s", name, args.input, destinations[name])
                module.run_classifier(input_path=args.input, output_dir=destinations[name])
            except (ImportError, ValueError, OSError) as error:
                logger.error("%s training failed: %s", name, error)
                return 1
        logger.info("Finished training: %s", ", ".join(names))
        return 0
    if args.command == "merge":
        from src import data_merge
        try:
            if args.netcdf_only:
                data_merge.merge_csvs_to_netcdf(args.output_dir)
            else:
                data_merge.merge(args.processed_dir, args.output_dir, args.boundary)
        except (FileNotFoundError, ValueError, OSError) as error:
            logger.error("Historical merging failed: %s", error)
            return 1
        return 0
    if args.only == "fire":
        from src import data_fire
        try:
            outputs = data_fire.preprocess(args.output_dir)
        except (ValueError, OSError) as error:
            logger.error("Fire preprocessing failed: %s", error)
            return 1
        logger.info("Finished: %s fire outputs under %s", len(outputs), args.output_dir / "fire")
        return 0

    # Import data stages only when requested, keeping CLI help inexpensive.
    from src import data_climate, data_geological
    from src.preprocessing import create_grid, grid_cells, load_boundary, save_dataset
    from pyogrio.errors import DataSourceError

    try:
        boundary = load_boundary(args.boundary)
        grid = create_grid(boundary)
        grid.attrs["boundary_source"] = str(args.boundary.resolve())
        save_dataset(grid, args.output_dir / "grid.nc", grid, static=True)
        grid_cells(grid, boundary).to_file(args.output_dir / "canada_cells.gpkg", driver="GPKG", layer="cells")
    except (FileNotFoundError, ValueError) as error:
        logger.error("Cannot construct the Canadian grid: %s", error)
        return 1
    logger.info("Common grid: %s Canadian centres at %s by %s degrees", grid.sizes["cell"],
                config.TARGET_LATITUDE_RESOLUTION_DEGREES, config.TARGET_LONGITUDE_RESOLUTION_DEGREES)
    stages = {"climate": data_climate.preprocess, "geological": data_geological.preprocess}
    outputs, errors = [], []
    for name, stage in stages.items():
        if args.only in ("all", name):
            try:
                outputs.extend(stage(grid, boundary, args.output_dir))
            except (FileNotFoundError, ValueError, OSError, DataSourceError) as error:
                logger.error("%s preprocessing failed: %s", name, error)
                errors.append(name)
    logger.info("Finished: %s predictor outputs under %s", len(outputs), args.output_dir)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

# Outputs

`binning.csv` and `variable_selection.csv` document shared predictor preparation
for all models. Regression outputs for the WoE logistic baseline are stored in
`baseline/`. Raw selected-feature tree-model outputs are stored separately in
`randomforest/` and `xgboost/` when those models are explicitly run.

Fire-size predictors use `[t-90 days, t)` and `[t-2 calendar years, t-90 days)`
over the centre cell and eight retained neighbours. The current day is excluded.
After changing these definitions, rebuild preparation stages in order, then
refit models after resolving any missing selected predictors:

```powershell
.venv/Scripts/python.exe run_pipeline.py preprocess --only fire
.venv/Scripts/python.exe run_pipeline.py merge
.venv/Scripts/python.exe -m src.baseline
.venv/Scripts/python.exe -m src.variable_selection
.venv/Scripts/python.exe -m src.baseline --fit
```

## Predictor binning

Run from the project root after installing `requirements.txt`:

```powershell
.venv/Scripts/python.exe -m src.baseline
```

`binning.csv` documents bins fitted against `is_large_fire` using **only training
rows** from `data/clean/merged.nc`. Training labels must match the chronological
training dates from `src/config.py`. Validation/test predictor values and targets
are not used. All training rows are included, without sampling or class weighting.

The predictor list comes from the existing merge configuration. Elevation,
climate, rolling weather, and cumulative fire-area predictors each receive exactly
five OptBinning intervals, maximizing IV without a monotonicity constraint. Intervals are
left-inclusive and right-exclusive; the outer bounds are infinite. Failure to
obtain five optimal bins stops the run without replacing the previous output.
Land cover keeps one bin per observed training category. Categories are never combined, including categories
with no fire events. Dates, cell IDs, coordinates, partition labels, and the target
are excluded from the predictor list.

Each row contains a bin's exact bounds or category, sample/event/non-event counts,
sample fraction, event rate, class distributions, WoE, IV contribution, and total
predictor IV. Units, binning method/status, number of regular bins, training dates,
training sample/event counts, and target name document the fit. Missing predictor
values, if present, receive a separate bin beyond the five numerical intervals.
No empty special/missing bins or total rows are exported.

`90_day_fire_size` and `2_year_90_day_fire_size` are numerical, in hectares.
The recent window includes `t-90` through `t-1`; the older window includes the
two-year anniversary through `t-91`. Each fire contributes once in its window
across the centre cell and eight retained neighbours. Unknown areas propagate to
missing values, while no qualifying report gives zero. Stored snapshot sizes are
used without reconstructing historical as-of-date sizes. Previous binary fire
predictors and the old cumulative-size name have been removed from preparation.
Both features receive five training-fitted numerical bins and WoE/IV statistics.

Rebuild the clean data, binning/WoE, and variable selection after changing these
features. Existing model outputs remain from their previous fit until refitted.
All current selected predictors are complete. Matching NWT published sizes,
including zeros, replaced 24 unavailable CWFIS areas before computing rolling
totals, resolving 4,827 previously missing test values in `90_day_fire_size`.
Training/validation and the training-fitted binning/selection are unchanged.

WoE uses `ln((bin non-events / total non-events) / (bin events / total events))`;
positive WoE indicates a lower large-fire rate. IV is the sum of
`(non-event distribution - event distribution) * WoE`. No smoothing is applied:
populated bins with zero events or non-events retain infinite WoE/IV and are
identified by `woe_status`. Unseen validation/test categories do not acquire bins
or estimated WoE from heldout data. The separate regression step below applies
these bins. The existing centered temperature imputation remains part
of the cleaned inputs; this step performs no further imputation.

OptBinning's numerical method and constraints follow its
[official documentation](https://gnpalencia.org/optbinning/binning_binary.html).
The script writes only this bin documentation; cleaned and processed data are
unchanged. Use `--input` and `--output` to select alternative paths.

## Variable selection

After binning, run:

```powershell
.venv/Scripts/python.exe -m src.variable_selection
```

`variable_selection.csv` has one row per predictor, ranked by descending training
IV from `binning.csv`. It records the retained/dropped decision, the earlier
retained predictor responsible for a drop, the signed correlation, the configured
threshold, and training coverage. Each `corr_<predictor>` column holds one column
of the full raw-training Pearson correlation matrix, in the same predictor order
as the rows. Land-cover correlations are blank because nominal category codes
have no numerical ordering; land cover is retained outside the Pearson filter.
Both fire-size predictors participate in numerical Pearson correlations.

A candidate is dropped when its **absolute** correlation with any earlier
retained predictor is **greater than 0.6**. A correlation exactly at the threshold
is permitted. A dropped predictor cannot exclude later predictors. IV ties retain
the original predictor order from the binning report. IV and correlation fitting
use training data only; the same selection applies to validation and test.

The command also writes the selected, untransformed columns under
`data/inputs/`, keeping the daily CSV folders, `merged.nc`, and
`merge_summary.json` layout of `data/clean/`. Dates, identifiers, coordinates,
targets, partition labels, source values, units, and exclusions are preserved.
The inputs NetCDF also uses Git LFS. Source clean files and binning statistics
remain unchanged. Parameters and default paths are in `src/config.py`; use
`--clean-dir`, `--output-dir`, `--binning`, and `--report` for alternate paths.

## L2 logistic regression

After variable selection, run:

```powershell
.venv/Scripts/python.exe -m src.baseline --fit
```

The model reads the selected raw predictors from `data/inputs/merged.nc` and
applies their **exact existing WoE values** from `binning.csv`. Interval edges
remain left-inclusive/right-exclusive; categorical bins remain single categories.
No bin refitting, smoothing, scaling, class weighting, or resampling is performed.
Missing/unseen categories without a documented finite WoE stop the run rather
than receiving an invented value. Binning coverage and class counts must agree
with the training inputs. Source datasets, binning, and selection files are not
modified.

`src/config.py` sets five shuffled stratified folds, seed `RANDOM_SEED`, and the
eleven inverse-regularization strengths `C = 10**i`, for integer `i = -5, ..., 5`.
Each candidate is evaluated by mean ROC-AUC over **training-only** folds. Exact
ties favour the smallest C. The chosen L2 model is refitted on all training rows;
validation/test values and targets do not affect its coefficients or C. The
`newton-cholesky` solver uses warm starts only between C values within one fold;
the final fit starts independently. Fits must converge. ROC-AUC uses predicted
probabilities. After C is chosen, the flag threshold minimizes total cost on the
final model's **training predictions**, using `BASELINE_CONFUSION_COSTS`:

| Actual cell-day outcome | Unflagged | Flagged |
| --- | ---: | ---: |
| No large fire | 0 (TN) | 1 (FP) |
| Large fire | 750 (FN) | 50 (TP) |

Thus total cost is `FP + 50*TP + 750*FN`; correctly flagged fires still incur cost.
The search evaluates every distinct probability cutoff, keeps equal probabilities
together under `probability >= threshold`, and includes flagging no rows or all
rows. Equal costs favour the highest threshold (fewest flags). The same chosen
threshold is applied to validation and test without further optimization.
Threshold selection is in-sample, using no validation/test outcomes. It changes
the confusion matrices and costs; ROC-AUC is independent of that cutoff.

The existing supervised bins and variable selection were learned using the full
training partition, before these folds. Consequently, CV scores are conditional
on that fixed preprocessing, and are not an independent assessment of the entire
binning/selection pipeline. The training performance row and ROC curve are
in-sample; validation and test are held out. These shuffled row folds do not
measure forward-in-time generalization; the dated heldout partitions provide
that separate evaluation.

| Output | Contents |
| --- | --- |
| `baseline/baseline_coefficients.csv` | Intercept and one coefficient per selected WoE predictor; odds ratios are `exp(coefficient)` per one WoE unit. Includes chosen C, threshold, cost assumptions, and training/CV metadata. |
| `baseline/baseline_performance.csv` | One row per training/validation/test partition: TN, FP, FN, TP counts, probability-based ROC-AUC, optimized threshold, total/mean cost, unflag-everything comparison cost, precision, recall, specificity, F1, and accuracy. Includes all candidate mean/std/fold AUCs in the JSON-valued `cv_auc_by_C` field. |
| `baseline/baseline_performance.png` | ROC curves and AUCs for all three partitions; training is marked in-sample. Matching coloured dots mark the selected threshold's operating point on each curve. |
| `baseline/baseline_probabilities.nc` | Fitted `large_fire_probability(time, cell)` and `partition(time)` for every retained training/validation/test cell-day, with the input time, cell IDs, latitude/longitude coordinates, and CRS metadata. No predictor or observed-target values are included. |
| `baseline/baseline_shap.csv` | One row per selected predictor, ranked by mean absolute SHAP, with importance share, signed mean, standard deviation, range, coefficient, training WoE mean, expected log odds, additivity error, and model/background metadata. |
| `baseline/baseline_shap.png` | Global feature importance as mean absolute SHAP values on the log-odds scale, over every training cell-day. |

The probability NetCDF uses compressed float64 values from the final model fitted
on all training rows. Training probabilities are in-sample, rather than out-of-fold;
validation/test probabilities use the same fitted model. Dates and cells match
`data/inputs/merged.nc`, including its exclusions. Probability values range from
0 to 1 and are independent of the chosen flag threshold. Model, training, threshold,
and cost metadata document the exported predictions. Each `--fit` run writes this
file alongside the other regression outputs.

Each fit also uses SHAP's interventional `LinearExplainer` to explain the final
model on its WoE inputs. The background uses the exact mean of **all training
rows**, without sampling or validation/test data. For feature `j`, the exact
contribution is `coefficient_j * (WoE_j - mean_training_WoE_j)`; the expected
log odds plus the contributions reconstruct each model decision score, which is
checked during export. Explanations are computed in bounded chunks and aggregated
over all training rows. Importance shares sum to one when any contribution varies.
Signed means are approximately zero because the background and explained rows
are the same; they do not describe a feature's overall direction. These are
model contributions in log odds, rather than probability changes or causal effects.

Standard metrics are ratios from 0 to 1: precision is `TP / (TP + FP)`, recall is
`TP / (TP + FN)`, and specificity is `TN / (TN + FP)`. These use 0 when their
denominator is zero. F1 is `2*TP / (2*TP + FP + FN)` and accuracy is
`(TP + TN) / rows`.

`inverse_C` records `1/C`; it is not a fitted variable coefficient. Coefficients
describe log odds of `is_large_fire=1`, using the existing WoE convention where
larger WoE represents a lower univariate fire rate. Positive/negative regression
coefficients increase/decrease log odds as that predictor's WoE increases.
The default regression output directory is `outputs/baseline/`. Use `--input`,
`--binning`, and `--output-dir` with `--fit` for alternative paths.
The implementation follows scikit-learn's
[logistic regression API](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).

## Random forest and XGBoost

The pipeline runs both ensembles sequentially on the existing selected
`data/inputs/merged.nc`:

```powershell
.venv/Scripts/python.exe run_pipeline.py train
```

Use `train --model randomforest` or `train --model xgboost` to run one ensemble.
`--input` selects an alternative selected-predictor NetCDF. `--output-dir` selects
a parent output directory, with `randomforest/` and `xgboost/` subdirectories;
without that option, the model-specific configuration paths are used. Training
uses the existing input partitions and model settings. Prepare missing inputs
with `python -m src.variable_selection`. The command returns a nonzero exit code
on failure and stops before starting the next ensemble.

The standalone module commands also remain available and require `--fit`.
Importing a module, displaying pipeline help, or running a standalone module
without that flag leaves training unstarted:

```powershell
.venv/Scripts/python.exe -m src.randomforest --fit
.venv/Scripts/python.exe -m src.xgboost --fit
```

Both read only the selected predictors from `data/inputs/merged.nc`. They do not
read `binning.csv`, refit bins, or use WoE. Numerical predictors retain
their values, represented as float32 for the tree libraries. Nominal land cover
uses one-hot encoding fitted inside each training CV fold and then refitted on
the complete training partition. An unseen heldout category has all-zero dummy
columns; heldout categories never expand the training schema. Missing/infinite
predictors stop the run instead of being filled or silently dropped. Identifiers,
coordinates, partition labels, and the target are never predictors.

Random forest uses 300 trees, bootstrap sampling with replacement, a sample-draw
fraction of 0.8, and `criterion="log_loss"`. Each CV tree draws from its own fold's
training rows; the final forest draws from all training rows. The fraction counts
draws, not unique rows. The full grid is `max_depth=(5, 10, 15)`,
`max_features=(2, 3, 4)`, and `min_samples_leaf=(10, 50, 100)`: **27 candidates,
135 CV fits, and one final full-training fit**. `max_features` counts columns after
one-hot encoding. Original-variable importance sums the dummy-column importances.

XGBoost uses `objective="binary:logistic"`, `eval_metric="logloss"`, at most 3,000
boosting rounds, early-stopping patience of 100 rounds, `subsample=0.8`, and
`tree_method="hist"`. Its grid is `learning_rate=(0.03, 0.05, 0.10)`,
`max_depth=(2, 4, 6)`, `min_child_weight=(1, 5, 10)`,
`colsample_bytree=(0.6, 0.8, 1.0)`, and `reg_lambda=(1, 10, 50)`:
**243 candidates and 1,215 CV fits**, followed by one full-training refit.

Inside each outer CV training fold, XGBoost reserves the configured
`VALIDATION_FRACTION` (20%) as a stratified early-stopping subset, with seed
`RANDOM_SEED`. Encoding is fitted on the remaining fitting rows only. The outer
scoring fold never supplies an early-stopping signal. Each candidate stops on
log loss and is scored on the untouched outer fold using exactly
`best_iteration + 1` rounds. Mean outer-fold **log loss** selects the candidate;
fold and mean/std ROC-AUC are also recorded. The selected candidate's median best
round count, rounded up if necessary, determines the final boosting-round count.
The final encoder and model are then fitted on all training rows, with that fixed
count and early stopping disabled because no training rows are withheld from the
final fit. The dated validation/test partitions do not determine this count.

Neither model applies automatic class weighting, class resampling, or numerical
standardization. The configured forest bootstrap and XGBoost row/column subsampling
remain part of their respective algorithms.

Both reuse `RANDOM_SEED`, `BASELINE_CV_FOLDS`, and `BASELINE_CONFUSION_COSTS` from
`src/config.py`. Five shuffled stratified folds are created only from training
rows; every candidate uses the same seeded folds. Mean training-CV ROC-AUC selects
the forest configuration; mean training-CV log loss selects XGBoost. Exact ties
favour the first grid entry. Estimators receive
the same configured seed for every candidate/fold; no additional seeds are drawn
by our code. Random forest derives its per-tree seeds internally. Candidates/folds
run sequentially; trees use `TREE_MODEL_N_JOBS` to avoid nested parallel searches.

After the final training fit, its in-sample training probabilities determine the
minimum-cost flag threshold under the existing FP/TP/TN/FN costs. That single
threshold is applied to training, validation, and test, with ROC threshold markers
and the same metrics as the logistic baseline. Validation/test outcomes do not
influence tuning, encoding, fitting, or threshold selection. Variable selection
is fixed from full training before CV; these shuffled folds measure performance
conditional on that selection, rather than forward-in-time performance.

When run, each model writes the following files under its own output directory,
using `randomforest_` or `xgboost_` as the filename prefix:

| Filename suffix | Contents |
| --- | --- |
| `cv_results.csv` | Candidate parameters, per-fold and mean/std ROC-AUC, rank, chosen candidate, and training coverage. XGBoost also records log loss, each fold's best round count, stopping settings, and the full-training refit round count. |
| `feature_importances.csv` | Original selected-variable importances, aggregating one-hot columns; forest impurity decrease or XGBoost normalized gain. |
| `performance.csv` | Training/validation/test confusion counts, ROC-AUC, log loss, precision/recall/specificity/F1/accuracy, threshold, costs, and model/CV metadata. |
| `performance.png` | Partition ROC curves with the training-selected threshold marked. |
| `probabilities.nc` | Fitted cell-day probabilities and partition labels on the original input coordinates; training predictions are in-sample. |

Use `--input` and `--output-dir` to override the configured locations. All training
settings are in `src/config.py`; source data and shared selection outputs remain
unchanged.

# Outputs

`binning.csv` and `variable_selection.csv` document shared predictor preparation
for all models. Regression outputs for the WoE logistic baseline are stored in
`baseline/`.

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
climate, and rolling weather predictors each receive exactly five OptBinning
intervals, maximizing IV without a monotonicity constraint. Intervals are
left-inclusive and right-exclusive; the outer bounds are infinite. Failure to
obtain five optimal bins stops the run without replacing the previous output.
Land cover and the three binary fire-history indicators each keep one bin per
observed training category. Categories are never combined, including categories
with no fire events. Dates, cell IDs, coordinates, partition labels, and the target
are excluded from the predictor list.

Each row contains a bin's exact bounds or category, sample/event/non-event counts,
sample fraction, event rate, class distributions, WoE, IV contribution, and total
predictor IV. Units, binning method/status, number of regular bins, training dates,
training sample/event counts, and target name document the fit. Missing predictor
values, if present, receive a separate bin beyond the five numerical intervals.
No empty special/missing bins or total rows are exported.

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
Binary fire-history indicators participate in Pearson correlations.

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
| Large fire | 1,000 (FN) | 50 (TP) |

Thus total cost is `FP + 50*TP + 1000*FN`; correctly flagged fires still incur cost.
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

The probability NetCDF uses compressed float64 values from the final model fitted
on all training rows. Training probabilities are in-sample, rather than out-of-fold;
validation/test probabilities use the same fitted model. Dates and cells match
`data/inputs/merged.nc`, including its exclusions. Probability values range from
0 to 1 and are independent of the chosen flag threshold. Model, training, threshold,
and cost metadata document the exported predictions. Each `--fit` run writes this
file alongside the other regression outputs.

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

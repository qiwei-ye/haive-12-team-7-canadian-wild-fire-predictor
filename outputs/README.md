# Baseline binning

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
or estimated WoE from heldout data; applying bins and fitting a predictive model
are outside this step. The existing centered temperature imputation remains part
of the cleaned inputs; this step performs no further imputation.

OptBinning's numerical method and constraints follow its
[official documentation](https://gnpalencia.org/optbinning/binning_binary.html).
The script writes only this bin documentation; cleaned and processed data are
unchanged. Use `--input` and `--output` to select alternative paths.

# Variable selection

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

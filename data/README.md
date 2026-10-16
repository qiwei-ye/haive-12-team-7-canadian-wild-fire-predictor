Processed predictors are created with:

```powershell
.venv/Scripts/python.exe run_pipeline.py preprocess
.venv/Scripts/python.exe run_pipeline.py preprocess --only fire
```

To combine the existing processed inputs into daily historical tables, run:

```powershell
.venv/Scripts/python.exe run_pipeline.py merge
```

The merge reads `src/config.py` for dates, resolution, variables, units, and split
fractions. It keeps the configured testing window separate and divides the earlier
training/validation window chronologically: the first 80% of whole dates are
training, and the remaining dates are validation. All cells for a date stay together.
The training count is rounded down. No random row split or partition column is used.
The configured exclusions are applied after determining these boundaries: 109
cells previously missing land cover are removed from every processed spatial
dataset and daily table. Four dates listed in `EXCLUDED_HISTORICAL_DATES` have no
daily CSV. These exclusions do not shift the original partition boundaries.

Daily files are saved as `data/clean/training/YYYY-MM-DD.csv`,
`data/clean/validation/YYYY-MM-DD.csv`, and `data/clean/test/YYYY-MM-DD.csv`.
Each file contains every retained Canadian grid cell, including cells with missing
predictors. `data/clean/merge_summary.json` records exact dates, counts, units,
definitions, and every excluded fire record. Processed and clean outputs are
tracked by Git; raw datasets remain local.

The two large CanSIPS forecast NetCDF files use Git LFS. Install Git LFS before
cloning; if these files contain pointers instead of NetCDF data, run
`git lfs install --local` followed by `git lfs pull` in the repository.

| Columns | Meaning |
| --- | --- |
| `date`, `cell`, `lat`, `lon` | Report/calendar date and common grid identifier/centre coordinates. |
| `hurs`, `pr`, `sfcWind`, `tas` | Historical ORRC predictors, retaining the processed units in configuration. |
| `MIN_ELEV`, `MAX_ELEV`, `MEAN_ELEV`, `ELEVDIFF` | Processed ecodistrict elevation attributes, in metres. |
| `landcover` | Modal 2020 land-cover category code; categorical, without interpolation. |
| `previous_fire` | 1 if an available fire report in this cell strictly precedes this date; otherwise 0. Any reported fire counts, regardless of size. |
| `previous_fire_neighbour` | 1 if an available earlier report is in one of the eight retained side- or corner-sharing cells; otherwise 0. The current cell is excluded. |
| `is_large_fire` | 1 if at least one reported fire in this cell on this date meets the configured large-fire threshold; missing if no known large fire exists but at least one reported size is unknown; otherwise 0. |

History carries forward across the training, validation, and testing boundaries;
same-day and future reports never enter a row's history. Multiple fires in a cell
on a day produce one target, with a known large fire taking precedence over an
unknown size. Fire dates are CIFFC report dates, not ignition or status dates.
Reports on omitted CSV dates still contribute to fire history on later dates.
Processed climate files retain their complete daily time coordinates, including
the four dates excluded from the clean CSVs. Raw datasets remain unchanged.

CIFFC reporting is incomplete, especially in the earlier historical years. Zero
targets mean **no reported large fire**, not verified absence. Zero history values
mean **no earlier fire in the available reports**, not no fire ever. Unknown sizes
and missing climate/static values remain empty CSV fields; nothing is imputed.

Fire locations outside the Canadian boundary or within cells absent from the
existing centre-filtered grid are excluded and documented in the summary. They
are never moved to a neighbouring cell. Raw and processed inputs remain unchanged.
NFDB, fuel type, ecodistrict identifiers, and forecast-only climate sources are
excluded from these historical modelling tables.

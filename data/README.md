Processed predictors and fire reports are created with:

```powershell
.venv/Scripts/python.exe run_pipeline.py preprocess
.venv/Scripts/python.exe run_pipeline.py preprocess --only fire
```

Each folder under [processed/](processed/README.md) documents its processing
logic, output files, variables, coverage, and limitations.

Processed fire records begin on 2018-09-01. Historical climate processing begins
on 2020-08-01, with August stored under `climate/ORRC/history/` for weather
lookback features. Clean training/validation and testing dates keep their existing
configured windows beginning on 2020-09-01 and 2025-09-01, respectively.

Fire preprocessing consolidates the CWFIS annual CSV snapshots into
`data/processed/fire/cwfis.csv`, with the six configured output columns. The
`fire_id` column uses `national_fire_id` to distinguish agencies and years.
For IDs repeated across snapshots, the earliest snapshot's complete record wins
before date filtering. Later carryover/reset records cannot create another event
or change its original report date, location, and area. Dates are taken from
`situation_report_date`, except that January 1 NWT 2026 placeholders are replaced
with the official NWT `estimatedstart` calendar date from
`data/raw/fire/NWT/fire_incidents_2026.json`. Matching uses exact national/agency
IDs and checks coordinates at CWFIS's published precision. CWFIS locations and
areas are preserved; status dates are never substituted. Correction occurs before
the historical window filter, so corrected September 2026 fires are omitted.
Unknown or negative areas remain blank in the processed source.

Unmatched January 1 records retain their CWFIS dates and trigger console warnings.
NWT start dates are estimates, and its original report dates are unavailable.
The six-column `cwfis.csv` schema is retained; its `report_date` column now denotes
the processed fire date with this documented exception. NWT is a date reference
for CWFIS records, without adding duplicate fire observations.

To combine the existing processed inputs into daily historical tables, run:

```powershell
.venv/Scripts/python.exe run_pipeline.py merge
```

The merge reads `src/config.py` for dates, resolution, variables, units, and split
fractions. It keeps the configured testing window separate and divides the earlier
training/validation window chronologically: the first 80% of whole dates are
training, and the remaining dates are validation. All cells for a date stay together.
The training count is rounded down. No random row split or CSV partition column is used.
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

The merge also creates `data/clean/merged.nc` from all daily CSVs. Its dimensions
are `time` and `cell`; `partition(time)` contains `training`, `validation`, or
`test`, applying to all cells on that date. The CSV `date` column becomes `time`.
Elevation and land cover are stored once per cell; the other predictors and target
use `(time, cell)`. Coordinates, units, category codes, and missing predictor values
are preserved. Missing `is_large_fire` indicators use `0` in both formats.
Excluded dates remain absent. To rebuild this NetCDF from existing CSVs without
rerunning preprocessing or regenerating daily predictors, use:

```powershell
.venv/Scripts/python.exe run_pipeline.py merge --netcdf-only
```

This command also replaces any missing target indicators in existing CSVs with
`0` so the CSVs and NetCDF remain consistent; other CSV fields are preserved.

The large CanSIPS forecast files and consolidated `merged.nc` use Git LFS. Install Git LFS before
cloning; if these files contain pointers instead of NetCDF data, run
`git lfs install --local` followed by `git lfs pull` in the repository.

| Columns | Meaning |
| --- | --- |
| `date`, `cell`, `lat`, `lon` | Calendar date and common grid identifier/centre coordinates; fire dates follow the correction rule above. |
| `hurs`, `pr`, `sfcWind`, `tas` | Historical ORRC predictors, retaining the processed units in configuration. Missing daily `tas` uses the centered mean rule below. |
| `MIN_ELEV`, `MAX_ELEV`, `MEAN_ELEV`, `ELEVDIFF` | Processed ecodistrict elevation attributes, in metres. |
| `landcover` | Modal 2020 land-cover category code; categorical, without interpolation. |
| `previous_large_fire` | 1 if a known fire >= 1,000 ha occurred in this cell in the preceding two calendar years; otherwise 0. |
| `previous_large_fire_neighbour` | 1 if a known fire >= 1,000 ha occurred in any of the eight retained side- or corner-sharing cells in the preceding two calendar years; otherwise 0. The current cell is excluded. |
| `previous_small_fire_neighbour` | 1 if a known fire < 1,000 ha occurred in any of those eight surrounding cells in the preceding two calendar years; otherwise 0. Unknown sizes count as neither small nor large. |
| `30_day_pr` | Sum of daily `pr` over the current day and preceding 29 calendar days, in mm. |
| `7_day_min_avg_tas` | Minimum daily average `tas` over the current day and preceding six calendar days, in degC. |
| `is_large_fire` | 1 if at least one reported fire assigned to this cell/date meets the configured large-fire threshold; otherwise 0, including missing indicators and unknown reported fire sizes. |

Fire-history windows are `[row date - 2 calendar years, row date)`: the anniversary
date is included, while same-day and future reports are excluded. Events expire
after two years. History carries across partition boundaries; the 2018-2019
snapshots supply context for the first training dates. Multiple fires in a cell
on a day produce one target, with a known large fire taking precedence over an
unknown size. Fire dates follow `FIRE_DATE_DEFINITION` in configuration, also saved
in merge metadata and the NetCDF `fire_date_definition` attribute. Corrected dates
apply to both the target and strictly earlier fire-history predictors.
Reports on omitted CSV dates still contribute to fire history on later dates.
Weather windows are calculated on consecutive daily climate observations before
partitioning or omitting clean dates, so they cross split boundaries correctly.
A rolling weather value is missing if any required daily observation is missing;
partial sums/minima are not used. Before these calculations, missing historical
daily `tas` is filled with the same-cell mean of originally available observations
in `[t-3, t+3]`, inclusive. Existing temperatures are preserved. All replacements
are calculated in one pass; an entirely unavailable window stays missing.
This centered fill uses future observations and can cross partition boundaries;
those observations must be available when constructing the features.
The four configured excluded dates remain omitted because humidity and wind are
still unavailable. Their filled temperatures contribute to later seven-day minima.
All current cleaned CSV and merged NetCDF columns are complete after this fill.
Processed climate files retain their complete daily time coordinates, including
the four dates excluded from the clean CSVs. Raw datasets remain unchanged.

CWFIS operational reporting can have coverage gaps and source errors. Corrected
NWT dates follow the agency's estimated start field, including its distinction
from discovery dates. Unmatched dates remain unresolved. Zero targets mean
**no reported large fire**, not verified absence. Zero history values
mean **no qualifying fire in the available two-year history**, not no fire ever. Unknown fire
sizes remain missing in the processed CWFIS source. Cleaned large-fire indicators
use `0` for missing values. Missing climate/static predictors remain empty CSV
fields; the centered historical `tas` fill is the sole predictor-imputation rule.

Fire locations outside the Canadian boundary or within cells absent from the
existing centre-filtered grid are excluded and documented in the summary. They
are never moved to a neighbouring cell. Raw and processed inputs remain unchanged.
CIFFC, NFDB, fuel type, ecodistrict identifiers, and forecast-only climate sources are
excluded from these historical modelling tables.

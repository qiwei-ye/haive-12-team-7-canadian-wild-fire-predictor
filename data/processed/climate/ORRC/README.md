# Processed ORRC historical predictors

**Processing:** NetCDF inputs from `data/raw/climate/ORRC v1.0_<variable>/` are
combined by variable. Geographic source coordinates, including rotated-grid
locations, are used to average valid Canadian source centres per common cell.
Temperatures become Celsius, precipitation becomes mm day-1, and observations
are aggregated to daily values before saving the configured historical splits.

**Data:** Each split contains `hurs.nc`, `pr.nc`, `sfcWind.nc`, and `tas.nc`, with
dimensions `(time, cell)` and the common 2,168-cell EPSG:4326 1° grid.

| Folder | Inclusive dates | Daily coordinates |
| --- | --- | --- |
| [history/](history/README.md) | 2020-08-01 to 2020-08-31 | 31 |
| [testing/](testing/README.md) | 2025-09-01 to 2026-08-31 | 365 |
| [training_validation/](training_validation/README.md) | 2020-09-01 to 2025-08-31 | 1,826 |

Observations outside these windows are discarded. Training and validation remain
combined here; the clean merge divides them chronologically. Missing historical
daily `tas` uses the mean of originally available same-cell observations over
`[t-3, t+3]`, inclusive, before saving the splits. Observed temperatures are
preserved; replacements are simultaneous and never reused to fill another gap.
Windows with no available observations remain missing. The centered fill uses
future days and can cross temporal partitions. Other missing values are retained,
including humidity and wind on the four dates excluded later from clean tables.
The history folder supplies August observations for the 30-day precipitation and
7-day minimum-temperature features; clean modelling dates begin on 2020-09-01.

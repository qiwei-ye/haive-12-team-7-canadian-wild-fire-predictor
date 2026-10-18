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
| [testing/](testing/README.md) | 2025-09-01 to 2026-08-31 | 365 |
| [training_validation/](training_validation/README.md) | 2020-09-01 to 2025-08-31 | 1,826 |

Observations outside these windows are discarded. Training and validation remain
combined here; the clean merge divides them chronologically. Missing values are
preserved, including the four dates excluded later from clean tables.

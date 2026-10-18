# ORRC training/validation data

**Processing:** [ORRC preprocessing](../README.md) standardizes coordinates and
units, computes Canadian source-centre means, aggregates daily observations, and
retains 2020-09-01 to 2025-08-31, inclusive. The training/validation window is kept
together here; no random split is applied.

**Data:** Four NetCDF files, each with dimensions `(time: 1826, cell: 2168)`, daily
dates, and EPSG:4326 1° latitude x 1° longitude centre coordinates.

| File | Variable | Definition | Unit |
| --- | --- | --- | --- |
| `hurs.nc` | `hurs` | Near-surface relative humidity. | % |
| `pr.nc` | `pr` | Daily precipitation amount. | mm day-1 |
| `sfcWind.nc` | `sfcWind` | Near-surface wind speed. | m s-1 |
| `tas.nc` | `tas` | Near-surface air temperature. | degC |

Missing values remain NaN. The daily coordinate includes 2025-05-26, which is
excluded from the later clean tables: `hurs`, `sfcWind`, and `tas` are missing for
every cell on that date, while `pr` remains available. The clean merge applies the
configured chronological 80/20 split.

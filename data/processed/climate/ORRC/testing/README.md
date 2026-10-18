# ORRC testing data

**Processing:** [ORRC preprocessing](../README.md) standardizes coordinates and
units, computes Canadian source-centre means, aggregates daily observations, and
retains the configured testing window: 2025-09-01 to 2026-08-31, inclusive.

**Data:** Four NetCDF files, each with dimensions `(time: 365, cell: 2168)`, daily
dates, and EPSG:4326 1° latitude x 1° longitude centre coordinates.

| File | Variable | Definition | Unit |
| --- | --- | --- | --- |
| `hurs.nc` | `hurs` | Near-surface relative humidity. | % |
| `pr.nc` | `pr` | Daily precipitation amount. | mm day-1 |
| `sfcWind.nc` | `sfcWind` | Near-surface wind speed. | m s-1 |
| `tas.nc` | `tas` | Near-surface air temperature. | degC |

Missing values remain NaN. The daily coordinate includes 2026-03-17, 2026-04-13,
and 2026-04-14, which are excluded from the later clean tables: `hurs`, `sfcWind`,
and `tas` are missing for every cell on these dates, while `pr` remains available.

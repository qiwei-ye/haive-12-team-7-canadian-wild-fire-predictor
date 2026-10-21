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

The daily coordinate includes 2026-03-17, 2026-04-13, and 2026-04-14. Missing `tas`
on these dates is filled with the same-cell mean of original available values over
`[t-3, t+3]`. Consecutive gaps are filled simultaneously using original
observations. These dates remain excluded from clean tables because `hurs` and
`sfcWind` are still missing for every cell. `pr` remains available. Other missing
values remain NaN, including any temperature window with no observations.

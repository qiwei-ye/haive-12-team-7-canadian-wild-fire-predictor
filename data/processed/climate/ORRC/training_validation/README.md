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

The daily coordinate includes 2025-05-26. Missing `tas` on this date is filled with
the same-cell mean of original available temperatures over `[t-3, t+3]`; observed
values are preserved. The date remains excluded from clean tables because `hurs`
and `sfcWind` are still missing for every cell. `pr` remains available. Other
missing values remain NaN. The clean merge applies the
configured chronological 80/20 split.

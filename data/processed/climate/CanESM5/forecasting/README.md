# CanESM5 forecasting data

**Processing:** [CanESM5 preprocessing](../README.md) combines annual inputs,
applies Canadian source-centre means and unit conversions, and selects only
2026-09-01 to 2027-08-31, inclusive. No historical split is produced.

**Data:** Four NetCDF files, each with dimensions `(time: 365, cell: 2168)`, daily
dates, and common EPSG:4326 1° latitude x 1° longitude centre coordinates.

| File | Variable | Definition | Unit |
| --- | --- | --- | --- |
| `hurs.nc` | `hurs` | Near-surface relative humidity. | % |
| `pr.nc` | `pr` | Daily precipitation amount. | mm day-1 |
| `sfcWind.nc` | `sfcWind` | Near-surface wind speed. | m s-1 |
| `tas.nc` | `tas` | Near-surface air temperature. | degC |

All files represent SSP585, member `r1i1p1f1`. Unavailable source values and
unsupported target cells remain NaN; the grid does not add native spatial detail.

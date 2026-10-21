# ORRC climate history

**Processing:** [ORRC preprocessing](../README.md) converts source units and
coordinates, averages valid Canadian source centres, and aggregates daily values
from 2020-08-01 to 2020-08-31, inclusive. These observations supply lookback
features before the first clean training date; no modelling rows are created here.

**Data:** Each NetCDF has dimensions `(time: 31, cell: 2168)` on the common
EPSG:4326 1 degree latitude x 1 degree longitude grid, with `lat(cell)` and
`lon(cell)` coordinates. Missing source observations remain NaN.

| File | Variable | Definition | Unit |
| --- | --- | --- | --- |
| `hurs.nc` | `hurs` | Near-surface relative humidity. | % |
| `pr.nc` | `pr` | Daily precipitation amount. | mm day-1 |
| `sfcWind.nc` | `sfcWind` | Near-surface wind speed. | m s-1 |
| `tas.nc` | `tas` | Daily average near-surface air temperature. | degC |

The clean merge combines these dates with the full historical climate timeline
before computing inclusive 30-day precipitation sums and 7-day temperature
minima. Required missing observations propagate to derived features.

# Processed CanSIPSv3 predictors

**Processing:** GRIB inputs from `data/raw/climate/CanSIPSv3/` are grouped by
forecast system, initialization, and ensemble member. Valid times are derived
from initialization plus lead time. Six-hourly samples use complete daily
intervals `(00:00, next 00:00]`, labelled by interval start. Daily wind speed is
the mean of subdaily `sqrt(uas² + vas²)` values.

Accumulated precipitation is converted from metres to millimetres and differenced
between consecutive 24-hour totals on the native grid before spatial averaging.
Missing intervals, negative accumulation differences, and incomplete daily
samples remain NaN. Canadian source-centre means give the common grid; Kelvin
temperatures become Celsius. Relative humidity is unavailable and is not inferred
from dewpoint. Models and ensemble members are never averaged together.

**Data:** [forecasting/](forecasting/README.md) contains one NetCDF per model,
initialized on 2026-09-01: CanESM5.1p1bc and GEM5.2-NEMO. Each retains 20 members,
181 daily dates from 2026-09-01 to 2027-02-28, and 2,168 cells. `tas`, `tdps`,
`uas`, `vas`, `pr`, and `sfcWind` are stored with forecast-reference and lead-time
coordinates. Available coverage is six months; no later values are fabricated.

Only the configured forecasting window is eligible; these sources contribute
no training or testing observations. The large output NetCDF files use Git LFS.

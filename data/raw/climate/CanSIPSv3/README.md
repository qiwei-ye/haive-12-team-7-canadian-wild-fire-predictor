**File name:** `ECCC_system4_CanESM5_1p1bc_20260901_20270228_6hourly.grib`

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**File purpose:** Provide seasonal forecasts of near-surface air temperature, dewpoint temperature, and wind over the Canada region at 6-hour intervals for 20 ensemble members for the CanESM5.1p1bc model.

**Time horizon:** 2026-09-01 to 2027-03-01

**Grid resolution:** 1 degree latitude x 1 degree longitude

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `dataDate` | Nominal forecast reference date. | `YYYYMMDD`; value: `20260901` |
| `dataTime` | Nominal forecast reference time of day. | `HHMM` (UTC); value: `0000` |
| `step` | Forecast lead time from the reference time. | Hours; 6 to 4,344 in 6-hour increments |
| `systemNumber` | CanSIPSv3 forecast model identifier. | `4`: CanESM5.1p1bc |
| `perturbationNumber` | Ensemble member identifier within the model. | Integer; 0 to 19 |
| `latitude` | Latitude of the grid cell centre. | Decimal degrees north |
| `longitude` | Longitude of the grid cell centre. | Decimal degrees east |
| `2t` (GRIB parameter 167) | Instantaneous air temperature at 2 metres above the surface. | Kelvin (K); subtract 273.15 to obtain degrees Celsius (°C) |
| `2d` (GRIB parameter 168) | Instantaneous dewpoint temperature at 2 metres above the surface. | Kelvin (K); subtract 273.15 to obtain degrees Celsius (°C) |
| `10u` (GRIB parameter 165) | Instantaneous eastward wind component at 10 metres above the surface; positive values indicate eastward flow. | Metres per second (m/s) |
| `10v` (GRIB parameter 166) | Instantaneous northward wind component at 10 metres above the surface; positive values indicate northward flow. | Metres per second (m/s) |

---

**File name:** `ECCC_system4_CanESM5_1p1bc_20260901_20270228_total_precipitation.grib`

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**File purpose:** Provide seasonal forecasts of accumulated precipitation over the Canada region at 24-hour intervals for 20 ensemble members for the CanESM5.1p1bc model.

**Time horizon:** 2026-09-02 to 2027-03-01

**Grid resolution:** 1 degree latitude x 1 degree longitude

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `dataDate` | Nominal forecast reference date. | `YYYYMMDD`; value: `20260901` |
| `dataTime` | Nominal forecast reference time of day. | `HHMM` (UTC); value: `0000` |
| `step` | Forecast lead time of the accumulation endpoint. | Hours; 24 to 4,344 in 24-hour increments |
| `systemNumber` | CanSIPSv3 forecast model identifier. | `4`: CanESM5.1p1bc |
| `perturbationNumber` | Ensemble member identifier within the model. | Integer; 0 to 19 |
| `latitude` | Latitude of the grid cell centre. | Decimal degrees north |
| `longitude` | Longitude of the grid cell centre. | Decimal degrees east |
| `tp` (GRIB parameter 228) | Total precipitation accumulated since the forecast reference time, including rain and the water equivalent of snow; subtract the preceding step's value from the current value to obtain a 24-hour total (the first step covers the first 24 hours). | Metres of water equivalent (m); multiply by 1,000 to obtain millimetres (mm) |

---

**File name:** `ECCC_system5_GEM5_2-NEMO_20260901_20270228_6hourly.grib`

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**File purpose:** Provide seasonal forecasts of near-surface air temperature, dewpoint temperature, and wind over the Canada region at 6-hour intervals for 20 ensemble members for the GEM5.2-NEMO model.

**Time horizon:** 2026-09-01 to 2027-03-01

**Grid resolution:** 1 degree latitude x 1 degree longitude

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `dataDate` | Nominal forecast reference date. | `YYYYMMDD`; value: `20260901` |
| `dataTime` | Nominal forecast reference time of day. | `HHMM` (UTC); value: `0000` |
| `step` | Forecast lead time from the reference time. | Hours; 6 to 4,344 in 6-hour increments |
| `systemNumber` | CanSIPSv3 forecast model identifier. | `5`: GEM5.2-NEMO |
| `perturbationNumber` | Ensemble member identifier within the model. | Integer; 0 to 19 |
| `latitude` | Latitude of the grid cell centre. | Decimal degrees north |
| `longitude` | Longitude of the grid cell centre. | Decimal degrees east |
| `2t` (GRIB parameter 167) | Instantaneous air temperature at 2 metres above the surface. | Kelvin (K); subtract 273.15 to obtain degrees Celsius (°C) |
| `2d` (GRIB parameter 168) | Instantaneous dewpoint temperature at 2 metres above the surface. | Kelvin (K); subtract 273.15 to obtain degrees Celsius (°C) |
| `10u` (GRIB parameter 165) | Instantaneous eastward wind component at 10 metres above the surface; positive values indicate eastward flow. | Metres per second (m/s) |
| `10v` (GRIB parameter 166) | Instantaneous northward wind component at 10 metres above the surface; positive values indicate northward flow. | Metres per second (m/s) |

---

**File name:** `ECCC_system5_GEM5_2-NEMO_20260901_20270228_total_precipitation.grib`

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**File purpose:** Provide seasonal forecasts of accumulated precipitation over the Canada region at 24-hour intervals for 20 ensemble members for the GEM5.2-NEMO model.

**Time horizon:** 2026-09-02 to 2027-03-01

**Grid resolution:** 1 degree latitude x 1 degree longitude

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `dataDate` | Nominal forecast reference date. | `YYYYMMDD`; value: `20260901` |
| `dataTime` | Nominal forecast reference time of day. | `HHMM` (UTC); value: `0000` |
| `step` | Forecast lead time of the accumulation endpoint. | Hours; 24 to 4,344 in 24-hour increments |
| `systemNumber` | CanSIPSv3 forecast model identifier. | `5`: GEM5.2-NEMO |
| `perturbationNumber` | Ensemble member identifier within the model. | Integer; 0 to 19 |
| `latitude` | Latitude of the grid cell centre. | Decimal degrees north |
| `longitude` | Longitude of the grid cell centre. | Decimal degrees east |
| `tp` (GRIB parameter 228) | Total precipitation accumulated since the forecast reference time, including rain and the water equivalent of snow; subtract the preceding step's value from the current value to obtain a 24-hour total (the first step covers the first 24 hours). | Metres of water equivalent (m); multiply by 1,000 to obtain millimetres (mm) |

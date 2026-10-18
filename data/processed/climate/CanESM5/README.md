# Processed CanESM5 predictors

**Processing:** Daily NetCDF inputs from `data/raw/climate/CanESM5_<variable>/`
are combined by variable and restricted to the configured forecasting window.
Coordinates and calendars are standardized, Canadian source centres are averaged
onto the common grid, temperatures are converted from Kelvin to Celsius, and
precipitation flux is converted to mm day-1. Missing values remain NaN.

**Data:** [forecasting/](forecasting/README.md) contains `hurs.nc`, `pr.nc`,
`sfcWind.nc`, and `tas.nc`, each with 365 daily dates from 2026-09-01 to 2027-08-31
and 2,168 cells. These are SSP585 model projections for member `r1i1p1f1`;
scenario and member are recorded in file attributes.

CanESM5 contributes only forecast-period data. The coarse native grid can leave
1° cells without a source centre; those values remain missing. Calendar
conversion preserves date labels without interpolating unavailable days.

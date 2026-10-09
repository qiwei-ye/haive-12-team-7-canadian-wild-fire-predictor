**File name structure:** `hurs_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`, where `{YYYY}` is `2026`, `2027`, or `2028` (3 files, each containing `hurs`).

**File path:** `data/raw/climate/CanESM5_hurs/hurs_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`

**File purpose:** Provide daily bias-corrected, downscaled CanESM5 climate projections under SSP5-8.5 (`ssp585`) for ensemble member `r1i1p1f1`.

**File source:** [NASA - NEX-GDDP-CMIP6 v2.0, CanESM5, SSP5-8.5, r1i1p1f1](https://ds.nccs.nasa.gov/thredds/catalog/AMES/NEX/GDDP-CMIP6/CanESM5/ssp585/r1i1p1f1/catalog.html).

**Time horizon:** 2026-01-01 to 2028-12-31

**Grid resolution:** 0.25 degrees latitude by 0.25 degrees longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily model time coordinate at 12:00. | Days since `1850-01-01 00:00:00`; calendar: `365_day` |
| `lat` | Latitude of the grid cell centre. | Decimal degrees north |
| `lon` | Longitude of the grid cell centre. | Decimal degrees east; 0-360 convention |
| `hurs` | Daily mean near-surface relative humidity, referenced to liquid water above 0 °C and ice below 0 °C; stored in `hurs_*.nc`. | Percent (%) |

---

**File name structure:** `pr_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`, where `{YYYY}` is `2026`, `2027`, or `2028` (3 files, each containing `pr`).

**File path:** `data/raw/climate/CanESM5_pr/pr_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`

**File purpose:** Provide daily bias-corrected, downscaled CanESM5 climate projections under SSP5-8.5 (`ssp585`) for ensemble member `r1i1p1f1`.

**File source:** [NASA - NEX-GDDP-CMIP6 v2.0, CanESM5, SSP5-8.5, r1i1p1f1](https://ds.nccs.nasa.gov/thredds/catalog/AMES/NEX/GDDP-CMIP6/CanESM5/ssp585/r1i1p1f1/catalog.html).

**Time horizon:** 2026-01-01 to 2028-12-31

**Grid resolution:** 0.25 degrees latitude by 0.25 degrees longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily model time coordinate at 12:00. | Days since `1850-01-01 00:00:00`; calendar: `365_day` |
| `lat` | Latitude of the grid cell centre. | Decimal degrees north |
| `lon` | Longitude of the grid cell centre. | Decimal degrees east; 0-360 convention |
| `pr` | Daily mean precipitation flux, including liquid and solid precipitation; stored in `pr_*.nc`. | Kilograms per square metre per second (kg/m²/s); multiply by 86,400 to obtain millimetres of water equivalent per day (mm/day) |

---

**File name structure:** `sfcWind_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`, where `{YYYY}` is `2026`, `2027`, or `2028` (3 files, each containing `sfcWind`).

**File path:** `data/raw/climate/CanESM5_sfcWind/sfcWind_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`

**File purpose:** Provide daily bias-corrected, downscaled CanESM5 climate projections under SSP5-8.5 (`ssp585`) for ensemble member `r1i1p1f1`.

**File source:** [NASA - NEX-GDDP-CMIP6 v2.0, CanESM5, SSP5-8.5, r1i1p1f1](https://ds.nccs.nasa.gov/thredds/catalog/AMES/NEX/GDDP-CMIP6/CanESM5/ssp585/r1i1p1f1/catalog.html).

**Time horizon:** 2026-01-01 to 2028-12-31

**Grid resolution:** 0.25 degrees latitude by 0.25 degrees longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily model time coordinate at 12:00. | Days since `1850-01-01 00:00:00`; calendar: `365_day` |
| `lat` | Latitude of the grid cell centre. | Decimal degrees north |
| `lon` | Longitude of the grid cell centre. | Decimal degrees east; 0-360 convention |
| `sfcWind` | Daily mean near-surface wind speed, usually at 10 metres above the surface; stored in `sfcWind_*.nc`. | Metres per second (m/s) |

---

**File name structure:** `tas_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`, where `{YYYY}` is `2026`, `2027`, or `2028` (3 files, each containing `tas`).

**File path:** `data/raw/climate/CanESM5_tas/tas_day_CanESM5_ssp585_r1i1p1f1_gn_{YYYY}_v2.0.nc`

**File purpose:** Provide daily bias-corrected, downscaled CanESM5 climate projections under SSP5-8.5 (`ssp585`) for ensemble member `r1i1p1f1`.

**File source:** [NASA - NEX-GDDP-CMIP6 v2.0, CanESM5, SSP5-8.5, r1i1p1f1](https://ds.nccs.nasa.gov/thredds/catalog/AMES/NEX/GDDP-CMIP6/CanESM5/ssp585/r1i1p1f1/catalog.html).

**Time horizon:** 2026-01-01 to 2028-12-31

**Grid resolution:** 0.25 degrees latitude by 0.25 degrees longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily model time coordinate at 12:00. | Days since `1850-01-01 00:00:00`; calendar: `365_day` |
| `lat` | Latitude of the grid cell centre. | Decimal degrees north |
| `lon` | Longitude of the grid cell centre. | Decimal degrees east; 0-360 convention |
| `tas` | Daily mean near-surface air temperature, usually at 2 metres above the surface, derived from downscaled daily maximum and minimum temperatures; stored in `tas_*.nc`. | Kelvin (K); subtract 273.15 to obtain degrees Celsius (°C) |

---

**File name:** `ECCC_system4_CanESM5_1p1bc_20260901_20270228_6hourly.grib`

**File path:** `data/raw/climate/CanSIPSv3/ECCC_system4_CanESM5_1p1bc_20260901_20270228_6hourly.grib`

**File purpose:** Provide seasonal forecasts of near-surface air temperature, dewpoint temperature, and wind over the Canada region at 6-hour intervals for 20 ensemble members per CanSIPSv3 model.

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**Time horizon:** 2026-09-01 to 2027-03-01

**Grid resolution:** 1 degree latitude by 1 degree longitude

| Variable | Definition | Units / format |
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

**File path:** `data/raw/climate/CanSIPSv3/ECCC_system4_CanESM5_1p1bc_20260901_20270228_total_precipitation.grib`

**File purpose:** Provide seasonal forecasts of accumulated precipitation over the Canada region at 24-hour intervals for 20 ensemble members per CanSIPSv3 model.

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**Time horizon:** 2026-09-02 to 2027-03-01

**Grid resolution:** 1 degree latitude by 1 degree longitude

| Variable | Definition | Units / format |
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

**File path:** `data/raw/climate/CanSIPSv3/ECCC_system5_GEM5_2-NEMO_20260901_20270228_6hourly.grib`

**File purpose:** Provide seasonal forecasts of near-surface air temperature, dewpoint temperature, and wind over the Canada region at 6-hour intervals for 20 ensemble members per CanSIPSv3 model.

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**Time horizon:** 2026-09-01 to 2027-03-01

**Grid resolution:** 1 degree latitude by 1 degree longitude

| Variable | Definition | Units / format |
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

**File path:** `data/raw/climate/CanSIPSv3/ECCC_system5_GEM5_2-NEMO_20260901_20270228_total_precipitation.grib`

**File purpose:** Provide seasonal forecasts of accumulated precipitation over the Canada region at 24-hour intervals for 20 ensemble members per CanSIPSv3 model.

**File source:** [Environment and Climate Change Canada (ECCC), via the Copernicus Climate Data Store - Seasonal forecast daily and subdaily data on single levels](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels).

**Time horizon:** 2026-09-02 to 2027-03-01

**Grid resolution:** 1 degree latitude by 1 degree longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `dataDate` | Nominal forecast reference date. | `YYYYMMDD`; value: `20260901` |
| `dataTime` | Nominal forecast reference time of day. | `HHMM` (UTC); value: `0000` |
| `step` | Forecast lead time of the accumulation endpoint. | Hours; 24 to 4,344 in 24-hour increments |
| `systemNumber` | CanSIPSv3 forecast model identifier. | `5`: GEM5.2-NEMO |
| `perturbationNumber` | Ensemble member identifier within the model. | Integer; 0 to 19 |
| `latitude` | Latitude of the grid cell centre. | Decimal degrees north |
| `longitude` | Longitude of the grid cell centre. | Decimal degrees east |
| `tp` (GRIB parameter 228) | Total precipitation accumulated since the forecast reference time, including rain and the water equivalent of snow; subtract the preceding step's value from the current value to obtain a 24-hour total (the first step covers the first 24 hours). | Metres of water equivalent (m); multiply by 1,000 to obtain millimetres (mm) |

---

**File name structure:** `hurs_day_NAM_Ouranos_ORRC_v10_{period}.nc`, where `{period}` is `2019-2022` or `20230101-20260926` (2 files, each containing `hurs`).

**File path:** `data/raw/climate/ORRC v1.0_hurs/hurs_day_NAM_Ouranos_ORRC_v10_{period}.nc`

**File purpose:** Provide daily reconstructed near-surface weather for the North American domain from Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0.

**File source:** [Ouranos - Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0](https://doi.org/10.5281/zenodo.21381480); [Ouranos - ORRC data catalogue](https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/ouranos/ORRC/catalog.html).

**Time horizon:** 2019-01-01 to 2026-09-26

**Grid resolution:** 0.09 degrees rotated latitude by 0.09 degrees rotated longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily time coordinate at 00:00. | Days since `2015-01-01 00:00:00`; calendar: `proleptic_gregorian` |
| `rlat` | Rotated latitude of the grid cell centre. | Degrees |
| `rlon` | Rotated longitude of the grid cell centre. | Degrees |
| `lat` | Geographic latitude of the grid cell centre. | Decimal degrees north; 2D array (`rlat`, `rlon`) |
| `lon` | Geographic longitude of the grid cell centre. | Decimal degrees east; negative values indicate west; 2D array (`rlat`, `rlon`) |
| `rotated_pole` | Coordinate reference system of the rotated grid. | Scalar grid mapping metadata; `rotated_latitude_longitude` |
| `hurs` | Daily mean relative humidity at 1.5 metres above the surface; stored in `hurs_*.nc`. | Percent (%) |

---

**File name structure:** `pr_day_NAM_Ouranos_ORRC_v10_{period}.nc`, where `{period}` is `2019-2022` or `20230101-20260926` (2 files, each containing `pr`).

**File path:** `data/raw/climate/ORRC v1.0_pr/pr_day_NAM_Ouranos_ORRC_v10_{period}.nc`

**File purpose:** Provide daily reconstructed near-surface weather for the North American domain from Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0.

**File source:** [Ouranos - Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0](https://doi.org/10.5281/zenodo.21381480); [Ouranos - ORRC data catalogue](https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/ouranos/ORRC/catalog.html).

**Time horizon:** 2019-01-01 to 2026-09-26

**Grid resolution:** 0.09 degrees rotated latitude by 0.09 degrees rotated longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily time coordinate at 00:00. | Days since `2015-01-01 00:00:00`; calendar: `proleptic_gregorian` |
| `rlat` | Rotated latitude of the grid cell centre. | Degrees |
| `rlon` | Rotated longitude of the grid cell centre. | Degrees |
| `lat` | Geographic latitude of the grid cell centre. | Decimal degrees north; 2D array (`rlat`, `rlon`) |
| `lon` | Geographic longitude of the grid cell centre. | Decimal degrees east; negative values indicate west; 2D array (`rlat`, `rlon`) |
| `rotated_pole` | Coordinate reference system of the rotated grid. | Scalar grid mapping metadata; `rotated_latitude_longitude` |
| `pr` | Daily mean precipitation flux adjusted with the Canadian Precipitation Analysis (CaPA); stored in `pr_*.nc`. | Kilograms per square metre per second (kg/m²/s); multiply by 86,400 to obtain millimetres of water equivalent per day (mm/day) |

---

**File name structure:** `sfcWind_day_NAM_Ouranos_ORRC_v10_{period}.nc`, where `{period}` is `2019-2022` or `20230101-20260926` (2 files, each containing `sfcWind`).

**File path:** `data/raw/climate/ORRC v1.0_sfcWind/sfcWind_day_NAM_Ouranos_ORRC_v10_{period}.nc`

**File purpose:** Provide daily reconstructed near-surface weather for the North American domain from Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0.

**File source:** [Ouranos - Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0](https://doi.org/10.5281/zenodo.21381480); [Ouranos - ORRC data catalogue](https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/ouranos/ORRC/catalog.html).

**Time horizon:** 2019-01-01 to 2026-09-26

**Grid resolution:** 0.09 degrees rotated latitude by 0.09 degrees rotated longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily time coordinate at 00:00. | Days since `2015-01-01 00:00:00`; calendar: `proleptic_gregorian` |
| `rlat` | Rotated latitude of the grid cell centre. | Degrees |
| `rlon` | Rotated longitude of the grid cell centre. | Degrees |
| `lat` | Geographic latitude of the grid cell centre. | Decimal degrees north; 2D array (`rlat`, `rlon`) |
| `lon` | Geographic longitude of the grid cell centre. | Decimal degrees east; negative values indicate west; 2D array (`rlat`, `rlon`) |
| `rotated_pole` | Coordinate reference system of the rotated grid. | Scalar grid mapping metadata; `rotated_latitude_longitude` |
| `sfcWind` | Daily mean wind speed at 10 metres above the surface; stored in `sfcWind_*.nc`. | Metres per second (m/s) |

---

**File name structure:** `tas_day_NAM_Ouranos_ORRC_v10_{period}.nc`, where `{period}` is `2019-2022` or `20230101-20260926` (2 files, each containing `tas`).

**File path:** `data/raw/climate/ORRC v1.0_tas/tas_day_NAM_Ouranos_ORRC_v10_{period}.nc`

**File purpose:** Provide daily reconstructed near-surface weather for the North American domain from Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0.

**File source:** [Ouranos - Ouranos Reconstruction - RDPS-CaPA (ORRC) v1.0](https://doi.org/10.5281/zenodo.21381480); [Ouranos - ORRC data catalogue](https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/ouranos/ORRC/catalog.html).

**Time horizon:** 2019-01-01 to 2026-09-26

**Grid resolution:** 0.09 degrees rotated latitude by 0.09 degrees rotated longitude

| Variable | Definition | Units / format |
| --- | --- | --- |
| `time` | Daily time coordinate at 00:00. | Days since `2015-01-01 00:00:00`; calendar: `proleptic_gregorian` |
| `rlat` | Rotated latitude of the grid cell centre. | Degrees |
| `rlon` | Rotated longitude of the grid cell centre. | Degrees |
| `lat` | Geographic latitude of the grid cell centre. | Decimal degrees north; 2D array (`rlat`, `rlon`) |
| `lon` | Geographic longitude of the grid cell centre. | Decimal degrees east; negative values indicate west; 2D array (`rlat`, `rlon`) |
| `rotated_pole` | Coordinate reference system of the rotated grid. | Scalar grid mapping metadata; `rotated_latitude_longitude` |
| `tas` | Daily mean air temperature at 1.5 metres above the surface; stored in `tas_*.nc`. | Kelvin (K); subtract 273.15 to obtain degrees Celsius (°C) |

---

**File name:** `NFDB_point_20260811.csv`

**File path:** `data/raw/fire/Canadian National Fire Database/NFDB_point_20260811.csv`

**File purpose:** Provide Canadian fire records, including locations, dates, burned areas, causes, and source agency attributes.

**File source:** [Natural Resources Canada, Canadian Forest Service - Canadian National Fire Database (CNFDB)](https://cwfis.cfs.nrcan.gc.ca/ha/nfdb).

**Time horizon:** 1930-01-01 to 2025-12-31

**Grid resolution:** Not applicable

| Variable | Definition | Units / format |
| --- | --- | --- |
| `NFDBFIREID` | National fire identifier combining `SRC_AGENCY`, `YEAR`, and `FIRE_ID`. | Text |
| `SRC_AGENCY` | Source agency for the fire record. | Province or territory code, or `PC` (Parks Canada) |
| `NAT_PARK` | National park identifier, where applicable. | Text code; blank if not provided |
| `FIRE_ID` | Fire identifier assigned by the source agency. | Text |
| `FIRENAME` | Fire name assigned by the source agency. | Text; blank if not provided |
| `LATITUDE` | Latitude of the reported fire location. | Decimal degrees north |
| `LONGITUDE` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `YEAR` | Recorded year of the fire. | Integer year; `-999`: unknown |
| `MONTH` | Recorded month of the fire. | Integer; 1 to 12; `0`: unspecified |
| `DAY` | Recorded day of the fire (day of month). | Integer; 1 to 31; `0`: unspecified |
| `REP_DATE` | Fire date reported by the source agency. | `YYYY-MM-DD H:MM:SS`; blank if not provided |
| `ATTK_DATE` | Recorded date of the initial attack. | `YYYY-MM-DD H:MM:SS`; blank if not provided |
| `OUT_DATE` | Recorded date the fire was extinguished. | `YYYY-MM-DD H:MM:SS`; blank if not provided |
| `SIZE_HA` | Fire area reported by the source agency. | Hectares (ha) |
| `CAUSE` | National fire-cause classification. | `H`: human; `N`: natural/lightning; `U`: unknown |
| `CAUSE2` | Fire cause reported by the source agency, including additional categories. | `H`, `N`, `U` as above; `H-PB`: prescribed burn; `RE`: reburn |
| `FIRE_TYPE` | Fire type used by the source agency. | Text or code; blank if not provided |
| `RESPONSE` | Fire management response category used by the source agency. | Text or code; for example, `FUL`: full, `MOD`: modified, `MON`: monitored; blank if not provided |
| `PROTZONE` | Protection zone used by the source agency. | Text or code; blank if not provided |
| `PRESCRIBED` | Prescribed-burn status recorded by the source agency. | `PB` or `1`: prescribed; `No` or `0`: not prescribed; blank if not provided |
| `MORE_INFO` | Additional attributes supplied by the source agency. | Text; blank if not provided |
| `CFS_NOTE1` | Canadian Forest Service compilation note. | Text; blank if not provided |
| `CFS_NOTE2` | Additional Canadian Forest Service compilation note. | Text; blank if not provided |
| `ACQ_DATE` | Date the source agency's data were acquired. | `YYYY-MM-DD H:MM:SS`; blank if not provided |

---

**File name:** `ciffc.csv`

**File path:** `data/raw/fire/CIFFC/ciffc.csv`

**File purpose:** Provide Canadian wildland fire records, including agency identifiers, situation report and status dates, control status, causes, response categories, reported areas, and locations, in a headerless CSV.

**File source:** [Canadian Interagency Forest Fire Centre (CIFFC) - National Fires List](https://ciffc.net/national).

**Time horizon:** 2020-05-26 to 2026-10-09

**Grid resolution:** Not applicable

| Variable | Definition | Units / format |
| --- | --- | --- |
| Column 1 (`agency_fire_id`) | Fire identifier assigned by the source agency. | Text |
| Column 2 (`agency_code`) | Source agency for the fire record. | Province or territory code, or `PC` (Parks Canada) |
| Column 3 (`situation_report_date`) | Recorded situation report date and time. | `YYYY-MM-DDTHH:MM:SS` |
| Column 4 (`status_date`) | Date and time of the latest fire status update. | `YYYY-MM-DDTHH:MM:SS` |
| Column 5 (`stage_of_control`) | Recorded stage of control. | `out_of_control`, `being_held`, `under_control`, or `extinguished` |
| Column 6 (`national_fire_cause`) | National fire-cause classification. | `human`, `natural`, or `undetermined` |
| Column 7 (`response_type`) | Fire management response category. | `full_response`, `modified_response`, or `monitored_response` |
| Column 8 (`fire_size`) | Fire area reported by the source agency. | Hectares (ha) |
| Column 9 (`latitude`) | Latitude of the reported fire location. | Decimal degrees north |
| Column 10 (`longitude`) | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |

---

**File name:** `landcover-2020-classification.tif`

**File path:** `data/raw/geological/2020 Land Cover of Canada/landcover-2020-classification.tif`

**File purpose:** Provide Canada's 2020 land-cover classes as a single-band categorical raster.

**File source:** [Natural Resources Canada - 2020 Land Cover of Canada](https://open.canada.ca/data/en/dataset/ee1580ab-a23d-4f86-a09b-79763677eb47); [Natural Resources Canada - Land Cover Class Index](https://datacube-prod-data-public.s3.ca-central-1.amazonaws.com/store/land/landcover/ClassIndex_v2.pdf).

**Time horizon:** Not applicable, static snapshot

**Grid resolution:** 30 metres by 30 metres

| Variable | Definition | Units / format |
| --- | --- | --- |
| Band 1 (`Canada2020`) | Land-cover class assigned to each pixel. | Unsigned 8-bit integer code; `0`: no data |

**Class codes:**

| Code | Definition |
| --- | --- |
| `0` | No data |
| `1` | Temperate or sub-polar needleleaf forest |
| `2` | Sub-polar taiga needleleaf forest |
| `5` | Temperate or sub-polar broadleaf deciduous forest |
| `6` | Mixed forest |
| `8` | Temperate or sub-polar shrubland |
| `10` | Temperate or sub-polar grassland |
| `11` | Sub-polar or polar shrubland-lichen-moss |
| `12` | Sub-polar or polar grassland-lichen-moss |
| `13` | Sub-polar or polar barren-lichen-moss |
| `14` | Wetland |
| `15` | Cropland |
| `16` | Barren land |
| `17` | Urban and built-up |
| `18` | Water |
| `19` | Snow and ice |

---

**File name:** `CIFFC_standard_colours_for_FBPfueltypes.pdf`

**File path:** `data/raw/geological/FBPfueltypes/CIFFC_standard_colours_for_FBPfueltypes.pdf`

**File purpose:** Provide standard map colours for Fire Behaviour Prediction (FBP) fuel types, developed by the Canadian Interagency Forest Fire Centre (CIFFC) Geospatial Working Group.

**File source:** [Canadian Interagency Forest Fire Centre (CIFFC) - Standard FBP Fueltypes, hosted by Natural Resources Canada](https://cwfis.cfs.nrcan.gc.ca/downloads/fuels/current/CIFFC_standard_colours_for_FBPfueltypes.pdf).

**Time horizon:** Not applicable

**Grid resolution:** Not applicable

| Variable | Definition | Units / format |
| --- | --- | --- |
| `Agency fuel type` | Fuel-type name used in the reference. | Text |
| `FBP fuel type` | Symbolic identifier for the fuel type. | `C-1` to `C-7`, `D-1`, `D-2`, `M-1` to `M-4`, `S-1` to `S-3`, `O-1a`, `O-1b`, `Non-fuel`, or `Water` |
| `R` | Red component of the standard colour. | Integer; 0 to 255 |
| `G` | Green component of the standard colour. | Integer; 0 to 255 |
| `B` | Blue component of the standard colour. | Integer; 0 to 255 |

---

**File name:** `FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif`

**File path:** `data/raw/geological/FBPfueltypes/FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif`

**File purpose:** Provide Canada's FBP fuel-type classes as a single-band categorical raster.

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS FBP fuel-type downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/fuels/current/).

**Time horizon:** Not applicable, static snapshot

**Grid resolution:** 100 metres by 100 metres

| Variable | Definition | Units / format |
| --- | --- | --- |
| Band 1 (`Canadian FBP Fuel Types, 100m, May 27th, 2024`) | FBP fuel-type class assigned to each pixel. | Signed 16-bit integer code; `-9999`: no data |

---

**File name:** `dt_elevation.dbf`

**File path:** `data/raw/geological/National Ecological Framework/dt_elevation.dbf`

**File purpose:** Provide the minimum, maximum, mean, and range of elevation for 1,021 Canadian ecodistricts.

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework: Elevation Data (1999)](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/1999report/elevation.html).

**Time horizon:** Not applicable, static snapshot

**Grid resolution:** Not applicable

| Variable | Definition | Units / format |
| --- | --- | --- |
| `DISTRICT` | Ecodistrict identifier; matches `ECODISTRIC` in `ecodistricts.dbf`. | Numeric identifier; stored with 5 decimal places |
| `MIN_ELEV` | Minimum elevation within the ecodistrict. | Metres (m) |
| `MAX_ELEV` | Maximum elevation within the ecodistrict. | Metres (m) |
| `MEAN_ELEV` | Mean elevation within the ecodistrict. | Metres (m) |
| `ELEVDIFF` | Elevation range: `MAX_ELEV` minus `MIN_ELEV`. | Metres (m) |

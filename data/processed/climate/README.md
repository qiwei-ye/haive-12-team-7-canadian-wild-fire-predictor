# Processed climate predictors

**Processing:** `src/data_climate.py` normalizes coordinates and longitudes,
averages valid Canadian source centres within each common grid cell, converts
units, and aggregates to daily values. Missing values remain NaN except for the
historical `tas` fill described below. Source definitions and windows come from
[configuration](../../../src/config.py) and the raw source READMEs.

**Data:** All files share the [common 2,168-cell grid](../README.md). ORRC and
CanESM5 store one variable per NetCDF with dimensions `(time, cell)`; CanSIPSv3
also retains separate model and ensemble-member dimensions.

| Source | Folder | Inclusive time coverage | Days |
| --- | --- | --- | --- |
| [CanESM5](CanESM5/README.md) | `forecasting/` | 2026-09-01 to 2027-08-31 | 365 |
| [CanSIPSv3](CanSIPSv3/README.md) | `forecasting/` | 2026-09-01 to 2027-02-28 | 181 |
| [ORRC](ORRC/README.md) | `history/` | 2020-08-01 to 2020-08-31 | 31 |
| [ORRC](ORRC/README.md) | `training_validation/` | 2020-09-01 to 2025-08-31 | 1,826 |
| [ORRC](ORRC/README.md) | `testing/` | 2025-09-01 to 2026-08-31 | 365 |

| Variable | Definition | Unit |
| --- | --- | --- |
| `hurs` | Near-surface relative humidity; ORRC and CanESM5 only. | % |
| `pr` | Daily precipitation amount. | mm day-1 |
| `sfcWind` | Near-surface wind speed. | m s-1 |
| `tas` | Near-surface air temperature. | degC |
| `tdps` | Near-surface dewpoint; CanSIPSv3 only. | degC |
| `uas`, `vas` | Eastward and northward wind components; CanSIPSv3 only. | m s-1 |

Historical and forecast sources remain separate. No random training/validation
split is performed here. Processed time coordinates
retain dates excluded later from clean tables. Historical ORRC `tas` uses a
same-cell centered `[t-3, t+3]` mean to fill missing values before saving splits.
Other missing climate values remain NaN; observed temperatures are unchanged.
The August history supplies complete lookback windows for the first clean dates;
it does not add modelling rows or change partition boundaries.

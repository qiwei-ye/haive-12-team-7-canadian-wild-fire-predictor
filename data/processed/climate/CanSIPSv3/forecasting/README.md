# CanSIPSv3 forecasting data

**Processing:** [CanSIPSv3 preprocessing](../README.md) converts lead times to
dates, aggregates complete subdaily intervals, deaccumulates precipitation,
converts units, and computes Canadian source-centre means on the common grid.

**Data:** Daily coverage is 2026-09-01 to 2027-02-28, inclusive. Each file has
dimensions `(model: 1, member: 20, time: 181, cell: 2168)`, EPSG:4326 1° latitude
x 1° longitude centres, `forecast_reference_time = 2026-09-01`, and daily
`lead_time` from 0 to 180 days. Members are numbered 0 to 19.

| File | Forecast model |
| --- | --- |
| `CanESM5.1p1bc_20260901.nc` | CanESM5.1p1bc, system 4. |
| `GEM5.2-NEMO_20260901.nc` | GEM5.2-NEMO, system 5. |

| Variable | Definition | Unit |
| --- | --- | --- |
| `tas` | Daily mean near-surface air temperature. | degC |
| `tdps` | Daily mean near-surface dewpoint. | degC |
| `uas`, `vas` | Daily mean eastward and northward wind components. | m s-1 |
| `sfcWind` | Daily mean subdaily wind-speed magnitude. | m s-1 |
| `pr` | Daily precipitation total after deaccumulation. | mm day-1 |

Missing data remain NaN. No humidity variable, ensemble averaging, or extension
through August 2027 is produced. These files use Git LFS.

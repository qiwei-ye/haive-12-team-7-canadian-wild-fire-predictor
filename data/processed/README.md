# Processed data

Parameters and source paths come from [src/config.py](../../src/config.py).
Processing uses `src/preprocessing.py`, `src/data_climate.py`,
`src/data_geological.py`, and `src/data_fire.py`; raw inputs remain unchanged.

**Processing:** Gridded predictors use a common 1° latitude x 1° longitude grid
in EPSG:4326, with `cell` IDs and `lat(cell)`, `lon(cell)` centre coordinates.
Longitudes use -180 to 180 degrees. Centres must intersect the dissolved Canadian
ecodistrict polygons; the 109 configured excluded cells are removed. The current
grid contains 2,168 cells. This boundary comes from the local ecological dataset.

Continuous climate values use means of valid Canadian source centres per cell.
Categorical rasters use mode; elevation uses polygon overlap weights. Missing
values remain missing except historical `tas`, whose missing values use available
same-cell observations over `[t-3, t+3]` in a single centered mean fill. Climate
outputs are daily and separated by configured
time windows; static predictors have no time dimension. Fire data retain event
dates and point locations, with grid assignment performed during the clean merge.
Fire processing begins on 2018-09-01; historical climate processing begins on
2020-08-01. August climate observations are stored as lookback history, while
clean modelling dates still begin on 2020-09-01.

| File/folder | Description |
| --- | --- |
| `grid.nc` | Common `cell`, `lat`, and `lon` coordinates; 2,168 cells, no time dimension. |
| `canada_cells.gpkg` | `cells` layer containing the Canadian portion of each retained grid cell, keyed by `cell`; EPSG:4326. |
| [climate/](climate/README.md) | Daily historical ORRC predictors and forecast-only CanESM5/CanSIPSv3 predictors. |
| [fire/](fire/README.md) | Consolidated CWFIS event records with NWT date corrections. |
| [static/](static/README.md) | Elevation, fuel type, and 2020 land-cover predictors stored once per cell. |

Run from the project root:

```powershell
.venv/Scripts/python.exe run_pipeline.py preprocess
.venv/Scripts/python.exe run_pipeline.py preprocess --only fire
```

The first command processes climate and geological predictors; the second
processes fire reports. Missing local source files are reported; no downloads are
performed. [Daily clean tables and their merged NetCDF](../README.md) are produced
separately with `run_pipeline.py merge`.

# Processed static predictors

**Processing:** `src/data_geological.py` reads the rasters and ecodistrict
attributes specified in [configuration](../../../src/config.py). Categorical
rasters are reprojected using mode with source nodata excluded. Elevation
attributes are joined by ecodistrict ID and weighted by Canadian polygon overlap
area. Reference documents are not processed as datasets.

**Data:** Each source folder contains `predictors.nc`, with 2,168 entries on the
[common EPSG:4326 1° grid](../README.md). All variables have dimension `cell`;
there is no time dimension, temporal split, or daily duplication. Native category
codes and missing values are preserved.

| Folder | Variables | Current missing cells |
| --- | --- | --- |
| [ecodistrict_elevation/](ecodistrict_elevation/README.md) | `ECODISTRIC`, `MIN_ELEV`, `MAX_ELEV`, `MEAN_ELEV`, `ELEVDIFF` | 0 per variable |
| [fuel_type/](fuel_type/README.md) | `fuel_type` | 596 |
| [landcover/](landcover/README.md) | `landcover`, 2020 snapshot | 0 |

The clean historical tables use elevation and 2020 land cover; fuel type and the
ecodistrict identifier remain available only in these processed source outputs.

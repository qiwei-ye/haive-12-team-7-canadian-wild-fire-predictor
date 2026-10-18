# Processed fuel type

**Processing:** The 100 m raster
`FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif` is reprojected to EPSG:4326 using
mode of valid source classes. Native nodata `-9999` is excluded; cells without
valid source support remain missing. Original category codes are preserved.
[Raw documentation](../../../raw/geological/FBPfueltypes/README.md) describes the
source raster and reference documents.

**Data:** `predictors.nc` stores static `fuel_type(cell)` on the common 1° latitude
x 1° longitude grid, with 2,168 cells and geographic centre coordinates. It is a
static May 2024 source snapshot, without temporal splitting or daily duplication.

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `fuel_type` | Modal FBP fuel-type category within each target cell. | Original integer class code; dimensionless; missing values decode as NaN |

Currently 1,572 cells have a category and 596 are missing. Missing cells are not
assigned a substitute class. Fuel type is excluded from the clean historical tables.

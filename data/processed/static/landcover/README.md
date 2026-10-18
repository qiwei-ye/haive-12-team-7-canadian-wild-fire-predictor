# Processed 2020 land cover

**Processing:** The 30 m `landcover-2020-classification.tif` raster is reprojected
to EPSG:4326 using mode of valid source classes; native nodata code 0 is excluded.
The common grid removes the 109 cells previously missing land cover. Category
codes retain the meanings in the [raw source README](../../../raw/geological/2020%20Land%20Cover%20of%20Canada/README.md).

**Data:** `predictors.nc` stores static `landcover(cell)` for the 2020 snapshot,
with 2,168 retained cells, EPSG:4326 centre coordinates, and 1° latitude x 1°
longitude spacing. All retained cells currently have a category.

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `landcover` | Modal 2020 land-cover class within each target cell. | Original integer class code; dimensionless |

No interpolation, temporal splitting, or daily duplication is performed. Missing
source support remains NaN when present. The clean merge uses this 2020 snapshot
for all historical dates.

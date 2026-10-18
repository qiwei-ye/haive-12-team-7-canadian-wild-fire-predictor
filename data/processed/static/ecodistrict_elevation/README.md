# Processed ecodistrict elevation

**Processing:** [National Ecological Framework inputs](../../../raw/geological/National%20Ecological%20Framework/README.md)
join `ecodistricts.shp:ECODISTRIC` to `dt_elevation.dbf:DISTRICT`. Each elevation
attribute is averaged using geodesic overlap area between ecodistrict polygons
and the Canadian portion of a grid cell. `ECODISTRIC` selects the district with
the greatest total overlap; ties choose the lower identifier.

**Data:** `predictors.nc` stores static `(cell: 2168)` variables on the EPSG:4326
1° latitude x 1° longitude grid, with `lat(cell)` and `lon(cell)` coordinates.
All five variables currently have complete coverage; no time dimension is added.

| Variable | Processed definition | Unit |
| --- | --- | --- |
| `ECODISTRIC` | Dominant ecodistrict identifier by overlap area. | Categorical code |
| `MIN_ELEV` | Area-weighted mean of district minimum-elevation attributes. | m |
| `MAX_ELEV` | Area-weighted mean of district maximum-elevation attributes. | m |
| `MEAN_ELEV` | Area-weighted mean of district mean-elevation attributes. | m |
| `ELEVDIFF` | Area-weighted mean of district elevation ranges. | m |

These values summarize ecodistrict attributes; they do not resolve terrain within
districts. Missing joins or spatial support remain NaN when present. The clean
merge uses the four elevation variables and omits `ECODISTRIC`.

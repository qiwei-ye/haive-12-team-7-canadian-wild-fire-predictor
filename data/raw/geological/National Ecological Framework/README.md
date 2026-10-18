**File name:** `dt_elevation.dbf`

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework: Elevation Data (1999)](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/1999report/elevation.html).

**File purpose:** Provide the minimum, maximum, mean, and range of elevation for 1,021 Canadian ecodistricts.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `DISTRICT` | Ecodistrict identifier; matches `ECODISTRIC` in `ecodistricts.dbf`. | Numeric identifier; stored with 5 decimal places |
| `MIN_ELEV` | Minimum elevation within the ecodistrict. | Metres (m) |
| `MAX_ELEV` | Maximum elevation within the ecodistrict. | Metres (m) |
| `MEAN_ELEV` | Mean elevation within the ecodistrict. | Metres (m) |
| `ELEVDIFF` | Elevation range: `MAX_ELEV` minus `MIN_ELEV`. | Metres (m) |

---

**File name:** `ecodistricts.dbf`

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework GIS data](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/gis_data.html).

**File purpose:** Provide the seven source attributes for 1,025 ecodistrict polygon records. ECODISTRIC links the polygons to DISTRICT in dt_elevation.dbf.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `AREA` | Source polygon-area attribute. | Numeric source value; units are not specified in the local attribute table |
| `PERIMETER` | Source polygon-perimeter attribute. | Numeric source value; units are not specified in the local attribute table |
| `DISTRICT_` | Source internal district-record identifier. | Integer identifier |
| `DISTRICT_I` | Source district-feature identifier. | Integer identifier |
| `ECODISTRIC` | Ecodistrict identifier; joins to DISTRICT in dt_elevation.dbf. | Integer identifier |
| `ECOREGION` | Ecoregion identifier. | Integer identifier |
| `REGION_POL` | Source region/polygon code, retained as supplied. | Integer source code; detailed coding is not specified locally |

---

**File name:** `ecodistricts.prj`

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework GIS data](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/gis_data.html).

**File purpose:** Define the geographic coordinate reference system used by ecodistricts.shp. This is a shapefile companion file containing coordinate metadata.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `GEOGCS` | Name of the geographic coordinate reference system. | WKT text; GCS_North_American_1983_CSRS98 (NAD83(CSRS)) |
| `DATUM` | Geodetic datum used by the coordinates. | WKT text; D_North_American_1983_CSRS98 |
| `SPHEROID` | Reference ellipsoid. | GRS_1980; semi-major axis 6,378,137 m; inverse flattening 298.257222101 |
| `PRIMEM` | Prime meridian. | Greenwich; 0 degrees |
| `UNIT` | Angular coordinate unit. | Degree; 0.0174532925199433 radians per degree |

---

**File name:** `ecodistricts.sbn`

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework GIS data](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/gis_data.html).

**File purpose:** Provide a spatial index for querying ecodistricts.shp in compatible GIS software. This companion file contains no predictor observations.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `spatial_index` | Spatial lookup information for the ecodistrict polygon geometries. | ESRI binary spatial-index file |

---

**File name:** `ecodistricts.sbx`

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework GIS data](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/gis_data.html).

**File purpose:** Provide the companion index for ecodistricts.sbn. This shapefile support file contains no predictor observations.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `spatial_index_lookup` | Lookup information supporting the ecodistrict spatial index. | ESRI binary spatial-index companion file |

---

**File name:** `ecodistricts.shp`

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework GIS data](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/gis_data.html).

**File purpose:** Provide 1,025 Canadian ecodistrict polygon geometries. Attribute records are stored in ecodistricts.dbf and coordinate metadata in ecodistricts.prj.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `geometry` | Ecodistrict polygon geometry. | ESRI shapefile polygons; longitude/latitude in decimal degrees, NAD83(CSRS), EPSG:4617 |

---

**File name:** `ecodistricts.shx`

**File source:** [Agriculture and Agri-Food Canada, CanSIS - National Ecological Framework GIS data](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/gis_data.html).

**File purpose:** Index the geometry records in ecodistricts.shp. This shapefile companion file contains no predictor observations.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `shape_record_index` | Lookup information for locating geometry records in ecodistricts.shp. | ESRI shapefile geometry-index file (binary) |

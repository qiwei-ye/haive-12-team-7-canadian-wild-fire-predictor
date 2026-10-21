**File name:** `reported_fires_2018_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-21.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2018, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2017-03-28 to 2018-11-06

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2019_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-21.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2019, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2019-01-01 to 2019-11-08

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2020_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-16.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2020, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2020-01-30 to 2020-12-19

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2021_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-16.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2021, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2021-01-10 to 2021-12-22

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2022_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-16.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2022, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2022-01-31 to 2022-12-21

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2023_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-16.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2023, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2023-01-06 to 2023-12-20

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2024_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-16.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2024, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2023-01-01 to 2024-12-31

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2025_year_end.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-16.

**File purpose:** Provide the CWFIS operational fire-report snapshot at the end of 2025, with one record per national fire identifier. Records are selected by record_end in the final second of December 31. Earlier-year carryover fires and source missing-value codes are retained; the time horizon describes the report-date field.

**Time horizon:** 2023-05-10 to 2025-12-22

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC; the CSV omits the timezone suffix |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

---

**File name:** `reported_fires_2026_latest.csv`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS reported-fire downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/reportedfires/); [Canadian Wildland Fire Information Framework GeoServer](https://geoserver.cwfif.nrcan.gc.ca/geoserver/wfs), layer `public:cwfif_national_reportedfires`. Downloaded 2026-10-16.

**File purpose:** Provide the latest available CWFIS operational reports for fire_year 2026 as downloaded on 2026-10-16, with one record per national fire identifier. Original report dates, current areas, and missing-value codes are retained; all 290 NWT report dates are January 1 in this snapshot.

**Time horizon:** 2026-01-01 to 2026-10-16

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `FID` | Feature identifier returned by the WFS service. | Text |
| `id` | Internal source record identifier. | Integer |
| `agency_code` | Source agency for the fire record. | Province or territory code, or `PC` for Parks Canada |
| `region_code` | Source agency's fire region code. | Text; blank if unavailable |
| `national_fire_id` | National identifier for the fire. | Text |
| `agency_fire_id` | Fire identifier assigned by the source agency. | Text |
| `national_fire_cause` | National fire-cause classification. | Source code; `H`: human, `N`: natural, `U`: unknown |
| `fire_type_ics` | Source incident-type classification. | Integer code; `-1` if unavailable |
| `severity_nearest_dsr` | Source nearest-DSR severity attribute. | Numeric source value; `-1` if unavailable |
| `fire_was_prescribed` | Source prescribed-fire indicator. | Integer flag; `-1` if unavailable |
| `percent_contained` | Reported proportion of fire containment. | Percent (%); `-1` if unavailable |
| `fire_size` | Latest reported fire area. | Hectares (ha); `-1` if unavailable, retained unchanged |
| `response_type` | Recorded fire management response category. | Source code; for example, `FUL` or `MON` |
| `stage_of_control_status` | Recorded fire control status. | Source code; for example, `EX` |
| `situation_report_date` | Recorded situation report timestamp. | ISO 8601 UTC, with no timezone suffix in the CSV; all 290 NWT records in the 2026 snapshot contain `2026-01-01T00:00:00` |
| `status_date` | Timestamp of the fire status update. | ISO 8601 UTC; distinct from a start, discovery, or report date |
| `latitude` | Latitude of the reported fire location. | Decimal degrees north |
| `longitude` | Longitude of the reported fire location. | Decimal degrees east; negative values indicate west |
| `geometry` | Native source point geometry. | WKT point; EPSG:3978, metres |
| `fire_year` | Recorded year assigned to the fire, retained as supplied. | Integer source year; may differ from the snapshot year |
| `status_year` | Year associated with the status timestamp. | Integer year |
| `record_start` | Beginning of the source record's validity interval. | ISO 8601 UTC |
| `record_end` | End of the source record's validity interval. | ISO 8601 UTC; may extend beyond the snapshot date |

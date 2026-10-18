**File name:** `fire_incidents_2026.json`

**File source:** [Government of the Northwest Territories, Environment and Climate Change - wildfire incident feed](https://www.gov.nt.ca/ecc/services/wildfire-update/sites/default/files/firedata/fires.json), used by the [official NWT fire map](https://www.gov.nt.ca/ecc/services/wildfire-update/en/firemap). Downloaded 2026-10-17; this is the unchanged snapshot used in the January 1 CWFIS comparison.

**File purpose:** Provide 290 NWT fire incidents for the 2026 season, including agency identifiers, starting locations, estimated start and discovery dates, areas, and operational classifications. Preserve the original JSON array, timestamp strings, zero values, and missing-value codes. The time horizon describes estimated start and discovery dates.

**Time horizon:** 2026-05-09 to 2026-09-26

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `latitude` | Latitude of the published starting location. | Decimal degrees north |
| `longitude` | Longitude of the published starting location. | Decimal degrees east; negative values indicate west |
| `title` | NWT agency fire identifier. | Text; for example, `ZF018-26` |
| `currentsize` | Current estimated fire area recorded by NWT. | Hectares (ha); source zero values retained unchanged |
| `estimatedstart` | Estimated fire start timestamp. | ISO 8601 `YYYY-MM-DDTHH:MM:SS`; no timezone suffix |
| `discoverydate` | Recorded fire discovery timestamp; may differ from estimated start. | ISO 8601 `YYYY-MM-DDTHH:MM:SS`; no timezone suffix |
| `reporteddate` | Recorded fire report timestamp, when available. | JSON boolean `false` in all 290 records, indicating unavailable report dates |
| `controlleddate` | Timestamp when the fire was recorded as controlled. | ISO 8601 `YYYY-MM-DDTHH:MM:SS`, without timezone suffix, or JSON boolean `false` if unavailable |
| `outdate` | Timestamp when the fire was declared out. | ISO 8601 `YYYY-MM-DDTHH:MM:SS`, without timezone suffix, or JSON boolean `false` if unavailable |
| `region` | NWT fire management region. | Text; for example, `South Slave` |
| `status` | Operational fire status code. | Text; for example, `DECLARED_OUT`, `OUT_OF_CONTROL`, or `UNDER_CONTROL` |
| `cause` | Broad recorded fire-cause classification. | Text; `Natural` or `Human Caused` |
| `subcause` | More detailed recorded cause, when available. | Text or JSON `null`; for example, `Lightning` or `Holdover` |
| `responsecategory` | Recorded fire management response category. | Text; for example, `Initial Attack`, `Sustained Action`, or `Being Monitored` |
| `filter` | Display grouping used by the official NWT fire map. | Text; for example, `Declared out`, `Being monitored`, `Being actioned`, or `Under control` |

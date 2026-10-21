# Processed fire records

**Processing:** `src/data_fire.py` reads the annual snapshots documented in
[raw/fire/CWFIS/README.md](../../raw/fire/CWFIS/README.md). Records are identified
by national fire ID; the earliest snapshot's complete record wins for repeated
IDs. Dates normally use the calendar portion of `situation_report_date`, without
timezone conversion or substitution of status dates.

January 1 NWT 2026 placeholders are matched to
[NWT records](../../raw/fire/NWT/README.md) by exact year/agency/fire ID, with
coordinates checked at CWFIS's four-decimal precision. Matched dates use NWT
`estimatedstart`; CWFIS locations and areas are preserved. This correction occurs
before retaining 2018-09-01 to 2026-08-31, inclusive. Fires in the 109 configured
excluded cells are removed. Unmatched January 1 dates remain unchanged and are
reported in console warnings. Negative, invalid, or unavailable areas remain blank.

**Data:** `cwfis.csv` contains 45,933 event rows, including 2,288 known large fires.
The current output has 24 missing areas and corresponding missing indicators;
IDs, coordinates, and dates are complete. Among corrected NWT dates, 288 events
remain in the historical window; two September 2026 events are excluded. Two
unmatched January 1, 2019 Alberta records and two January 1, 2023 Alberta records
remain unresolved. The 2018 and 2019 year-end snapshots extend available history
for the first clean training dates.

| Column | Definition | Unit/format |
| --- | --- | --- |
| `fire_id` | CWFIS national identifier distinguishing year and agency. | Text |
| `latitude` | Original fire-point latitude. | Decimal degrees north |
| `longitude` | Original fire-point longitude. | Decimal degrees east; west is negative |
| `report_date` | Processed fire date following the CWFIS/NWT rule above. | YYYY-MM-DD |
| `size_ha` | CWFIS reported fire area. | Hectares; blank if unknown |
| `is_large_fire` | 1 for area >= 1,000 ha, 0 for smaller known area. | Binary; blank if area is unknown |

Coordinates are geographic point locations; observations are kept per event
without daily duplication or spatial aggregation. The clean merge applies the
Canadian boundary and retained-grid checks, builds daily targets and preceding
two-calendar-year large/small-fire history features, and
uses 0 for missing target indicators. NWT start dates are estimates; original
NWT report dates are unavailable. No separate corrections CSV is generated.

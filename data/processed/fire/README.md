# Processed fire records

**Processing:** `src/data_fire.py` reads the annual snapshots documented in
[raw/fire/CWFIS/README.md](../../raw/fire/CWFIS/README.md). Records are identified
by national fire ID; the earliest snapshot's complete record wins for repeated
IDs. Dates normally use the calendar portion of `situation_report_date`, without
timezone conversion or substitution of status dates.

January 1 NWT 2026 placeholders are matched to
[NWT records](../../raw/fire/NWT/README.md) by exact year/agency/fire ID, with
coordinates checked at CWFIS's four-decimal precision. Matched dates use NWT
`estimatedstart`; CWFIS locations and valid areas are preserved. Missing or invalid
2026 NT areas use matched NWT `currentsize`, accepting published numeric zeros.
The same exact ID and coordinate checks apply to area replacements. These corrections occur
before retaining 2017-09-01 to 2026-08-31, inclusive. Fires in the 109 configured
excluded cells are removed. Unmatched January 1 dates remain unchanged and are
reported in console warnings. Areas without a valid CWFIS value or supported NWT
replacement remain blank.

**Data:** `cwfis.csv` contains 53,156 event rows, including 2,519 known large fires.
The 24 unavailable CWFIS areas use NWT's published zeros. All six columns are
complete. Among corrected NWT dates, 288 events
remain in the historical window; two September 2026 events are excluded. Two
unmatched January 1, 2019 Alberta records and two January 1, 2023 Alberta records
remain unresolved. The 2018 and 2019 snapshots provide context for the first
clean training dates. Fire-size features use `[t-90 days, t)` and
`[t-2 calendar years, t-90 days)`, including each lower bound and excluding each
upper bound.

| Column | Definition | Unit/format |
| --- | --- | --- |
| `fire_id` | CWFIS national identifier distinguishing year and agency. | Text |
| `latitude` | Original fire-point latitude. | Decimal degrees north |
| `longitude` | Original fire-point longitude. | Decimal degrees east; west is negative |
| `report_date` | Processed fire date following the CWFIS/NWT rule above. | YYYY-MM-DD |
| `size_ha` | CWFIS reported fire area, with matched NWT fallback for unavailable 2026 NT areas. | Hectares; blank if unresolved |
| `is_large_fire` | 1 for area >= 1,000 ha, 0 for smaller known area. | Binary; blank if area is unknown |

Coordinates are geographic point locations; observations are kept per event
without daily duplication or spatial aggregation. The clean merge applies the
Canadian boundary and retained-grid checks, builds daily targets and the two
numerical fire-size features, and
uses 0 for missing target indicators. NWT start dates are estimates; original
NWT report dates are unavailable. No separate corrections CSV is generated.
Accepting a published NWT zero does not establish that no fire occurred. Raw
CWFIS and NWT files are unchanged; `FIRE_AREA_DEFINITION` documents area provenance
in the clean/input summaries and NetCDF attributes.

The clean merge derives `90_day_fire_size` and `2_year_90_day_fire_size`, summing
stored areas across the centre cell and eight retained neighbours over their
configured disjoint windows. Today is excluded from both. Each fire contributes
once in hectares; an unknown area makes affected totals missing. Snapshot areas
are used rather than daily growth or reconstructed as-of-date areas.

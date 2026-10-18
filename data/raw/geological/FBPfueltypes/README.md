**File name:** `CIFFC_standard_colours_for_FBPfueltypes.pdf`

**File source:** [Canadian Interagency Forest Fire Centre (CIFFC) - Standard FBP Fueltypes, hosted by Natural Resources Canada](https://cwfis.cfs.nrcan.gc.ca/downloads/fuels/current/CIFFC_standard_colours_for_FBPfueltypes.pdf).

**File purpose:** Provide standard map colours for Fire Behaviour Prediction (FBP) fuel types, developed by the Canadian Interagency Forest Fire Centre (CIFFC) Geospatial Working Group.

**Time horizon:** static

**Grid resolution:** not applicable

| Variable | Definition | Unit/format |
| --- | --- | --- |
| `Agency fuel type` | Fuel-type name used in the reference. | Text |
| `FBP fuel type` | Symbolic identifier for the fuel type. | `C-1` to `C-7`, `D-1`, `D-2`, `M-1` to `M-4`, `S-1` to `S-3`, `O-1a`, `O-1b`, `Non-fuel`, or `Water` |
| `R` | Red component of the standard colour. | Integer; 0 to 255 |
| `G` | Green component of the standard colour. | Integer; 0 to 255 |
| `B` | Blue component of the standard colour. | Integer; 0 to 255 |

---

**File name:** `FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif`

**File source:** [Natural Resources Canada, Canadian Forest Service - CWFIS FBP fuel-type downloads](https://cwfis.cfs.nrcan.gc.ca/downloads/fuels/current/).

**File purpose:** Provide Canada's FBP fuel-type classes as a single-band categorical raster.

**Time horizon:** static

**Grid resolution:** 100 metres x 100 metres (native projected grid)

| Variable | Definition | Unit/format |
| --- | --- | --- |
| Band 1 (`Canadian FBP Fuel Types, 100m, May 27th, 2024`) | FBP fuel-type class assigned to each pixel. | Signed 16-bit integer code; `-9999`: no data |

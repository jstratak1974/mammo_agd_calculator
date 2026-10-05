# Mammography MGD/AGD Calculator

A small desktop application for estimating mean glandular dose (MGD), also
called average glandular dose (AGD), from incident air kerma and the `g`, `c`,
and `s` factors used in the Dance breast-dosimetry formalism.

The program provides a Tkinter graphical interface, loads coefficient tables
from a JSON file, interpolates the required factors, and reports the dose per
exposure and the total for a user-defined number of equal exposures.

> [!CAUTION]
> This repository is intended for medical-physics calculation support,
> education, and independent verification. The supplied JSON states that its
> values were transcribed from source tables and must be checked against the
> original publications before clinical use. Users are responsible for
> confirming the measurement geometry, coefficient set, spectrum factor,
> units, and applicability of the selected dosimetry protocol.

## Contents

- [Features](#features)
- [Calculation model](#calculation-model)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Input fields](#input-fields)
- [Coefficient tables](#coefficient-tables)
- [Interpolation and boundary behavior](#interpolation-and-boundary-behavior)
- [Worked examples](#worked-examples)
- [JSON format](#json-format)
- [Using the calculation functions from Python](#using-the-calculation-functions-from-python)
- [Validation](#validation)
- [Current limitations](#current-limitations)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Features

- Cross-platform desktop GUI built with the Python standard-library Tkinter
  interface.
- Automatic loading of `dance_factors.json` when it is found in the current
  working directory or beside the Python script.
- Manual selection of another JSON coefficient file.
- Bilinear interpolation of `g` over compressed breast thickness and HVL.
- Linear interpolation of `c` over glandularity, followed by interpolation
  over compressed breast thickness and HVL.
- Robust matching of numeric JSON keys such as `"0.30"`, `"0.3"`, `"45"`,
  and `"45.0"`.
- Optional conversion of entrance surface air kerma that includes backscatter
  to incident air kerma by division by a user-supplied backscatter factor.
- Manual spectrum correction factor `s`, or `s = 1.0`.
- Dose per exposure and total dose for multiple equal exposures.
- Copy-to-clipboard output.

## Calculation model

For one exposure, the program evaluates

$$
D_G = K_{a,i}\,g\,c\,s,
$$

where:

| Symbol | Meaning | Unit |
| --- | --- | --- |
| $D_G$ | Mean/average glandular dose | mGy |
| $K_{a,i}$ | Incident air kerma at the upper surface of the compressed breast, without backscatter | mGy |
| $g$ | Conversion from incident air kerma to glandular dose for the reference 50% glandularity breast model | Dimensionless |
| $c$ | Correction for glandularity other than the reference composition | Dimensionless |
| $s$ | Correction for the selected target/filter spectrum | Dimensionless |

The input field is labelled **ESD / ESE (mGy)**. Its treatment depends on the
backscatter checkbox:

$$
K_{a,i} =
\begin{cases}
\dfrac{K_{\mathrm{input}}}{\mathrm{BSF}}, &
\text{if the input includes backscatter},\\[6pt]
K_{\mathrm{input}}, &
\text{if the input is already incident air kerma without backscatter}.
\end{cases}
$$

For `N` equal exposures, the current implementation calculates

$$
D_{G,\mathrm{total}} = N\,D_G.
$$

The value entered in the dose field is therefore interpreted as the dose/kerma
quantity **per exposure**, not as the total for the series.

## Requirements

- Python 3.9 or later is recommended.
- Tk/Tkinter must be available in the Python installation.
- No third-party Python packages are required.
- `dance_factors.json`, or another compatible coefficient JSON file, is
  required for calculations.

Check whether Tkinter is available:

```bash
python -m tkinter
```

This should open a small Tk test window. On Debian or Ubuntu, install Tkinter
if needed:

```bash
sudo apt update
sudo apt install python3-tk
```

## Installation

Clone or download the repository, then keep the script and coefficient file in
the same directory:

```text
mammo-agd-calculator/
├── mammo_agd_calculator.py
├── dance_factors.json
└── README.md
```

No virtual environment is required because the application uses only Python's
standard library. A virtual environment can still be used if desired:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

## Quick start

Run the application from the repository directory:

```bash
python mammo_agd_calculator.py
```

On systems where Python 3 is invoked explicitly:

```bash
python3 mammo_agd_calculator.py
```

If `dance_factors.json` is in the working directory or beside the script, it is
loaded automatically. Otherwise:

1. Select **Load JSON...**.
2. Choose the required coefficient file.
3. Enter the measured dose/kerma and breast/beam parameters.
4. Select compatible `g` and `c` tables.
5. Enter a validated `s` factor or select `s = 1.0` when appropriate.
6. State whether the input includes backscatter and enter the applicable BSF.
7. Select **Calculate**.
8. Review the inputs, interpolated factors, incident air kerma, per-exposure
   dose, and total dose in the results panel.

## Input fields

| GUI field | Expected value | Notes |
| --- | --- | --- |
| **ESD / ESE (mGy)** | Positive number | Treated as a per-exposure input. The program divides it by BSF only when the backscatter option is selected. Confirm that the measured quantity and geometry agree with the protocol definition of $K_{a,i}$. |
| **Thickness (mm)** | Compressed breast thickness in millimetres | Used for both `g` and `c` interpolation. |
| **HVL (mm Al)** | Half-value layer in millimetres of aluminium | Used as the beam-quality coordinate for both `g` and `c`. |
| **Glandularity (%)** | Percentage by weight used by the selected table | `50` gives `c = 1.0` throughout the supplied `c` table. The lowest tabulated entry is `0.1%`, not zero. |
| **Number of exposures** | Integer greater than or equal to 1 | Multiplies the calculated per-exposure dose. Use only when each exposure can be represented by the same input and factors. |
| **g-table** | Name of a `g` table in the JSON | The script prefers `interpolated_JRM_Table3` when present. |
| **c-table** | Name of a `c` table in the JSON | The supplied JSON contains `dance_original_JRM_Table2`. |
| **Spectrum factor (s)** | `1.0` or a manually entered factor | The application does not derive `s` from anode/filter, kVp, or HVL. |
| **ESD includes backscatter** | Selected or cleared | When selected, $K_{a,i}=K_{\mathrm{input}}/\mathrm{BSF}$. |
| **BSF** | Positive number | Used only when the backscatter option is selected. The GUI default is `1.12`; this is an example and must be validated for the measurement setup. |

The initial GUI values are:

| Parameter | Initial value |
| --- | ---: |
| ESD/ESE | 3.57 mGy |
| Thickness | 42 mm |
| HVL | 0.517 mm Al |
| Glandularity | 50% |
| Exposures | 1 |
| `s` | 1.087 |
| Input includes backscatter | Yes |
| BSF | 1.12 |

These values demonstrate the interface. They do not define a recommended
clinical protocol. In particular, `0.517 mm Al` exceeds the HVL range of the
automatically selected `interpolated_JRM_Table3`; see
[Interpolation and boundary behavior](#interpolation-and-boundary-behavior).

## Coefficient tables

The supplied `dance_factors.json` has schema version `1.0` and contains the
following data.

### Usable `g` tables

| JSON table | Thickness grid | HVL grid | GUI behavior |
| --- | --- | --- | --- |
| `dance_original_JRM_Table1` | 20–110 mm; 11 tabulated thicknesses | 0.30–0.60 mm Al in 0.05 mm Al steps | Readable by the current script |
| `interpolated_JRM_Table3` | 20–60 mm in 5 mm steps | 0.30–0.45 mm Al in 0.01 mm Al steps | Readable; selected automatically when available |

### `c` table

| JSON table | Thickness grid | HVL grid | Glandularity grid |
| --- | --- | --- | --- |
| `dance_original_JRM_Table2` | 20–110 mm, mainly in 10 mm steps | 0.30, 0.35, 0.40, and 0.45 mm Al | 0.1%, 25%, 50%, 75%, and 100% |

### Incompatible table in the supplied JSON

The JSON also contains `dance1990_Table2_broader_HVL_range`, covering
2–8 cm and 0.25–2.00 mm Al. It is displayed in the `g`-table list, but the
current program cannot calculate from it because:

- it declares `thickness_cm` instead of the required `thickness_mm`; and
- its `values` hierarchy is `values[HVL][thickness]`, whereas the program
  expects `values[thickness_mm][HVL]`.

Selecting this table currently produces:

```text
g-table missing thickness_mm or hvl_mmAl.
```

Normalize that table to the schema described below before using it. Do not use
the broad-HVL selection as evidence that the table is supported.

### Spectrum factor

The JSON contains a note for `s`, but no machine-readable `s` table. The user
must enter a spectrum-specific value manually. The value must correspond to
the target/filter combination and dosimetry formalism being applied.

## Interpolation and boundary behavior

### `g` factor

`compute_g_from_table()` performs bilinear interpolation within the rectangular
grid defined by compressed breast thickness and HVL:

1. bracket the requested thickness between two table rows;
2. bracket the requested HVL between two table columns;
3. linearly interpolate across thickness at each bounding HVL; and
4. linearly interpolate those two results across HVL.

If either coordinate lies exactly on the grid, the interpolation reduces to a
one-dimensional interpolation or a direct table lookup.

### `c` factor

`compute_c_from_table()` interpolates in three dimensions:

1. linearly interpolate across glandularity at each required
   HVL/thickness corner;
2. interpolate the resulting values across thickness; and
3. interpolate across HVL.

### Numeric JSON keys

JSON object keys are strings. `_dict_get_by_numeric_key()` accepts common
representations of the same numeric coordinate, including:

```text
0.3  ↔  "0.3" or "0.30"
45.0 ↔  "45.0", "45", or "45.00"
```

### Out-of-range coordinates

The current `bracket()` function **clamps silently to the nearest boundary**.
It does not extrapolate and it does not warn the user.

Examples:

| Requested value | Table range | Value used |
| --- | --- | --- |
| Thickness 15 mm | 20–60 mm | 20 mm boundary |
| Thickness 75 mm | 20–60 mm | 60 mm boundary |
| HVL 0.25 mm Al | 0.30–0.45 mm Al | 0.30 mm Al boundary |
| HVL 0.517 mm Al | 0.30–0.45 mm Al | 0.45 mm Al boundary |

The clamping is performed independently for `g` and `c`, so tables with
different domains can use different boundary points for the same input.
Verify that all inputs lie within every selected table's range. Silent
clamping can otherwise produce a plausible-looking result based on unintended
coefficients.

## Worked examples

The following values were reproduced directly with
`mammo_agd_calculator.py` and the supplied `dance_factors.json`.

### Example 1: in-range single exposure

Inputs:

| Parameter | Value |
| --- | ---: |
| Input including backscatter | 3.570 mGy |
| BSF | 1.12 |
| Thickness | 42 mm |
| HVL | 0.417 mm Al |
| Glandularity | 50% |
| `g` table | `interpolated_JRM_Table3` |
| `c` table | `dance_original_JRM_Table2` |
| `s` | 1.087 |
| Exposures | 1 |

Derived values:

```text
Ka,i = 3.570 / 1.12 = 3.187500 mGy
g    = 0.259320
c    = 1.000000
s    = 1.087000
gcs  = 0.28188084
```

Result:

```text
MGD/AGD per exposure = 0.898495 mGy
MGD/AGD total        = 0.898495 mGy
```

### Example 2: effect of interpolating glandularity

Using the same inputs but changing glandularity from 50% to 37.5% gives:

```text
c                      = 1.053422
MGD/AGD per exposure   = 0.946495 mGy
```

The glandularity lies midway between the 25% and 50% entries, while thickness
and HVL also lie between tabulated coordinates.

### Built-in DBT button

The **Example DBT (9×0.402 mGy)** button fills the GUI with:

```text
Input per exposure = 0.402 mGy
Number of exposures = 9
Thickness = 50 mm
HVL = 0.517 mm Al
Glandularity = 50%
s = 1.087
Input includes backscatter = Yes
BSF = 1.12
```

With the automatically selected `interpolated_JRM_Table3`, the HVL is silently
clamped from 0.517 to 0.45 mm Al. The current result is:

```text
Ka,i per exposure      = 0.358929 mGy
g                      = 0.232000
c                      = 1.000000
MGD/AGD per exposure   = 0.090516 mGy
MGD/AGD total (×9)     = 0.814644 mGy
```

This button is an arithmetic demonstration. A formal DBT calculation may
require projection-angle `t` factors or a complete-sweep `T` factor. The
current application does not implement those factors and assumes all nine
exposures share the same central-projection `g`, `c`, and `s` values.

## JSON format

The application expects the following hierarchy:

```json
{
  "schema_version": "1.0",
  "coefficients": {
    "g": {
      "example_g_table": {
        "thickness_mm": [40, 50],
        "hvl_mmAl": [0.40, 0.45],
        "values": {
          "40": {
            "0.40": 0.261,
            "0.45": 0.289
          },
          "50": {
            "0.40": 0.209,
            "0.45": 0.232
          }
        }
      }
    },
    "c": {
      "example_c_table": {
        "thickness_mm": [40, 50],
        "hvl_mmAl": [0.40, 0.45],
        "glandularity_percent": [25, 50, 75],
        "values": {
          "0.40": {
            "40": {
              "25": 1.105,
              "50": 1.0,
              "75": 0.907
            },
            "50": {
              "25": 1.120,
              "50": 1.0,
              "75": 0.899
            }
          },
          "0.45": {
            "40": {
              "25": 1.102,
              "50": 1.0,
              "75": 0.909
            },
            "50": {
              "25": 1.115,
              "50": 1.0,
              "75": 0.898
            }
          }
        }
      }
    },
    "s": {
      "note": "Spectrum factors are entered manually in the GUI."
    }
  }
}
```

The required value layouts are:

```text
g values: values[thickness_mm][hvl_mmAl] = coefficient
c values: values[hvl_mmAl][thickness_mm][glandularity_percent] = coefficient
```

All coordinate lists must be non-empty. Numeric values may be JSON numbers,
while object keys are necessarily strings. Keep each coefficient value numeric.

## Using the calculation functions from Python

The calculation layer can be imported without starting the GUI because
`main()` runs only when the file is executed as a script.

```python
from mammo_agd_calculator import (
    compute_c_from_table,
    compute_g_from_table,
    compute_mgd,
    get_c_table,
    get_g_table,
    load_json,
)

data = load_json("dance_factors.json")

g_table = get_g_table(data, "interpolated_JRM_Table3")
c_table = get_c_table(data, "dance_original_JRM_Table2")

g = compute_g_from_table(
    g_table,
    thickness_mm=42,
    hvl_mmAl=0.417,
)

c = compute_c_from_table(
    c_table,
    thickness_mm=42,
    hvl_mmAl=0.417,
    gland_pct=50,
)

result = compute_mgd(
    esd_mGy=3.57,
    g=g,
    c=c,
    s=1.087,
    esd_includes_backscatter=True,
    bsf=1.12,
    n_exposures=1,
)

print(result["MGD_per_exposure_mGy"])
```

Expected output:

```text
0.8984951774999999
```

`compute_mgd()` returns a dictionary with these keys:

```text
Ka_i_mGy
g
c
s
g*c*s
MGD_per_exposure_mGy
MGD_total_mGy
```

## Validation

Before using the application for a measurement campaign or clinical QA:

1. Compare every coefficient table in the JSON with the cited source.
2. Confirm whether the measured input is incident air kerma without
   backscatter or a quantity that requires BSF correction.
3. Confirm the reference position and compression-paddle conditions required
   by the adopted protocol.
4. Confirm that compressed thickness, HVL, and glandularity are within the
   domains of both selected tables.
5. Verify that the manual `s` value matches the target/filter spectrum.
6. Recalculate several table-node cases, interpolation cases, and independent
   reference examples.
7. For DBT, apply a validated method that accounts for projection geometry and
   system-specific acquisition parameters.
8. Record the JSON version, table names, inputs, and software revision with
   every reported result.

The following technical checks were performed while preparing this README:

- the module imports without opening the GUI;
- all 77 cells in `dance_original_JRM_Table1` are readable;
- all 144 cells in `interpolated_JRM_Table3` are readable;
- all 200 tabulated combinations in `dance_original_JRM_Table2` are readable;
- backscatter conversion and dose multiplication were reproduced directly
  from `compute_mgd()`; and
- boundary clamping and the broader-HVL schema error were reproduced.

These checks confirm software behavior; they do not validate the transcribed
coefficient values or the clinical applicability of a calculation.

## Current limitations

- Inputs outside a coefficient table are silently clamped to its closest
  boundary.
- The broad-HVL `g` table in the supplied JSON is not compatible with the
  current loader.
- `s` is entered manually; target/filter selection and spectrum-factor lookup
  are not implemented.
- The number-of-exposures field assumes identical exposures and factors.
- DBT projection-angle `t` factors and complete-sweep `T` factors are not
  implemented.
- The application does not distinguish measured entrance surface air kerma,
  entrance surface dose, and incident air kerma beyond the backscatter option;
  the user must provide the correct quantity.
- The application does not propagate measurement or coefficient uncertainty.
- The application does not save an audit file or calculation history.
- The JSON schema is implicit and is not currently enforced by a JSON Schema
  validator.
- User inputs are checked for basic numeric validity, but physical and
  table-range validation is limited.

## Troubleshooting

### The application starts but no factors are available

Place `dance_factors.json` beside `mammo_agd_calculator.py`, start the program
from a directory containing the JSON, or select **Load JSON...**.

### `No module named tkinter`

Install the Tk package supplied by the operating system or use a Python build
that includes Tkinter. On Debian/Ubuntu:

```bash
sudo apt install python3-tk
```

### `g-table missing thickness_mm or hvl_mmAl`

The selected table does not use the schema required by
`compute_g_from_table()`. This occurs with the supplied
`dance1990_Table2_broader_HVL_range`. Select a compatible table or normalize
its units and value hierarchy.

### `Key for value ... not found`

The grid declares a coordinate for which the matching nested coefficient is
missing. Check that every value in each coordinate list has a corresponding
entry in `values` and that the nesting order matches the required schema.

### The result does not change beyond a table boundary

This is the current clamping behavior. Choose a validated table that covers the
input range or modify the program to reject out-of-range inputs explicitly.

### The **Open folder** button does nothing

The button relies on the platform's default file manager (`os.startfile` on
Windows, `open` on macOS, or `xdg-open` on Linux). The path remains visible in
the JSON file field if the system command is unavailable.

## References

1. Dance DR. *Monte Carlo calculation of conversion factors for the estimation
   of mean glandular breast dose.* Physics in Medicine & Biology. 1990;35(9):
   1211–1219. [doi:10.1088/0031-9155/35/9/002](https://doi.org/10.1088/0031-9155/35/9/002)
2. Dance DR, Skinner CL, Young KC, Beckett JR, Kotre CJ. *Additional factors
   for the estimation of mean glandular breast dose using the UK mammography
   dosimetry protocol.* Physics in Medicine & Biology. 2000;45(11):3225–3240.
   [doi:10.1088/0031-9155/45/11/308](https://doi.org/10.1088/0031-9155/45/11/308)
3. Nakamura N, Okafuji Y, Adachi S, Ichiura K. *Interpolation of Dance's
   coefficients for the estimation of average glandular dose in mammography.*
   Journal of Rural Medicine. 2019;14(1):103–109.
   [doi:10.2185/jrm.2994](https://doi.org/10.2185/jrm.2994)
4. Dance DR, Young KC, van Engen RE. *Estimation of mean glandular dose for
   breast tomosynthesis: factors for use with the UK, European and IAEA breast
   dosimetry protocols.* Physics in Medicine & Biology. 2011;56(2):453–471.
   [doi:10.1088/0031-9155/56/2/011](https://doi.org/10.1088/0031-9155/56/2/011)

## Repository notes

The project currently has no declared software license in the supplied files.
Add a `LICENSE` file before distributing or accepting contributions under a
specific open-source license.


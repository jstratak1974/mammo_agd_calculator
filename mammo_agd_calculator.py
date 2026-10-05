#!/usr/bin/env python3
"""
MGD/AGD Calculator (Dance) — Tkinter GUI (FIXED key lookup)
Works with the supplied / generated: dance_factors.json

Fix:
- Robust key matching for JSON keys like "0.30" vs "0.3", "45" vs "45.0"
"""

from __future__ import annotations
import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "MGD/AGD Calculator (Dance) — using dance_factors.json"
DEFAULT_JSON = "dance_factors.json"


# -------------------------
# Helpers
# -------------------------
def _sorted_unique(nums):
    return sorted(set(float(x) for x in nums))


def lerp(x0, x1, y0, y1, x):
    if x1 == x0:
        return float(y0)
    t = (x - x0) / (x1 - x0)
    return float(y0) + t * (float(y1) - float(y0))


def bracket(grid, x):
    if not grid:
        raise ValueError("Empty grid")
    if x <= grid[0]:
        return grid[0], grid[0]
    if x >= grid[-1]:
        return grid[-1], grid[-1]
    for i in range(1, len(grid)):
        if grid[i] >= x:
            return grid[i - 1], grid[i]
    return grid[-1], grid[-1]


def _candidate_keys(v: float, decimals: int = 2) -> list[str]:
    """
    Return common string forms that may exist as JSON keys.
    Example: 0.3 -> ["0.3", "0.30"]
             45.0 -> ["45.0", "45", "45.00"]
    """
    v = float(v)
    out = []
    out.append(str(v))                      # "0.3" or "45.0"
    if abs(v - round(v)) < 1e-9:
        out.append(str(int(round(v))))      # "45"
    out.append(f"{v:.{decimals}f}")         # "0.30" or "45.00"
    # also try trimming trailing zeros for safety
    out.append(f"{v:.{decimals}f}".rstrip("0").rstrip("."))  # "0.3", "45"
    # unique preserve order
    seen = set()
    uniq = []
    for k in out:
        if k not in seen:
            uniq.append(k)
            seen.add(k)
    return uniq


def _dict_get_by_numeric_key(d: dict, v: float, decimals: int = 2):
    """
    Find d[key] where key matches v in any common numeric string formatting.
    """
    for k in _candidate_keys(v, decimals=decimals):
        if k in d:
            return d[k], k
    raise KeyError(f"Key for value {v} not found. Tried: {_candidate_keys(v, decimals)}")


def bilinear_nested(grid_x, grid_y, nested_values, x, y, key_decimals_y=2):
    """
    Bilinear interpolation for values stored as:
        values[str(xi)][str(yi)] = v
    with robust key lookup.
    """
    x = float(x)
    y = float(y)
    x0, x1 = bracket(grid_x, x)
    y0, y1 = bracket(grid_y, y)

    def getv(xx, yy):
        row_dict, used_x = _dict_get_by_numeric_key(nested_values, xx, decimals=0)  # thickness keys are integers in JSON
        v, used_y = _dict_get_by_numeric_key(row_dict, yy, decimals=key_decimals_y) # HVL keys are "0.30"
        return float(v)

    v00 = getv(x0, y0)
    v10 = getv(x1, y0)
    v01 = getv(x0, y1)
    v11 = getv(x1, y1)

    if x0 == x1 and y0 == y1:
        return v00
    if x0 == x1:
        return lerp(y0, y1, v00, v01, y)
    if y0 == y1:
        return lerp(x0, x1, v00, v10, x)

    v0 = lerp(x0, x1, v00, v10, x)
    v1 = lerp(x0, x1, v01, v11, x)
    return lerp(y0, y1, v0, v1, y)


def linear_1d(grid_x, values_map, x, key_decimals=1):
    """
    Linear interpolation for values stored as values_map[str(xi)] = v,
    robust key lookup.
    """
    x = float(x)
    x0, x1 = bracket(grid_x, x)

    v0, _ = _dict_get_by_numeric_key(values_map, x0, decimals=key_decimals)
    v1, _ = _dict_get_by_numeric_key(values_map, x1, decimals=key_decimals)
    return lerp(x0, x1, float(v0), float(v1), x)


# -------------------------
# JSON accessors
# -------------------------
def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_g_tables(data: dict) -> list[str]:
    return sorted(list((data.get("coefficients", {}).get("g", {}) or {}).keys()))


def list_c_tables(data: dict) -> list[str]:
    return sorted(list((data.get("coefficients", {}).get("c", {}) or {}).keys()))


def get_g_table(data: dict, name: str) -> dict:
    g = data.get("coefficients", {}).get("g", {}) or {}
    if name not in g:
        raise KeyError(f"g-table '{name}' not found.")
    return g[name]


def get_c_table(data: dict, name: str) -> dict:
    c = data.get("coefficients", {}).get("c", {}) or {}
    if name not in c:
        raise KeyError(f"c-table '{name}' not found.")
    return c[name]


def compute_g_from_table(gtable: dict, thickness_mm: float, hvl_mmAl: float) -> float:
    tx = _sorted_unique(gtable.get("thickness_mm", []))
    hy = _sorted_unique(gtable.get("hvl_mmAl", []))
    vals = gtable.get("values", {})
    if not tx or not hy:
        raise ValueError("g-table missing thickness_mm or hvl_mmAl.")
    # HVL keys in JSON are typically 2 decimals ("0.30")
    return float(bilinear_nested(tx, hy, vals, thickness_mm, hvl_mmAl, key_decimals_y=2))


def compute_c_from_table(ctable: dict, thickness_mm: float, hvl_mmAl: float, gland_pct: float) -> float:
    """
    c-table in supplied JSON:
      values["0.30"]["20"]["50"] = 1.0
    We interpolate across glandularity (1D), thickness (1D), HVL (1D).
    """
    hgrid = _sorted_unique(ctable.get("hvl_mmAl", []))
    tgrid = _sorted_unique(ctable.get("thickness_mm", []))
    ggrid = _sorted_unique(ctable.get("glandularity_percent", []))
    vals = ctable.get("values", {})
    if not hgrid or not tgrid or not ggrid:
        raise ValueError("c-table missing hvl_mmAl / thickness_mm / glandularity_percent.")

    h0, h1 = bracket(hgrid, float(hvl_mmAl))
    t0, t1 = bracket(tgrid, float(thickness_mm))

    def c_at(hh, tt, gg):
        hv_slice, _ = _dict_get_by_numeric_key(vals, hh, decimals=2)          # "0.30"
        t_slice, _ = _dict_get_by_numeric_key(hv_slice, tt, decimals=0)      # "20"
        # glandularity keys include "0.1" and integers like "50"
        return float(linear_1d(ggrid, t_slice, gg, key_decimals=1))

    # HVL = h0
    c_h0_t0 = c_at(h0, t0, gland_pct)
    c_h0_t1 = c_at(h0, t1, gland_pct)
    c_h0 = lerp(t0, t1, c_h0_t0, c_h0_t1, float(thickness_mm))

    # HVL = h1
    c_h1_t0 = c_at(h1, t0, gland_pct)
    c_h1_t1 = c_at(h1, t1, gland_pct)
    c_h1 = lerp(t0, t1, c_h1_t0, c_h1_t1, float(thickness_mm))

    return float(lerp(h0, h1, c_h0, c_h1, float(hvl_mmAl)))


# -------------------------
# Core calculator
# -------------------------
def compute_mgd(esd_mGy: float, g: float, c: float, s: float, esd_includes_backscatter: bool, bsf: float, n_exposures: int) -> dict:
    esd_mGy = float(esd_mGy)
    n_exposures = int(n_exposures)
    if esd_mGy <= 0:
        raise ValueError("ESD/ESE must be > 0")
    if n_exposures < 1:
        raise ValueError("Number of exposures must be >= 1")

    if esd_includes_backscatter:
        if bsf <= 0:
            raise ValueError("BSF must be > 0")
        ka_i = esd_mGy / float(bsf)
    else:
        ka_i = esd_mGy

    mgd_per = ka_i * float(g) * float(c) * float(s)
    mgd_total = mgd_per * n_exposures
    return {
        "Ka_i_mGy": ka_i,
        "g": float(g),
        "c": float(c),
        "s": float(s),
        "g*c*s": float(g) * float(c) * float(s),
        "MGD_per_exposure_mGy": mgd_per,
        "MGD_total_mGy": mgd_total
    }


# -------------------------
# GUI
# -------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x620")

        self.data = None
        self.json_path = None

        self._build_ui()
        self._try_load_default()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Factors JSON:").pack(side="left")
        self.path_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.path_var, width=74).pack(side="left", padx=8)
        ttk.Button(top, text="Load JSON...", command=self.on_load_json).pack(side="left")
        ttk.Button(top, text="Open folder", command=self.on_open_folder).pack(side="left", padx=(6, 0))

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, **pad)

        left = ttk.LabelFrame(main, text="Inputs")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right = ttk.LabelFrame(main, text="Results")
        right.pack(side="left", fill="both", expand=True)

        self.esd_var = tk.StringVar(value="3.57")
        self.thick_var = tk.StringVar(value="42")
        self.hvl_var = tk.StringVar(value="0.517")
        self.gland_var = tk.StringVar(value="50")
        self.nexp_var = tk.StringVar(value="1")

        self.bs_var = tk.BooleanVar(value=True)
        self.bsf_var = tk.StringVar(value="1.12")

        self.s_mode_var = tk.StringVar(value="manual")
        self.s_manual_var = tk.StringVar(value="1.087")

        self.g_table_var = tk.StringVar(value="")
        self.c_table_var = tk.StringVar(value="")

        left.columnconfigure(1, weight=1)
        r = 0

        def row(label, widget):
            nonlocal r
            ttk.Label(left, text=label).grid(row=r, column=0, sticky="w", padx=10, pady=6)
            widget.grid(row=r, column=1, sticky="ew", padx=10, pady=6)
            r += 1

        row("ESD / ESE (mGy):", ttk.Entry(left, textvariable=self.esd_var))
        row("Thickness (mm):", ttk.Entry(left, textvariable=self.thick_var))
        row("HVL (mm Al):", ttk.Entry(left, textvariable=self.hvl_var))
        row("Glandularity (%):", ttk.Entry(left, textvariable=self.gland_var))
        row("Number of exposures (DBT projections):", ttk.Entry(left, textvariable=self.nexp_var))

        self.g_combo = ttk.Combobox(left, textvariable=self.g_table_var, state="readonly")
        row("g-table:", self.g_combo)

        self.c_combo = ttk.Combobox(left, textvariable=self.c_table_var, state="readonly")
        row("c-table:", self.c_combo)

        s_frame = ttk.Frame(left)
        ttk.Radiobutton(s_frame, text="s = 1.0", variable=self.s_mode_var, value="unity").pack(side="left")
        ttk.Radiobutton(s_frame, text="Manual s:", variable=self.s_mode_var, value="manual").pack(side="left", padx=(12, 4))
        ttk.Entry(s_frame, textvariable=self.s_manual_var, width=10).pack(side="left")
        row("Spectrum factor (s):", s_frame)

        bs_frame = ttk.Frame(left)
        ttk.Checkbutton(bs_frame, text="ESD includes backscatter (divide by BSF)", variable=self.bs_var).pack(side="left")
        ttk.Label(bs_frame, text="BSF:").pack(side="left", padx=(12, 4))
        ttk.Entry(bs_frame, textvariable=self.bsf_var, width=10).pack(side="left")
        row("Backscatter:", bs_frame)

        btns = ttk.Frame(left)
        ttk.Button(btns, text="Calculate", command=self.on_calc).pack(side="left")
        ttk.Button(btns, text="Example DBT (9×0.402 mGy)", command=self.on_example_dbt).pack(side="left", padx=8)
        row("", btns)

        self.notes = tk.Text(left, height=9, wrap="word")
        self.notes.grid(row=r, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        left.rowconfigure(r, weight=1)

        self.out = tk.Text(right, height=30, wrap="word")
        self.out.pack(fill="both", expand=True, padx=10, pady=10)
        self.out.configure(state="disabled")

        ttk.Button(right, text="Copy results", command=self.on_copy).pack(padx=10, pady=(0, 10), anchor="e")

    def _try_load_default(self):
        candidates = [
            os.path.join(os.getcwd(), DEFAULT_JSON),
        ]
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            candidates.append(os.path.join(base, DEFAULT_JSON))
        except Exception:
            pass

        for p in candidates:
            if os.path.exists(p):
                self._load_json(p)
                return

    def _load_json(self, path: str):
        data = load_json(path)
        self.data = data
        self.json_path = path
        self.path_var.set(os.path.abspath(path))

        g_tables = list_g_tables(data)
        c_tables = list_c_tables(data)
        self.g_combo["values"] = g_tables
        self.c_combo["values"] = c_tables

        if g_tables:
            pref = "interpolated_JRM_Table3"
            self.g_table_var.set(pref if pref in g_tables else g_tables[0])
        if c_tables:
            self.c_table_var.set(c_tables[0])

        notes = [
            "Loaded JSON successfully.",
            "",
            "MGD/AGD formula: MGD = Ka,i * g * c * s",
            "• If your ESE/ESAK includes backscatter, tick the box and set BSF (typ. 1.10–1.15).",
            "• g is interpolated over thickness & HVL from the selected g-table.",
            "• c is interpolated over glandularity, thickness and HVL from the selected c-table.",
            "• s is set manually here (e.g., 1.087 for Rh/Ag) or s=1.0.",
            "",
            "This version fixes JSON key-format mismatches (e.g., '0.30' vs '0.3')."
        ]
        self.notes.configure(state="normal")
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", "\n".join(notes))
        self.notes.configure(state="disabled")

    def on_load_json(self):
        path = filedialog.askopenfilename(
            title="Select dance_factors.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self._load_json(path)
        except Exception as e:
            messagebox.showerror("Load error", str(e))

    def on_open_folder(self):
        if not self.json_path:
            messagebox.showinfo("Info", "No JSON loaded yet.")
            return
        folder = os.path.dirname(os.path.abspath(self.json_path))
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception:
            messagebox.showinfo("Folder", folder)

    def on_example_dbt(self):
        self.esd_var.set("0.402")
        self.nexp_var.set("9")
        self.thick_var.set("50")
        self.hvl_var.set("0.517")
        self.gland_var.set("50")
        self.s_mode_var.set("manual")
        self.s_manual_var.set("1.087")
        self.bs_var.set(True)
        self.bsf_var.set("1.12")

    def on_calc(self):
        if not self.data:
            messagebox.showerror("Error", "Load a factors JSON first.")
            return
        try:
            esd = float(self.esd_var.get())
            thick = float(self.thick_var.get())
            hvl = float(self.hvl_var.get())
            gland = float(self.gland_var.get())
            nexp = int(float(self.nexp_var.get()))

            g_name = self.g_table_var.get().strip()
            c_name = self.c_table_var.get().strip()
            if not g_name or not c_name:
                raise ValueError("Select both a g-table and a c-table.")

            gtable = get_g_table(self.data, g_name)
            ctable = get_c_table(self.data, c_name)

            g_val = compute_g_from_table(gtable, thick, hvl)
            c_val = compute_c_from_table(ctable, thick, hvl, gland)

            s_val = 1.0 if self.s_mode_var.get() == "unity" else float(self.s_manual_var.get())
            esd_incl_bs = bool(self.bs_var.get())
            bsf = float(self.bsf_var.get())

            out = compute_mgd(esd, g_val, c_val, s_val, esd_incl_bs, bsf, nexp)

            lines = []
            lines.append("Inputs")
            lines.append(f"  ESD/ESE: {esd:.6f} mGy")
            lines.append(f"  Thickness: {thick:.2f} mm")
            lines.append(f"  HVL: {hvl:.4f} mm Al")
            lines.append(f"  Glandularity: {gland:.1f} %")
            lines.append(f"  # exposures: {nexp}")
            lines.append(f"  g-table: {g_name}")
            lines.append(f"  c-table: {c_name}")
            lines.append(f"  s-factor: {s_val:.6f}")
            lines.append(f"  ESD includes backscatter: {'Yes' if esd_incl_bs else 'No'}")
            if esd_incl_bs:
                lines.append(f"  BSF: {bsf:.3f}")
            lines.append("")
            lines.append("Derived")
            lines.append(f"  Ka,i: {out['Ka_i_mGy']:.6f} mGy")
            lines.append(f"  g: {out['g']:.6f}")
            lines.append(f"  c: {out['c']:.6f}")
            lines.append(f"  s: {out['s']:.6f}")
            lines.append(f"  g*c*s: {out['g*c*s']:.6f}")
            lines.append("")
            lines.append("Results")
            lines.append(f"  MGD/AGD per exposure: {out['MGD_per_exposure_mGy']:.6f} mGy")
            lines.append(f"  MGD/AGD total (x{nexp}): {out['MGD_total_mGy']:.6f} mGy")

            self._set_output("\n".join(lines))

        except Exception as e:
            messagebox.showerror("Calculation error", str(e))

    def _set_output(self, txt: str):
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", txt)
        self.out.configure(state="disabled")

    def on_copy(self):
        try:
            s = self.out.get("1.0", "end").strip()
            self.clipboard_clear()
            self.clipboard_append(s)
            self.update()
            messagebox.showinfo("Copied", "Results copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

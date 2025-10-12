# Assignment 1 – Project README
## Overview

This project implements a modular workflow for 46750 – Optimization in Modern Power Systems (Assignment 1). It includes:

- Data loading for the assignment’s questions and scenarios
- A configurable Gurobi-based optimization model
- A runner to execute multiple scenarios
- Plotting utilities for scenario comparisons, dual variables, tariffs/prices overlays, and a battery capacity sensitivity
- Utilities for scenario selection and reporting

The code is organized for clarity and extension, with explicit hooks for varying tariffs or fixing day-ahead prices, exporting duals, and saving figures per question.

## Installation

Use either pip or conda. On Windows PowerShell, the following commands apply.

### Option A: pip (virtualenv)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Option B: conda

```powershell
conda env create -f environment.yaml
conda activate gurobi-opt
```

Ensure your Gurobi license is installed and available to Python (see Gurobi docs if needed).

## Getting Started

- Main entry point: `src/main.py`
- Default configuration is set inside `main()` (question, scenarios, flags)

Run from the repository root:

```powershell
python .\src\main.py
```

Key runtime flags (set in `main.py`):
- `question`: 'question_1a' | 'question_1b' | 'question_1c' | 'question_2b'
- `scenarios`: "All" or a list of scenario names (case-insensitive)
- `vary_tariff`: True/False — randomly scales import/export tariffs per hour
- `fixed_da`: None or a float — overrides DA price with a constant
- `show_plots` / `save_plots`: control visualization display and saving
- `num_hours`: hours simulated (default 24)
- `print_size`: "small" or "large" summary output

## Project Structure

- `src/main.py` — Entry point; configures question and scenarios, runs simulations, prints results, optionally generates dual plots.
- `src/runner/runner.py` — Orchestrates simulations across selected scenarios and triggers plotting.
- `src/opt_model/opt_model.py` — Implements data-driven model classes (Consumer, DER, Grid) and the Gurobi optimization model (EnergySystemModel).
- `src/data_ops/data_loader.py` — Loads all JSON/CSV inputs per question via `utils.load_dataset()`.
- `src/data_ops/data_visualizer.py` — Plotting utilities: scenario comparisons with tariffs/DA price overlays, DA price, battery capacity vs price, and duals-from-text.
- `src/utils/utils.py` — Scenario discovery/selection, printing/reporting, duals export, and helpers.
- `data/` — Input data grouped per question (e.g., `question_1a`, `question_1b`, ...).
- `txt/` — Exported dual values per scenario.
- `img/` — Saved plots, grouped per question.

## Input Data

Per question folder under `data/<question>/`:
- `consumer_params.json` — Consumer and load preference parameters
- `appliance_params.json` — Max load, DER, storage parameters (including battery price coeff for 2b)
- `DER_production.json` — Hourly production ratios for PV/DER
- `bus_params.json` — Import/export tariffs, energy price, grid limits
- Usage preferences file (`usage_preference.json` or `usage_preferences.json`) — reference profile, min/max equivalent energy, storage SoC targets

Scenario names are defined in `data/scenarios_<question>/_scenario_names.json` and map scenario names to the scaling JSON file paths used by the model (selected via `utils.get_all_scenarios` + `utils.select_scenarios`).

## How the Code Works

### main.py
- Sets the `question`, loads available scenarios, selects which to run, and configures flags (`vary_tariff`, `fixed_da`, `show_plots`, `save_plots`, `num_hours`, `print_size`).
- Constructs a `Runner` with these settings and calls `run_all_simulations`.
- Optionally iterates duals text files under `txt/<question>` and plots them (code provided; currently gated by early `return`).

### runner/runner.py
- `Runner.run_all_simulations(...)` loops over selected scenarios:
  - Calls `run_single_simulation(...)` to build inputs and solve once
  - Converts flat results (e.g., `p_import_0`) to lists (e.g., `p_import: [...]`) via `_results_flat_to_lists`
  - Aggregates results and profit per scenario
  - Adds each scenario to `DataVisualizer` and prints a summary line
- If `show_plots` or `save_plots`:
  - Calls `DataVisualizer.plot_comparison(...)` on selected keys
  - For `question_2b`, calls `plot_battery_capacity_vs_price(...)`

### data_ops/data_loader.py
- `DataLoader(question, input_path)` loads all files under `data/<question>/` using `utils.load_dataset()`.
- Loaded files become attributes: e.g., `self.DER_production`, `self.bus_params`, `self.appliance_params`, `self.usage_preference`.

### opt_model/opt_model.py
Implements: `Consumer`, `DER`, `Grid`, and `EnergySystemModel`.

- Consumer
  - Reads usage preferences (min/max equivalent energy, reference profile ratios)
  - Storage parameters (capacity, efficiencies, charging/discharging ratios, initial/final/min SoC)
  - Battery price coefficient for 2b sensitivity (`battery_price_coeff`)
  - Applies scenario scaling factors (e.g., `load_scale`, `reference_profile_scale`, etc.)

- DER
  - PV hourly profile from `DER_production.hourly_profile_ratio`, scaled
  - Max PV capacity from `appliance_params["DER"][0]["max_power_kW"]`

- Grid
  - Tariffs: `import_tariff_DKK/kWh`, `export_tariff_DKK/kWh`
  - Day-ahead price: `energy_price_DKK_per_kWh`
  - Grid limits: `max_import_kW`, `max_export_kW`

- EnergySystemModel.build_and_solve_standardized(...)
  - Variables per hour: `p_import, p_export, p_load, p_pv_actual, y, z, p_bat_charge, p_bat_discharge, soc` and `p_bat_cap` (fixed unless question=2b)
  - Objective:
    - 1a: Maximize profit with small penalties to discourage simultaneous import/export and charge/discharge
    - 1b/1c: Maximize (profit − discomfort_cost × squared deviation from reference profile − penalties)
    - 2b: As above plus linear penalty on `p_bat_cap` via `battery_price_coeff`
  - Constraints:
    - Total load bounds (min/max equivalent energy)
    - Hourly limits (import/export, PV, load, SOC ≤ capacity)
    - Exclusivity for battery charge/discharge using a continuous selector `z_t` (Big-M flavor adapted for 2b)
    - Hourly energy balance: import + PV + discharge = load + export + charge
    - SOC dynamics with efficiencies; initial and final SOC targets
  - Varying tariffs and DA prices:
    - `vary_tariff=True` randomly scales import/export tariffs per hour
    - `fixed_da=<float>` overrides DA price to a constant
  - Outputs:
    - Timeseries for all variables and derived `p_curtailment = P_pv − p_pv_actual`
    - `soc_normal` (normalized SOC by capacity)
    - `phi_imp`, `phi_exp`, `da_price` for plotting
    - `duals` per constraint
    - `actual_profit` (true export revenue minus import cost). For 1a equals the objective value

### utils/utils.py
- `print_results(...)` and `print_results_small(...)` print objective value and, when available, `actual_profit`, plus summaries
- `print_all_scenarios(...)` prints each and exports duals to `txt/<question>/duals_<scenario>[suffixes].txt`
- `get_all_scenarios(question)` reads `data/scenarios_<question>/_scenario_names.json`
- `select_scenarios(d, keys)` returns selected scenarios (case-insensitive), or all
- `get_unique_filename(...)` currently returns the provided path as-is (no uniquifying)

### data_ops/data_visualizer.py
- `plot_comparison(...)`
  - For each key (e.g., `p_import`, `p_export`, `p_load`, `p_pv_actual`, `p_bat_charge`, `p_bat_discharge`, `soc_normal`, `p_curtailment`):
    - Plots all scenarios on the left y-axis (Power [kWh])
    - Overlays day-ahead price and tariffs on a twin right y-axis (DKK/kWh)
      - DA price shown as semi-transparent bars
      - `phi_imp` and `phi_exp` shown as semi-transparent bars (only if non-constant)
    - Optionally overlays `reference_profile` when applicable
    - Saves to `img/<question>/...`, appending `_fixedDA<val>` and/or `_varyTariff` suffixes
- `plot_battery_capacity_vs_price(...)` (used for 2b)
  - Plots optimal `p_bat_cap` vs `battery_price_coeff` across scenarios
  - Adds suffixes to filenames based on DA/tariff settings
- `plot_da_price()`
  - Standalone DA price plot from `data/question_1a/bus_params.json` → `img/other/da_price.png`
- `plot_duals_from_txt(...)`
  - Accepts a file or a directory (auto-selects the newest `duals_*.txt`, optional scenario hint)
  - Parses time-indexed constraints like `name_5: value` into lines over time
  - Prints scalar duals
  - By default, ignores any constraints containing `excl`, and suppresses high-volume series `balance` and `soc_update` unless you explicitly include them via `include=[...]`
  - Saves under `img/duals[/<question>]`

## Outputs

- Console prints include objective value and, when computed, `actual_profit`
- Duals exported as text: `txt/<question>/duals_<scenario>[suffixes].txt`
- Plots saved under `img/<question>/` for comparisons and `img/duals/` for duals; DA price under `img/other/`

## Configuration & Scenarios

- Define scenario mappings in `data/scenarios_<question>/_scenario_names.json`
  - Keys are scenario names; values are paths to scaling files consumed by the model
- In `main.py`, set `scenarios = "All"` to run all, or pass a list of names (case-insensitive)
- Useful flags in `main.py`:
  - `vary_tariff=True` for randomized hourly tariff variation
  - `fixed_da=2.0` to set a constant DA price
  - `num_hours=24` to adjust the horizon

## Tips & Troubleshooting

- Gurobi license: Ensure your Gurobi license is properly installed; otherwise the model won’t solve
- Missing inputs: Verify question folder files exist (e.g., `usage_preference*.json` naming differences between questions)
- Duals plotting: If you don’t see time-series lines, check the filter — by default `balance`, `soc_update`, and any `excl`-related constraints are not plotted. Use `include=[...]` to force them in
- File paths: The project assumes relative paths from the repo root

## License

See `LICENSE` in the repository.


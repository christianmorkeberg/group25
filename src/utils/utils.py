import os

# Utility: get a unique filename by appending a number if needed
def get_unique_filename(base_name):
    return base_name
    """Return a unique filename by appending a number if needed."""
    name, ext = os.path.splitext(base_name)
    i = 1
    candidate = base_name
    while os.path.exists(candidate):
        candidate = f"{name}_{i}{ext}"
        i += 1
    return candidate

# Print results and profit for a single scenario
def print_results(results, profit, scenario_name=None):
    if "actual_profit" in results:
        print(f"Actual Profit: {results['actual_profit']:.2f} DKK")
    if results is None:
        print(f"No results available for scenario '{scenario_name}'.")
        return
    title = f"=== OPTIMIZATION RESULTS"
    if scenario_name:
        title += f" ({scenario_name})"
    title += " ==="
    print(f"\n{title}")
    for key, values in results.items():
        if key not in ["duals", "reference_profile", "true_cost", "discomfort"]:
            print(f"{key}: {values}")
    # Print true cost/discomfort if present
    if "true_cost" in results:
        print(f"True Cost (import/export only): {results['true_cost']:.2f} DKK")
    if "discomfort" in results:
        print(f"Discomfort term: {results['discomfort']:.2f}")
    if profit is not None:
        print(f"Objective Value: {profit:.2f}")
        if "true_cost" in results or "discomfort" in results:
            print("(Objective value is a weighted sum of cost and discomfort, not pure profit)")
        else:
            print("(Objective value is total profit)")
    else:
        print("Model did not find an optimal solution.")
    print("============================\n")

# Print results and profit for a single scenario (small version)
def print_results_small(results, profit, scenario_name=None):
    if "actual_profit" in results:
        print(f"Actual Profit: {results['actual_profit']:.2f} DKK")
    if results is None:
        print(f"No results available for scenario '{scenario_name}'.")
        return
    title = f"=== OPTIMIZATION SUMMARY"
    if scenario_name:
        title += f" ({scenario_name})"
    title += " ==="
    print(f"\n{title}")
    # Only print key summary values
    for key in ["p_import", "p_export", "p_load", "curtailment"]:
        if key in results:
            print(f"{key} (sum): {sum(results[key]):.2f}")
    if profit is not None:
        print(f"Objective Value: {profit:.2f}")
        if "true_cost" in results or "discomfort" in results:
            print("(Objective value is a weighted sum of cost and discomfort, not pure profit)")
        else:
            print("(Objective value is total profit)")
    else:
        print("Model did not find an optimal solution.")
    print("============================\n")

# Print results and profit for all scenarios
def print_all_scenarios(scenario_results, mode="large",question=None,vary_tariff=False,fixed_da=None):
    print("\n=== Scenario Results ===")
    for name, result in scenario_results.items():
        print(f"\nScenario: {name}")
        if mode == "small":
            print_results_small(result['results'], result['profit'], name)
        else:
            print_results(result['results'], result['profit'], name)
        # Print duals if available
        duals = result['results'].get('duals', None)
        if duals:
            # Export duals to a .txt file per scenario
            filename = f"txt/{question}/duals_{name.replace(' ', '_')}.txt"
            if vary_tariff:
                # add suffix to filename
                filename = filename.replace(".txt", "_varytariff.txt")
            if fixed_da is not None:
                filename = filename.replace(".txt", f"_fixedDA{fixed_da}.txt")
            with open(filename, 'w') as f:
                f.write(f"Dual values (shadow prices) for scenario: {name}\n")
                for cname, dual in duals.items():
                    f.write(f"{cname}: {dual:.6f}\n")
            print(f"  Dual values exported to {filename}")
"placeholder for various utils functions"

import json
import csv
import pandas as pd
from pathlib import Path

# example function to load data from a specified directory
def load_dataset(question_name):
    base_path = Path("data") / question_name
    result = {}
 
    for file_path in base_path.glob("*"):
        stem = file_path.stem
        suffix = file_path.suffix.lower()
 
        try:
            if suffix == '.json':
                with open(file_path, 'r') as f:
                    result[stem] = json.load(f)
            elif suffix == '.csv':
                with open(file_path, 'r') as f:
                    result[stem] = list(csv.DictReader(f))
            else:
                with open(file_path, 'r') as f:
                    result[stem] = f.read()
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
 
    return result

# example function to save model results in a specified directory
def save_model_results():
    """Placeholder for save_model_results function."""
    pass

# example function to plot data from a specified directory
def plot_data():
    """Placeholder for plot_data function."""
    pass

def select_scenarios(d, keys):
    if keys == "All" or keys == ["All"]or keys == ["all"]:
        return d
    if isinstance(keys, str):
        keys = [keys]
    # Create a mapping from lowercase keys to original keys
    lower_map = {k.lower(): k for k in d}
    selected = {}
    for key in keys:
        k_lower = key.lower()
        if k_lower in lower_map:
            selected[lower_map[k_lower]] = d[lower_map[k_lower]]
    return selected

def get_all_scenarios(question):
    """Load and return all scenario names from the _scenario_names.json file."""
    try:
        with open(f'data/scenarios_{question}/_scenario_names.json', 'r') as f:
            scenarios = json.load(f)
        return scenarios
    except Exception as e:
        print(f"Error loading scenario names: {e}")
        return {}
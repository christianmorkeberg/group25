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
    if results is None:
        print(f"No results available for scenario '{scenario_name}'.")
        return
    title = f"=== OPTIMIZATION RESULTS"
    if scenario_name:
        title += f" ({scenario_name})"
    title += " ==="
    print(f"\n{title}")
    for key, values in results.items():
        print(f"{key}: {values}")
    if profit is not None:
        print(f"Total Profit: {profit:.2f} DKK")
    else:
        print("Model did not find an optimal solution.")
    print("============================\n")

# Print results and profit for a single scenario (small version)
def print_results_small(results, profit, scenario_name=None):
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
        print(f"Total Profit: {profit:.2f} DKK")
    else:
        print("Model did not find an optimal solution.")
    print("============================\n")

# Print results and profit for all scenarios
def print_all_scenarios(scenario_results, mode="large"):
    print("\n=== Scenario Results ===")
    for name, result in scenario_results.items():
        print(f"\nScenario: {name}")
        if mode == "small":
            print_results_small(result['results'], result['profit'], name)
        else:
            print_results(result['results'], result['profit'], name)
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
    if keys == "All":
        return d
    if isinstance(keys, str):
        keys = [keys]
    return {k: d[k] for k in keys if k in d}

def get_all_scenarios(question):
    """Load and return all scenario names from the _scenario_names.json file."""
    try:
        with open(f'data/scenarios_{question}/_scenario_names.json', 'r') as f:
            scenarios = json.load(f)
        return scenarios
    except Exception as e:
        print(f"Error loading scenario names: {e}")
        return {}
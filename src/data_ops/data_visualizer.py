import matplotlib.pyplot as plt
import os

class DataVisualizer:
    """
    Modular class for visualizing optimization results and comparing scenarios.
    """
    def __init__(self, question=None):
        self.scenarios = {}
        self.question = question

    def add_scenario(self, name, results, label=None):
        """
        Add a scenario's results for later comparison/plotting.
        name: unique identifier for the scenario (should be a simple string, e.g. 'base', 'high_pv')
        results: dict of optimization results (e.g., from EnergySystemModel)
        label: optional label for legend
        """
        # Always sanitize the scenario name for internal use
        import os
        key = os.path.basename(name)
        key = os.path.splitext(key)[0]
        key = key.replace(" ", "_")
        self.scenarios[key] = {
            'results': results,
            'label': label if label else key
        }

    def plot_scenario(self, name, keys=None):
        """
        Plot the results for a single scenario.
        keys: list of result keys to plot (e.g., ['p_import', 'p_export'])
        """
        if name not in self.scenarios:
            print(f"Scenario '{name}' not found.")
            return
        results = self.scenarios[name]['results']
        if keys is None:
            keys = [k for k in results.keys() if isinstance(results[k], list)]
        plt.figure(figsize=(10, 6))
        for k in keys:
            plt.plot(results[k], label=k)
        plt.title(f"Scenario: {self.scenarios[name]['label']}")
        plt.xlabel("Hour")
        plt.ylabel("Energy (kWh)")
        plt.legend()
        plt.grid(True)
        plt.show()

    def plot_comparison(self, keys=None, show_plots=False, save_plots=False):
        """
        For each key, plot all scenarios together in one file (cross-scenario comparison for each physical quantity).
        keys: list of result keys to plot (e.g., ['p_import', 'p_export'])
        """
        if not self.scenarios:
            print("No scenarios to compare.")
            return
        if keys is None:
            # Use keys from the first scenario
            first = next(iter(self.scenarios.values()))['results']
            keys = [k for k in first.keys() if isinstance(first[k], list)]
        import itertools
        line_styles = ['-', '--', '-.', ':']
        markers = ['o', 's', 'D', '^', 'v', '>', '<', 'p', '*', 'h', 'x']
        color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
        # Check if reference_profile exists and is not all None in any scenario
        ref_profile_to_plot = None
        for scenario in self.scenarios.values():
            ref_profile = scenario['results'].get('reference_profile', None)
            if isinstance(ref_profile, list) and any(v is not None for v in ref_profile):
                ref_profile_to_plot = ref_profile
                break
        for k in keys:
            # Check if all values for this key are None in all scenarios
            all_none = True
            for scenario in self.scenarios.values():
                values = scenario['results'].get(k, None)
                if isinstance(values, list) and any(v is not None for v in values):
                    all_none = False
                    break
            if all_none:
                print(f"Skipping key '{k}' in plot_comparison: all values are None.")
                continue
            plt.figure(figsize=(10, 6))
            style_cycle = itertools.cycle(line_styles)
            marker_cycle = itertools.cycle(markers)
            color_cycle_iter = itertools.cycle(color_cycle)
            for scenario_idx, (scenario_name, scenario) in enumerate(self.scenarios.items()):
                style = next(style_cycle)
                marker = next(marker_cycle)
                color = next(color_cycle_iter)
                plt.plot(
                    scenario['results'][k],
                    label=scenario['label'],
                    linestyle=style,
                    marker=marker,
                    color=color,
                    markersize=5,
                    linewidth=2
                )
            # Plot reference_profile if available and not all None, and if key is not 'soc'
            if ref_profile_to_plot is not None and k != 'soc':
                plt.plot(ref_profile_to_plot, label='reference_profile', linestyle='--', color='black', linewidth=2)
            plt.title(f"Comparison: {k}")
            plt.xlabel("Hour")
            plt.ylabel("Power (kWh)")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            if save_plots:
                from utils.utils import get_unique_filename
                img_dir = os.path.join("img", self.question if self.question else "")
                if not os.path.exists(img_dir):
                    os.makedirs(img_dir)
                scenario_names = "_".join([scenario['label'] for scenario in self.scenarios.values() if scenario.get('label')])
                if not scenario_names:
                    scenario_names = "all_scenarios"
                # Sanitize scenario_names for filesystem
                scenario_names = scenario_names.replace(" ", "_").replace("/", "-").replace("\\", "-")
                filename = get_unique_filename(os.path.join(img_dir, f"{k}_comparison_{scenario_names}.png"))
                if filename:
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    plt.savefig(filename)
                    print(f"Plot saved: {filename}")
                else:
                    print(f"Warning: Could not generate filename for plot {k}. Plot not saved.")
            if show_plots:
                plt.show()
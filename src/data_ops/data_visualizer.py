import matplotlib.pyplot as plt
import os

class DataVisualizer:
    def plot_battery_capacity_vs_price(self, price_coeff_key="battery_price_coeff", cap_key="p_bat_cap", show_plot=True, save_plot=False):
        """
        Plots battery capacity as a function of battery price coefficient across scenarios.
        price_coeff_key: key in results or scenario label for battery price coefficient
        cap_key: key in results for battery capacity (default: 'p_bat_cap')
        """
        if not self.scenarios:
            print("No scenarios to plot.")
            return
        x_vals = []
        y_vals = []
        labels = []
        for scenario_name, scenario in self.scenarios.items():
            # Try to get price coefficient from results, else from label or scenario name
            price_coeff = scenario['results'].get(price_coeff_key)
            if price_coeff is None:
                # Try to parse from label or scenario name (assume format like 'price_0.1')
                import re
                match = re.search(r"([\d.]+)", scenario['label'])
                if match:
                    price_coeff = float(match.group(1))
                else:
                    price_coeff = scenario_name
            cap = scenario['results'].get(cap_key)
            if cap is not None:
                x_vals.append(price_coeff)
                y_vals.append(cap)
                labels.append(scenario['label'])
        if not x_vals:
            print(f"No data found for keys '{price_coeff_key}' and '{cap_key}'.")
            return
        # Convert all x and y values to floats (handle Gurobi Var objects)
        def to_float(val):
            if hasattr(val, 'X'):
                return float(val.X)
            try:
                return float(val)
            except Exception:
                return None
        x_vals_f = [to_float(x) for x in x_vals]
        y_vals_f = [to_float(y) for y in y_vals]
        # Remove any pairs where conversion failed
        filtered = [(x, y, label) for x, y, label in zip(x_vals_f, y_vals_f, labels) if x is not None and y is not None]
        if not filtered:
            print("No valid numeric data to plot.")
            return
        x_vals_f, y_vals_f, labels = zip(*filtered)
        # Sort by x for nice plotting
        xy = sorted(zip(x_vals_f, y_vals_f, labels), key=lambda tup: tup[0])
        x_vals_f, y_vals_f, labels = zip(*xy)
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 5))
        plt.plot(x_vals_f, y_vals_f, marker="o", linestyle="-", color="tab:blue")
        plt.xlabel("Battery Price Coefficient")
        plt.ylabel("Optimal Battery Capacity (kWh)")
        plt.title("Battery Capacity vs. Battery Price Coefficient")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        if save_plot:
            img_dir = os.path.join("img", self.question if self.question else "")
            os.makedirs(img_dir, exist_ok=True)
            filename = os.path.join(img_dir, "battery_capacity_vs_price.png")
            plt.savefig(filename)
            print(f"Plot saved: {filename}")
        if show_plot:
            plt.show()
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

    # def plot_scenario(self, name, keys=None):
    #     """
    #     Plot the results for a single scenario.
    #     keys: list of result keys to plot (e.g., ['p_import', 'p_export'])
    #     """
    #     if name not in self.scenarios:
    #         print(f"Scenario '{name}' not found.")
    #         return
    #     results = self.scenarios[name]['results']
    #     if keys is None:
    #         keys = [k for k in results.keys() if isinstance(results[k], list)]
    #     plt.figure(figsize=(10, 6))
    #     for k in keys:
    #         plt.plot(results[k], label=k)
    #     plt.title(f"Scenario: {self.scenarios[name]['label']}")
    #     plt.xlabel("Hour")
    #     plt.ylabel("Energy (kWh)")
    #     plt.legend()
    #     plt.grid(True)
    #     plt.show()

    def plot_comparison(self, keys=None, show_plots=False, save_plots=False, fixed_da=None, vary_tariff=False):
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

            # If present and varying, plot phi_imp/phi_exp as background bars and da_price as a line on a twin y-axis
            # Determine length from the first scenario's series for this key
            first_results = next(iter(self.scenarios.values()))['results']
            series_example = first_results.get(k)
            n_points = len(series_example) if isinstance(series_example, list) else None
            ax = plt.gca()
            ax.set_ylabel("Power [kWh]")
            ax2 = None
            if n_points is not None:
                phi_imp = first_results.get('phi_imp')
                phi_exp = first_results.get('phi_exp')
                da_price = first_results.get('da_price') or first_results.get('energy_price') or first_results.get('price')
                # Build secondary axis and always plot DA price if available
                ax2 = ax.twinx()
                ax2.set_ylabel("Tariff / Price [DKK/kWh]")
                if isinstance(da_price, list) and len(da_price) > 0:
                    x_idx_price = list(range(len(da_price)))
                    #ax2.plot(x_idx_price, da_price, color='tab:purple', linestyle='--', linewidth=2, label='DA price (right axis)', zorder=2)
                    ax2.bar(x_idx_price, da_price, color='tab:purple', width=0.25, alpha = 0.4,label='DA price (right axis)', zorder=1)
                # Tariffs as bars when available and non-constant
                def non_constant_list(lst):
                    return isinstance(lst, list) and len(lst) > 0 and any(v != lst[0] for v in lst[1:])
                plot_imp = non_constant_list(phi_imp)
                plot_exp = non_constant_list(phi_exp)
                if plot_imp or plot_exp:
                    # Choose bar index length based on available series
                    bar_len = len(phi_imp) if plot_imp else len(phi_exp)
                    x_idx_bars = list(range(bar_len))
                    width = 0.25
                    if plot_imp:
                        ax2.bar([i - 2 *width for i in x_idx_bars], phi_imp, width=width, alpha=0.2, color='tab:red', label='phi_imp (right axis)', zorder=1)
                    if plot_exp:
                        ax2.bar([i - width for i in x_idx_bars], phi_exp, width=width, alpha=0.2, color='tab:green', label='phi_exp (right axis)', zorder=1)
                    
            for scenario_idx, (scenario_name, scenario) in enumerate(self.scenarios.items()):
                style = next(style_cycle)
                marker = next(marker_cycle)
                color = next(color_cycle_iter)
                ax.plot(
                    scenario['results'][k],
                    label=scenario['label'],
                    linestyle=style,
                    marker=marker,
                    color=color,
                    markersize=5,
                    linewidth=2
                )
            # Plot reference_profile if available and not all None, and if key is not 'soc'
            if ref_profile_to_plot is not None and k != 'soc_normal':
                ax.plot(ref_profile_to_plot, label='reference_profile', linestyle='--', color='black', linewidth=2)
            ax.set_title(f"Comparison: {k}")
            ax.set_xlabel("Hour")
            #plt.ylabel("Power [kWh]")
            # Combined legend if tariffs were plotted
            if 'ax2' in locals() and ax2 is not None:
                h1, l1 = ax.get_legend_handles_labels()
                h2, l2 = ax2.get_legend_handles_labels()
                ax.legend(h1 + h2, l1 + l2, loc='best')
            else:
                    ax.legend(title='Left y-axis: Power [kWh]')
            ax.grid(True)
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
                    # if fixed_da add suffix
                    if fixed_da and isinstance(fixed_da,(int,float)):
                        filename = filename.replace(".png", f"_fixedDA{fixed_da}.png")
                    if vary_tariff:
                        filename = filename.replace(".png", f"_varyTariff.png")
                        
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    plt.savefig(filename)
                    print(f"Plot saved: {filename}")
                else:
                    print(f"Warning: Could not generate filename for plot {k}. Plot not saved.")
            if show_plots:
                plt.show()

def plot_da_price():

    """
    Plots the DA price for a given scenario and saves it in the appropriate img/question folder.
    """
    import json
    from pathlib import Path
    import os 
    import matplotlib.pyplot as plt
    path = Path('data/question_1a/bus_params.json')
    r = json.loads(path.read_text())
    DA_prices = r[0].get("energy_price_DKK_per_kWh", None)
    img_dir = os.path.join("img/other")
    os.makedirs(img_dir, exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(DA_prices, label="DA Price", color="tab:blue", marker="o")
    plt.xlabel("Hour")
    plt.ylabel("DA Price [DKK/kWh]")
    plt.title(f"Day-Ahead Price")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    filename = os.path.join(img_dir, f"da_price.png")
    plt.savefig(filename)
    plt.close()
    print(f"DA price plot saved to {filename}")


def plot_duals_from_txt(dual_file_path, include=None, exclude=None, show_plot=True, save_plot=False, out_dir="img/duals", scenario_hint=None):
    """
    Plot dual values for a single scenario from a duals_*.txt file.

    Params:
    - dual_file_path: path to the exported duals text file.
    - include: optional list of base constraint names (e.g., ['balance','soc_update']) to plot; if None, plot all series.
    - exclude: optional list of base names to skip.
    - show_plot/save_plot: control display and saving.
    - out_dir: directory to save the figure when save_plot=True.
    - scenario_hint: optional string to help choose the right file when dual_file_path is a folder

    The function detects time-indexed constraints by names ending with _<int> (e.g., balance_5) and
    plots each base name as a line over time. Non-indexed (scalar) duals are printed to console.
    """
    import re
    import os
    import matplotlib.pyplot as plt

    if not os.path.exists(dual_file_path):
        print(f"Dual file not found: {dual_file_path}")
        return
    # If a directory was provided, try to auto-pick a duals_*.txt file inside
    if os.path.isdir(dual_file_path):
        dir_path = dual_file_path
        try:
            files = [f for f in os.listdir(dir_path) if f.lower().endswith('.txt')]
        except Exception as e:
            print(f"Failed to list directory '{dir_path}': {e}")
            return
        # Prefer files starting with 'duals_'
        dual_candidates = [f for f in files if f.lower().startswith('duals_')]
        # If a hint is provided, try to match it
        if scenario_hint:
            hint = scenario_hint.replace(' ', '_')
            dual_candidates_hint = [f for f in dual_candidates if hint in f]
            if dual_candidates_hint:
                dual_candidates = dual_candidates_hint
        # Choose the newest by modification time, or fallback to any
        if dual_candidates:
            dual_candidates_full = [os.path.join(dir_path, f) for f in dual_candidates]
        else:
            dual_candidates_full = [os.path.join(dir_path, f) for f in files]
        if not dual_candidates_full:
            print(f"No dual text files found in directory: {dir_path}")
            return
        dual_file_path = max(dual_candidates_full, key=lambda p: os.path.getmtime(p))
        print(f"Using duals file: {dual_file_path}")

    # Parse file
    series = {}         # base_name -> {idx:int -> value:float}
    scalars = {}        # name -> value
    scenario_title = os.path.basename(dual_file_path)
    try:
        with open(dual_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    # Try to parse scenario name from header
                    if line.lower().startswith('dual values') and ':' in line:
                        scenario_title = line.split(':', 1)[-1].strip()
                    continue
                name, val_str = line.split(':', 1)
                name = name.strip()
                try:
                    val = float(val_str.strip())
                except ValueError:
                    continue
                m = re.match(r"^(.*?)[_\s](\d+)$", name)
                if m:
                    base = m.group(1)
                    idx = int(m.group(2))
                    series.setdefault(base, {})[idx] = val
                else:
                    scalars[name] = val
    except Exception as e:
        print(f"Failed to read dual file: {e}")
        return

    # Filter by include/exclude
    def allowed(base):
        if include and base not in include:
            return False
        if exclude and base in exclude:
            return False
        return True

    # Prepare plot
    plt.figure(figsize=(11, 6))
    color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
    import itertools
    style_cycle = itertools.cycle(['-', '--', '-.', ':'])
    marker_cycle = itertools.cycle(['o', 's', 'D', '^', 'v', 'x'])
    color_cycle_iter = itertools.cycle(color_cycle)

    any_series = False
    for base, points in series.items():
        if not allowed(base):
            continue
        if not points:
            continue
        idxs = sorted(points.keys())
        xs = idxs
        ys = [points[i] for i in idxs]
        plt.plot(
            xs,
            ys,
            label=base,
            linestyle=next(style_cycle),
            marker=next(marker_cycle),
            color=next(color_cycle_iter),
            linewidth=2,
            markersize=5,
        )
        any_series = True

    if not any_series:
        print("No time-indexed dual series found to plot.")
        if scalars:
            print("Scalars:")
            for k, v in scalars.items():
                print(f"  {k}: {v}")
        return

    plt.title(f"Dual values over time - {scenario_title}")
    plt.xlabel("Hour")
    plt.ylabel("Dual value")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()

    if save_plot:
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(dual_file_path))[0]
        out_path = os.path.join(out_dir, f"{base}.png")
        plt.savefig(out_path)
        print(f"Duals plot saved: {out_path}")
    if show_plot:
        plt.show()


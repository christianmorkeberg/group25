"""Scenario orchestration and plotting runner."""

from pathlib import Path
from typing import Dict, List
from data_ops.data_visualizer import DataVisualizer

class Runner:
    """Coordinates simulations across scenarios and plotting.

    Responsibilities:
    - Manage configuration flags (plotting, horizon, tariff/price options)
    - Load inputs per scenario and run the optimization model
    - Aggregate and return results for printing/exporting
    - Trigger comparative plots and sensitivity plots (for question 2b)
    """
    @staticmethod
    def _results_flat_to_lists(results: dict) -> dict:
        """Convert flat keys into list series.

        Converts results like {'p_import_0': 1.0, 'p_import_1': 2.0}
        into {'p_import': [1.0, 2.0]}. Non-indexed keys are kept as-is.
        """
        from collections import defaultdict
        import re
        grouped = defaultdict(list)
        pattern = re.compile(r"(.+)_([0-9]+)$")
        for k, v in results.items():
            m = pattern.match(k)
            if m:
                base, idx = m.group(1), int(m.group(2))
                grouped[base].append((idx, v))
            else:
                grouped[k] = v
        # Sort by index and convert to lists
        out = {}
        for base, values in grouped.items():
            if isinstance(values, list) and values and isinstance(values[0], tuple):
                values.sort(key=lambda x: x[0])
                out[base] = [v for _, v in values]
            else:
                out[base] = values
        return out

    def __init__(self,show_plots=False,save_plots=False,question=None,num_hours=24,vary_tariff=False,fixed_da=None) -> None:
        """Initialize the Runner with execution flags and context."""
        self.show_plots = show_plots
        self.save_plots = save_plots
        self.question = question
        self.num_hours = num_hours # default, will be updated in run_single_simulation
        self.vary_tariff = vary_tariff
        self.fixed_da = fixed_da

    def run_single_simulation(self, question, input_path, scaling_path):
        """Run a single simulation for a given scaling file.

        Args:
            question: Assignment question id (e.g., 'question_1a').
            input_path: Path to the question's data directory.
            scaling_path: Path to the scenario scaling JSON.

        Returns:
            Tuple (results: dict, profit: float) where results include
            time series and metadata needed for plotting and reporting.
        """
        import json
        from data_ops.data_loader import DataLoader
        from opt_model.opt_model import Consumer, DER, Grid, EnergySystemModel

        dataloader = DataLoader(question=question, input_path=input_path)
        der_production = getattr(dataloader, 'DER_production', None)
        bus_params = getattr(dataloader, 'bus_params', None)
        appliance_params = getattr(dataloader, 'appliance_params', None)
        usage_preference = getattr(dataloader, 'usage_preference', None)

        with open(scaling_path) as f:
            scaling = json.load(f)

        consumer = Consumer(
            usage_preference,
            appliance_params,
            scale=scaling
        )
        #Attach discomfort_cost_per_kWh if present in scaling
        if "discomfort_cost_per_kWh" in scaling:
            consumer.discomfort_cost_per_kWh = scaling["discomfort_cost_per_kWh"]

        der = DER(
            der_production,
            appliance_params,
            scale=scaling
        )
        grid = Grid(
            bus_params,
            scale=scaling
        )
        model = EnergySystemModel(consumer, der, grid)
        results, profit = model.build_and_solve_standardized(debug=False,question=self.question,num_hours=self.num_hours,vary_tariff=self.vary_tariff,fixed_da=self.fixed_da)
    # Only add scenario and plot in run_all_simulations, not here
        return results, profit

    def run_all_simulations(self, question, input_path, scenario_files):
        """Run all simulations for the provided scenarios and plot.

        Args:
            question: Assignment question id.
            input_path: Base path to the question data.
            scenario_files: Mapping scenario_name -> scaling file path.

        Returns:
            Dict mapping scenario_name -> {'results': dict, 'profit': float}.
        """
        visualizer = DataVisualizer(question=self.question)
        scenario_results = {}
        for scenario_name, scaling_path in scenario_files.items():
            results, profit = self.run_single_simulation(question, input_path, scaling_path)
            results_listed = self._results_flat_to_lists(results)
            scenario_results[scenario_name] = {'results': results_listed, 'profit': profit}
            visualizer.add_scenario(scenario_name, results_listed, label=scenario_name)
            print(f"Scenario: {scenario_name}, Profit: {profit}")
        # Plot comparison
        if self.show_plots or self.save_plots:
            visualizer.plot_comparison(keys=["p_import", "p_export", "p_load", "p_pv_actual",'curtailment','P_pv',"p_bat_charge","p_bat_discharge","soc_normal","p_curtailment"],
                                       show_plots = self.show_plots,
                                       save_plots=self.save_plots,
                                       fixed_da=self.fixed_da,
                                       vary_tariff=self.vary_tariff)
            if self.question == "question_2b":
                # Plot the p_bat_cap for question 2b using plot_battery_capacity_vs_price 
                visualizer.plot_battery_capacity_vs_price(show_plot=self.show_plots, save_plot=self.save_plots,fixed_da=self.fixed_da,vary_tariff=self.vary_tariff)

                
        return scenario_results


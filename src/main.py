"""
Placeholder for main function to execute the model runner. This function creates a single/multiple instance of the Runner class, prepares input data,
and runs a single/multiple simulation.

Suggested structure:
- Import necessary modules and functions.
- Define a main function to encapsulate the workflow (e.g. Create an instance of your the Runner class, Run a single simulation or multiple simulations, Save results and generate plots if necessary.)
- Prepare input data for a single simulation or multiple simulations.
- Execute main function when the script is run directly.
"""

from pathlib import Path
from runner.runner import Runner
from utils.utils import print_all_scenarios, get_all_scenarios, select_scenarios


def main():
    # question_1a, question_1b, question_1c, or question_2b
    question = 'question_2b'
    
    # Load all available scenarios
    scenario_files = get_all_scenarios(question=question)
    print(f"Available scenarios: {list(scenario_files.keys())}")
    
    scenarios = "All" # "All" or list of specific scenario names | See scenario names in _scenario_names.json, case insensitive
    scenario_files = select_scenarios(scenario_files, scenarios) 

    input_path = Path(f'data/{question}/')
    vary_tariff=False # Vary tariff [True,False]
    fixed_da= 2.0 # fixed_da [None or float]
    show_plots = False # [True,False] Show plots during execution
    save_plots = True # [True,False] Save plots during execution
    num_hours = 24 # Number of hours to simulate
    print_size = "small" # small or large print of results

    runner = Runner(show_plots=show_plots, 
                    save_plots=save_plots,
                    question=question,
                    num_hours=num_hours,
                    vary_tariff=vary_tariff,
                    fixed_da=fixed_da) 
    scenario_results = runner.run_all_simulations(question, input_path, scenario_files)
    print_all_scenarios(scenario_results,
                        mode=print_size,
                        question=question,
                        vary_tariff=vary_tariff,
                        fixed_da=fixed_da) 
    
    # Plot duals
    show_dual_plots = False # [True,False]
    save_dual_plots = False # [True,False]
    return
    from data_ops.data_visualizer import plot_duals_from_txt
    duals_dir = Path(f"txt/{question}")
    for dual_file in duals_dir.glob("duals_*.txt"):
        plot_duals_from_txt(str(dual_file), 
                            save_plot=save_dual_plots, 
                            show_plot=show_dual_plots, 
                            out_dir=f"img/duals/{question}/")

if __name__ == "__main__":
    main()


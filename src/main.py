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
    question = 'question_1a' # question_1a, question_1b, question_1c, or question_2b
    # Load all available scenarios
    scenario_files = get_all_scenarios(question=question)
    print(f"Available scenarios: {list(scenario_files.keys())}")
    
    scenario_files = select_scenarios(scenario_files, ["All"]) # See scenario names in _scenario_names.json, case insensitive

    input_path = Path(f'data/{question}/')
    vary_tariff=False # Vary tariff [True,False]
    fixed_da=None# fixed_da [None or float]
    runner = Runner(show_plots=False, save_plots=False,question=question,num_hours=24,vary_tariff=vary_tariff,fixed_da=fixed_da) 
    scenario_results = runner.run_all_simulations(question, input_path, scenario_files)
    print_all_scenarios(scenario_results,mode="small",question=question,vary_tariff=vary_tariff,fixed_da=fixed_da) # small or large
    
    # Plot duals
    if 1:
        from data_ops.data_visualizer import plot_duals_from_txt
        duals_dir = Path(f"txt/{question}")
        for dual_file in duals_dir.glob("duals_*.txt"):
            plot_duals_from_txt(str(dual_file), save_plot=True, show_plot=False, out_dir=f"img/duals/{question}/")

if __name__ == "__main__":
    main()


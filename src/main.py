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
    question = 'question_1b'
    # Load all available scenarios
    scenario_files = get_all_scenarios(question=question)
    print(f"Available scenarios: {list(scenario_files.keys())}")
    scenario_files = select_scenarios(scenario_files, "All")

    input_path = Path(f'data/{question}/')
    runner = Runner(show_plots=False, save_plots=True,question=question)
    scenario_results = runner.run_all_simulations(question, input_path, scenario_files)
    print_all_scenarios(scenario_results,mode="small")

if __name__ == "__main__":
    main()

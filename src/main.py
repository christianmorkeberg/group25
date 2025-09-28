"""
Placeholder for main function to execute the model runner. This function creates a single/multiple instance of the Runner class, prepares input data,
and runs a single/multiple simulation.

Suggested structure:
- Import necessary modules and functions.
- Define a main function to encapsulate the workflow (e.g. Create an instance of your the Runner class, Run a single simulation or multiple simulations, Save results and generate plots if necessary.)
- Prepare input data for a single simulation or multiple simulations.
- Execute main function when the script is run directly.
"""
# Imports
from data_ops.data_loader import *

# Instantiate dataloader 
dataloader = DataLoader(question='question_1a', input_path=Path('data/question_1a/'))

from opt_model.opt_model import build_and_solve 

build_and_solve(dataloader)
"""Data loading utilities for question-specific inputs."""
import json
import csv
import pandas as pd
from pathlib import Path
from utils import load_dataset
from pathlib import Path
from dataclasses import dataclass
from logging import Logger
import pandas as pd
import xarray as xr
import numpy as np
#import yaml


class DataLoader:
    """Load all JSON/CSV files for a given question under data/<question>."""
    question: str
    input_path: Path

    def __init__(self, question: str, input_path: Path):
        """Initialize and load datasets for the specified question."""
        self.question = question
        self.input_path = input_path
        if question:
            self._load_dataset(question)

    def _load_dataset(self, question_name: str):
        """Load all files using utils.load_dataset and attach them as attributes."""
        # Load the data
        data = load_dataset(question_name)
        # 
        if data:
            for key, value in data.items():
                setattr(self, key, value)
            print(f"Loaded {len(data)} files from {self.input_path}")
        else:
            print(f"No data loaded from {self.input_path}")



    def _load_data_file(self, question_name: str, file_name: str):
        """
        Placeholder for loading a specific file if needed in the future.

        Note: Not used in current workflow; keep as extension point.
        """
        pass

    def load_aux_data(self, question_name: str, filename: str):
        """Placeholder for loading auxiliary metadata for a scenario/question."""
        pass
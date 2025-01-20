from abc import ABC, abstractmethod
import pandas as pd
from typing import Any, Dict, List, Optional
from modules.storage.minio_manager import MinioManager
from utils.shared_utils import load_data, save_data_to_json, ensure_output_directory
import os
import logging

class BaseProcessor(ABC):
    def __init__(self, input_file_path: str, output_file: Optional[str] = None, minio_config: Optional[Dict[str, Any]] = None):
        self.input_file_path = input_file_path
        self.output_file = output_file
        self.minio_config = minio_config
        self.results = None
        self.minio_manager = MinioManager(**minio_config) if minio_config else None

    def load_data(self):
        """Load data from input file."""
        self.element_data = load_data(self.input_file_path)
        self.validate_data()

    @abstractmethod
    def validate_data(self) -> None:
        """Validate that the required fields are present in the element data."""
        pass

    @abstractmethod
    def process_data(self) -> None:
        """Process the data and store results."""
        pass

    def save_results(self):
        """Save results to output file."""
        if self.results is None:
            raise ValueError("No results to save. Run process_data first.")

        if self.output_file:
            save_data_to_json(self.results, self.output_file)
            logging.info(f"Results saved to {self.output_file}")

            if self.minio_manager:
                self.minio_manager.upload_file(self.output_file)
                logging.info(f"Results uploaded to MinIO")

    def run(self):
        """Run the complete processing pipeline."""
        self.load_data()
        self.process_data()
        self.save_results()
        return self.results

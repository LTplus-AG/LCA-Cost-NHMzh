from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Optional
from modules.storage.minio_manager import MinioManager
from utils.shared_utils import load_data, save_data_to_json, ensure_output_directory
import os
import logging

class BaseProcessor(ABC):
    def __init__(self, input_file_path: str, data_file_path: str, output_file: str, 
                 minio_config: Optional[Dict] = None):
        # File paths
        self.input_file_path = input_file_path
        self.data_file_path = data_file_path
        self.output_file = output_file
        
        # Data containers
        self.element_data = None
        self.data = None
        self.results = None
        
        # MinIO setup (optional)
        self.minio_manager = MinioManager(minio_config) if minio_config else None
        if self.minio_manager:
            # Extract project and filename from input path
            self.project_id = os.path.basename(os.path.dirname(input_file_path))
            self.filename = os.path.splitext(os.path.basename(input_file_path))[0]

    def load_data(self):
        """Load data from file system"""
        self.element_data = load_data(self.input_file_path)
        self.data = load_data(self.data_file_path)
        self.validate_data()

    @abstractmethod
    def validate_data(self) -> None:
        pass

    @abstractmethod
    def process_data(self) -> None:
        pass

    def save_results(self):
        """Save results to both file system and MinIO if configured"""
        # Save to local file system
        ensure_output_directory(os.path.dirname(self.output_file))
        save_data_to_json(self.results, self.output_file)
        
        # Save to MinIO if configured
        if self.minio_manager:
            try:
                # Convert results to DataFrame for MinIO storage
                results_df = pd.DataFrame([
                    {
                        'guid': item['guid'],
                        'components': item['components'],
                        'shared_guid': item['shared_guid']
                    }
                    for item in self.results
                ])
                
                # Store in MinIO based on processor type
                if isinstance(self, LCAProcessor):
                    self.minio_manager.store_lca_data(
                        self.project_id, 
                        self.filename, 
                        results_df
                    )
                elif isinstance(self, CostProcessor):
                    self.minio_manager.store_cost_data(
                        self.project_id, 
                        self.filename, 
                        results_df
                    )
            except Exception as e:
                logging.error(f"Failed to save to MinIO: {str(e)}")
                # Continue execution even if MinIO save fails

    def run(self):
        self.load_data()
        self.process_data()
        self.save_results()

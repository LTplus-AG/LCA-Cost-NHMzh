from abc import ABC, abstractmethod
from utils.shared_utils import load_data, save_data_to_json, ensure_output_directory
from modules.storage.minio_manager import MinioManager
import os
import pandas as pd

class BaseProcessor(ABC):
    def __init__(self, input_file_path, data_file_path, output_file):
        self.input_file_path = input_file_path
        self.data_file_path = data_file_path
        self.output_file = output_file
        self.element_data = None
        self.data = None
        self.results = None
        self.minio_manager = MinioManager()  # Initialize MinIO manager
        
        # Extract project and filename from input path
        self.project_id = os.path.basename(os.path.dirname(input_file_path))
        self.filename = os.path.splitext(os.path.basename(input_file_path))[0]

    def run(self):
        self.load_data()
        self.process_data()
        self.save_results()

    def load_data(self):
        self.element_data = load_data(self.input_file_path)
        self.data = load_data(self.data_file_path)
        self.validate_data()

    @abstractmethod
    def validate_data(self):
        pass

    @abstractmethod
    def process_data(self):
        pass

    def save_results(self):
        # Save to local file system
        ensure_output_directory(os.path.dirname(self.output_file))
        save_data_to_json(self.results, self.output_file)
        
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
            self.minio_manager.store_lca_data(self.project_id, self.filename, results_df)
        elif isinstance(self, CostProcessor):
            self.minio_manager.store_cost_data(self.project_id, self.filename, results_df)

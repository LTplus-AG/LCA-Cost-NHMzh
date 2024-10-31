from abc import ABC, abstractmethod
from utils.shared_utils import load_data, save_data_to_json, ensure_output_directory
import os

class BaseProcessor(ABC):
    def __init__(self, input_file_path, data_file_path, output_file):
        self.input_file_path = input_file_path
        self.data_file_path = data_file_path
        self.output_file = output_file
        self.element_data = None
        self.data = None
        self.results = None

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
        ensure_output_directory(os.path.dirname(self.output_file))
        save_data_to_json(self.results, self.output_file)

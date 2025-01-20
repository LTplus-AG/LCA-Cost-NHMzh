import unittest
import pandas as pd
from pathlib import Path
import sys
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.storage.minio_manager import MinioManager
from tests.config import MINIO_TEST_CONFIG
from tests.data.input.test_data import create_test_lca_data, create_test_cost_data

class TestMinioIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests."""
        cls.minio_manager = MinioManager(MINIO_TEST_CONFIG)
        cls.test_project = "test_project"
        cls.test_filename = "test_file"

    def test_full_lca_workflow(self):
        """Test storing and retrieving LCA data."""
        # Create test data
        test_data = create_test_lca_data()
        
        # Store data
        object_path = self.minio_manager.store_lca_data(
            self.test_project, 
            self.test_filename, 
            test_data
        )
        self.assertIsNotNone(object_path)
        
        # Retrieve data
        retrieved_data = self.minio_manager.get_lca_data(
            self.test_project, 
            self.test_filename
        )
        
        # Compare data
        pd.testing.assert_frame_equal(test_data, retrieved_data)

    def test_full_cost_workflow(self):
        """Test storing and retrieving cost data."""
        # Create test data
        test_data = create_test_cost_data()
        
        # Store data
        object_path = self.minio_manager.store_cost_data(
            self.test_project, 
            self.test_filename, 
            test_data
        )
        self.assertIsNotNone(object_path)
        
        # Retrieve data
        retrieved_data = self.minio_manager.get_cost_data(
            self.test_project, 
            self.test_filename
        )
        
        # Compare data
        pd.testing.assert_frame_equal(test_data, retrieved_data)

if __name__ == '__main__':
    unittest.main() 
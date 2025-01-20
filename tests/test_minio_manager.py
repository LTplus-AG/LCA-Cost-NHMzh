import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import io
from modules.storage.minio_manager import MinioManager

class TestMinioManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_config = {
            'endpoint': 'test-endpoint',
            'access_key': 'test-access-key',
            'secret_key': 'test-secret-key',
            'bucket': 'test-bucket'
        }
        
        # Create sample test data
        self.test_lca_data = pd.DataFrame({
            'id': ['1', '2'],
            'gwp_absolute': [100.0, 200.0],
            'penr_absolute': [300.0, 400.0],
            'ubp_absolute': [500.0, 600.0]
        })
        
        self.test_cost_data = pd.DataFrame({
            'id': ['1', '2'],
            'cost': [1000.0, 2000.0],
            'cost_unit': [100.0, 200.0]
        })

    @patch('modules.storage.minio_manager.Minio')
    def test_initialization(self, mock_minio):
        """Test MinioManager initialization."""
        # Setup mock
        mock_client = Mock()
        mock_client.bucket_exists.return_value = False
        mock_minio.return_value = mock_client

        # Create manager instance
        manager = MinioManager(self.mock_config)

        # Verify Minio client was initialized correctly
        mock_minio.assert_called_once_with(
            endpoint=self.mock_config['endpoint'],
            access_key=self.mock_config['access_key'],
            secret_key=self.mock_config['secret_key'],
            secure=False
        )

        # Verify bucket existence was checked
        mock_client.bucket_exists.assert_called_once_with(self.mock_config['bucket'])
        
        # Verify bucket was created
        mock_client.make_bucket.assert_called_once()

    @patch('modules.storage.minio_manager.Minio')
    def test_store_lca_data(self, mock_minio):
        """Test storing LCA data."""
        # Setup mock
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_minio.return_value = mock_client

        # Create manager instance
        manager = MinioManager(self.mock_config)

        # Store test data
        project_id = "test_project"
        filename = "test_file"
        
        object_path = manager.store_lca_data(project_id, filename, self.test_lca_data)

        # Verify put_object was called
        mock_client.put_object.assert_called_once()
        
        # Verify the object path format
        self.assertTrue(object_path.startswith(f"lca/{project_id}/{filename}"))
        self.assertTrue(object_path.endswith(".parquet"))

    @patch('modules.storage.minio_manager.Minio')
    def test_store_cost_data(self, mock_minio):
        """Test storing cost data."""
        # Setup mock
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_minio.return_value = mock_client

        # Create manager instance
        manager = MinioManager(self.mock_config)

        # Store test data
        project_id = "test_project"
        filename = "test_file"
        
        object_path = manager.store_cost_data(project_id, filename, self.test_cost_data)

        # Verify put_object was called
        mock_client.put_object.assert_called_once()
        
        # Verify the object path format
        self.assertTrue(object_path.startswith(f"cost/{project_id}/{filename}"))
        self.assertTrue(object_path.endswith(".parquet"))

    @patch('modules.storage.minio_manager.Minio')
    def test_get_lca_data(self, mock_minio):
        """Test retrieving LCA data."""
        # Setup mock
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        
        # Create a mock object that simulates a parquet file
        mock_data = self.test_lca_data.to_parquet()
        mock_object = io.BytesIO(mock_data)
        
        # Setup mock responses
        mock_list_object = Mock()
        mock_list_object.object_name = "test_object"
        mock_list_object.last_modified = "2024-01-01"
        mock_client.list_objects.return_value = [mock_list_object]
        mock_client.get_object.return_value = mock_object
        
        mock_minio.return_value = mock_client

        # Create manager instance
        manager = MinioManager(self.mock_config)

        # Retrieve test data
        df = manager.get_lca_data("test_project", "test_file")

        # Verify the data was retrieved correctly
        pd.testing.assert_frame_equal(df, self.test_lca_data)

    @patch('modules.storage.minio_manager.Minio')
    def test_get_cost_data(self, mock_minio):
        """Test retrieving cost data."""
        # Setup mock
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        
        # Create a mock object that simulates a parquet file
        mock_data = self.test_cost_data.to_parquet()
        mock_object = io.BytesIO(mock_data)
        
        # Setup mock responses
        mock_list_object = Mock()
        mock_list_object.object_name = "test_object"
        mock_list_object.last_modified = "2024-01-01"
        mock_client.list_objects.return_value = [mock_list_object]
        mock_client.get_object.return_value = mock_object
        
        mock_minio.return_value = mock_client

        # Create manager instance
        manager = MinioManager(self.mock_config)

        # Retrieve test data
        df = manager.get_cost_data("test_project", "test_file")

        # Verify the data was retrieved correctly
        pd.testing.assert_frame_equal(df, self.test_cost_data)

if __name__ == '__main__':
    unittest.main() 
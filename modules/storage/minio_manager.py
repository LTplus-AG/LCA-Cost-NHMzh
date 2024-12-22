from minio import Minio
from typing import Dict, Optional
import os
from dotenv import load_dotenv
import pandas as pd
import io
import logging
from pydantic import BaseModel, Field
from datetime import datetime

# Load environment variables
load_dotenv()

class MinioManager:
    def __init__(self, config: Optional[Dict] = None):
        """Initialize MinIO client with configuration.
        
        Args:
            config (Dict, optional): Configuration dictionary. If not provided, 
                                   will use environment variables.
        """
        if config is None:
            config = {
                'endpoint': os.getenv('MINIO_ENDPOINT', 'play.min.io'),
                'access_key': os.getenv('MINIO_ACCESS_KEY'),
                'secret_key': os.getenv('MINIO_SECRET_KEY'),
                'bucket': os.getenv('MINIO_LCA_COST_DATA_BUCKET', 'lca-cost-data')
            }

        self.client = Minio(
            endpoint=config['endpoint'],
            access_key=config['access_key'],
            secret_key=config['secret_key'],
            secure=False  # Set to True for production with SSL
        )
        
        self.bucket = config['bucket']
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logging.info(f"Created bucket: {self.bucket}")
        except Exception as e:
            logging.error(f"Error ensuring bucket exists: {e}")
            raise

    def _get_object_path(self, project_id: str, filename: str, data_type: str) -> str:
        """Generate the object path in MinIO."""
        timestamp = datetime.now().isoformat()
        return f"{data_type}/{project_id}/{filename}_{timestamp}.parquet"

    def store_lca_data(self, project_id: str, filename: str, data: pd.DataFrame) -> str:
        """Store LCA data as parquet file in MinIO.
        
        Args:
            project_id: Project identifier
            filename: Name of the file
            data: DataFrame containing LCA data
            
        Returns:
            str: Object path in MinIO
        """
        object_path = self._get_object_path(project_id, filename, "lca")
        
        try:
            # Convert DataFrame to parquet format in memory
            parquet_buffer = io.BytesIO()
            data.to_parquet(parquet_buffer)
            parquet_buffer.seek(0)
            
            # Upload to MinIO
            self.client.put_object(
                self.bucket,
                object_path,
                parquet_buffer,
                length=parquet_buffer.getbuffer().nbytes,
                content_type='application/octet-stream'
            )
            
            logging.info(f"Stored LCA data: {object_path}")
            return object_path
            
        except Exception as e:
            logging.error(f"Error storing LCA data: {e}")
            raise

    def store_cost_data(self, project_id: str, filename: str, data: pd.DataFrame) -> str:
        """Store cost data as parquet file in MinIO.
        
        Args:
            project_id: Project identifier
            filename: Name of the file
            data: DataFrame containing cost data
            
        Returns:
            str: Object path in MinIO
        """
        object_path = self._get_object_path(project_id, filename, "cost")
        
        try:
            # Convert DataFrame to parquet format in memory
            parquet_buffer = io.BytesIO()
            data.to_parquet(parquet_buffer)
            parquet_buffer.seek(0)
            
            # Upload to MinIO
            self.client.put_object(
                self.bucket,
                object_path,
                parquet_buffer,
                length=parquet_buffer.getbuffer().nbytes,
                content_type='application/octet-stream'
            )
            
            logging.info(f"Stored cost data: {object_path}")
            return object_path
            
        except Exception as e:
            logging.error(f"Error storing cost data: {e}")
            raise

    def get_lca_data(self, project_id: str, filename: str) -> pd.DataFrame:
        """Retrieve LCA data from MinIO.
        
        Args:
            project_id: Project identifier
            filename: Name of the file
            
        Returns:
            pd.DataFrame: Retrieved LCA data
        """
        try:
            # Get the latest file for the project/filename combination
            prefix = f"lca/{project_id}/{filename}"
            objects = self.client.list_objects(self.bucket, prefix=prefix)
            latest_object = sorted(objects, key=lambda obj: obj.last_modified)[-1]
            
            # Get the object data
            data = self.client.get_object(self.bucket, latest_object.object_name)
            
            # Read parquet data into DataFrame
            df = pd.read_parquet(io.BytesIO(data.read()))
            return df
            
        except Exception as e:
            logging.error(f"Error retrieving LCA data: {e}")
            raise

    def get_cost_data(self, project_id: str, filename: str) -> pd.DataFrame:
        """Retrieve cost data from MinIO.
        
        Args:
            project_id: Project identifier
            filename: Name of the file
            
        Returns:
            pd.DataFrame: Retrieved cost data
        """
        try:
            # Get the latest file for the project/filename combination
            prefix = f"cost/{project_id}/{filename}"
            objects = self.client.list_objects(self.bucket, prefix=prefix)
            latest_object = sorted(objects, key=lambda obj: obj.last_modified)[-1]
            
            # Get the object data
            data = self.client.get_object(self.bucket, latest_object.object_name)
            
            # Read parquet data into DataFrame
            df = pd.read_parquet(io.BytesIO(data.read()))
            return df
            
        except Exception as e:
            logging.error(f"Error retrieving cost data: {e}")
            raise 
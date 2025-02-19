import os
import sys
# Add the parent directory to sys.path so that the 'modules' package can be found.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uuid
import logging
import requests
import json
from modules.storage.db_manager import DatabaseManager
from minio import Minio
import io
from typing import Optional, Dict, Any

class IFCExtractBuildingElementsService:
    def __init__(self,
                 ifc_url: str,
                 api_endpoint: str,
                 db: DatabaseManager,
                 project_name: str = None,
                 query_params: Optional[Dict[str, Any]] = None,
                 callback_config: Optional[Dict[str, Any]] = None,
                 project_id: Optional[str] = None):
        """
        Args:
            ifc_url (str): Public URL to fetch the IFC file.
            api_endpoint (str): URL of the OpenBIM IFC extract API endpoint (e.g., 
                                "https://openbim-service-production.up.railway.app/api/ifc/extract-building-elements").
            db (DatabaseManager): Shared database instance.
            project_name (str): Optional project name.
            query_params (dict): Optional query parameters for filtering/pagination.
            callback_config (dict): Optional callback configuration. If provided,
                                    the API will return immediately with a task ID and
                                    use the callback URL to send progress and final data.
            project_id (str): Optional project ID.
        """
        self.ifc_url = ifc_url
        self.api_endpoint = api_endpoint
        self.db = db
        logging.info(f"Using database file: {os.path.abspath(db.db_path)}")
        self.project_id = project_id or str(uuid.uuid4())
        self.project_name = project_name or f"IFC Building Elements Project {self.project_id}"
        self.query_params = query_params or {}
        self.callback_config = callback_config
        
        # Initialize MinIO client
        self.minio_client = Minio(
            endpoint=os.getenv('MINIO_ENDPOINT', 'minio1:9000'),
            access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            secure=False  # Set to True if using HTTPS
        )

    def fetch_ifc(self) -> bytes:
        """Fetch the IFC file from MinIO."""
        try:
            # Parse the bucket and object path from the URL
            # URL format: http://minio1:9001/ifc-files/02_BIMcollab_Example_STR.ifc
            path_parts = self.ifc_url.split('/')
            bucket_name = path_parts[-2]  # 'ifc-files'
            object_name = path_parts[-1]  # '02_BIMcollab_Example_STR.ifc'
            
            logging.info(f"Fetching IFC file from MinIO - Bucket: {bucket_name}, Object: {object_name}")
            
            # Get the object data
            response = self.minio_client.get_object(bucket_name, object_name)
            
            # Read all data into memory
            ifc_data = response.read()
            response.close()
            response.release_conn()
            
            return ifc_data
            
        except Exception as e:
            logging.error(f"Error fetching IFC file from MinIO: {str(e)}")
            raise

    def send_to_api(self, ifc_data: bytes) -> dict:
        """
        Sends the IFC file along with query parameters and an optional callback configuration
        to the external IFC extraction API.
        """
        # The API requires the file to be sent as multipart/form-data.
        files = {
            "file": ("model.ifc", ifc_data, "application/octet-stream")
        }
        data = {}
        if self.callback_config:
            # The API expects callback_config as a JSON string.
            data["callback_config"] = json.dumps(self.callback_config)
        
        # Convert boolean values in query_params to lowercase strings
        processed_params = {
            k: ("true" if v is True else "false" if v is False else v)
            for k, v in self.query_params.items()
        }
        
        # Include the API key header
        headers = {
            "X-API-Key": "wgxc9Mr88i7u5l347GPjAiw6FxTTPFlpAoLl47w"
        }
        
        logging.info(f"Sending IFC file to API endpoint {self.api_endpoint} with params {processed_params} and callback_config {self.callback_config}")
        response = requests.post(self.api_endpoint, params=processed_params, files=files, data=data, headers=headers)
        response.raise_for_status()
        return response.json()

    def store_data(self, data: dict):
        """
        Stores the extracted building elements data into the database.
        
        The expected response object (in synchronous mode) should have an "elements" key.
        """
        if "elements" not in data:
            raise ValueError("Processed data is missing the 'elements' key")
        
        # Instead of deduplication logic with original IDs, assign a unique random id to every element.
        elements = data["elements"]
        for element in elements:
            element["id"] = str(uuid.uuid4())
        
        logging.info("Initializing project in the database")
        self.db.init_project(project_id=self.project_id, name=self.project_name, kbob_version="N/A")
        logging.info("Storing extracted IFC elements into the database")
        self.db.store_ifc_elements(elements, self.project_id)
        logging.info(f"Stored {len(elements)} IFC elements for project {self.project_id} into the database.")

    def run(self):
        """
        Executes the entire workflow:
         - Fetches the IFC file from MinIO
         - Sends it to the extraction API
         - Processes the response
        """
        try:
            # Fetch the IFC file from MinIO
            ifc_data = self.fetch_ifc()
            
            # Send to API and get response
            result = self.send_to_api(ifc_data)
            
            if self.callback_config and "task_id" in result:
                logging.info(f"Asynchronous processing initiated. Task ID: {result['task_id']}")
                return result
            else:
                logging.info("Synchronous processing completed.")
                self.store_data(result)
                logging.info(f"IFC extraction stored successfully. Project ID: {self.project_id}")
                return result
                
        except Exception as e:
            logging.error(f"Error during IFC extraction: {e}")
            raise

    def close(self):
        """Close any maintained resources, such as the database connection."""
        self.db.close()

# Example usage:
if __name__ == "__main__":
    # Replace these with your actual URLs and desired parameters.
    # Make sure the API endpoint includes the proper path as needed.
    IFC_URL = "https://www.dropbox.com/scl/fi/1ivktea41wq2d9bdq453m/02_BIMcollab_Example_STR.ifc?rlkey=k0g00occzaghkttd65wagfjna&st=wjbt0k2k&dl=1"
    API_ENDPOINT = "https://openbim-service-production.up.railway.app/api/ifc/extract-building-elements"
    
    # Optional query parameters as described by the API:
    query_params = {
        "page": 1,
        "page_size": 50,
        "exclude_properties": False,
        "exclude_quantities": False,
        "exclude_materials": False,
        "exclude_width": False,
        "exclude_constituent_volumes": False,
        "enable_filter": False,
        # "ifc_classes": ["IfcWall", "IfcSlab"]  # Example filtering
    }
    
    # Optional callback configuration (if you want asynchronous processing)
    callback_config = {
        "url": "https://your-callback-url.com/webhook",
        "token": "your-callback-token"
    }
    
    # For synchronous processing, set callback_config to None:
    service = IFCExtractBuildingElementsService(
        ifc_url=IFC_URL,
        api_endpoint=API_ENDPOINT,
        db=DatabaseManager("data/nhmzh_data.duckdb"),
        query_params=query_params,
        callback_config=None  # or callback_config if async processing is desired.
    )
    try:
        result = service.run()
        logging.info("Processing result:")
        logging.info(result)
    finally:
        service.close() 
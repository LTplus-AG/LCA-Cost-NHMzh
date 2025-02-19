import os
import logging
from typing import Any, Dict, List, Optional
import time
import uuid
import pandas as pd


from modules.base_processor import BaseProcessor
from modules.storage.db_manager import DatabaseManager, DEFAULT_PROJECT_ID
from utils.shared_utils import validate_columns, validate_value, ensure_output_directory, save_data_to_json

class CostProcessor(BaseProcessor):
    def __init__(self, input_file_path, data_file_path, output_file, 
                 db, minio_config=None, project_id=None, project_name=None):
        super().__init__(input_file_path, output_file, minio_config)
        self.data_file_path = data_file_path
        self.db = db
        self.project_id = project_id or DEFAULT_PROJECT_ID
        self.project_name = project_name or f"Cost Project {self.project_id}"
        self.processing_start_time = None
    
    def load_data(self):
        # Initialize project in the database (Cost processing doesn't use a KBOB version)
        self.db.init_project(
            project_id=self.project_id,
            name=self.project_name,
            kbob_version="N/A"
        )
        
        # Update project status to processing
        self.db.update_project_status(self.project_id, "processing")
        
        # Load IFC element data. If no file was provided, load from the database.
        if self.input_file_path is None:
            # Load data from the database
            elements = self.db.get_ifc_elements(self.project_id)
            for element in elements:
                element["GUID"] = element.get("id")
                element["Volume"] = element.get("volume_net")
                element["Length"] = element.get("length")
                element["Area"] = element.get("area_net")
                element["KBOB UUID-Nummer"] = element.get("id")
                element["eBKP-H"] = element.get("ebkp")
            self.element_data = pd.DataFrame(elements)
        else:
            # Load data from CSV
            df = pd.read_csv(self.input_file_path)
            if 'id' in df.columns:
                df['GUID'] = df['id']
                df['KBOB UUID-Nummer'] = df['id']
            if 'volume_net' in df.columns:
                df['Volume'] = df['volume_net']
            if 'length' in df.columns:
                df['Length'] = df['length']
            if 'area_net' in df.columns:
                df['Area'] = df['area_net']
            if 'ebkp' in df.columns:
                df['eBKP-H'] = df['ebkp']
            self.element_data = df
        
        # Load cost data. If no file was provided, load from the database.
        if self.data_file_path is None:
            # Assuming get_cost_data returns a list of dictionaries with cost information
            cost_data = self.db.get_cost_data(self.project_id)
            if not cost_data:
                raise ValueError(f"No cost data found in the database for project {self.project_id}")
            self.data = pd.DataFrame(cost_data)
        else:
            self.data = pd.read_csv(self.data_file_path)
        
        # Convert DataFrame to list of dictionaries if needed (for storing IFC elements)
        csv_elements = self.element_data.to_dict('records')
        if not csv_elements:
            raise ValueError("No elements found in input data")
        
        # Store IFC elements in database
        self.db.store_ifc_elements(csv_elements, self.project_id)
        
        self.validate_data()
        self.processing_start_time = time.time()
    
    def process_data(self) -> None:
        """Process the element data and compute cost metrics."""
        try:
            # Prepare cost data
            cost_data_df = self.data[["Kennwert", "reference"]]
            
            # Ensure 'eBKP-H' is string and strip whitespace
            self.element_data['eBKP-H'] = self.element_data['eBKP-H'].astype(str).str.strip()
            
            # Initialize counters
            total_elements = len(self.element_data)
            processed_elements = 0
            failed_elements = 0
            results = []
            
            # Process each element
            for _, element in self.element_data.iterrows():
                try:
                    # Get cost data for element
                    cost_data = cost_data_df.loc[element['eBKP-H']]
                    
                    # Determine quantity based on reference unit
                    if cost_data['reference'] == 'm2':
                        quantity = element['Area']
                    elif cost_data['reference'] == 'm':
                        quantity = element['Length']
                    else:
                        raise ValueError(f"Unknown unit type: {cost_data['reference']}")
                    
                    # Validate quantity
                    if pd.isna(quantity) or quantity <= 0:
                        raise ValueError(f"Invalid quantity: {quantity}")
                    
                    # Calculate total cost
                    total_cost = quantity * cost_data['Kennwert']
                    
                    # Add successful result with 'material' key added
                    results.append({
                        "guid": element["GUID"],
                        "components": [{
                            "guid": element["GUID"],
                            "material": "Cost Calculation",
                            "ebkp_h": element["eBKP-H"],
                            "total_cost": round(total_cost, 2),
                            "unit_cost": round(cost_data["Kennwert"], 2),
                            "unit": cost_data["reference"],
                            "failed": False
                        }],
                        "shared_guid": False
                    })
                    
                except Exception as e:
                    # Log processing error
                    self.db.log_processing_error(
                        project_id=self.project_id,
                        error_data={
                            "element_id": element["GUID"],
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    )
                    
                    # Add failed result with 'material' key added
                    results.append({
                        "guid": element["GUID"],
                        "components": [{
                            "guid": element["GUID"],
                            "material": "Cost Calculation",
                            "ebkp_h": element["eBKP-H"],
                            "failed": True,
                            "error": str(e)
                        }],
                        "shared_guid": False
                    })
                    failed_elements += 1
                
                processed_elements += 1
            
            self.results = results
            
            # Update processing history
            processing_time = time.time() - self.processing_start_time
            self.db.update_processing_history(
                project_id=self.project_id,
                stats={
                    "total_elements": total_elements,
                    "processed_elements": processed_elements,
                    "failed_elements": failed_elements,
                    "processing_time": processing_time,
                    "kbob_version": "N/A"
                }
            )
            
            # Update project status
            final_status = "completed" if failed_elements == 0 else "failed"
            self.db.update_project_status(self.project_id, final_status)
            
        except Exception as e:
            self.db.update_project_status(self.project_id, "failed")
            raise

    def save_results(self):
        try:
            self.db.save_project_results(self.project_id, self.results)
            logging.info("Results successfully saved to the database.")
        except Exception as e:
            logging.error("Error saving results to the database", exc_info=True)

        # Get and log final project info
        project_info = self.db.get_project_info(self.project_id)
        logging.info(f"Project processing completed. Status: {project_info['status']}")
        logging.info(f"Total elements: {project_info['total_elements']}")
        logging.info(f"Total errors: {project_info['total_errors']}")
        if project_info.get('latest_processing'):
            logging.info(f"Processing time: {project_info['latest_processing'].get('processing_time', 0):.2f}s")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def validate_data(self) -> None:
        """Validate that the required columns are present in the element data and cost data."""
        required_columns = [
            "GUID",
            "Volume",
            "Length",
            "Area",
            "KBOB UUID-Nummer",
            "eBKP-H",
        ]
        validate_columns(self.element_data, required_columns)
        if 'Code' not in self.data.columns:
            raise ValueError("Cost data is missing 'Code' column")
        # Ensure 'Code' is string and set as index
        self.data['Code'] = self.data['Code'].astype(str).str.strip()
        self.data.set_index('Code', inplace=True)

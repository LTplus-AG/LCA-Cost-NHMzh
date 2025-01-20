import logging
from typing import Any, Dict, List

import pandas as pd
import re
import os
import time
import uuid

from modules.base_processor import BaseProcessor
from modules.storage.db_manager import DatabaseManager
from utils.shared_utils import load_data, validate_columns, validate_value, ensure_output_directory, save_data_to_json


class LCAProcessor(BaseProcessor):
    def __init__(self, input_file_path, material_mappings_file, 
                 db_path="nhmzh_data.duckdb", output_file=None, minio_config=None,
                 project_id=None, project_name=None):
        super().__init__(input_file_path, output_file, minio_config)
        self.material_mappings_file = material_mappings_file
        self.db = DatabaseManager(db_path)
        self.project_id = project_id or str(uuid.uuid4())
        self.project_name = project_name or f"LCA Project {self.project_id}"
        self.processing_start_time = None

    def load_data(self):
        # Initialize project in database
        active_version = self.db.get_active_kbob_version()
        if not active_version:
            raise ValueError("No active KBOB version found in database")
        
        self.db.init_project(
            project_id=self.project_id,
            name=self.project_name,
            kbob_version=active_version
        )
        
        # Update project status to processing
        self.db.update_project_status(self.project_id, "processing")
        
        # Load data
        self.element_data = load_data(self.input_file_path)
        self.material_mappings = load_data(self.material_mappings_file)
        
        # Validate data structure before storing
        if not isinstance(self.element_data, dict) or "elements" not in self.element_data:
            raise ValueError("Input data must be a dictionary with 'elements' key")
        
        # Store IFC elements in database
        elements = self.element_data.get("elements", [])
        if not isinstance(elements, list):
            raise ValueError("Elements must be a list")
            
        self.db.store_ifc_elements(elements, self.project_id)
        
        self.validate_data()
        self.processing_start_time = time.time()

    def validate_data(self) -> None:
        """Validate that the required fields are present in the element data."""
        # For element data (JSON)
        if not isinstance(self.element_data, dict) or "elements" not in self.element_data:
            raise ValueError("Input data must be a dictionary with 'elements' key")
        
        # Check each element has required structure
        for element in self.element_data["elements"]:
            required_fields = ["id", "materials", "material_volumes", "properties"]
            missing_fields = [field for field in required_fields if field not in element]
            if missing_fields:
                raise ValueError(f"Element missing required fields: {', '.join(missing_fields)}")
            
            # Check properties
            if "ebkp" not in element["properties"]:
                raise ValueError(f"Element {element['id']} missing ebkp in properties")
            
            # Check material volumes
            for material in element["materials"]:
                if material not in element["material_volumes"]:
                    raise ValueError(f"Element {element['id']} missing volume data for material {material}")
                
                volume_data = element["material_volumes"][material]
                if "volume" not in volume_data or "fraction" not in volume_data:
                    raise ValueError(f"Element {element['id']} material {material} missing volume or fraction")

    def get_life_expectancy(self, ebkp_code: str) -> int:
        """Get life expectancy for a given eBKP-H code from the database."""
        if not ebkp_code:
            return None
        
        ebkp_code = str(ebkp_code).strip()
        result = self.db.conn.execute("""
            SELECT years 
            FROM life_expectancy 
            WHERE ebkp_code = ?
        """, [ebkp_code]).fetchone()
        
        return result[0] if result else None

    def process_data(self) -> None:
        """Process the element data and compute LCA metrics."""
        try:
            # Get active KBOB version
            active_version = self.db.get_active_kbob_version()
            if not active_version:
                raise ValueError("No active KBOB version found in database")

            # Load material mappings
            material_mappings = {
                item["ifc_material"]: item["kbob_id"]
                for item in self.material_mappings
                if item.get("kbob_id")
            }
            
            results = []
            total_elements = len(self.element_data["elements"])
            processed_elements = 0
            failed_elements = 0
            
            for element in self.element_data["elements"]:
                element_result = {
                    "guid": element["id"],
                    "components": []
                }
                
                for material_name in element["materials"]:
                    try:
                        material_data = element["material_volumes"].get(material_name)
                        if not material_data:
                            raise ValueError(f"Missing volume data for material: {material_name}")
                        
                        # Process material data and calculate metrics
                        volume = material_data.get("volume", 0) * material_data.get("fraction", 1.0)
                        density = material_data.get("density", 0)
                        
                        if volume <= 0:
                            raise ValueError(f"Invalid volume: {volume}")
                        
                        if density <= 0:
                            raise ValueError(f"Invalid density: {density}")
                        
                        # Get KBOB ID and material
                        kbob_id = material_mappings.get(material_name)
                        if not kbob_id:
                            raise ValueError(f"Material mapping not found: {material_name}")
                        
                        kbob_material = self.db.get_kbob_material(kbob_id, active_version)
                        if not kbob_material:
                            raise ValueError(f"KBOB ID not found: {kbob_id}")
                        
                        # Calculate impacts
                        ebkp = element.get("properties", {}).get("ebkp", "")
                        life_expectancy = self.get_life_expectancy(ebkp) or 60
                        
                        co2_eq = volume * density * kbob_material["indicator_co2eq"]
                        penre = volume * density * kbob_material["indicator_penre"]
                        ubp = volume * density * kbob_material["indicator_ubp"]
                        
                        # Add successful component
                        element_result["components"].append({
                            "guid": element["id"],
                            "material": material_name,
                            "mat_kbob": kbob_id,
                            "kbob_material_name": kbob_material["name"],
                            "volume": round(volume, 3),
                            "density": round(density, 3),
                            "amortization": life_expectancy,
                            "ebkp_h": ebkp,
                            "gwp_absolute": round(co2_eq, 3),
                            "gwp_relative": round(co2_eq / life_expectancy, 3),
                            "penr_absolute": round(penre, 3),
                            "penr_relative": round(penre / life_expectancy, 3),
                            "ubp_absolute": round(ubp, 0),
                            "ubp_relative": round(ubp / life_expectancy, 0),
                            "failed": False
                        })
                        
                    except Exception as e:
                        # Log processing error
                        self.db.log_processing_error(
                            project_id=self.project_id,
                            error_data={
                                "element_id": element["id"],
                                "material_name": material_name,
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            }
                        )
                        
                        # Add failed component
                        element_result["components"].append({
                            "guid": element["id"],
                            "material": material_name,
                            "failed": True,
                            "error": str(e)
                        })
                        failed_elements += 1
                
                # Add element to results
                element_result["shared_guid"] = len(element_result["components"]) > 1
                results.append(element_result)
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
                    "kbob_version": active_version
                }
            )
            
            # Update project status
            final_status = "completed" if failed_elements == 0 else "failed"
            self.db.update_project_status(self.project_id, final_status)
            
        except Exception as e:
            self.db.update_project_status(self.project_id, "failed")
            raise

    def save_results(self):
        ensure_output_directory(os.path.dirname(self.output_file))
        save_data_to_json(self.results, self.output_file)
        
        if self.minio_manager:
            self.minio_manager.upload_file(self.output_file)
            
        # Get and log final project info
        project_info = self.db.get_project_info(self.project_id)
        logging.info(f"Project processing completed. Status: {project_info['status']}")
        logging.info(f"Total elements: {project_info['total_elements']}")
        logging.info(f"Total errors: {project_info['total_errors']}")
        if project_info['latest_processing']:
            logging.info(f"Processing time: {project_info['latest_processing']['processing_time']:.2f}s")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        self.load_data()
        self.process_data()
        self.save_results()

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import re
import os
import time
import uuid

from modules.base_processor import BaseProcessor
from modules.storage.db_manager import DatabaseManager
from utils.shared_utils import load_data, validate_columns, validate_value, ensure_output_directory, save_data_to_json


class LCAProcessor(BaseProcessor):
    def __init__(self, input_file_path, material_mappings_file, db, project_id: Optional[str] = None, project_name: Optional[str] = None):
        self.material_mappings_file = material_mappings_file
        super().__init__(input_file_path, material_mappings_file)
        self.db = db
        self.project_id = project_id or str(uuid.uuid4())
        self.project_name = project_name or f"LCA Project {self.project_id}"
        self.processing_start_time = None

    def load_data(self):
        # Get active KBOB version from the database
        active_version = self.db.get_active_kbob_version()
        if not active_version:
            raise ValueError("No active KBOB version found in database")
        
        # Upsert project record
        self.db.init_project(
            project_id=self.project_id,
            name=self.project_name,
            kbob_version=active_version
        )
        
        # Update project status to processing
        self.db.update_project_status(self.project_id, "processing")
        
        # Load from the db when file paths are not provided.
        if self.input_file_path is None:
            elements = self.db.get_ifc_elements(self.project_id)
            # For each IFC element, fetch associated materials and their volume data from the database
            for element in elements:
                materials, material_volumes = self.db.get_ifc_element_materials(element["id"])
                logging.debug(f"Element {element['id']}: fetched materials: {materials}, material_volumes: {material_volumes}")
                element["materials"] = materials
                element["material_volumes"] = material_volumes
            self.element_data = { "elements": elements }
        else:
            self.element_data = load_data(self.input_file_path)
            
        if self.material_mappings_file is None:
            self.material_mappings = self.db.get_material_mappings(self.project_id)
        else:
            self.material_mappings = load_data(self.material_mappings_file)
        
        # Validate the retrieved data as before
        self.validate_data()        
        self.processing_start_time = time.time()

    def validate_data(self):
        """Validate input data structure"""
        if not isinstance(self.element_data, dict):
            raise ValueError("Input data must be a dictionary")
        
        if "elements" not in self.element_data:
            raise ValueError("Input data must contain 'elements' key")
        
        elements = self.element_data["elements"]
        logging.debug(f"Validating {len(elements)} IFC elements")
        if not isinstance(elements, list):
            raise ValueError("Elements must be a list")
        
        valid_elements = []
        for i, element in enumerate(elements):
            try:
                if not isinstance(element, dict):
                    raise ValueError(f"Element at index {i} must be a dictionary")
                
                # Get element identifier for better error messages
                element_id = element.get('guid') or element.get('id') or f"at index {i}"
                
                if not (element.get('guid') or element.get('id')):
                    raise ValueError(f"Element {element_id} missing identifier (guid or id)")
                
                # Check for materials and their volumes
                materials = element.get('materials', [])
                material_volumes = element.get('material_volumes', {})
                
                if not materials:
                    logging.debug(f"Element {element_id} materials field: {element.get('materials')}")
                    raise ValueError(f"Element {element_id} missing materials")
                
                has_volume = False
                for material_name in materials:
                    material_data = material_volumes.get(material_name, {})
                    volume = material_data.get('volume')
                    logging.debug(f"Element {element_id} - material '{material_name}' has volume: {volume}")
                    if volume is not None and volume > 0:
                        has_volume = True
                        break
                
                if not has_volume:
                    logging.debug(f"Element {element_id} has materials {materials} but missing valid volume information in material_volumes: {material_volumes}")
                    raise ValueError(f"Element {element_id} missing volume information")
                
                valid_elements.append(element)
                logging.debug(f"Valid element: {element_id} with materials: {materials}")
            except Exception as e:
                logging.warning(f"Skipping invalid element: {str(e)}")
        
        self.element_data["elements"] = valid_elements
        logging.debug(f"Total elements processed: {len(elements)}, valid elements: {len(valid_elements)}")
        if not valid_elements:
            raise ValueError("No valid elements found after validation")

    def get_life_expectancy(self, ebkp_code: str) -> int:
        """Get life expectancy for a given eBKP-H code from the database."""
        if not ebkp_code:
            return None
        
        ebkp_code = str(ebkp_code).strip()
        result = self.db.conn.execute("""
            SELECT MIN(years) 
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
                
                # Skip elements without materials
                if not element.get("materials"):
                    logging.warning(f"Element {element['id']} missing materials, skipping")
                    failed_elements += 1
                    continue
                
                for material_name in element["materials"]:
                    try:
                        # Get material volume data
                        material_data = element.get("material_volumes", {}).get(material_name, {})
                        volume = material_data.get("volume", 0)
                        fraction = material_data.get("fraction", 1.0)
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
                
                # Only add elements that have at least one component
                if element_result["components"]:
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
            
            # Update project status - consider it completed even with some failures
            self.db.update_project_status(self.project_id, "completed")
            
        except Exception as e:
            self.db.update_project_status(self.project_id, "failed")
            raise

    def save_results(self):
        try:
            # Instead of writing to a file, save the processing results directly to the database
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

    def run(self):
        self.load_data()
        self.process_data()
        self.save_results()

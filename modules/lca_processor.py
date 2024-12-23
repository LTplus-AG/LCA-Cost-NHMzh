import logging
from typing import Any, Dict, List

import pandas as pd
import re
import os

from modules.base_processor import BaseProcessor
from utils.shared_utils import load_data, validate_columns, validate_value, ensure_output_directory, save_data_to_json


class LCAProcessor(BaseProcessor):
    def __init__(self, input_file_path, data_file_path, output_file, 
                 life_expectancy_file_path, material_mappings_file, minio_config=None):
        super().__init__(input_file_path, data_file_path, output_file, minio_config)
        self.life_expectancy_file_path = life_expectancy_file_path
        self.material_mappings_file = material_mappings_file

    def load_data(self):
        self.element_data = load_data(self.input_file_path)
        self.data = load_data(self.data_file_path, encoding="ISO-8859-1")
        self.life_expectancy_data = self.load_life_expectancy_data()
        self.material_mappings = load_data(self.material_mappings_file)
        self.validate_data()

    def load_life_expectancy_data(self) -> pd.DataFrame:
        """Load the life expectancy data from the amortization CSV file."""
        return load_data(self.life_expectancy_file_path)

    def validate_data(self) -> None:
        """Validate that the required fields are present in the element data."""
        # For KBOB data (DataFrame)
        kbob_required_columns = [
            "UUID-Nummer",
            "Treibhausgasemissionen, Total [kg CO2-eq]",
            "Primaerenergie nicht erneuerbar, Total [kWh oil-eq]",
            "UBP (Total)",
        ]
        validate_columns(self.data, kbob_required_columns)
        
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
        
        # For life expectancy data (DataFrame)
        life_expectancy_required_columns = [
            "eBKP-H Code",
            "Life Expectancy (years)"
        ]
        validate_columns(self.life_expectancy_data, life_expectancy_required_columns)

    def get_density_from_kbob(self, kbob_uuid: str) -> float:
        """Get material density from KBOB data."""
        if kbob_uuid and kbob_uuid in self.data.index:
            return self.data.loc[kbob_uuid, "density"]
        return None

    def prepare_kbob_data(self) -> pd.DataFrame:
        """Prepare the KBOB data for merging with element data."""
        self.data["UUID-Nummer"] = self.data["UUID-Nummer"].astype(str).str.strip()
        
        kbob_data_df = self.data.set_index("UUID-Nummer")[
            [
                "Treibhausgasemissionen, Total [kg CO2-eq]",
                "Primaerenergie nicht erneuerbar, Total [kWh oil-eq]",
                "UBP (Total)",
                "BAUMATERIALIEN",
                "Rohdichte/ Flaechenmasse",
            ]
        ].rename(
            columns={
                "Treibhausgasemissionen, Total [kg CO2-eq]": "indicator_co2eq",
                "Primaerenergie nicht erneuerbar, Total [kWh oil-eq]": "indicator_penre",
                "UBP (Total)": "indicator_ubp",
                "Rohdichte/ Flaechenmasse": "density",
            }
        )
        
        def parse_density(value):
            if isinstance(value, str):
                # Check if it's a range (e.g., "1400 - 1500")
                match = re.match(r'(\d+)\s*-\s*(\d+)', value)
                if match:
                    low, high = map(float, match.groups())
                    return (low + high) / 2  # Return the average
                # Try to convert to float
                try:
                    return float(value)
                except ValueError:
                    return None
            return value

        # Convert density to numeric, handling ranges and replacing non-numeric values with NaN
        kbob_data_df["density"] = kbob_data_df["density"].apply(parse_density)
        
        # Replace NaN values with 0 density
        kbob_data_df["density"].fillna(0, inplace=True)
        
        # Log a warning for any rows where we used the default density
        default_density_rows = kbob_data_df[kbob_data_df["density"] == 0].index
        if not default_density_rows.empty:
            logging.warning(f"Used no density (0) for the following UUID-Nummer: {', '.join(default_density_rows)}")
        
        return kbob_data_df

    def get_life_expectancy(self, ebkp_code: str) -> int:
        """Get life expectancy for a given eBKP-H code."""
        if not ebkp_code:
            return None
        
        ebkp_code = str(ebkp_code).strip()
        for code, years in zip(
            self.life_expectancy_data["eBKP-H Code"], 
            self.life_expectancy_data["Life Expectancy (years)"]
        ):
            if str(code).strip() == ebkp_code:
                return int(years)
        return None

    def process_data(self) -> None:
        """Process the element data and compute LCA metrics."""
        kbob_data_df = self.prepare_kbob_data()

        # Load material mappings
        material_mappings = {
            item["ifc_material"]: item["kbob_id"]
            for item in self.material_mappings
            if item.get("kbob_id")
        }
        
        results = []
        for element in self.element_data["elements"]:
            element_result = {
                "guid": element["id"],
                "components": []
            }
            
            for material_name in element["materials"]:
                material_data = element["material_volumes"].get(material_name)
                if not material_data:
                    element_result["components"].append({
                        "guid": element["id"],
                        "material": material_name,
                        "failed": True,
                        "error": f"Missing volume data for material: {material_name}"
                    })
                    continue
                
                # Get volume and density from material_data
                volume = material_data.get("volume", 0) * material_data.get("fraction", 1.0)
                density = material_data.get("density", 0)
                
                if volume <= 0:
                    element_result["components"].append({
                        "guid": element["id"],
                        "material": material_name,
                        "failed": True,
                        "error": f"Invalid volume: {volume}"
                    })
                    continue
                
                if density <= 0:
                    element_result["components"].append({
                        "guid": element["id"],
                        "material": material_name,
                        "failed": True,
                        "error": f"Invalid density: {density}"
                    })
                    continue
                
                # Get KBOB ID from material mappings
                kbob_id = material_mappings.get(material_name)
                if not kbob_id:
                    element_result["components"].append({
                        "guid": element["id"],
                        "material": material_name,
                        "failed": True,
                        "error": f"Material mapping not found: {material_name}"
                    })
                    continue
                
                if kbob_id not in kbob_data_df.index:
                    element_result["components"].append({
                        "guid": element["id"],
                        "material": material_name,
                        "mat_kbob": kbob_id,
                        "failed": True,
                        "error": f"KBOB ID not found: {kbob_id}"
                    })
                    continue
                
                kbob_row = kbob_data_df.loc[kbob_id]
                
                # Get life expectancy and ebkp
                ebkp = element.get("properties", {}).get("ebkp", "")
                life_expectancy = self.get_life_expectancy(ebkp)
                
                if not life_expectancy:
                    life_expectancy = 60  # Default value
                
                # Calculate impacts using density from material_data
                co2_eq = volume * density * kbob_row["indicator_co2eq"]
                penre = volume * density * kbob_row["indicator_penre"]
                ubp = volume * density * kbob_row["indicator_ubp"]
                
                # Add component with metrics using standardized names
                element_result["components"].append({
                    "guid": element["id"],
                    "material": material_name,
                    "mat_kbob": kbob_id,
                    "kbob_material_name": kbob_row["BAUMATERIALIEN"],
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
            
            # Add element to results
            element_result["shared_guid"] = len(element_result["components"]) > 1
            results.append(element_result)
        
        self.results = results

    def save_results(self):
        ensure_output_directory(os.path.dirname(self.output_file))
        save_data_to_json(self.results, self.output_file)  

    def run(self):
        self.load_data()
        self.process_data()
        self.save_results()

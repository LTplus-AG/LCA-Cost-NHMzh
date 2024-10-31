import logging
from typing import Any, Dict, List

import pandas as pd
import re
import os

from modules.base_processor import BaseProcessor
from utils.shared_utils import load_data, validate_columns, validate_value, ensure_output_directory, save_data_to_json


class LCAProcessor(BaseProcessor):
    def __init__(self, input_file_path, data_file_path, output_file, life_expectancy_file_path):
        super().__init__(input_file_path, data_file_path, output_file)
        self.life_expectancy_file_path = life_expectancy_file_path

    def load_data(self):
        self.element_data = load_data(self.input_file_path)
        self.data = load_data(self.data_file_path, encoding="ISO-8859-1")
        self.life_expectancy_data = self.load_life_expectancy_data()
        self.validate_data()

    def load_life_expectancy_data(self) -> pd.DataFrame:
        """Load the life expectancy data from the amortization CSV file."""
        return load_data(self.life_expectancy_file_path)

    def validate_data(self) -> None:
        """Validate that the required columns are present in the element data."""
        required_columns = [
            "GUID",
            "Volume",
            "KBOB UUID-Nummer",
            "eBKP-H",
        ]
        validate_columns(self.element_data, required_columns)

    def prepare_kbob_data(self) -> pd.DataFrame:
        """Prepare the KBOB data for merging with element data."""
        self.data["UUID-Nummer"] = self.data["UUID-Nummer"].astype(str).str.strip()
        
        kbob_data_df = self.data.set_index("UUID-Nummer")[
            [
                "Treibhausgasemissionen, Total [kg CO2-eq]",
                "Primaerenergie nicht erneuerbar, Total [kWh oil-eq]",
                "UBP (Total)",
                "Rohdichte/ Flaechenmasse",
                "BAUMATERIALIEN",
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
        default_density_rows = kbob_data_df[kbob_data_df["density"] == 1.0].index
        if not default_density_rows.empty:
            logging.warning(f"Used no density (0) for the following UUID-Nummer: {', '.join(default_density_rows)}")
        
        return kbob_data_df

    def get_life_expectancy(self, ebkp_h: str) -> float:
        """Get life expectancy for a given eBKP-H code, handling partial matches."""
        if pd.isna(ebkp_h):
            logging.warning(f"eBKP-H code is missing (NaN).")
            return None
        ebkp_h = str(ebkp_h).strip()
        for code, years in zip(self.life_expectancy_data["eBKP-H Code"], self.life_expectancy_data["Years"]):
            if ebkp_h.startswith(code):
                return years
        logging.warning(f"No life expectancy found for eBKP-H code: {ebkp_h}")
        return None

    def process_data(self) -> None:
        """Process the element data and compute LCA metrics, including per-year calculations."""
        kbob_data_df = self.prepare_kbob_data()

        # Ensure KBOB UUID-Nummer is a string and strip whitespace
        self.element_data["KBOB UUID-Nummer"] = self.element_data["KBOB UUID-Nummer"].astype(str).str.strip()

        # Ensure 'eBKP-H' is a string and strip whitespace
        self.element_data['eBKP-H'] = self.element_data['eBKP-H'].astype(str).str.strip()

        # Merge element data with KBOB data
        merged_data = pd.merge(
            self.element_data,
            kbob_data_df,
            left_on="KBOB UUID-Nummer",
            right_index=True,
            how="left",
            indicator=True,
        )

        # Handle missing material properties
        missing_materials = merged_data["_merge"] == "left_only"
        if missing_materials.any():
            missing_uuids = merged_data.loc[missing_materials, "KBOB UUID-Nummer"].unique()
            for uuid in missing_uuids:
                logging.warning(f"KBOB UUID '{uuid}' not found in KBOB data.")

        # Validate volume
        merged_data["volume_error"] = merged_data.apply(
            lambda row: validate_value(
                row["Volume"], "volume", row["GUID"], row["eBKP-H"]
            ),
            axis=1,
        )

        # Validate density (from KBOB data)
        merged_data["density_error"] = merged_data.apply(
            lambda row: validate_value(
                row["density"], "density", row["GUID"], row["eBKP-H"]
            ),
            axis=1,
        )

        # Combine errors
        merged_data["error"] = merged_data["volume_error"].combine_first(
            merged_data["density_error"]
        )
        merged_data["failed"] = merged_data["error"].notna()

        # Calculate LCA metrics for valid data
        valid_data = merged_data[
            ~merged_data["failed"] & (merged_data["_merge"] == "both")
        ].copy()

        # Map life expectancy to each building element based on eBKP-H code
        valid_data["life_expectancy"] = valid_data["eBKP-H"].apply(self.get_life_expectancy)

        # Calculate total and per year values for LCA indicators
        valid_data["co2_emission"] = (
            valid_data["density"]
            * valid_data["Volume"]
            * valid_data["indicator_co2eq"]
        )
        valid_data["co2_emission_per_year"] = valid_data["co2_emission"] / valid_data["life_expectancy"]

        valid_data["primary_energy"] = (
            valid_data["density"]
            * valid_data["Volume"]
            * valid_data["indicator_penre"]
        )
        valid_data["primary_energy_per_year"] = valid_data["primary_energy"] / valid_data["life_expectancy"]

        valid_data["ubp"] = (
            valid_data["density"]
            * valid_data["Volume"]
            * valid_data["indicator_ubp"]
        )
        valid_data["ubp_per_year"] = valid_data["ubp"] / valid_data["life_expectancy"]

        # Prepare components for valid data
        components_valid = valid_data.apply(
            lambda row: {
                "guid": row["GUID"],
                "kbob_uuid": row["KBOB UUID-Nummer"],
                "kbob_name": row["BAUMATERIALIEN"],
                "density": round(row["density"], 3),
                "amortization": round(row["life_expectancy"], 3) if pd.notnull(row["life_expectancy"]) else None,
                "co2_eq": round(row["co2_emission"], 3),
                "co2_eq_per_year": round(row["co2_emission_per_year"], 3),
                "penre": round(row["primary_energy"], 3),
                "penre_per_year": round(row["primary_energy_per_year"], 3),
                "ubp": round(row["ubp"], 0),
                "ubp_per_year": round(row["ubp_per_year"], 0),
                "failed": False,
            },
            axis=1,
        ).tolist()

        # Prepare components for failed data
        failed_data = merged_data[
            merged_data["failed"] | (merged_data["_merge"] == "left_only")
        ].copy()
        failed_data["error"] = failed_data.apply(
            lambda row: row["error"]
            if pd.notna(row["error"])
            else f"KBOB UUID '{row['KBOB UUID-Nummer']}' not found",
            axis=1,
        )

        components_failed = failed_data.apply(
            lambda row: {
                "guid": row["GUID"],
                "ebkp_h": row["eBKP-H"],
                "failed": True,
                "error": row["error"],
            },
            axis=1,
        ).tolist()

        # Combine components
        all_components = components_valid + components_failed

        # Group components by GUID
        components_by_guid: Dict[Any, List[Dict[str, Any]]] = {}
        for comp in all_components:
            guid = comp["guid"]
            components_by_guid.setdefault(guid, []).append(comp)

        # Build the results list
        self.results = [
            {
                "guid": guid,
                "components": comps,
                "shared_guid": len(comps) > 1,
            }
            for guid, comps in components_by_guid.items()
        ]

    def save_results(self):
        ensure_output_directory(os.path.dirname(self.output_file))
        save_data_to_json(self.results, self.output_file)  

    def run(self):
        self.load_data()
        self.process_data()
        self.save_results()

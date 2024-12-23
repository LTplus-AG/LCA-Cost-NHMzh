import logging
from typing import Any, Dict, List

import pandas as pd

from modules.base_processor import BaseProcessor
from utils.shared_utils import validate_columns, validate_value

class CostProcessor(BaseProcessor):
    def __init__(self, input_file_path, data_file_path, output_file, minio_config=None):
        super().__init__(input_file_path, data_file_path, output_file, minio_config)
    
    def load_data(self):
        super().load_data()
    
    def run(self):
        super().run()

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

    def process_data(self) -> None:
        """Process the element data and compute cost metrics."""
        # Prepare cost data
        cost_data_df = self.data[["Kennwert", "reference"]]

        # Ensure 'eBKP-H' is string and strip whitespace
        self.element_data['eBKP-H'] = self.element_data['eBKP-H'].astype(str).str.strip()

        # Merge element_data with cost_data_df on 'eBKP-H' and 'Code'
        merged_data = pd.merge(
            self.element_data,
            cost_data_df,
            left_on='eBKP-H',
            right_index=True,
            how='left',
            indicator=True
        )

        # Handle missing cost data
        missing_costs = merged_data['_merge'] == 'left_only'
        if missing_costs.any():
            missing_codes = merged_data.loc[missing_costs, 'eBKP-H'].unique()
            for code in missing_codes:
                logging.warning(f"Cost data for eBKP-H '{code}' not found.")

        # Initialize 'error' column with None
        merged_data['error'] = None

        # Determine 'quantity' based on 'reference' (unit_type)
        merged_data['quantity'] = merged_data.apply(
            lambda row: row['Area'] if row['reference'] == 'm2' else
                        (row['Length'] if row['reference'] == 'm' else pd.NA),
            axis=1
        )

        # Identify rows with unknown 'reference' unit_type
        unknown_units = merged_data['quantity'].isna()
        if unknown_units.any():
            unknown_unit_types = merged_data.loc[unknown_units, 'reference'].unique()
            for unit in unknown_unit_types:
                logging.error(f"Unknown unit type '{unit}' in cost data.")
            # Mark these rows as failed
            merged_data.loc[unknown_units, 'error'] = merged_data.loc[unknown_units].apply(
                lambda row: f"Unknown unit type '{row['reference']}'", axis=1)
            merged_data.loc[unknown_units, 'failed'] = True
        else:
            merged_data['failed'] = False

        # Validate 'quantity'
        merged_data['quantity_error'] = merged_data.apply(
            lambda row: validate_value(
                row['quantity'], 'quantity', row['GUID'], row['eBKP-H']
            ), axis=1
        )
        # Combine errors
        merged_data['error'] = merged_data['error'].combine_first(merged_data['quantity_error'])
        merged_data['failed'] = merged_data['failed'] | merged_data['error'].notna()

        # Calculate 'total_cost' for valid rows
        valid_data = merged_data[~merged_data['failed'] & (merged_data['_merge'] == 'both')].copy()
        valid_data['total_cost'] = valid_data['quantity'] * valid_data['Kennwert']

        # Prepare components for valid data
        components_valid = valid_data.apply(
            lambda row: {
                "guid": row["GUID"],
                "ebkp_h": row["eBKP-H"],
                "total_cost": row["total_cost"],
                "unit_cost": row["Kennwert"],
                "unit": row["reference"],
                "failed": False,
            },
            axis=1,
        ).tolist()

        # Prepare components for failed data
        failed_data = merged_data[merged_data['failed'] | (merged_data['_merge'] == 'left_only')].copy()
        failed_data['error'] = failed_data.apply(
            lambda row: row['error'] if pd.notna(row.get('error')) else f"Cost data for eBKP-H '{row['eBKP-H']}' not found",
            axis=1
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

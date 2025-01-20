import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.storage.db_manager import DatabaseManager
from utils.shared_utils import load_data

class DatabaseLoader:
    def __init__(self, db_path: str = "nhmzh_data.duckdb"):
        self.db = DatabaseManager(db_path)
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def load_all_reference_data(self, version: str = "2024-v1", description: str = None):
        """Load all reference data from the paths specified in .env"""
        try:
            # Start transaction
            conn = self.db.conn
            conn.execute("BEGIN TRANSACTION")

            # Load KBOB data
            kbob_path = os.getenv("KBOB_DATA_PATH")
            if kbob_path:
                self.db.import_kbob_data(csv_path=kbob_path, version=version, description=description, use_transaction=False)
                self.db.set_active_kbob_version(version, use_transaction=False)
            else:
                logging.warning("KBOB_DATA_PATH not found in environment variables")

            # Load amortization periods
            amort_path = os.getenv("AMORTIZATION_PERIODS_PATH")
            if amort_path:
                # Load life expectancy data
                if amort_path.endswith('.json'):
                    data = load_data(amort_path)
                    if not isinstance(data, list):
                        raise ValueError("Life expectancy data must be a list of objects")
                else:
                    # Assume CSV format
                    df = pd.read_csv(amort_path)
                    data = []
                    for _, row in df.iterrows():
                        data.append({
                            "ebkp_code": row["eBKP-H Code"],
                            "description": row["Description"],
                            "years": int(row["Years"]),
                            "model_based": row["model-based?"]
                        })
                
                self.db.init_life_expectancy_data(data, use_transaction=False)
            else:
                logging.warning("AMORTIZATION_PERIODS_PATH not found in environment variables")

            # Load cost data
            cost_path = os.getenv("COST_DB_PATH")
            if cost_path:
                # Load cost data directly from CSV
                df = pd.read_csv(cost_path)
                for _, row in df.iterrows():
                    conn.execute("""
                        INSERT INTO cost_reference (
                            ebkp_code, description, unit, cost_per_unit, version
                        ) VALUES (?, ?, ?, ?, ?)
                    """, [
                        row["Code"],
                        row["Bezeichnung"],
                        row["reference"],
                        row["Kennwert"],
                        version
                    ])
            else:
                logging.warning("COST_DB_PATH not found in environment variables")

            conn.execute("COMMIT")
            logging.info("Successfully loaded all reference data")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except:
                pass  # Ignore rollback errors
            logging.error(f"Failed to load reference data: {e}")
            raise

    def load_kbob_data(self, csv_path: str, version: str, description: Optional[str] = None, set_active: bool = False):
        """Load KBOB materials and version data."""
        try:
            self.db.import_kbob_data(csv_path, version, description)
            if set_active:
                self.db.set_active_kbob_version(version)
            logging.info(f"Successfully loaded KBOB data version {version}")
        except Exception as e:
            logging.error(f"Failed to load KBOB data: {e}")
            raise

    def load_life_expectancy(self, file_path: str):
        """Load life expectancy data from JSON or CSV file."""
        try:
            if file_path.endswith('.json'):
                data = load_data(file_path)
                if not isinstance(data, list):
                    raise ValueError("Life expectancy data must be a list of objects")
            else:
                # Assume CSV format
                df = pd.read_csv(file_path)
                data = []
                for _, row in df.iterrows():
                    data.append({
                        "ebkp_code": row["eBKP-H Code"],
                        "description": row["Description"],
                        "years": int(row["Years"]),
                        "model_based": row["model-based?"]
                    })
            
            self.db.init_life_expectancy_data(data)
            logging.info(f"Successfully loaded {len(data)} life expectancy entries")
        except Exception as e:
            logging.error(f"Failed to load life expectancy data: {e}")
            raise

    def load_material_mappings(self, json_path: str):
        """Load material mappings from JSON file."""
        try:
            data = load_data(json_path)
            if not isinstance(data, list):
                raise ValueError("Material mappings must be a list of objects")
            
            conn = self.db.conn
            conn.execute("BEGIN TRANSACTION")
            
            for mapping in data:
                conn.execute("""
                    INSERT INTO material_mappings (
                        ifc_material, kbob_material, kbob_id, kbob_version,
                        type, is_modelled, ebkp, quantity
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    mapping["ifc_material"],
                    mapping.get("kbob_material"),
                    mapping.get("kbob_id"),
                    mapping["kbob_version"],
                    mapping.get("type"),
                    mapping.get("is_modelled", True),
                    mapping.get("ebkp"),
                    mapping.get("quantity")
                ])
            
            conn.execute("COMMIT")
            logging.info(f"Successfully loaded {len(data)} material mappings")
        except Exception as e:
            conn.execute("ROLLBACK")
            logging.error(f"Failed to load material mappings: {e}")
            raise

    def load_ifc_elements(self, json_file: str, project_name: str = None):
        """Load IFC elements from JSON file."""
        try:
            data = load_data(json_file)
            if not isinstance(data, dict) or "elements" not in data:
                raise ValueError("Invalid JSON format: missing 'elements' key")
            
            if not project_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                project_name = f"IFC_Import_{timestamp}"
            
            project_id = f"ifc_{Path(json_file).stem}"
            self.db.init_project(
                project_id=project_id,
                name=project_name,
                kbob_version="N/A"
            )
            
            elements = data["elements"]
            self.db.store_ifc_elements(elements, project_id)
            
            if "metadata" in data:
                logging.info(f"Metadata: {json.dumps(data['metadata'], indent=2)}")
            
            project_info = self.db.get_project_info(project_id)
            logging.info(f"Successfully loaded {project_info['total_elements']} IFC elements")
            return project_id
        except Exception as e:
            logging.error(f"Failed to load IFC elements: {e}")
            raise

    def export_data(self, output_dir: str):
        """Export all database data to JSON files."""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Export KBOB materials
            kbob_data = self.db.conn.execute("SELECT * FROM kbob_materials").fetchall()
            with open(os.path.join(output_dir, "kbob_materials.json"), "w") as f:
                json.dump(kbob_data, f, indent=2, default=str)
            
            # Export KBOB versions
            versions = self.db.conn.execute("SELECT * FROM kbob_versions").fetchall()
            with open(os.path.join(output_dir, "kbob_versions.json"), "w") as f:
                json.dump(versions, f, indent=2, default=str)
            
            # Export life expectancy data
            life_exp = self.db.conn.execute("SELECT * FROM life_expectancy").fetchall()
            with open(os.path.join(output_dir, "life_expectancy.json"), "w") as f:
                json.dump(life_exp, f, indent=2, default=str)
            
            # Export material mappings
            mappings = self.db.conn.execute("SELECT * FROM material_mappings").fetchall()
            with open(os.path.join(output_dir, "material_mappings.json"), "w") as f:
                json.dump(mappings, f, indent=2, default=str)
            
            # Export projects and their data
            projects = self.db.conn.execute("SELECT * FROM projects").fetchall()
            for project in projects:
                project_id = project[0]
                project_dir = os.path.join(output_dir, f"project_{project_id}")
                os.makedirs(project_dir, exist_ok=True)
                
                # Export project info
                with open(os.path.join(project_dir, "project.json"), "w") as f:
                    json.dump(project, f, indent=2, default=str)
                
                # Export IFC elements
                elements = self.db.conn.execute(
                    "SELECT * FROM ifc_elements WHERE project_id = ?", 
                    [project_id]
                ).fetchall()
                with open(os.path.join(project_dir, "ifc_elements.json"), "w") as f:
                    json.dump(elements, f, indent=2, default=str)
                
                # Export element materials
                materials = self.db.conn.execute("""
                    SELECT m.* FROM ifc_element_materials m
                    JOIN ifc_elements e ON m.element_id = e.id
                    WHERE e.project_id = ?
                """, [project_id]).fetchall()
                with open(os.path.join(project_dir, "element_materials.json"), "w") as f:
                    json.dump(materials, f, indent=2, default=str)
                
                # Export processing results
                results = self.db.conn.execute(
                    "SELECT * FROM processing_results WHERE project_id = ?",
                    [project_id]
                ).fetchall()
                with open(os.path.join(project_dir, "processing_results.json"), "w") as f:
                    json.dump(results, f, indent=2, default=str)
                
                # Export processing errors
                errors = self.db.conn.execute(
                    "SELECT * FROM processing_errors WHERE project_id = ?",
                    [project_id]
                ).fetchall()
                with open(os.path.join(project_dir, "processing_errors.json"), "w") as f:
                    json.dump(errors, f, indent=2, default=str)
                
                # Export processing history
                history = self.db.conn.execute(
                    "SELECT * FROM processing_history WHERE project_id = ?",
                    [project_id]
                ).fetchall()
                with open(os.path.join(project_dir, "processing_history.json"), "w") as f:
                    json.dump(history, f, indent=2, default=str)
            
            logging.info(f"Successfully exported all data to {output_dir}")
        except Exception as e:
            logging.error(f"Failed to export data: {e}")
            raise

    def import_data(self, input_dir: str):
        """Import all database data from JSON files."""
        try:
            # Import KBOB materials
            with open(os.path.join(input_dir, "kbob_materials.json"), "r") as f:
                kbob_data = json.load(f)
                for material in kbob_data:
                    self.db.conn.execute("""
                        INSERT INTO kbob_materials (
                            uuid, name, indicator_co2eq, indicator_penre,
                            indicator_ubp, density, version, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, material)
            
            # Import KBOB versions
            with open(os.path.join(input_dir, "kbob_versions.json"), "r") as f:
                versions = json.load(f)
                for version in versions:
                    self.db.conn.execute("""
                        INSERT INTO kbob_versions (
                            version, is_active, release_date, description, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                    """, version)
            
            # Import life expectancy data
            with open(os.path.join(input_dir, "life_expectancy.json"), "r") as f:
                life_exp = json.load(f)
                for entry in life_exp:
                    self.db.conn.execute("""
                        INSERT INTO life_expectancy (
                            ebkp_code, years, created_at
                        ) VALUES (?, ?, ?)
                    """, entry)
            
            # Import material mappings
            with open(os.path.join(input_dir, "material_mappings.json"), "r") as f:
                mappings = json.load(f)
                for mapping in mappings:
                    self.db.conn.execute("""
                        INSERT INTO material_mappings (
                            ifc_material, kbob_material, kbob_id, kbob_version,
                            type, is_modelled, ebkp, quantity, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, mapping)
            
            # Import projects and their data
            for project_dir in Path(input_dir).glob("project_*"):
                # Import project
                with open(project_dir / "project.json", "r") as f:
                    project = json.load(f)
                    self.db.conn.execute("""
                        INSERT INTO projects (
                            project_id, name, life_expectancy, kbob_version,
                            created_at, updated_at, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, project)
                
                # Import IFC elements
                with open(project_dir / "ifc_elements.json", "r") as f:
                    elements = json.load(f)
                    for element in elements:
                        self.db.conn.execute("""
                            INSERT INTO ifc_elements (
                                id, ifc_class, object_type, load_bearing, is_external,
                                ebkp, volume_net, volume_gross, area_net, area_gross,
                                length, width, height, project_id, timestamp
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, element)
                
                # Import element materials
                with open(project_dir / "element_materials.json", "r") as f:
                    materials = json.load(f)
                    for material in materials:
                        self.db.conn.execute("""
                            INSERT INTO ifc_element_materials (
                                id, element_id, material_name, fraction,
                                volume, width, density
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, material)
                
                # Import processing results
                with open(project_dir / "processing_results.json", "r") as f:
                    results = json.load(f)
                    for result in results:
                        self.db.conn.execute("""
                            INSERT INTO processing_results (
                                id, element_id, material_name, kbob_uuid, kbob_version,
                                volume, density, gwp_absolute, gwp_relative,
                                penr_absolute, penr_relative, ubp_absolute, ubp_relative,
                                amortization, ebkp_h, failed, error, project_id, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, result)
                
                # Import processing errors
                with open(project_dir / "processing_errors.json", "r") as f:
                    errors = json.load(f)
                    for error in errors:
                        self.db.conn.execute("""
                            INSERT INTO processing_errors (
                                id, project_id, element_id, material_name,
                                error_type, error_message, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, error)
                
                # Import processing history
                with open(project_dir / "processing_history.json", "r") as f:
                    history = json.load(f)
                    for entry in history:
                        self.db.conn.execute("""
                            INSERT INTO processing_history (
                                id, project_id, total_elements, processed_elements,
                                failed_elements, processing_time, kbob_version, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, entry)
            
            logging.info(f"Successfully imported all data from {input_dir}")
        except Exception as e:
            logging.error(f"Failed to import data: {e}")
            raise

    def close(self):
        """Close database connection."""
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management tool")
    parser.add_argument("--db-path", default="nhmzh_data.duckdb", help="Path to database file")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Load all reference data
    load_all_parser = subparsers.add_parser("load-all", help="Load all reference data from .env paths")
    load_all_parser.add_argument("--version", default="2024-v1", help="KBOB version")
    load_all_parser.add_argument("--description", help="Version description")
    
    # KBOB data
    kbob_parser = subparsers.add_parser("load-kbob", help="Load KBOB data")
    kbob_parser.add_argument("csv_path", help="Path to KBOB CSV file")
    kbob_parser.add_argument("version", help="KBOB version")
    kbob_parser.add_argument("--description", help="Version description")
    kbob_parser.add_argument("--set-active", action="store_true", help="Set as active version")
    
    # Life expectancy
    life_parser = subparsers.add_parser("load-life", help="Load life expectancy data")
    life_parser.add_argument("file_path", help="Path to life expectancy JSON or CSV file")
    
    # Material mappings
    map_parser = subparsers.add_parser("load-mappings", help="Load material mappings")
    map_parser.add_argument("json_path", help="Path to mappings JSON file")
    
    # IFC elements
    ifc_parser = subparsers.add_parser("load-ifc", help="Load IFC elements")
    ifc_parser.add_argument("json_file", help="Path to IFC JSON file")
    ifc_parser.add_argument("--project-name", help="Project name")
    
    # Export/Import
    export_parser = subparsers.add_parser("export", help="Export all data")
    export_parser.add_argument("output_dir", help="Output directory")
    
    import_parser = subparsers.add_parser("import", help="Import all data")
    import_parser.add_argument("input_dir", help="Input directory")
    
    args = parser.parse_args()
    
    loader = DatabaseLoader(args.db_path)
    try:
        if args.command == "load-all":
            loader.load_all_reference_data(args.version, args.description)
        elif args.command == "load-kbob":
            loader.load_kbob_data(args.csv_path, args.version, args.description, args.set_active)
        elif args.command == "load-life":
            loader.load_life_expectancy(args.file_path)
        elif args.command == "load-mappings":
            loader.load_material_mappings(args.json_path)
        elif args.command == "load-ifc":
            loader.load_ifc_elements(args.json_file, args.project_name)
        elif args.command == "export":
            loader.export_data(args.output_dir)
        elif args.command == "import":
            loader.import_data(args.input_dir)
        else:
            parser.print_help()
    finally:
        loader.close()

if __name__ == "__main__":
    main() 
import duckdb
import pandas as pd
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path
from datetime import date, datetime

class DatabaseManager:
    def __init__(self, db_path: str = "nhmzh_data.duckdb"):
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def conn(self):
        if self._conn is None:
            try:
                self._conn = duckdb.connect(self.db_path)
                self._conn.execute("PRAGMA threads=4")
                self._conn.execute("PRAGMA memory_limit='4GB'")
            except Exception as e:
                logging.error(f"Failed to connect to database: {str(e)}")
                raise
        return self._conn

    def close(self):
        """Explicitly close the connection"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass  # Ignore errors during close
            finally:
                self._conn = None

    def _init_db(self):
        """Initialize database tables if they don't exist"""
        try:
            conn = self.conn
            conn.execute("""
                -- Create sequences for auto-incrementing IDs
                CREATE SEQUENCE IF NOT EXISTS material_id_seq;
                CREATE SEQUENCE IF NOT EXISTS processing_history_id_seq;
                CREATE SEQUENCE IF NOT EXISTS processing_error_id_seq;
                CREATE SEQUENCE IF NOT EXISTS processing_result_id_seq;

                -- Reference Data Tables
                CREATE TABLE IF NOT EXISTS kbob_materials (
                    uuid TEXT NOT NULL,
                    name TEXT NOT NULL,
                    indicator_co2eq REAL NOT NULL,
                    indicator_penre REAL NOT NULL,
                    indicator_ubp REAL NOT NULL,
                    density REAL,
                    version TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (uuid, version)
                );

                CREATE TABLE IF NOT EXISTS kbob_versions (
                    version TEXT PRIMARY KEY,
                    is_active BOOLEAN DEFAULT false,
                    release_date DATE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS life_expectancy (
                    ebkp_code TEXT PRIMARY KEY,
                    years INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Project Data Tables
                CREATE TABLE IF NOT EXISTS projects (
                    project_id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    life_expectancy INTEGER DEFAULT 60,
                    kbob_version VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    status VARCHAR CHECK(status IN ('active', 'processing', 'completed', 'failed'))
                );

                -- IFC Data Tables
                CREATE TABLE IF NOT EXISTS ifc_elements (
                    id VARCHAR PRIMARY KEY,
                    ifc_class VARCHAR NOT NULL,
                    object_type VARCHAR,
                    load_bearing BOOLEAN,
                    is_external BOOLEAN,
                    ebkp VARCHAR,
                    -- Quantities
                    volume_net DOUBLE,
                    volume_gross DOUBLE,
                    area_net DOUBLE,
                    area_gross DOUBLE,
                    length DOUBLE,
                    width DOUBLE,
                    height DOUBLE,
                    -- Metadata
                    project_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS ifc_element_materials (
                    id BIGINT PRIMARY KEY DEFAULT nextval('material_id_seq'),
                    element_id VARCHAR,
                    material_name VARCHAR NOT NULL,
                    fraction DOUBLE,
                    volume DOUBLE,
                    width DOUBLE,
                    density DOUBLE,
                    UNIQUE(element_id, material_name),
                    FOREIGN KEY(element_id) REFERENCES ifc_elements(id)
                );

                CREATE TABLE IF NOT EXISTS material_mappings (
                    ifc_material VARCHAR NOT NULL,
                    kbob_material VARCHAR,
                    kbob_id VARCHAR,
                    kbob_version VARCHAR NOT NULL,
                    type VARCHAR,
                    is_modelled BOOLEAN DEFAULT true,
                    ebkp VARCHAR,
                    quantity DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ifc_material, kbob_id, kbob_version)
                );

                -- Processing Tables
                CREATE TABLE IF NOT EXISTS processing_results (
                    id BIGINT PRIMARY KEY DEFAULT nextval('processing_result_id_seq'),
                    element_id VARCHAR,
                    material_name VARCHAR NOT NULL,
                    kbob_uuid VARCHAR NOT NULL,
                    kbob_version VARCHAR NOT NULL,
                    volume DOUBLE,
                    density DOUBLE,
                    gwp_absolute DOUBLE,
                    gwp_relative DOUBLE,
                    penr_absolute DOUBLE,
                    penr_relative DOUBLE,
                    ubp_absolute DOUBLE,
                    ubp_relative DOUBLE,
                    amortization INTEGER,
                    ebkp_h VARCHAR,
                    failed BOOLEAN DEFAULT false,
                    error TEXT,
                    project_id VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(element_id) REFERENCES ifc_elements(id)
                );

                CREATE TABLE IF NOT EXISTS processing_errors (
                    id BIGINT PRIMARY KEY DEFAULT nextval('processing_error_id_seq'),
                    project_id VARCHAR NOT NULL,
                    element_id VARCHAR,
                    material_name VARCHAR,
                    error_type VARCHAR,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS processing_history (
                    id BIGINT PRIMARY KEY DEFAULT nextval('processing_history_id_seq'),
                    project_id VARCHAR NOT NULL,
                    total_elements INTEGER,
                    processed_elements INTEGER,
                    failed_elements INTEGER,
                    processing_time DOUBLE,
                    kbob_version VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Create indexes for better query performance
                CREATE INDEX IF NOT EXISTS idx_kbob_name ON kbob_materials(name);
                CREATE INDEX IF NOT EXISTS idx_kbob_version ON kbob_materials(version);
                CREATE INDEX IF NOT EXISTS idx_ifc_elements_project ON ifc_elements(project_id);
                CREATE INDEX IF NOT EXISTS idx_element_materials ON ifc_element_materials(element_id);
                CREATE INDEX IF NOT EXISTS idx_material_mappings ON material_mappings(ifc_material, kbob_version);
                CREATE INDEX IF NOT EXISTS idx_processing_results_project ON processing_results(project_id);
                CREATE INDEX IF NOT EXISTS idx_processing_errors_project ON processing_errors(project_id);
                CREATE INDEX IF NOT EXISTS idx_processing_history_project ON processing_history(project_id);
            """)
        except Exception as e:
            logging.error(f"Failed to initialize database: {str(e)}")
            raise

    def import_kbob_data(self, csv_path: str, version: str, description: Optional[str] = None) -> None:
        """Import KBOB data from CSV file"""
        df = pd.read_csv(csv_path, encoding="ISO-8859-1")
        
        # Transform the dataframe to match our schema
        kbob_df = pd.DataFrame({
            'uuid': df['UUID-Nummer'].astype(str).str.strip(),
            'name': df['BAUMATERIALIEN'],
            'indicator_co2eq': df['Treibhausgasemissionen, Total [kg CO2-eq]'],
            'indicator_penre': df['Primaerenergie nicht erneuerbar, Total [kWh oil-eq]'],
            'indicator_ubp': df['UBP (Total)'],
            'density': pd.to_numeric(df['Rohdichte/ Flaechenmasse'], errors='coerce'),
            'version': version
        })

        # Fill NaN densities with 0
        kbob_df['density'] = kbob_df['density'].fillna(0)

        try:
            conn = self.conn
            conn.execute("BEGIN TRANSACTION")
            
            # Insert version info with explicit date
            today = date.today().isoformat()
            conn.execute("""
                INSERT INTO kbob_versions (version, release_date, description)
                VALUES (?, ?, ?)
                ON CONFLICT (version) DO UPDATE SET
                    release_date = excluded.release_date,
                    description = excluded.description
            """, [version, today, description])

            # First, delete existing records for this version
            conn.execute("""
                DELETE FROM kbob_materials 
                WHERE version = ?
            """, [version])

            # Then insert new records
            conn.execute("""
                INSERT INTO kbob_materials (
                    uuid, name, indicator_co2eq, indicator_penre, 
                    indicator_ubp, density, version
                )
                SELECT * FROM kbob_df
            """)
            
            conn.execute("COMMIT")
            logging.info(f"Successfully imported {len(kbob_df)} KBOB materials")
        except Exception as e:
            conn.execute("ROLLBACK")
            logging.error(f"Failed to import KBOB data: {str(e)}")
            raise

    def get_kbob_material(self, uuid: str, version: Optional[str] = None) -> Optional[dict]:
        """Get KBOB material by UUID and optionally version"""
        try:
            conn = self.conn
            if version:
                # Get column names first
                result = conn.execute("""
                    SELECT 
                        uuid, name, indicator_co2eq, indicator_penre, 
                        indicator_ubp, density, version, created_at
                    FROM kbob_materials 
                    WHERE uuid = ? AND version = ?
                """, [uuid, version])
                columns = [desc[0] for desc in result.description]
                row = result.fetchone()
            else:
                # Get column names first
                result = conn.execute("""
                    SELECT 
                        m.uuid, m.name, m.indicator_co2eq, m.indicator_penre, 
                        m.indicator_ubp, m.density, m.version, m.created_at
                    FROM kbob_materials m
                    JOIN kbob_versions v ON m.version = v.version
                    WHERE m.uuid = ? AND v.is_active = true
                """, [uuid])
                columns = [desc[0] for desc in result.description]
                row = result.fetchone()
            
            if row:
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logging.error(f"Failed to get KBOB material: {str(e)}")
            raise

    def get_active_kbob_version(self) -> Optional[str]:
        """Get the currently active KBOB version"""
        try:
            conn = self.conn
            result = conn.execute("""
                SELECT version FROM kbob_versions 
                WHERE is_active = true 
                ORDER BY release_date DESC 
                LIMIT 1
            """).fetchone()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"Failed to get active KBOB version: {str(e)}")
            raise

    def set_active_kbob_version(self, version: str) -> None:
        """Set the active KBOB version"""
        try:
            conn = self.conn
            conn.execute("BEGIN TRANSACTION")
            
            # First deactivate all versions
            conn.execute("UPDATE kbob_versions SET is_active = false")
            # Then activate the specified version
            rows_updated = conn.execute("""
                UPDATE kbob_versions 
                SET is_active = true 
                WHERE version = ?
            """, [version]).rowcount
            
            if rows_updated == 0:
                conn.execute("ROLLBACK")
                raise ValueError(f"Version {version} not found")
            
            conn.execute("COMMIT")
            logging.info(f"Successfully set version {version} as active")
        except Exception as e:
            conn.execute("ROLLBACK")
            raise

    def init_reference_data(self, kbob_path: str, cost_path: str):
        """Initialize reference data tables from source files"""
        with self.conn as conn:
            # Load data directly from CSV/Parquet files
            conn.execute("""
                INSERT INTO kbob_materials
                SELECT * FROM read_csv_auto(?)
            """, [kbob_path])

            conn.execute("""
                INSERT INTO cost_reference
                SELECT * FROM read_csv_auto(?)
            """, [cost_path])

    def init_life_expectancy_data(self, data: List[Dict[str, Any]]):
        """Initialize life expectancy data in the database"""
        with self.conn as conn:
            conn.execute("DELETE FROM life_expectancy")  # Clear existing data
            for item in data:
                conn.execute("""
                    INSERT INTO life_expectancy (ebkp_code, years)
                    VALUES (?, ?)
                """, [item["ebkp_code"], item["years"]])

    def store_ifc_elements(self, elements: List[Dict[str, Any]], project_id: str) -> None:
        """Store IFC elements and their materials in the database"""
        try:
            conn = self.conn
            conn.execute("BEGIN TRANSACTION")

            for element in elements:
                # Handle both dictionary and DataFrame row inputs
                if isinstance(element, str):
                    continue  # Skip if element is a string
                
                # Get element ID based on input type
                element_id = element.get("id") or element.get("GUID")
                if not element_id:
                    logging.warning(f"Skipping element without ID: {element}")
                    continue

                # Extract properties based on input format
                if "properties" in element:
                    # LCA format
                    properties = element.get("properties", {})
                    quantities = element.get("quantities", {})
                    volume_data = quantities.get("volume", {})
                    dimensions = quantities.get("dimensions", {})
                    
                    conn.execute("""
                        INSERT INTO ifc_elements (
                            id, ifc_class, object_type, load_bearing, is_external,
                            ebkp, volume_net, volume_gross, area_net, area_gross,
                            length, width, height, project_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        element_id,
                        element.get("ifc_class"),
                        element.get("object_type"),
                        properties.get("loadBearing"),
                        properties.get("isExternal"),
                        properties.get("ebkp"),
                        volume_data.get("net"),
                        volume_data.get("gross"),
                        quantities.get("area", {}).get("net"),
                        quantities.get("area", {}).get("gross"),
                        dimensions.get("length"),
                        dimensions.get("width"),
                        dimensions.get("height"),
                        project_id
                    ])

                    # Handle material volumes for LCA format
                    for material_name, material_data in element.get("material_volumes", {}).items():
                        conn.execute("""
                            INSERT INTO ifc_element_materials (
                                element_id, material_name, fraction, volume, width, density
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, [
                            element_id,
                            material_name,
                            material_data.get("fraction"),
                            material_data.get("volume"),
                            material_data.get("width"),
                            material_data.get("density", 0)
                        ])
                else:
                    # Cost format
                    conn.execute("""
                        INSERT INTO ifc_elements (
                            id, ebkp, volume_gross, length, area_gross, project_id
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, [
                        element_id,
                        element.get("eBKP-H"),
                        element.get("Volume"),
                        element.get("Length"),
                        element.get("Area"),
                        project_id
                    ])

            conn.execute("COMMIT")
            logging.info(f"Successfully stored {len(elements)} IFC elements for project {project_id}")
        except Exception as e:
            conn.execute("ROLLBACK")
            logging.error(f"Failed to store IFC elements: {str(e)}")
            raise

    def delete_ifc_element(self, element_id: str) -> None:
        """Delete an IFC element and its related records"""
        try:
            conn = self.conn
            conn.execute("BEGIN TRANSACTION")

            # Delete related records first
            conn.execute("DELETE FROM processing_results WHERE element_id = ?", [element_id])
            conn.execute("DELETE FROM ifc_element_materials WHERE element_id = ?", [element_id])
            
            # Then delete the element itself
            conn.execute("DELETE FROM ifc_elements WHERE id = ?", [element_id])

            conn.execute("COMMIT")
        except Exception as e:
            conn.execute("ROLLBACK")
            logging.error(f"Failed to delete IFC element: {str(e)}")
            raise

    def delete_project_elements(self, project_id: str) -> None:
        """Delete all IFC elements and related records for a project"""
        try:
            conn = self.conn
            conn.execute("BEGIN TRANSACTION")

            # Get all element IDs for the project
            element_ids = conn.execute("""
                SELECT id FROM ifc_elements WHERE project_id = ?
            """, [project_id]).fetchall()

            # Delete related records for each element
            for (element_id,) in element_ids:
                conn.execute("DELETE FROM processing_results WHERE element_id = ?", [element_id])
                conn.execute("DELETE FROM ifc_element_materials WHERE element_id = ?", [element_id])

            # Delete all elements for the project
            conn.execute("DELETE FROM ifc_elements WHERE project_id = ?", [project_id])

            conn.execute("COMMIT")
        except Exception as e:
            conn.execute("ROLLBACK")
            logging.error(f"Failed to delete project elements: {str(e)}")
            raise

    def init_project(self, project_id: str, name: str, kbob_version: str, life_expectancy: int = 60) -> None:
        """Initialize a new project in the database."""
        try:
            self.conn.execute("""
                INSERT INTO projects (
                    project_id, name, life_expectancy, kbob_version, 
                    created_at, status
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'active')
            """, [project_id, name, life_expectancy, kbob_version])
            logging.info(f"Initialized project {project_id} in database")
        except Exception as e:
            logging.error(f"Failed to initialize project: {e}")
            raise

    def log_processing_error(self, project_id: str, error_data: Dict[str, Any]) -> None:
        """Log a processing error to the database."""
        try:
            self.conn.execute("""
                INSERT INTO processing_errors (
                    project_id, element_id, material_name, 
                    error_type, error_message
                ) VALUES (?, ?, ?, ?, ?)
            """, [
                project_id,
                error_data.get("element_id"),
                error_data.get("material_name"),
                error_data.get("error_type"),
                error_data.get("error_message")
            ])
        except Exception as e:
            logging.error(f"Failed to log processing error: {e}")
            raise

    def update_processing_history(self, project_id: str, stats: Dict[str, Any]) -> None:
        """Update processing history with statistics."""
        try:
            self.conn.execute("""
                INSERT INTO processing_history (
                    project_id, total_elements, processed_elements,
                    failed_elements, processing_time, kbob_version
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                project_id,
                stats.get("total_elements", 0),
                stats.get("processed_elements", 0),
                stats.get("failed_elements", 0),
                stats.get("processing_time", 0.0),
                stats.get("kbob_version")
            ])
        except Exception as e:
            logging.error(f"Failed to update processing history: {e}")
            raise

    def update_project_status(self, project_id: str, status: str) -> None:
        """Update project status."""
        valid_statuses = ['active', 'processing', 'completed', 'failed']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        try:
            self.conn.execute("""
                UPDATE projects 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = ?
            """, [status, project_id])
        except Exception as e:
            logging.error(f"Failed to update project status: {e}")
            raise

    def get_project_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project information including processing history."""
        try:
            # First get the project details
            project = self.conn.execute("""
                SELECT 
                    p.project_id,
                    p.name,
                    p.life_expectancy,
                    p.kbob_version,
                    p.created_at,
                    p.updated_at,
                    p.status,
                    COUNT(DISTINCT e.id) as total_elements,
                    COUNT(DISTINCT pe.id) as total_errors
                FROM projects p
                LEFT JOIN ifc_elements e ON p.project_id = e.project_id
                LEFT JOIN processing_errors pe ON p.project_id = pe.project_id
                WHERE p.project_id = ?
                GROUP BY 
                    p.project_id, p.name, p.life_expectancy, p.kbob_version,
                    p.created_at, p.updated_at, p.status
            """, [project_id]).fetchone()

            if not project:
                return None

            # Get latest processing history separately
            history = self.conn.execute("""
                SELECT * FROM processing_history
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, [project_id]).fetchone()

            # Get column names for history
            history_columns = None
            if history:
                history_columns = [desc[0] for desc in self.conn.description]
                history = dict(zip(history_columns, history))

            return {
                "project_id": project[0],
                "name": project[1],
                "life_expectancy": project[2],
                "kbob_version": project[3],
                "created_at": project[4],
                "updated_at": project[5],
                "status": project[6],
                "total_elements": project[7],
                "total_errors": project[8],
                "latest_processing": history
            }
        except Exception as e:
            logging.error(f"Failed to get project info: {e}")
            raise


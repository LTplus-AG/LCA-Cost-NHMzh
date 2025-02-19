import duckdb
import pandas as pd
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path
from datetime import date, datetime

class DatabaseManager:
    def __init__(self, db_path: str = "nhmzh_data.duckdb"):
        """Initialize database connection and tables"""
        self.db_path = db_path
        self._conn = None
        self._init_connection()
        self._init_db()

    def _init_connection(self):
        """Initialize database connection"""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)

    @property
    def conn(self):
        """Get database connection, reinitializing if necessary"""
        if self._conn is None:
            self._init_connection()
        return self._conn

    def close(self):
        """Close database connection"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __del__(self):
        """Ensure connection is closed on deletion"""
        self.close()

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
                    ebkp_code TEXT NOT NULL,
                    description TEXT NOT NULL,
                    years INTEGER NOT NULL,
                    model_based BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ebkp_code, description)
                );

                CREATE TABLE IF NOT EXISTS cost_reference (
                    ebkp_code TEXT NOT NULL,
                    description TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    cost_per_unit REAL NOT NULL,
                    version TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ebkp_code, version)
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

    def import_kbob_data(self, csv_path: str, version: str, description: Optional[str] = None, use_transaction: bool = True) -> None:
        """Import KBOB data from CSV file"""
        try:
            conn = self.conn
            
            if use_transaction:
                conn.execute("BEGIN TRANSACTION")
            
            # First, delete existing version info and materials for this version
            conn.execute("DELETE FROM kbob_materials WHERE version = ?", [version])
            conn.execute("DELETE FROM kbob_versions WHERE version = ?", [version])
            
            # Read and transform the data
            df = pd.read_csv(csv_path, encoding="ISO-8859-1")
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
            
            # Insert version info with explicit date
            today = date.today().isoformat()
            conn.execute("""
                INSERT INTO kbob_versions (version, release_date, description)
                VALUES (?, ?, ?)
            """, [version, today, description])

            # Insert new records
            for _, row in kbob_df.iterrows():
                conn.execute("""
                    INSERT INTO kbob_materials (
                        uuid, name, indicator_co2eq, indicator_penre, 
                        indicator_ubp, density, version
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    row['uuid'], row['name'], row['indicator_co2eq'],
                    row['indicator_penre'], row['indicator_ubp'],
                    row['density'], row['version']
                ])
            
            if use_transaction:
                conn.execute("COMMIT")
            logging.info(f"Successfully imported {len(kbob_df)} KBOB materials")
        except Exception as e:
            if use_transaction:
                try:
                    conn.execute("ROLLBACK")
                except:
                    pass  # Ignore rollback errors
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

    def set_active_kbob_version(self, version: str, use_transaction: bool = True) -> None:
        """Set the active KBOB version"""
        try:
            conn = self.conn
            if use_transaction:
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
                if use_transaction:
                    conn.execute("ROLLBACK")
                raise ValueError(f"Version {version} not found")
            
            if use_transaction:
                conn.execute("COMMIT")
            logging.info(f"Successfully set version {version} as active")
        except Exception as e:
            if use_transaction:
                try:
                    conn.execute("ROLLBACK")
                except:
                    pass  # Ignore rollback errors
            raise

    def init_reference_data(self, kbob_path: str, cost_path: str):
        """Initialize reference data tables from source files"""
        try:
            conn = self.conn
            conn.execute("BEGIN TRANSACTION")
            
            # Load data directly from CSV/Parquet files
            conn.execute("""
                INSERT INTO kbob_materials
                SELECT * FROM read_csv_auto(?)
            """, [kbob_path])

            conn.execute("""
                INSERT INTO cost_reference
                SELECT * FROM read_csv_auto(?)
            """, [cost_path])
            
            conn.execute("COMMIT")
            logging.info("Successfully loaded reference data")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except:
                pass  # Ignore rollback errors
            logging.error(f"Failed to load reference data: {str(e)}")
            raise

    def init_life_expectancy_data(self, data: List[Dict[str, Any]], use_transaction: bool = True):
        """Initialize life expectancy data in the database"""
        try:
            conn = self.conn
            if use_transaction:
                conn.execute("BEGIN TRANSACTION")
            
            conn.execute("DELETE FROM life_expectancy")  # Clear existing data
            for item in data:
                conn.execute("""
                    INSERT INTO life_expectancy (ebkp_code, description, years, model_based)
                    VALUES (?, ?, ?, ?)
                """, [
                    item["ebkp_code"],
                    item["description"],
                    item["years"],
                    item.get("model_based", True)
                ])
            
            if use_transaction:
                conn.execute("COMMIT")
        except Exception as e:
            if use_transaction:
                try:
                    conn.execute("ROLLBACK")
                except:
                    pass  # Ignore rollback errors
            raise

    def store_ifc_elements(self, elements: List[Dict[str, Any]], project_id: str) -> None:
        conn = self.conn
        # First transaction: insert/update IFC elements without using ON CONFLICT clause
        try:
            logging.info(f"About to insert {len(elements)} IFC elements into table 'ifc_elements' for project {project_id} using database file: {self.db_path}")
            conn.execute("BEGIN TRANSACTION")
            for element in elements:
                element_id = element.get('id') or element.get('guid')
                if not element_id:
                    continue
                quantities = element.get('quantities', {})
                volume_data = quantities.get('volume', {})
                volume_net = volume_data.get('net')
                volume_gross = volume_data.get('gross')
                dimensions = quantities.get('dimensions', {})
                length = dimensions.get('length')
                width = dimensions.get('width')
                height = dimensions.get('height')
                area_data = quantities.get('area', {})
                area_net = area_data.get('net')
                area_gross = area_data.get('gross')
                load_bearing = element.get('load_bearing') if element.get('load_bearing') is not None else element.get('properties', {}).get('loadBearing')
                is_external = element.get('is_external') if element.get('is_external') is not None else element.get('properties', {}).get('isExternal')
                ebkp = element.get('properties', {}).get('ebkp') or element.get('properties', {}).get('reference')
                
                # Check if the element already exists
                existing = conn.execute("SELECT 1 FROM ifc_elements WHERE id = ?", [element_id]).fetchone()
                if existing:
                    conn.execute("""UPDATE ifc_elements SET
                        ifc_class = ?,
                        object_type = ?,
                        load_bearing = ?,
                        is_external = ?,
                        ebkp = ?,
                        volume_net = ?,
                        volume_gross = ?,
                        area_net = ?,
                        area_gross = ?,
                        length = ?,
                        width = ?,
                        height = ?,
                        timestamp = now()
                        WHERE id = ?
                    """, [
                        element.get('ifc_class', 'Unknown'),
                        element.get('object_type'),
                        load_bearing,
                        is_external,
                        ebkp,
                        volume_net,
                        volume_gross,
                        area_net,
                        area_gross,
                        length,
                        width,
                        height,
                        element_id
                    ])
                else:
                    conn.execute("""INSERT INTO ifc_elements (
                        id, ifc_class, object_type, load_bearing, is_external, ebkp,
                        volume_net, volume_gross, area_net, area_gross, length, width, height, project_id, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
                    """, [
                        element_id,
                        element.get('ifc_class', 'Unknown'),
                        element.get('object_type'),
                        load_bearing,
                        is_external,
                        ebkp,
                        volume_net,
                        volume_gross,
                        area_net,
                        area_gross,
                        length,
                        width,
                        height,
                        project_id
                    ])
            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise

        # Second transaction: insert materials for each IFC element
        try:
            conn.execute("BEGIN TRANSACTION")
            for element in elements:
                element_id = element.get('id') or element.get('guid')
                if not element_id:
                    continue
                for material_name, material_data in element.get('material_volumes', {}).items():
                    conn.execute("""INSERT INTO ifc_element_materials (
                        element_id, material_name, fraction, volume, width, density
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (element_id, material_name) DO UPDATE SET
                        fraction = EXCLUDED.fraction,
                        volume = EXCLUDED.volume,
                        width = EXCLUDED.width,
                        density = EXCLUDED.density
                    """, [
                        element_id,
                        material_name,
                        material_data.get('fraction'),
                        material_data.get('volume'),
                        material_data.get('width'),
                        material_data.get('density', 0)
                    ])
            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except:
                pass
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
        """Initialize a new project in the database or update if it exists."""
        try:
            self.conn.execute(
                """
                INSERT INTO projects (project_id, name, life_expectancy, kbob_version, status)
                VALUES (?, ?, ?, ?, 'active')
                ON CONFLICT(project_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    life_expectancy = EXCLUDED.life_expectancy,
                    kbob_version = EXCLUDED.kbob_version,
                    updated_at = now(),
                    status = 'active'
                """,
                [project_id, name, life_expectancy, kbob_version]
            )
            self.conn.commit()
            logging.info(f"Upserted project {project_id} successfully")
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

    def get_ifc_elements(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Fetch IFC elements for the given project from the database.
        
        Returns a list of dictionaries where each dictionary corresponds to a row in the ifc_elements table.
        """
        try:
            cursor = self.conn.execute(
                "SELECT * FROM ifc_elements WHERE project_id = ?",
                [project_id]
            )
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error fetching IFC elements for project {project_id}: {e}")
            raise

    def get_cost_data(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Fetch cost data (from the cost_reference table) to be used in cost processing.
        
        This example maps the underlying table columns to the expected cost data keys:
         - 'Code' for identifier (taken from ebkp_code)
         - 'Kennwert' for the cost value (taken from cost_per_unit)
         - 'reference' for the unit (taken from unit)
         
        Returns a list of dictionaries.
        """
        try:
            # Adjust the query as needed. Here we select from cost_reference without filtering by project_id,
            # since cost_reference may be shared across projects.
            cursor = self.conn.execute("""
                SELECT 
                    ebkp_code AS Code,
                    cost_per_unit AS Kennwert,
                    unit AS reference,
                    created_at
                FROM cost_reference
            """)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error fetching cost data for project {project_id}: {e}")
            raise

    def get_material_mappings(self, project_id: str) -> dict:
        """Retrieve material mappings for the given project (or globally if not project-specific) from the database."""
        try:
            cursor = self.conn.cursor()
            # Removed WHERE clause because project_id is not a column in material_mappings
            query = "SELECT ifc_material, kbob_id FROM material_mappings"
            cursor.execute(query)
            rows = cursor.fetchall()
            mappings = {}
            for row in rows:
                # Assuming row[0] is ifc_material and row[1] is kbob_id
                mappings[row[0]] = row[1]
            return mappings
        except Exception as e:
            logging.error("Error retrieving material mappings", exc_info=True)
            return {}

    def get_ifc_element_materials(self, element_id: str) -> (List[str], Dict[str, Dict[str, float]]):
        """Retrieve materials and their volume information for a given IFC element from the database.

        Returns a tuple where the first element is a list of material names and the second element is a dictionary mapping each material to a dictionary with volume information.
        """
        try:
            cursor = self.conn.execute("SELECT material_name, volume FROM ifc_element_materials WHERE element_id = ?", [element_id])
            rows = cursor.fetchall()
            materials = []
            material_volumes = {}
            for row in rows:
                material, volume = row[0], row[1]
                materials.append(material)
                material_volumes[material] = {"volume": volume}
            return materials, material_volumes
        except Exception as e:
            logging.error(f"Error fetching materials for element {element_id}: {e}")
            return [], {}

    def save_project_results(self, project_id: str, results: List[Dict[str, Any]]) -> None:
        """Save processing results to the processing_results table."""
        try:
            conn = self.conn
            conn.execute("BEGIN TRANSACTION")
            for result in results:
                element_id = result.get("guid")
                components = result.get("components", [])
                for component in components:
                    material_name = component.get("material")
                    # For successful components, use the provided 'mat_kbob'; otherwise, None
                    kbob_uuid = component.get("mat_kbob") if not component.get("failed") else ""
                    # Use active KBOB version if not provided in the result
                    kbob_version = component.get("kbob_version") if component.get("kbob_version") is not None else self.get_active_kbob_version()
                    volume = component.get("volume")
                    density = component.get("density")
                    gwp_absolute = component.get("gwp_absolute")
                    gwp_relative = component.get("gwp_relative")
                    penr_absolute = component.get("penr_absolute")
                    penr_relative = component.get("penr_relative")
                    ubp_absolute = component.get("ubp_absolute")
                    ubp_relative = component.get("ubp_relative")
                    amortization = component.get("amortization")
                    ebkp_h = component.get("ebkp_h")
                    failed = component.get("failed", True)
                    error_msg = component.get("error") if failed else None

                    conn.execute("""INSERT INTO processing_results (
                        element_id, material_name, kbob_uuid, kbob_version, volume, density,
                        gwp_absolute, gwp_relative, penr_absolute, penr_relative,
                        ubp_absolute, ubp_relative, amortization, ebkp_h, failed, error, project_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        element_id,
                        material_name,
                        kbob_uuid,
                        kbob_version,
                        volume,
                        density,
                        gwp_absolute,
                        gwp_relative,
                        penr_absolute,
                        penr_relative,
                        ubp_absolute,
                        ubp_relative,
                        amortization,
                        ebkp_h,
                        failed,
                        error_msg,
                        project_id
                    ])
            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise


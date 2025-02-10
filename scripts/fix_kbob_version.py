import duckdb
import logging
from datetime import date
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    db_path = os.path.join("data", "nhmzh_data.duckdb")
    abs_db_path = os.path.abspath(db_path)
    logging.info(f"Using database at: {abs_db_path}")
    
    if not os.path.exists(abs_db_path):
        logging.error(f"Database not found at: {abs_db_path}")
        return
    
    conn = duckdb.connect(abs_db_path)
    
    try:
        # Check KBOB materials
        result = conn.execute("SELECT DISTINCT version FROM kbob_materials").fetchall()
        versions = [r[0] for r in result]
        logging.info(f"Found KBOB versions in materials: {versions}")
        
        if versions:
            # Get latest version
            latest_version = max(versions)
            
            # Check if version exists in kbob_versions
            result = conn.execute(
                "SELECT version FROM kbob_versions WHERE version = ?",
                [latest_version]
            ).fetchone()
            
            if not result:
                # Add version to kbob_versions
                conn.execute("""
                    INSERT INTO kbob_versions (version, is_active, release_date)
                    VALUES (?, true, ?)
                """, [latest_version, date.today().isoformat()])
                logging.info(f"Added version {latest_version} to kbob_versions")
            
            # Set as active
            conn.execute("UPDATE kbob_versions SET is_active = false")
            conn.execute(
                "UPDATE kbob_versions SET is_active = true WHERE version = ?",
                [latest_version]
            )
            logging.info(f"Set version {latest_version} as active")
        else:
            logging.error("No KBOB materials found in database")
            
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 
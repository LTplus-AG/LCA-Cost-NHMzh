import json
import sys
from pathlib import Path

from modules.storage.db_manager import DatabaseManager


def load_ifc_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # if the JSON is a dict with 'elements' key, use its value, else assume data itself is a list
    if isinstance(data, dict) and 'elements' in data:
        return data['elements']
    elif isinstance(data, list):
        return data
    else:
        raise ValueError('JSON format not recognized. Expected a list or a dict with an "elements" key.')


def main():
    if len(sys.argv) < 3:
        print('Usage: python load_ifc_into_db.py <ifc_json_file> <project_id>')
        sys.exit(1)

    json_path = sys.argv[1]
    project_id = sys.argv[2]
    
    # Load IFC elements from JSON file
    try:
        elements = load_ifc_data(json_path)
    except Exception as e:
        print(f'Error loading JSON file: {e}')
        sys.exit(1)

    # Connect to the DuckDB database
    db_path = 'nhmzh_data.duckdb'  # or get from environment or argument
    db = DatabaseManager(db_path)
    
    try:
        # Delete existing IFC elements and related records for the project
        db.delete_project_elements(project_id)
        
        # Insert new IFC elements
        db.store_ifc_elements(elements, project_id)
        print(f'Successfully replaced IFC elements in project {project_id} with {len(elements)} new elements')
    except Exception as e:
        print(f'Error inserting elements into the database: {e}')
    finally:
        db.close()


if __name__ == '__main__':
    main() 
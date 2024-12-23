import pandas as pd
import logging
import os
import json
from joblib import Parallel, delayed
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def load_data(file_path, encoding='utf-8'):
    """Load data from various file formats."""
    file_path = Path(file_path)
    
    try:
        # Handle different file formats
        if file_path.suffix.lower() == '.csv':
            return pd.read_csv(file_path, encoding=encoding)
        elif file_path.suffix.lower() == '.xlsx':
            return pd.read_excel(file_path)
        elif file_path.suffix.lower() == '.json':
            # For JSON files, first check if it's a string containing JSON data
            if isinstance(file_path, str) and not os.path.exists(file_path):
                try:
                    return json.loads(file_path)
                except json.JSONDecodeError:
                    pass
            # Otherwise try to load from file
            with open(file_path, 'r', encoding=encoding) as f:
                return json.load(f)
        elif file_path.suffix.lower() == '.parquet':
            return pd.read_parquet(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
    except Exception as e:
        logging.exception(f"Error loading data from {file_path}: {e}")
        raise

def save_data_to_json(data, file_path: str) -> None:
    """Save data to a JSON file."""
    ensure_output_directory(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def validate_columns(data, required_columns: list) -> None:
    """Validate that all required columns/keys are present in the data structure."""
    if isinstance(data, pd.DataFrame):
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    elif isinstance(data, dict):
        # For JSON-like data, check if required fields exist in the elements
        if "elements" in data:
            # Check first element as sample
            if data["elements"]:
                sample_element = data["elements"][0]
                missing_columns = [col for col in required_columns if col not in sample_element]
                if missing_columns:
                    raise ValueError(f"Missing required fields in elements: {', '.join(missing_columns)}")
        else:
            raise ValueError("Data structure missing 'elements' key")
    else:
        raise ValueError(f"Unsupported data type for validation: {type(data)}")

def ensure_output_directory(directory_path: str) -> None:
    """Ensure the output directory exists."""
    os.makedirs(directory_path, exist_ok=True)

def process_in_parallel(function, iterable, n_jobs=-1):
    return Parallel(n_jobs=n_jobs)(delayed(function)(item) for item in iterable)

def validate_value(value, value_type: str, guid: str, ebkp_h: str) -> str:
    """Validate a numeric value and return error message if invalid."""
    if pd.isna(value):
        return f"Missing {value_type} for GUID {guid} (eBKP-H: {ebkp_h})"
    if not isinstance(value, (int, float)) or value <= 0:
        return f"Invalid {value_type} ({value}) for GUID {guid} (eBKP-H: {ebkp_h})"
    return None

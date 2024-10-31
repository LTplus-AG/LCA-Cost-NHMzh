import pandas as pd
import logging
import os
import json
from joblib import Parallel, delayed
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def load_data(
    file_path: str | Path, sheet_name: str = None, encoding: str = 'utf-8'
) -> pd.DataFrame:
    logging.info(f"Loading data from {file_path}...")
    try:
        file_path = Path(file_path)
        if file_path.suffix in (".xlsx", ".xls"):
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                # If no sheet_name is provided, read all sheets and concatenate them
                df = pd.concat(pd.read_excel(file_path, sheet_name=None).values(), ignore_index=True)
            return df
        elif file_path.suffix == ".csv":
            encodings_to_try = ['utf-8', 'ISO-8859-1', 'windows-1252']
            for enc in encodings_to_try:
                try:
                    return pd.read_csv(file_path, encoding=enc)
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"Unable to decode the CSV file with any of the attempted encodings: {encodings_to_try}")
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    except Exception as e:
        logging.exception(f"Error loading data from {file_path}: {e}")
        raise

def save_data_to_json(data, output_file):
    logging.info(f"Saving data to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logging.info(f"Data saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving data: {e}")
        raise

def validate_columns(df, required_columns):
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Data is missing required columns: {', '.join(missing_columns)}")

def ensure_output_directory(directory):
    os.makedirs(directory, exist_ok=True)

def process_in_parallel(function, iterable, n_jobs=-1):
    return Parallel(n_jobs=n_jobs)(delayed(function)(item) for item in iterable)

def validate_value(value, name, guid, ebkp_h):
    if pd.isna(value) or value <= 0:
        error_msg = f"Missing or invalid {name} for GUID '{guid}' and eBKP-H '{ebkp_h}'"
        logging.error(error_msg)
        return error_msg
    return None

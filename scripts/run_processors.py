import sys
import os
import logging
import json
from dotenv import load_dotenv

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))  # Path to 'scripts/'
parent_dir = os.path.dirname(current_dir)  # Path to 'NHMzh-modules/'
sys.path.insert(0, parent_dir)

from modules.lca_processor import LCAProcessor
from modules.cost_processor import CostProcessor
from utils.shared_utils import ensure_output_directory

def combine_results(lca_results, cost_results):
    combined_results = {}

    # Combine results based on GUID
    for result_list in [lca_results, cost_results]:
        for item in result_list:
            guid = item['guid']
            if guid not in combined_results:
                combined_results[guid] = item
            else:
                # Merge components
                combined_results[guid]['components'].extend(item['components'])
                combined_results[guid]['shared_guid'] = (
                    combined_results[guid]['shared_guid'] or item['shared_guid']
                )

    # Convert back to list
    return list(combined_results.values())

def get_minio_config():
    """Get MinIO configuration from environment variables"""
    load_dotenv()
    return {
        'endpoint': os.getenv('MINIO_ENDPOINT'),
        'access_key': os.getenv('MINIO_ACCESS_KEY'),
        'secret_key': os.getenv('MINIO_SECRET_KEY'),
        'bucket': os.getenv('MINIO_LCA_COST_DATA_BUCKET')
    } if all([
        os.getenv('MINIO_ENDPOINT'),
        os.getenv('MINIO_ACCESS_KEY'),
        os.getenv('MINIO_SECRET_KEY'),
        os.getenv('MINIO_LCA_COST_DATA_BUCKET')
    ]) else None

def get_db_path():
    """Get standardized database path."""
    if os.path.exists('/.dockerenv'):
        return "/app/data/nhmzh_data.duckdb"
    else:
        # Get the path to the NHMzh root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(current_dir))  # NHMzh root
        return os.path.join(base_dir, "LCA-Cost-NHMzh", "data", "nhmzh_data.duckdb")

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Get the absolute path to the LCA-Cost-NHMzh directory
    current_dir = os.path.dirname(os.path.abspath(__file__))  # scripts/
    base_dir = os.path.dirname(current_dir)  # LCA-Cost-NHMzh/
    
    # Use standardized database path
    db_path = get_db_path()
    logging.info(f"Using database at: {db_path}")
    
    # Ensure database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    if len(sys.argv) != 3:
        print("Usage: python scripts/run_processors.py <input_file_name> <mappings_file_name>")
        sys.exit(1)

    input_file_name = sys.argv[1]
    mappings_file_name = sys.argv[2]
    
    # Construct full paths for input files
    project_root = os.path.dirname(base_dir)  # NHMzh/
    input_file_path = os.path.join(project_root, input_file_name)
    mappings_file = os.path.join(project_root, mappings_file_name)

    # Construct paths
    output_directory = os.path.join(base_dir, "data", "output")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    
    if not os.path.exists(input_file_path):
        logging.error(f"Input file not found: {input_file_path}")
        sys.exit(1)
    
    if not os.path.exists(mappings_file):
        logging.error(f"Mappings file not found: {mappings_file}")
        sys.exit(1)

    logging.info(f"Input File Path: {input_file_path}")
    logging.info(f"Using material mappings from: {mappings_file}")

    lca_output_file = os.path.join(output_directory, "lca_results.json")
    cost_output_file = os.path.join(output_directory, "cost_results.json")
    combined_output_file = os.path.join(output_directory, "combined_results.json")
    summary_report_file = os.path.join(output_directory, "summary_report.txt")

    logging.info("Starting LCA and Cost modules...")

    # Get MinIO config if available
    minio_config = get_minio_config()
    if minio_config:
        logging.info("MinIO configuration found - results will be stored in MinIO")
    
    try:
        # Run LCA Processor
        lca_processor = LCAProcessor(
            input_file_path=input_file_path,
            material_mappings_file=mappings_file,
            db_path=db_path,
            output_file=lca_output_file,
            minio_config=minio_config
        )
        lca_processor.run()
        logging.info("LCA module completed successfully.")

        # Run Cost Processor
        cost_processor = CostProcessor(
            input_file_path=input_file_path,
            data_file_path=cost_data_file_path,
            output_file=cost_output_file,
            db_path=db_path,
            minio_config=minio_config
        )
        cost_processor.run()
        logging.info("Cost module completed successfully.")

        # Combine results
        try:
            with open(lca_output_file, 'r') as f:
                lca_content = f.read()
                if not lca_content:
                    raise ValueError("LCA output file is empty")
                lca_results = json.loads(lca_content)
            logging.info(f"Successfully loaded LCA results from {lca_output_file}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding LCA results JSON: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error reading LCA results file: {str(e)}")
            raise

        try:
            with open(cost_output_file, 'r') as f:
                cost_content = f.read()
                if not cost_content:
                    raise ValueError("Cost output file is empty")
                cost_results = json.loads(cost_content)
            logging.info(f"Successfully loaded Cost results from {cost_output_file}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding Cost results JSON: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error reading Cost results file: {str(e)}")
            raise

        combined_results = combine_results(lca_results, cost_results)

        # Save combined results
        ensure_output_directory(output_directory)
        with open(combined_output_file, 'w') as f:
            json.dump(combined_results, f, indent=4)

        logging.info(f"Combined results saved to {combined_output_file}")

    except Exception as e:
        logging.error(f"An error occurred during execution: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

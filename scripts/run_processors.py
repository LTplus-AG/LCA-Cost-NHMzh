import sys
import os
import logging
import json

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

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    if len(sys.argv) != 2:
        print("Usage: python scripts/run_processors.py <input_file_name>")
        sys.exit(1)

    input_file_name = sys.argv[1]
    
    # Check if we're running in Docker
    if os.path.exists('/.dockerenv'):
        # We're in Docker, use absolute paths
        base_dir = "/app"
        input_file_path = os.path.join("/app/data/input", input_file_name)
    else:
        # We're running locally, use relative paths
        base_dir = os.path.dirname(current_dir)  # Path to 'NHMzh-modules/'
        input_file_path = os.path.join(base_dir, input_file_name)

    # Construct paths
    kbob_data_file_path = os.path.join(base_dir, "data", "input", "KBOB.csv")
    life_expectancy_file_path = os.path.join(base_dir, "data", "input", "amortization_periods.csv")
    cost_data_file_path = os.path.join(base_dir, "data", "input", "CostDB.csv")
    output_directory = os.path.join(base_dir, "data", "output")
    
    if not os.path.exists(input_file_path):
        logging.error(f"Input file not found: {input_file_path}")
        sys.exit(1)

    logging.info(f"Input File Path: {input_file_path}")

    lca_output_file = os.path.join(output_directory, "lca_results.json")
    cost_output_file = os.path.join(output_directory, "cost_results.json")
    combined_output_file = os.path.join(output_directory, "combined_results.json")
    summary_report_file = os.path.join(output_directory, "summary_report.txt")

    logging.info("Starting LCA and Cost modules...")

    try:
        # Run LCA Processor
        lca_processor = LCAProcessor(
            input_file_path,
            kbob_data_file_path,
            lca_output_file,
            life_expectancy_file_path,
        )
        lca_processor.run()
        logging.info("LCA module completed successfully.")

        # Run Cost Processor
        cost_processor = CostProcessor(
            input_file_path, cost_data_file_path, cost_output_file
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

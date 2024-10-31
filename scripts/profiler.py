# python NHMzh-modules\scripts\profiler.py NHMzh-modules\data\input\large_dataset.csv

import cProfile
import pstats
import sys
import os
import logging
import json
from collections import defaultdict
import time

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))  # Path to 'scripts/'
parent_dir = os.path.dirname(current_dir)  # Path to 'NHMzh-modules/'
sys.path.insert(0, parent_dir)

from run_processors import main as run_main
from utils.shared_utils import ensure_output_directory

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    if len(sys.argv) != 2:
        print("Usage: profiler.py <input_file_path>")
        sys.exit(1)

    input_file_path = sys.argv[1]

    # Start total runtime timer
    total_start_time = time.time()

    # Create a cProfile profiler
    profiler = cProfile.Profile()
    profiler.enable()

    try:
        # Set sys.argv for run_processors.py
        sys.argv = ['run_processors.py', input_file_path]

        # Run the main function from run_processors.py
        run_main()

        logging.info("Processing completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred during execution: {str(e)}")
        sys.exit(1)

    finally:
        profiler.disable()
        total_end_time = time.time()
        total_runtime = total_end_time - total_start_time

        output_directory = os.path.join(parent_dir, "data", "output", "qa")
        ensure_output_directory(output_directory)
        stats = pstats.Stats(profiler)
        stats.dump_stats(os.path.join(output_directory, 'profile_stats.prof'))

        # Process stats to create a summary per .py file
        stats.sort_stats('cumtime')

        # Aggregate cumulative times per .py file
        file_stats = defaultdict(lambda: {'tottime': 0.0, 'cumtime': 0.0})

        for func_tuple, stat in stats.stats.items():
            filename, lineno, function_name = func_tuple
            cc, nc, tt, ct, callers = stat

            if filename.endswith('.py'):
                # Only consider .py files
                # Normalize filename to relative path from project root
                if filename.startswith(parent_dir):
                    # Project files
                    file_path = os.path.relpath(filename, parent_dir)
                else:
                    # Other files, keep as is
                    file_path = filename
                file_stats[file_path]['tottime'] += tt
                file_stats[file_path]['cumtime'] += ct

        # Convert file_stats to a list and sort
        file_stats_list = []
        for file_path, times in file_stats.items():
            file_stat = {
                'file': file_path,
                'tottime': round(times['tottime'], 6),
                'cumtime': round(times['cumtime'], 6),
            }
            file_stats_list.append(file_stat)

        file_stats_list.sort(key=lambda x: x['cumtime'], reverse=True)

        # Prepare the final summary
        profiling_summary = {
            'total_runtime': round(total_runtime, 6),
            'file_stats': file_stats_list
        }

        # Save the summary to a JSON file
        summary_file_path = os.path.join(output_directory, 'profile_summary_by_file.json')
        with open(summary_file_path, 'w') as f:
            json.dump(profiling_summary, f, indent=4)


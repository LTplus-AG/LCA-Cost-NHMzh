import json
import os
import logging
import math

logging.basicConfig(level=logging.INFO)

def load_json_data(file_path):
    logging.info(f"Loading data from {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        logging.info(f"Data loaded successfully from {file_path}.")
        return data
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error loading JSON data from {file_path}: {str(e)}")
        raise

def summarize_results(data):
    total_cost = 0
    total_co2 = 0
    total_primary_energy = 0
    total_ubp = 0

    failed_components = []

    for entry in data:
        for component in entry.get('components', []):
            if component.get('failed', False):
                failed_components.append(component)
                continue

            # Sum Cost
            if 'total_cost' in component:
                value = component['total_cost']
                if value is not None and isinstance(value, (int, float)) and not math.isnan(value):
                    total_cost += value
                else:
                    logging.warning(f"Invalid total_cost value: {value} for component {component.get('ebkp_h', 'N/A')}. Treating as zero.")

            # Sum LCA metrics
            if 'co2_eq' in component:
                value = component['co2_eq']
                if value is not None and isinstance(value, (int, float)) and not math.isnan(value):
                    total_co2 += value
                else:
                    logging.warning(f"Invalid co2_eq value: {value} for component {component.get('ebkp_h', 'N/A')}. Treating as zero.")

            if 'penre' in component:
                value = component['penre']
                if value is not None and isinstance(value, (int, float)) and not math.isnan(value):
                    total_primary_energy += value
                else:
                    logging.warning(f"Invalid penre value: {value} for component {component.get('ebkp_h', 'N/A')}. Treating as zero.")

            if 'ubp' in component:
                value = component['ubp']
                if value is not None and isinstance(value, (int, float)) and not math.isnan(value):
                    total_ubp += value
                else:
                    logging.warning(f"Invalid ubp value: {value} for component {component.get('ebkp_h', 'N/A')}. Treating as zero.")

    return {
        'total_cost': total_cost,
        'total_co2_emission': total_co2,
        'total_primary_energy': total_primary_energy,
        'total_ubp': total_ubp,
        'failed_components': failed_components
    }

def generate_report(summary):
    report = "\nSummary Report:\n"
    report += f"Total Cost: {summary['total_cost']:,.2f} Chf\n".replace(',', 'X').replace('.', ',').replace('X', '`')
    report += f"Total CO₂ Emissions: {summary['total_co2_emission']:,.2f} kg CO₂-eq\n".replace(',', 'X').replace('.', ',').replace('X', '`')
    report += f"Total Primary Energy (non-renewable): {summary['total_primary_energy']:,.2f} kWh oil-eq\n".replace(',', 'X').replace('.', ',').replace('X', '`')
    report += f"Total UBP: {summary['total_ubp']:,.2f}\n".replace(',', 'X').replace('.', ',').replace('X', '`')

    if summary['failed_components']:
        report += "\nFailed Components:\n"
        for component in summary['failed_components']:
            report += f"- GUID: {component.get('guid', 'N/A')}, eBKP-H: {component.get('ebkp_h', 'N/A')}, Error: {component.get('error', 'N/A')}\n"

    return report

def save_report(report, output_file):
    logging.info(f"Saving report to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(report)
    logging.info(f"Report saved to {output_file}")

if __name__ == "__main__":
    # Define paths to input and output files
    combined_results_file = "NHMzh-modules/data/output/combined_results.json"
    output_report_file = "NHMzh-modules/data/output/summary_report.txt"

    # Load combined data
    combined_data = load_json_data(combined_results_file)

    # Generate summary
    summary = summarize_results(combined_data)

    # Create report
    report = generate_report(summary)

    # Save the report to a file
    save_report(report, output_report_file)

    logging.info("Report generation completed successfully.")
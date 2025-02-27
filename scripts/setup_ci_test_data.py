#!/usr/bin/env python3
"""
Script to set up test data for CI/CD pipeline.
This script creates sample data files needed for testing.
"""

import os
import pandas as pd
import json
from pathlib import Path

# Create necessary directories
def create_directories():
    """Create necessary directories for test data"""
    directories = [
        "tests/data/input",
        "tests/data/output"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

# Create sample amortization periods file
def create_amortization_periods():
    """Create sample amortization periods CSV file"""
    data = {
        'element_type': ['Wall', 'Floor', 'Roof', 'Window', 'Door'],
        'amortization_period': [50, 60, 30, 25, 30]
    }
    
    df = pd.DataFrame(data)
    output_path = "tests/data/input/amortization_periods.csv"
    df.to_csv(output_path, index=False)
    print(f"Created sample amortization periods file: {output_path}")

# Create sample KBOB data file
def create_kbob_data():
    """Create sample KBOB data CSV file"""
    data = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Concrete', 'Steel', 'Wood', 'Glass', 'Aluminum'],
        'category': ['Structure', 'Structure', 'Finish', 'Openings', 'Openings'],
        'gwp_total': [250.5, 1800.2, 30.5, 800.1, 1500.3],
        'unit': ['m3', 'kg', 'm3', 'm2', 'kg'],
        'density': [2400, 7850, 500, 2500, 2700],
        'cost_per_unit': [120, 2.5, 800, 150, 5.8]
    }
    
    df = pd.DataFrame(data)
    output_path = "tests/data/input/KBOB.csv"
    df.to_csv(output_path, index=False)
    print(f"Created sample KBOB data file: {output_path}")

# Create sample Cost DB file
def create_cost_db():
    """Create sample Cost DB CSV file"""
    data = {
        'id': [1, 2, 3, 4, 5],
        'element_type': ['Wall', 'Floor', 'Roof', 'Window', 'Door'],
        'material': ['Concrete', 'Concrete', 'Wood', 'Glass', 'Wood'],
        'cost_per_unit': [150, 180, 250, 300, 200],
        'unit': ['m2', 'm2', 'm2', 'm2', 'piece']
    }
    
    df = pd.DataFrame(data)
    output_path = "tests/data/input/CostDB.csv"
    df.to_csv(output_path, index=False)
    print(f"Created sample Cost DB file: {output_path}")

# Create sample IFC processing result
def create_sample_ifc_result():
    """Create sample IFC processing result JSON file"""
    data = {
        "project_info": {
            "name": "Test Project",
            "description": "A test project for CI/CD",
            "id": "TEST-001"
        },
        "building_elements": [
            {
                "id": "wall-001",
                "type": "Wall",
                "material": "Concrete",
                "volume": 12.5,
                "area": 50.0,
                "length": 10.0,
                "height": 5.0,
                "thickness": 0.25
            },
            {
                "id": "floor-001",
                "type": "Floor",
                "material": "Concrete",
                "volume": 30.0,
                "area": 100.0,
                "thickness": 0.3
            },
            {
                "id": "window-001",
                "type": "Window",
                "material": "Glass",
                "area": 4.0,
                "width": 2.0,
                "height": 2.0
            }
        ]
    }
    
    output_path = "tests/data/input/sample_ifc_result.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Created sample IFC processing result file: {output_path}")

if __name__ == "__main__":
    print("Setting up test data for CI/CD pipeline...")
    create_directories()
    create_amortization_periods()
    create_kbob_data()
    create_cost_db()
    create_sample_ifc_result()
    print("Test data setup complete!") 
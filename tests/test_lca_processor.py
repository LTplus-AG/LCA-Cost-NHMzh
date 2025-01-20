import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import json
import pandas as pd
import time
import logging

from modules.lca_processor import LCAProcessor
from modules.storage.db_manager import DatabaseManager

@pytest.fixture
def test_data_dir():
    return Path(__file__).parent / "data"

@pytest.fixture
def input_dir(test_data_dir):
    input_path = test_data_dir / "input"
    input_path.mkdir(parents=True, exist_ok=True)
    return input_path

@pytest.fixture
def output_dir(test_data_dir):
    output_path = test_data_dir / "output"
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path

@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary database for testing"""
    return str(tmp_path / "test.duckdb")

@pytest.fixture
def db_manager(test_db_path, kbob_data):
    """Initialize database with test KBOB data"""
    # Save KBOB data to temporary CSV
    kbob_file = Path(test_db_path).parent / "test_kbob.csv"
    kbob_data.to_csv(kbob_file, index=True, encoding='ISO-8859-1')
    
    # Initialize database and import data
    with DatabaseManager(test_db_path) as db:
        db.import_kbob_data(
            csv_path=str(kbob_file),
            version="2024-6.2",
            description="Test KBOB data"
        )
        db.set_active_kbob_version("2024-6.2")
        yield db
    
    # Cleanup with retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
            if os.path.exists(kbob_file):
                os.remove(kbob_file)
            break
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.1)  # Wait 100ms before retrying
            else:
                pass  # If we still can't delete after retries, let the OS handle it later

@pytest.fixture
def life_expectancy_data(db_manager):
    """Initialize life expectancy data in the database"""
    data = [
        {"ebkp_code": "C", "years": 50},
        {"ebkp_code": "D", "years": 30},
        {"ebkp_code": "E", "years": 25},
        {"ebkp_code": "G", "years": 40},
        {"ebkp_code": "I", "years": 35}
    ]
    db_manager.init_life_expectancy_data(data)
    return data

@pytest.fixture
def material_mappings_file(input_dir):
    """Create a test material mappings file"""
    web_lca_dir = input_dir / "web-lca"
    web_lca_dir.mkdir(parents=True, exist_ok=True)
    file_path = web_lca_dir / "juch_p31_20241221_050139.json"
    
    mappings = [
        {
            "ifc_material": "Beton",
            "kbob_id": "E13EE05E-FD34-4FB5-A178-0FC4164A96F2"  # Hochbaubeton
        },
        {
            "ifc_material": "Wärmedämmung",
            "kbob_id": "43B03F61-91A1-438E-B958-6E274F13B241"  # Glaswolle
        }
    ]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2)
    
    return file_path

@pytest.fixture
def output_file(output_dir):
    return output_dir / "test_lca_output.json"

@pytest.fixture
def input_elements():
    """Create test input data matching the actual IFC element structure"""
    return {
        "elements": [
            {
                "id": "test_beam_1",
                "ifc_class": "IfcBeam",
                "object_type": "Beam-1",
                "properties": {
                    "loadBearing": True,
                    "isExternal": False,
                    "ebkp": "C"
                },
                "quantities": {
                    "volume": {
                        "net": 3.684,
                        "gross": 3.684
                    }
                },
                "materials": [
                    "Beton"
                ],
                "material_volumes": {
                    "Beton": {
                        "fraction": 1.0,
                        "volume": 3.684,
                        "width": 300,
                        "density": 2300.0
                    }
                }
            },
            {
                "id": "test_wall_1",
                "ifc_class": "IfcWall",
                "object_type": "Wall-1",
                "properties": {
                    "loadBearing": True,
                    "isExternal": True,
                    "ebkp": "D"
                },
                "quantities": {
                    "volume": {
                        "net": 86.392,
                        "gross": 86.392
                    }
                },
                "materials": [
                    "Wärmedämmung"
                ],
                "material_volumes": {
                    "Wärmedämmung": {
                        "fraction": 1.0,
                        "volume": 86.392,
                        "width": 200,
                        "density": 30.0
                    }
                }
            }
        ],
        "metadata": {
            "total_elements": 2,
            "total_pages": 1,
            "current_page": 1,
            "page_size": 10,
            "units": {
                "length": "METRE",
                "area": "METRE²",
                "volume": "METRE³"
            }
        }
    }

@pytest.fixture
def kbob_data():
    """Mock KBOB data with test values"""
    return pd.DataFrame({
        "UUID-Nummer": [
            "B0C749DA-292B-417D-8E38-65766E052FBC",  # Gussasphalt
            "43B03F61-91A1-438E-B958-6E274F13B241",  # Glaswolle
            "E13EE05E-FD34-4FB5-A178-0FC4164A96F2",  # Hochbaubeton
        ],
        "Treibhausgasemissionen, Total [kg CO2-eq]": [5785.45, 340.615, 232.3],
        "Primaerenergie nicht erneuerbar, Total [kWh oil-eq]": [26690.0, 1633.5, 402.5],
        "UBP (Total)": [10126500.0, 623150.0, 351900.0],
        "Rohdichte/ Flaechenmasse": [2400.0, 30.0, 2300.0],
        "BAUMATERIALIEN": [
            "Gussasphalt, 27.5 mm",
            "Glaswolle",
            "Hochbaubeton (ohne Bewehrung)"
        ]
    }).set_index("UUID-Nummer")

def test_lca_processor_run(input_elements, test_db_path, db_manager, output_file, life_expectancy_data, material_mappings_file):
    # Create a temporary input file with the test data
    input_file = output_file.parent / "test_input.json"
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(input_elements, f)
    
    # Initialize and run processor
    processor = LCAProcessor(
        input_file_path=str(input_file),
        material_mappings_file=str(material_mappings_file),
        db_path=test_db_path,
        output_file=str(output_file)
    )
    processor.run()
    
    # Verify output file exists
    assert output_file.exists()
    
    # Load and verify results
    with open(output_file) as f:
        results = json.load(f)
    
    # Verify results structure
    assert isinstance(results, list)
    for item in results:
        assert "guid" in item
        assert "components" in item
        assert "shared_guid" in item
        
        # Verify components structure
        for component in item["components"]:
            if not component.get("failed", False):
                assert "guid" in component
                assert "material" in component
                assert "mat_kbob" in component
                assert "kbob_material_name" in component
                assert "volume" in component
                assert "density" in component
                assert "amortization" in component
                assert "ebkp_h" in component
                assert "gwp_absolute" in component
                assert "gwp_relative" in component
                assert "penr_absolute" in component
                assert "penr_relative" in component
                assert "ubp_absolute" in component
                assert "ubp_relative" in component
                
                # Verify density is not zero
                assert component["density"] > 0
            else:
                assert "error" in component

def test_lca_processor_with_invalid_data(input_elements, test_db_path, db_manager, output_file, life_expectancy_data, material_mappings_file):
    # Add an invalid element
    input_elements["elements"].append({
        "id": "test_invalid_guid",
        "ifc_class": "IfcBeam",
        "object_type": "Invalid-1",
        "properties": {
            "loadBearing": True,
            "isExternal": False,
            "ebkp": "Z"
        },
        "quantities": {
            "volume": {
                "net": -1.0,
                "gross": -1.0
            }
        },
        "materials": [
            "NonexistentMaterial"
        ],
        "material_volumes": {
            "NonexistentMaterial": {
                "fraction": 1.0,
                "volume": -1.0,
                "width": 100
            }
        }
    })
    
    input_file = output_file.parent / "test_input_invalid.json"
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(input_elements, f)
    
    processor = LCAProcessor(
        input_file_path=str(input_file),
        material_mappings_file=str(material_mappings_file),
        db_path=test_db_path,
        output_file=str(output_file)
    )
    processor.run()
    
    # Verify output file exists
    assert output_file.exists()
    
    # Load and verify results contain error handling
    with open(output_file) as f:
        results = json.load(f)
    
    # Find the test component
    test_component = None
    for item in results:
        if item["guid"] == "test_invalid_guid":
            test_component = item
            break
    
    assert test_component is not None
    assert any(comp.get("failed", False) for comp in test_component["components"])

def test_lca_processor_file_handling(tmp_path, test_db_path, db_manager, life_expectancy_data, material_mappings_file):
    # Test with nonexistent input file
    logger = logging.getLogger()
    previous_level = logger.getEffectiveLevel()
    logger.setLevel(logging.CRITICAL)  # Temporarily disable lower-level logging
    
    try:
        with pytest.raises(FileNotFoundError):
            processor = LCAProcessor(
                input_file_path=str(tmp_path / "nonexistent.json"),
                material_mappings_file=str(material_mappings_file),
                db_path=test_db_path,
                output_file=str(tmp_path / "output.json")
            )
            processor.run()
    finally:
        logger.setLevel(previous_level)  # Restore previous logging level
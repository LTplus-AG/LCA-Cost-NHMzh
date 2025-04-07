# eBKP Classifier for IFC Files

This script processes IFC files to extract eBKP properties from property sets and creates proper IFC classifications based on these values.

## Overview

The script performs the following operations:

1. Opens an IFC file
2. Searches for properties named "eBKP" in all property sets
3. Normalizes the eBKP codes to a standard format
4. Looks up descriptions for these codes in the ebkp.md file
5. Creates proper IFC classifications with the normalized codes and descriptions
6. Saves the modified IFC file with a "\_classified" suffix

## Requirements

- Python 3.6 or higher
- ifcopenshell library

## Installation

1. Make sure you have Python installed
2. Install ifcopenshell:
   ```
   pip install ifcopenshell
   ```

## Usage

### Command Line

Run the script from the command line:

```
python ebkp_classifier.py path/to/your/file.ifc path/to/ebkp.md
```

### Interactive Mode

If you run the script without arguments, it will prompt you for the file paths:

```
python ebkp_classifier.py
```

## Input Files

- **IFC File**: The IFC file containing elements with eBKP properties
- **ebkp.md**: A markdown file containing eBKP codes and their descriptions in the format:
  ```
  B 1.1 Baugrunduntersuchung
  B 1.2 Bestandsaufnahme
  ...
  ```

## Output

The script creates a new IFC file with the suffix "\_classified" containing the added classifications. The original file is not modified.

## Example

```
python ebkp_classifier.py model.ifc ebkp.md
```

This will process `model.ifc` and create a new file called `model_classified.ifc` with the added classifications.

## Troubleshooting

- If you encounter errors related to ifcopenshell, make sure it's properly installed
- If the script doesn't find any eBKP properties, check that your IFC file contains property sets with properties named "eBKP"
- If classifications aren't being created, verify that the eBKP codes in your IFC file match the format in the ebkp.md file

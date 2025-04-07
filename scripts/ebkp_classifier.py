import ifcopenshell
import ifcopenshell.api
import os
import re
import sys

def load_ebkp_descriptions(ebkp_file_path):
    """
    Load eBKP codes and their descriptions from the ebkp.md file
    Returns a dictionary mapping eBKP codes to their descriptions
    """
    ebkp_dict = {}
    
    with open(ebkp_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
                
            # Match pattern like "B 1.1 Baugrunduntersuchung"
            match = re.match(r'([A-Z])\s+(\d+(?:\.\d+)?)\s+(.*)', line)
            if match:
                letter, number, description = match.groups()
                # Store both normalized and original format
                code = f"{letter}{number}"  # Remove space between letter and number
                normalized_code = normalize_ebkp_code(code)
                ebkp_dict[normalized_code] = description
                
    return ebkp_dict

def normalize_ebkp_code(code):
    """
    Normalize eBKP code to standard format by:
    1. Removing spaces
    2. Removing leading zeros in numbers
    3. Ensuring consistent format
    
    Examples:
    "B 1.1" -> "B1.1"
    "C02.01" -> "C2.1"
    "C 02.01" -> "C2.1"
    """
    # Remove spaces
    code = code.replace(" ", "")
    
    # Extract the letter and numbers with potential leading zeros
    match = re.match(r'([A-Z])(\d+)(?:\.(\d+))?', code)
    if match:
        letter, main, sub = match.groups()
        
        # Remove leading zeros by converting to int and back to string
        main_num = str(int(main))
        sub_num = str(int(sub)) if sub else None
        
        # Reconstruct the code
        if sub_num:
            return f"{letter}{main_num}.{sub_num}"
        else:
            return f"{letter}{main_num}"
            
    return code

def process_ifc_file(ifc_file_path, ebkp_file_path):
    """
    Process an IFC file to extract eBKP properties and create classifications
    """
    print(f"Processing file: {os.path.basename(ifc_file_path)}")
    
    # Load eBKP descriptions
    ebkp_descriptions = load_ebkp_descriptions(ebkp_file_path)
    print(f"Loaded {len(ebkp_descriptions)} eBKP codes with descriptions")
    
    # Open the IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Create output path by adding "_classified" before the extension
    file_name, file_ext = os.path.splitext(ifc_file_path)
    output_path = f"{file_name}_classified{file_ext}"
    
    # Create a classification system for eBKP
    classification = ifcopenshell.api.run("classification.add_classification", 
        ifc_file, classification="eBKP"
    )
    
    # Track statistics
    elements_processed = 0
    elements_with_ebkp = 0
    elements_with_match = 0
    
    # Iterate through all elements in the IFC file
    for element in ifc_file.by_type("IfcElement"):
        elements_processed += 1
        
        # Check if the element has property sets
        if hasattr(element, "IsDefinedBy"):
            ebkp_value = None
            
            # Look for eBKP property in all property sets
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    
                    # Check if it's a property set
                    if pset.is_a("IfcPropertySet") and hasattr(pset, "HasProperties"):
                        for prop in pset.HasProperties:
                            # Look for property named "eBKP" (case-insensitive)
                            if prop.Name.lower() == "ebkp":
                                if hasattr(prop, "NominalValue") and prop.NominalValue:
                                    ebkp_value = prop.NominalValue.wrappedValue
                                break
                
                if ebkp_value is not None:
                    break
            
            # If eBKP property was found, create a classification reference
            if ebkp_value is not None and ebkp_value.strip():
                elements_with_ebkp += 1
                
                # Normalize the eBKP code
                normalized_code = normalize_ebkp_code(ebkp_value)
                
                # Get description from the mapping if available
                description = ebkp_descriptions.get(normalized_code, ebkp_value)
                
                if normalized_code in ebkp_descriptions:
                    elements_with_match += 1
                
                # Add classification reference and assign it to the product
                reference = ifcopenshell.api.run("classification.add_reference",
                    ifc_file,
                    products=[element],
                    identification=normalized_code,
                    name=description,
                    classification=classification
                )
                
                print(f"Added classification for element {element.GlobalId}: {normalized_code} -> {description}")
    
    # Save the modified file
    ifc_file.write(output_path)
    
    print(f"Processed {elements_processed} elements, found {elements_with_ebkp} with eBKP property")
    print(f"Successfully matched {elements_with_match} eBKP codes with descriptions")
    print(f"Modified file saved to: {output_path}")
    
    return output_path

if __name__ == "__main__":
    # Check if file paths were provided as command-line arguments
    if len(sys.argv) > 2:
        ifc_file_path = sys.argv[1]
        ebkp_file_path = sys.argv[2]
        process_ifc_file(ifc_file_path, ebkp_file_path)
    else:
        # Prompt for file paths if not provided
        ifc_file_path = input("Enter the path to your IFC file: ")
        ebkp_file_path = input("Enter the path to your ebkp.md file: ")
        process_ifc_file(ifc_file_path, ebkp_file_path) 
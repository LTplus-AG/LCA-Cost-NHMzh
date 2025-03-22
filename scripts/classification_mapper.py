import ifcopenshell
import ifcopenshell.guid
import os
import ifcopenshell.api
import re
import sys

# Function to normalize EBKP codes to a standard format
def normalize_ebkp_code(code):
    # Remove spaces first
    code = code.replace(" ", "")
    
    # Extract the letter and numbers
    match = re.match(r'([A-Z])(\d+)(?:\.(\d+))?(?:\.(\d+))?', code)
    if match:
        letter, main, sub1, sub2 = match.groups()
        
        # Remove leading zeros
        if main:
            main = str(int(main))
        if sub1:
            sub1 = str(int(sub1))
        if sub2:
            sub2 = str(int(sub2))
            
        # Reconstruct the code without leading zeros
        if sub1 and sub2:
            return f"{letter}{main}.{sub1}.{sub2}"
        elif sub1:
            return f"{letter}{main}.{sub1}"
        else:
            return f"{letter}{main}"
    return code

def process_ifc_file(ifc_file_path):
    """Process an IFC file to add EBKP classifications"""
    print(f"Processing file: {os.path.basename(ifc_file_path)}")
    
    # Open the IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Create output path by adding "_modified" before the extension
    file_name, file_ext = os.path.splitext(ifc_file_path)
    output_path = f"{file_name}_modified{file_ext}"
    
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Use relative path for ebkp.md
    ebkp_md_path = os.path.join(script_dir, "ebkp.md")
    
    # Load EBKP code to description mapping from ebkp.md file
    ebkp_descriptions = {}
    with open(ebkp_md_path, 'r', encoding='utf-8') as md_file:
        for line in md_file:
            line = line.strip()
            if not line:
                continue
            
            # Match lines like "B 6.1 Abholzung, Rodung"
            match = re.match(r'([A-Z])\s+(\d+(?:\.\d+)?)\s+(.*)', line)
            if match:
                section, number, description = match.groups()
                raw_code = f"{section} {number}"
                # Normalize the code to standard format
                normalized_code = normalize_ebkp_code(raw_code)
                ebkp_descriptions[normalized_code] = description
    
    print(f"Loaded {len(ebkp_descriptions)} EBKP codes with descriptions")
    # Debug: Print some examples of loaded codes to verify format
    if ebkp_descriptions:
        print("Examples of loaded EBKP codes:")
        sample = list(ebkp_descriptions.items())[:5]
        for code, desc in sample:
            print(f"  {code} -> {desc}")
    else:
        print("WARNING: No EBKP codes were loaded from the MD file")
    
    # Show a specific example for matching debugging
    test_codes = ["E3.1", "E03.01", "E3", "E 3.1", "E 03.01"]
    print("\nFormat normalization test:")
    for test in test_codes:
        normalized = normalize_ebkp_code(test)
        matches = normalized in ebkp_descriptions
        desc = ebkp_descriptions.get(normalized, "No match")
        print(f"  {test} -> normalized: {normalized} -> matches: {matches} -> {desc}")
    
    # Add the classification system to the project
    classification = ifcopenshell.api.run("classification.add_classification", 
        ifc_file, classification="EBKP"
    )
    print(f"Added classification system: {classification.Name}")
    
    # First, gather all available EBKP values for debugging
    found_ebkp_values = []
    for element in ifc_file.by_type("IfcElement"):
        if hasattr(element, "IsDefinedBy"):
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset.is_a("IfcPropertySet") and hasattr(pset, "HasProperties"):
                        for prop in pset.HasProperties:
                            if prop.Name.lower() == "ebkp":
                                if hasattr(prop, "NominalValue") and prop.NominalValue:
                                    found_ebkp_values.append(prop.NominalValue.wrappedValue)
    
    if found_ebkp_values:
        print(f"Found {len(found_ebkp_values)} elements with EBKP values")
        print("Examples of EBKP values from the IFC file:")
        unique_values = list(set(found_ebkp_values))
        for val in unique_values[:10]:  # Show up to 10 unique values
            normalized = normalize_ebkp_code(val)
            print(f"  {val} -> normalized: {normalized} -> in dictionary: {normalized in ebkp_descriptions}")
    else:
        print("WARNING: No elements with EBKP property found in the IFC file")
    
    # Iterate over all IfcElement instances in the file
    elements_processed = 0
    elements_with_ebkp = 0
    elements_with_match = 0
    
    for element in ifc_file.by_type("IfcElement"):
        found_value = None
        # Check for property sets linked via IfcRelDefinesByProperties
        if hasattr(element, "IsDefinedBy"):
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    # Ensure the property definition is a property set
                    if pset.is_a("IfcPropertySet") and hasattr(pset, "HasProperties"):
                        for prop in pset.HasProperties:
                            # Look for property named "ebkp" (case-insensitive)
                            if prop.Name.lower() == "ebkp":
                                # Extract the value if available; otherwise use empty string
                                if hasattr(prop, "NominalValue") and prop.NominalValue:
                                    found_value = prop.NominalValue.wrappedValue
                                else:
                                    found_value = ""
                                break
                if found_value is not None:
                    break
        
        elements_processed += 1
        
        # If the property "ebkp" was found, create a classification reference
        if found_value is not None and found_value.strip():
            elements_with_ebkp += 1
            
            # Get description from the mapping if available, otherwise use the code itself
            original_code = found_value
            
            # Normalize the code format
            normalized_code = normalize_ebkp_code(original_code)
            
            # Try exact match first with normalized code
            description = ebkp_descriptions.get(normalized_code)
            
            # Debug: If exact match failed, try parent codes
            if description is None:
                print(f"DEBUG: No exact match for {original_code} (normalized: {normalized_code})")
                
                # Try parent codes by removing parts after the last decimal
                code_parts = normalized_code.split(".")
                if len(code_parts) > 1:
                    parent_code = ".".join(code_parts[:-1])
                    print(f"DEBUG: Trying parent code: {parent_code}")
                    description = ebkp_descriptions.get(parent_code)
                    if description:
                        print(f"DEBUG: Found match with parent code: {parent_code} -> {description}")
                
                # If still no match, try just the main code (letter + first number)
                if description is None and len(code_parts[0]) >= 2:
                    main_code = code_parts[0][0] + re.match(r'([A-Z])(\d+)', code_parts[0]).group(2)
                    print(f"DEBUG: Trying main code: {main_code}")
                    description = ebkp_descriptions.get(main_code)
                    if description:
                        print(f"DEBUG: Found match with main code: {main_code} -> {description}")
            
                # If still not found, use the original code as description
                if description is None:
                    print(f"DEBUG: No match found for {original_code} after all attempts")
                    description = original_code
            else:
                elements_with_match += 1
                print(f"DEBUG: Found exact match for {original_code} -> {description}")
            
            # Add classification reference and assign it to the product in one step
            reference = ifcopenshell.api.run("classification.add_reference",
                ifc_file,
                products=[element],
                identification=found_value,
                name=description,
                classification=classification
            )
            
            print(f"Processed element {element.GlobalId} with EBKP code: {found_value} -> {description}")
    
    print(f"Processed {elements_processed} elements, found {elements_with_ebkp} with EBKP property")
    print(f"Successfully matched {elements_with_match} EBKP codes with descriptions")
    # Save the modified file
    ifc_file.write(output_path)
    print(f"Modified file saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    # Check if file path was provided as command-line argument
    if len(sys.argv) > 1:
        ifc_file_path = sys.argv[1]
        process_ifc_file(ifc_file_path)
    else:
        # Prompt for file path if not provided
        ifc_file_path = input("Enter the path to your IFC file: ")
        process_ifc_file(ifc_file_path)

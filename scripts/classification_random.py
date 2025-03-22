import ifcopenshell
import ifcopenshell.api
import re
import random
import os
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

# Load EBKP codes from ebkp.md file
def load_ebkp_codes(md_file_path, filter_letter='C'):
    ebkp_codes = {}
    with open(md_file_path, 'r', encoding='utf-8') as md_file:
        for line in md_file:
            line = line.strip()
            if not line:
                continue
            
            # Match lines like "B 6.1 Abholzung, Rodung"
            match = re.match(r'([A-Z])\s+(\d+(?:\.\d+)?)\s+(.*)', line)
            if match:
                section, number, description = match.groups()
                
                # Only include codes that start with the specified letter
                if section == filter_letter:
                    raw_code = f"{section} {number}"
                    normalized_code = normalize_ebkp_code(raw_code)
                    ebkp_codes[normalized_code] = description
    
    return ebkp_codes

def verify_classification(element, reference, schema_version):
    """Verify that a classification reference was created correctly with appropriate attributes"""
    if not reference:
        return False
    
    if "2X3" in schema_version:
        # In IFC2X3, we use ItemReference and Name
        has_id = hasattr(reference, "ItemReference") and reference.ItemReference
        has_name = hasattr(reference, "Name") and reference.Name
        
        if not has_id or not has_name:
            print(f"Warning: Classification reference for {element.is_a()}:{element.GlobalId} is incomplete")
            print(f"  - ItemReference: {'Present' if has_id else 'MISSING'}")
            print(f"  - Name: {'Present' if has_name else 'MISSING'}")
            return False
    else:
        # In IFC4, we use Identification and Name
        has_id = hasattr(reference, "Identification") and reference.Identification
        has_name = hasattr(reference, "Name") and reference.Name
        
        if not has_id or not has_name:
            print(f"Warning: Classification reference for {element.is_a()}:{element.GlobalId} is incomplete")
            print(f"  - Identification: {'Present' if has_id else 'MISSING'}")
            print(f"  - Name: {'Present' if has_name else 'MISSING'}")
            return False
    
    return True

# Assign random EBKP codes to elements
def assign_random_ebkp_codes(ifc_file_path, output_path=None, filter_letter='C'):
    """Assign random EBKP codes to elements in an IFC file"""
    print(f"Processing file: {os.path.basename(ifc_file_path)}")
    
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Use relative path for ebkp.md
    ebkp_md_path = os.path.join(script_dir, "ebkp.md")
    
    # Create default output path if not provided
    if output_path is None:
        file_name, file_ext = os.path.splitext(ifc_file_path)
        output_path = f"{file_name}_random_{filter_letter}_ebkp{file_ext}"
    
    # Load EBKP codes (only those starting with the specified letter)
    ebkp_codes = load_ebkp_codes(ebkp_md_path, filter_letter)
    valid_codes = list(ebkp_codes.keys())
    
    if not valid_codes:
        print(f"Error: No valid EBKP codes found in the MD file starting with '{filter_letter}'")
        return None
    
    print(f"Loaded {len(valid_codes)} valid EBKP '{filter_letter}' codes")
    print("Examples: " + ", ".join(valid_codes[:5]))
    
    # Open the IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)
    schema_version = ifc_file.schema
    print(f"File schema version: {schema_version}")
    
    # Add the classification system
    classification = ifcopenshell.api.run("classification.add_classification", 
        ifc_file, classification="EBKP"
    )
    print(f"Added classification system: {classification.Name}")
    
    # Get all elements that can be classified
    elements = ifc_file.by_type("IfcElement")
    print(f"Found {len(elements)} elements to classify")
    
    # Assign random EBKP codes to elements
    classified_count = 0
    successful_count = 0
    for element in elements:
        # Choose a random EBKP code starting with the specified letter
        ebkp_code = random.choice(valid_codes)
        description = ebkp_codes[ebkp_code]
        
        # Create a classification reference first, then associate it with the element
        try:
            # Handle different schema versions
            if "2X3" in schema_version:
                # In IFC2X3, use ItemReference instead of Identification
                reference = ifc_file.create_entity(
                    "IfcClassificationReference",
                    ItemReference=ebkp_code,  # Use ItemReference in IFC2X3
                    Name=description,
                    ReferencedSource=classification
                )
            else:
                # In IFC4, use Identification
                reference = ifc_file.create_entity(
                    "IfcClassificationReference",
                    Identification=ebkp_code,
                    Name=description,
                    ReferencedSource=classification
                )
            
            # Now create the association
            association = ifc_file.create_entity(
                "IfcRelAssociatesClassification",
                GlobalId=ifcopenshell.guid.new(),
                RelatedObjects=[element],
                RelatingClassification=reference
            )
            
            if verify_classification(element, reference, schema_version):
                successful_count += 1
            
            classified_count += 1
            if classified_count % 100 == 0:
                print(f"Classified {classified_count} elements so far...")
                
        except Exception as e:
            print(f"Error classifying element {element.GlobalId}: {e}")
    
    # Save the modified file
    ifc_file.write(output_path)
    print(f"Successfully classified {successful_count} of {classified_count} elements with '{filter_letter}' codes")
    print(f"Modified file saved to: {output_path}")
    return output_path

# Main execution
if __name__ == "__main__":
    # Check if file path was provided as command-line argument
    if len(sys.argv) > 1:
        ifc_file_path = sys.argv[1]
        # Check if a specific letter was provided
        filter_letter = 'C'  # Default to 'C'
        if len(sys.argv) > 2:
            filter_letter = sys.argv[2].upper()
        assign_random_ebkp_codes(ifc_file_path, filter_letter=filter_letter)
    else:
        # Prompt for file path if not provided
        ifc_file_path = input("Enter the path to your IFC file: ")
        filter_letter = input("Enter the EBKP letter to filter by (default: C): ").upper() or 'C'
        assign_random_ebkp_codes(ifc_file_path, filter_letter=filter_letter)
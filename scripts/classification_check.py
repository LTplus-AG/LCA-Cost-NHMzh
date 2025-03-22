import ifcopenshell
import os
import sys

def check_classification_completeness(ifc_file_path):
    """Check all IfcElements for incomplete classification references"""
    print(f"Checking file: {os.path.basename(ifc_file_path)}")
    
    # Open the IFC file
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
        schema_version = ifc_file.schema
        print(f"File schema version: {schema_version}")
    except Exception as e:
        print(f"Error opening IFC file: {e}")
        return
    
    print(f"File contains {len(ifc_file.by_type('IfcElement'))} elements")
    
    # Track statistics
    elements_with_classification = 0
    elements_with_incomplete_classification = 0
    
    # Check all IfcElements
    for element in ifc_file.by_type("IfcElement"):
        element_has_classification = False
        element_has_incomplete_classification = False
        
        # Skip reporting elements with no classifications
        if not hasattr(element, "HasAssociations"):
            continue
            
        # Check all associations for classification references
        for association in element.HasAssociations:
            if association.is_a("IfcRelAssociatesClassification"):
                element_has_classification = True
                relating_classification = association.RelatingClassification
                
                # Check if the classification reference has a name and identification
                if relating_classification.is_a("IfcClassificationReference"):
                    # Handle different schemas
                    if "2X3" in schema_version:
                        name_missing = not hasattr(relating_classification, "Name") or not relating_classification.Name
                        id_missing = not hasattr(relating_classification, "ItemReference") or not relating_classification.ItemReference
                        id_attr = "ItemReference"
                    else:
                        name_missing = not hasattr(relating_classification, "Name") or not relating_classification.Name
                        id_missing = not hasattr(relating_classification, "Identification") or not relating_classification.Identification
                        id_attr = "Identification"
                    
                    if name_missing or id_missing:
                        element_has_incomplete_classification = True
                        
                        # Print information about the element and incomplete classification
                        element_name = element.Name if hasattr(element, "Name") and element.Name else "Unnamed"
                        element_type = element.is_a()
                        
                        print(f"\nINCOMPLETE CLASSIFICATION FOUND:")
                        print(f"  Element: {element_name} (Type: {element_type}, GlobalId: {element.GlobalId})")
                        print(f"  Classification System: {relating_classification.ReferencedSource.Name if hasattr(relating_classification, 'ReferencedSource') and relating_classification.ReferencedSource else 'Unknown'}")
                        print(f"  Issues:")
                        if name_missing:
                            print(f"    - Missing Name (Description)")
                        if id_missing:
                            print(f"    - Missing {id_attr} (Code)")
                        print(f"  Values:")
                        print(f"    - Name: {relating_classification.Name if hasattr(relating_classification, 'Name') else 'MISSING'}")
                        print(f"    - {id_attr}: {getattr(relating_classification, id_attr) if hasattr(relating_classification, id_attr) else 'MISSING'}")
        
        if element_has_classification:
            elements_with_classification += 1
        if element_has_incomplete_classification:
            elements_with_incomplete_classification += 1
    
    # Print summary statistics
    print("\nSUMMARY:")
    print(f"  Total elements: {len(ifc_file.by_type('IfcElement'))}")
    print(f"  Elements with classifications: {elements_with_classification}")
    print(f"  Elements with incomplete classifications: {elements_with_incomplete_classification}")
    if elements_with_classification > 0:
        percentage = (elements_with_incomplete_classification / elements_with_classification) * 100
        print(f"  Percentage incomplete: {percentage:.2f}%")

if __name__ == "__main__":
    # Check if a file path was provided as an argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        check_classification_completeness(file_path)
    else:
        # Default file path if none provided
        file_path = input("Enter the path to your IFC file: ")
        check_classification_completeness(file_path)
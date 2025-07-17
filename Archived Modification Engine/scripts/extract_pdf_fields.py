#!/usr/bin/env python3
"""
Extract actual field names from PDF
"""
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyPDFForm import PdfWrapper

def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_pdf_fields.py <pdf_file>")
        sys.exit(1)
    
    pdf_file = Path(sys.argv[1])
    
    if not pdf_file.exists():
        print(f"Error: PDF file not found: {pdf_file}")
        sys.exit(1)
    
    # Load PDF
    pdf = PdfWrapper(str(pdf_file))
    
    # Get field names and info
    field_names = list(pdf.widgets.keys())
    
    print(f"PDF: {pdf_file}")
    print(f"Total fields: {len(field_names)}")
    print()
    
    # Print all field names
    print("Field names:")
    for i, name in enumerate(sorted(field_names), 1):
        print(f"{i:2d}. {name}")
    
    # Save to JSON
    output_file = pdf_file.with_suffix('.fields.json')
    field_data = {
        "pdf_file": str(pdf_file),
        "total_fields": len(field_names),
        "field_names": sorted(field_names)
    }
    
    with open(output_file, 'w') as f:
        json.dump(field_data, f, indent=2)
    
    print(f"\nField names saved to: {output_file}")

if __name__ == "__main__":
    main()
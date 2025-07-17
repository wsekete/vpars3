#!/usr/bin/env python3
"""
Apply BEM field mappings to PDF form
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.pdf_enrichment.pdf_modifier import PDFModifier
from src.pdf_enrichment.utils import setup_logging

async def main():
    # Setup logging
    setup_logging(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Parse arguments
    if len(sys.argv) != 3:
        print("Usage: python apply_bem_mappings.py <mapping_json_file> <pdf_file>")
        sys.exit(1)
    
    mapping_file = Path(sys.argv[1])
    pdf_file = Path(sys.argv[2])
    
    # Validate files exist
    if not mapping_file.exists():
        print(f"Error: Mapping file not found: {mapping_file}")
        sys.exit(1)
    
    if not pdf_file.exists():
        print(f"Error: PDF file not found: {pdf_file}")
        sys.exit(1)
    
    # Load mapping data
    logger.info(f"Loading BEM mappings from: {mapping_file}")
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)
    
    # Extract field mappings
    field_mappings = mapping_data.get('bem_mappings', {})
    
    if not field_mappings:
        print("Error: No BEM mappings found in JSON file")
        sys.exit(1)
    
    logger.info(f"Found {len(field_mappings)} field mappings")
    
    # Create output filename
    output_file = pdf_file.with_stem(f"{pdf_file.stem}_BEM_renamed")
    
    # Create PDF modifier
    modifier = PDFModifier()
    
    # Generate field detection report before modification
    logger.info("Generating field detection report...")
    detection_report = modifier.generate_field_detection_report(pdf_file)
    
    # Save detection report
    detection_report_file = pdf_file.with_suffix('.detection_report.md')
    with open(detection_report_file, 'w') as f:
        f.write(detection_report)
    logger.info(f"Field detection report saved to: {detection_report_file}")
    
    # Apply modifications
    logger.info(f"Applying BEM mappings to: {pdf_file}")
    logger.info(f"Output file: {output_file}")
    
    result = await modifier.modify_fields(
        pdf_path=pdf_file,
        field_mappings=field_mappings,
        output_path=output_file,
        preserve_original=True,
        validate_mappings=True,
        create_backup=False
    )
    
    # Get detection result for additional analysis
    detection_result = modifier.get_last_detection_result()
    
    # Print field count analysis
    if detection_result:
        print(f"\n📊 Field Detection Analysis:")
        summary = detection_result.get_detection_summary()
        print(f"  PyPDFForm (modifiable): {summary['pypdfform']}")
        print(f"  PyMuPDF: {summary['pymupdf']}")
        print(f"  pypdf2: {summary['pypdf2']}")
        print(f"  Annotations: {summary['annotations']}")
        print(f"  Total unique fields: {summary['total_unique']}")
        print(f"  Expected from mapping: {len(field_mappings)}")
        
        # Show discrepancy if exists
        if summary['total_unique'] != len(field_mappings):
            print(f"  ⚠️  Field count discrepancy: {summary['total_unique']} detected vs {len(field_mappings)} expected")
            
        # Show field detection report location
        print(f"  📋 Detailed report: {detection_report_file}")
    
    # Print results
    if result.success:
        print(f"✅ Successfully modified PDF!")
        print(f"Original PDF: {result.original_pdf_path}")
        print(f"Modified PDF: {result.modified_pdf_path}")
        print(f"Fields modified: {len(result.modifications)}")
        print(f"Fields before: {result.field_count_before}")
        print(f"Fields after: {result.field_count_after}")
        
        if result.modifications:
            print("\nField modifications:")
            for mod in result.modifications[:10]:  # Show first 10
                print(f"  '{mod['old']}' → '{mod['new']}'")
            if len(result.modifications) > 10:
                print(f"  ... and {len(result.modifications) - 10} more")
        
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  ⚠️ {warning}")
    else:
        print(f"❌ Failed to modify PDF")
        print(f"Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  ❌ {error}")
    
    # Generate report
    report = modifier.create_field_mapping_report(result)
    report_file = output_file.with_suffix('.report.md')
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nDetailed report saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())
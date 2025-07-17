#!/usr/bin/env python3
"""
Comprehensive PDF Field Analysis Tool

This tool analyzes PDF forms using multiple detection methods to provide
comprehensive field discovery reports and validate field mappings.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.pdf_enrichment.enhanced_field_detector import EnhancedFieldDetector
from src.pdf_enrichment.pdf_modifier import PDFModifier
from src.pdf_enrichment.utils import setup_logging


def analyze_pdf_fields(pdf_path: Path, output_dir: Path = None) -> None:
    """Analyze PDF fields using multiple detection methods."""
    if output_dir is None:
        output_dir = pdf_path.parent
    
    # Create enhanced detector
    detector = EnhancedFieldDetector()
    
    # Run field detection
    print(f"🔍 Analyzing PDF: {pdf_path}")
    detection_result = detector.detect_all_fields(pdf_path)
    
    # Print summary
    print(f"\n📊 Field Detection Summary:")
    summary = detection_result.get_detection_summary()
    for method, count in summary.items():
        print(f"  {method}: {count} fields")
    
    # Generate detailed report
    report = detector.generate_field_report(detection_result)
    
    # Save report
    report_file = output_dir / f"{pdf_path.stem}_field_analysis.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"📋 Detailed report saved to: {report_file}")
    
    # Save JSON data
    json_data = {
        "pdf_file": str(pdf_path),
        "detection_summary": summary,
        "pypdfform_fields": detection_result.pypdfform_fields,
        "pymupdf_fields": detection_result.pymupdf_fields,
        "pypdf2_fields": detection_result.pypdf2_fields,
        "annotation_fields": detection_result.annotation_fields,
        "all_fields": sorted(list(detection_result.all_fields)),
        "field_sources": detection_result.field_sources,
        "detection_errors": detection_result.detection_errors,
        "detection_warnings": detection_result.detection_warnings
    }
    
    json_file = output_dir / f"{pdf_path.stem}_field_analysis.json"
    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"📊 JSON data saved to: {json_file}")
    
    # Print errors/warnings if any
    if detection_result.detection_errors:
        print(f"\n❌ Detection Errors:")
        for error in detection_result.detection_errors:
            print(f"  - {error}")
    
    if detection_result.detection_warnings:
        print(f"\n⚠️ Detection Warnings:")
        for warning in detection_result.detection_warnings:
            print(f"  - {warning}")


def validate_field_mapping(pdf_path: Path, mapping_file: Path) -> None:
    """Validate field mapping against PDF fields."""
    print(f"🔍 Validating mapping: {mapping_file}")
    print(f"📄 Against PDF: {pdf_path}")
    
    # Load mapping
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)
    
    field_mappings = mapping_data.get('bem_mappings', {})
    expected_fields = set(field_mappings.keys())
    
    # Analyze PDF fields
    detector = EnhancedFieldDetector()
    detection_result = detector.detect_all_fields(pdf_path)
    
    # Check field availability
    modifiable_fields = set(detection_result.pypdfform_fields)
    all_detected_fields = detection_result.all_fields
    
    print(f"\n📊 Field Mapping Validation:")
    print(f"  Expected fields: {len(expected_fields)}")
    print(f"  Modifiable fields (PyPDFForm): {len(modifiable_fields)}")
    print(f"  All detected fields: {len(all_detected_fields)}")
    
    # Find missing fields
    missing_modifiable = expected_fields - modifiable_fields
    missing_all = expected_fields - all_detected_fields
    
    print(f"\n🔍 Missing Fields Analysis:")
    print(f"  Missing from PyPDFForm: {len(missing_modifiable)}")
    print(f"  Missing from all detection: {len(missing_all)}")
    
    # Generate suggestions for missing fields
    if missing_modifiable:
        print(f"\n💡 Suggestions for Missing Fields:")
        suggestions = detector.suggest_missing_fields(modifiable_fields, missing_modifiable)
        
        for missing_field, suggested_fields in suggestions.items():
            print(f"  '{missing_field}':")
            if suggested_fields:
                for suggestion in suggested_fields[:3]:
                    print(f"    - {suggestion}")
            else:
                print(f"    - No similar fields found")
                
            # Check if field exists in other detection methods
            if missing_field in all_detected_fields:
                sources = detection_result.field_sources.get(missing_field, [])
                print(f"    - Found in: {', '.join(sources)}")
    
    # Show available fields
    print(f"\n📋 Available PyPDFForm Fields:")
    for field in sorted(modifiable_fields):
        print(f"  - {field}")


def compare_pdfs(pdf1_path: Path, pdf2_path: Path) -> None:
    """Compare field detection between two PDFs."""
    print(f"🔍 Comparing PDFs:")
    print(f"  PDF 1: {pdf1_path}")
    print(f"  PDF 2: {pdf2_path}")
    
    detector = EnhancedFieldDetector()
    
    # Analyze both PDFs
    result1 = detector.detect_all_fields(pdf1_path)
    result2 = detector.detect_all_fields(pdf2_path)
    
    # Compare results
    fields1 = result1.all_fields
    fields2 = result2.all_fields
    
    common_fields = fields1 & fields2
    unique_to_pdf1 = fields1 - fields2
    unique_to_pdf2 = fields2 - fields1
    
    print(f"\n📊 Field Comparison:")
    print(f"  PDF 1 fields: {len(fields1)}")
    print(f"  PDF 2 fields: {len(fields2)}")
    print(f"  Common fields: {len(common_fields)}")
    print(f"  Unique to PDF 1: {len(unique_to_pdf1)}")
    print(f"  Unique to PDF 2: {len(unique_to_pdf2)}")
    
    if unique_to_pdf1:
        print(f"\n📋 Fields unique to PDF 1:")
        for field in sorted(unique_to_pdf1):
            print(f"  - {field}")
    
    if unique_to_pdf2:
        print(f"\n📋 Fields unique to PDF 2:")
        for field in sorted(unique_to_pdf2):
            print(f"  - {field}")


def main():
    parser = argparse.ArgumentParser(description="Analyze PDF form fields using multiple detection methods")
    parser.add_argument("pdf_file", help="Path to PDF file to analyze")
    parser.add_argument("--output-dir", help="Output directory for reports (default: same as PDF)")
    parser.add_argument("--validate-mapping", help="Validate field mapping JSON file against PDF")
    parser.add_argument("--compare-with", help="Compare fields with another PDF")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Validate PDF file
    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Set output directory
    output_dir = Path(args.output_dir) if args.output_dir else pdf_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Main analysis
        analyze_pdf_fields(pdf_path, output_dir)
        
        # Validate mapping if provided
        if args.validate_mapping:
            mapping_file = Path(args.validate_mapping)
            if not mapping_file.exists():
                print(f"❌ Mapping file not found: {mapping_file}")
                sys.exit(1)
            validate_field_mapping(pdf_path, mapping_file)
        
        # Compare with another PDF if provided
        if args.compare_with:
            compare_pdf_path = Path(args.compare_with)
            if not compare_pdf_path.exists():
                print(f"❌ Comparison PDF not found: {compare_pdf_path}")
                sys.exit(1)
            compare_pdfs(pdf_path, compare_pdf_path)
            
        print(f"\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
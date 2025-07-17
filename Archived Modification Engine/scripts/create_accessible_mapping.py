#!/usr/bin/env python3
"""
Create Accessible Field Mapping for PDF Modification

This script creates a BEM mapping that includes only the fields that can actually
be modified by PyPDFForm, using the enhanced field detection and normalization.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.pdf_enrichment.enhanced_field_detector import EnhancedFieldDetector
from src.pdf_enrichment.utils import setup_logging


def create_accessible_mapping(pdf_path: Path) -> Dict:
    """Create BEM mapping for only accessible (modifiable) fields."""
    
    # Setup enhanced field detection
    detector = EnhancedFieldDetector()
    
    # Run field detection
    detection_result = detector.detect_all_fields(pdf_path)
    
    # Get only the accessible fields
    accessible_fields = detection_result.accessible_fields
    pypdfform_fields = set(detection_result.pypdfform_fields)
    
    print(f"📊 Field Analysis:")
    print(f"  Total fields detected: {len(detection_result.all_fields)}")
    print(f"  Accessible fields: {len(accessible_fields)}")
    print(f"  PyPDFForm fields: {len(pypdfform_fields)}")
    
    # Create BEM mappings for accessible fields
    bem_mappings = {}
    field_details = []
    radio_groups = {}
    
    # Enhanced BEM naming patterns
    bem_patterns = {
        # Owner information
        "FIRST_NAME": "owner-information_first-name",
        "LAST_NAME": "owner-information_last-name", 
        "FULL_NAME": "owner-information_full-name",
        "CONTRACT_NUMBER": "owner-information_contract-number",
        "ADDRESS": "owner-information_address",
        "CITY": "owner-information_city",
        "STATE": "owner-information_state",
        "ZIP": "owner-information_zip",
        "COUNTY": "owner-information_county",
        "PHONE": "owner-information_phone",
        "EMAIL": "owner-information_email",
        "SSN": "owner-information_ssn",
        "ADDR_SAME": "owner-information_address-same__checkbox",
        
        # Name change fields
        "name-change--group": "name-change--group",
        "name-change_reason--group": "name-change_reason--group", 
        "NAME_CHANGE_FORMER_NAME": "name-change_former-name",
        "NAME_CHANGE_NEW_NAME": "name-change_new-name",
        
        # Address change
        "address-change--group": "address-change--group",
        
        # Dividend options - create individual fields
        "CHANGE_DIVIDEND_OPTION": "dividend-option__accumulate-interest",
        "DIVIDEND_OPTION_OTHER": "dividend-option_other-specify",
        
        # Billing and payments
        "billing-frequency--group": "billing-frequency--group",
        "stop-payments--group": "stop-payments--group",
        "CHANGE_PREMIUM_PAYMENT": "premium-payments_change-request",
        "PREMIUM_PAYMENT_AMOUNT": "premium-payments_amount",
        
        # Signatures
        "SIGNATURE_FULL_NAME": "signatures_owner-name",
        "SIGNATURE_DATE": "signatures_owner-date",
        "Signature2": "signatures_owner-signature",
        "Signature3": "signatures_joint-owner-signature",
    }
    
    # Process accessible fields
    for field_name in sorted(accessible_fields):
        # Only include fields that are actually in PyPDFForm (modifiable)
        if field_name in pypdfform_fields:
            bem_name = bem_patterns.get(field_name, f"form_{field_name.lower().replace('_', '-')}")
            bem_mappings[field_name] = bem_name
            
            # Create field detail
            field_type = detection_result.field_types.get(field_name, "text")
            field_detail = {
                "original_name": field_name,
                "bem_name": bem_name,
                "field_type": field_type,
                "section": bem_name.split('_')[0] if '_' in bem_name else bem_name.split('-')[0],
                "confidence": "high",
                "reasoning": f"Accessible field mapped to BEM name '{bem_name}'"
            }
            field_details.append(field_detail)
    
    # Handle radio groups specifically
    group_fields = [f for f in bem_mappings.keys() if f.endswith("--group")]
    for group_field in group_fields:
        group_bem = bem_mappings[group_field]
        # For now, create empty radio groups - would need actual individual options
        radio_groups[group_bem] = []
    
    # Special handling for dividend options to create multiple individual fields
    if "CHANGE_DIVIDEND_OPTION" in bem_mappings:
        # Create individual dividend option mappings
        dividend_base = "dividend-option"
        dividend_options = [
            ("DIVIDEND_ACCUMULATE_INTEREST", f"{dividend_base}__accumulate-interest"),
            ("DIVIDEND_REDUCE_PREMIUM", f"{dividend_base}__reduce-premium"), 
            ("DIVIDEND_REDUCE_LOAN", f"{dividend_base}__reduce-loan-principal"),
            ("DIVIDEND_PAID_UP", f"{dividend_base}__paid-up-additional"),
            ("DIVIDEND_ANNUAL_PREMIUM", f"{dividend_base}__annual-premium"),
        ]
        
        # Note: These are conceptual mappings - the actual PDF may not have these individual fields
        print(f"\n💡 Suggested Individual Dividend Options:")
        for orig, bem in dividend_options:
            print(f"  {orig} → {bem}")
    
    # Create the mapping structure
    mapping = {
        "filename": pdf_path.name,
        "analysis_timestamp": datetime.now().isoformat(),
        "total_fields_found": len(detection_result.all_fields),
        "total_fields_mapped": len(bem_mappings),
        "form_context": f"Accessible field mapping for {pdf_path.name} - only modifiable fields included",
        "bem_mappings": bem_mappings,
        "radio_groups": radio_groups,
        "field_details": field_details,
        "notes": [
            "This mapping includes only fields that can be modified through PyPDFForm",
            f"Total accessible fields: {len(accessible_fields)}",
            f"Modifiable fields mapped: {len(bem_mappings)}",
            "Individual dividend options may need to be handled separately if they exist as distinct fields"
        ]
    }
    
    return mapping


def main():
    if len(sys.argv) != 2:
        print("Usage: python create_accessible_mapping.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Setup logging
    setup_logging(level=logging.INFO)
    
    print(f"🔍 Creating accessible field mapping for: {pdf_path}")
    
    # Create accessible mapping
    mapping = create_accessible_mapping(pdf_path)
    
    # Save mapping
    output_file = pdf_path.with_stem(f"{pdf_path.stem}_accessible_bem_mapping").with_suffix('.json')
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n✅ Accessible mapping created: {output_file}")
    print(f"📋 Modifiable fields: {mapping['total_fields_mapped']}")
    print(f"📊 Total fields found: {mapping['total_fields_found']}")
    
    # Show the accessible field mappings
    print(f"\n📋 Accessible Field Mappings:")
    for original, bem in sorted(mapping['bem_mappings'].items()):
        print(f"  {original} → {bem}")


if __name__ == "__main__":
    main()
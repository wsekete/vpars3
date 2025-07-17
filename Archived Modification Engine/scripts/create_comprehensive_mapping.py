#!/usr/bin/env python3
"""
Create Comprehensive BEM Field Mapping

This script uses the enhanced field detection to create a complete BEM mapping
for all detected fields, including normalized fields and proper field types.
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


class ComprehensiveMappingGenerator:
    """Generate comprehensive BEM mappings for all detected fields."""
    
    def __init__(self):
        self.detector = EnhancedFieldDetector()
        
        # BEM naming patterns for different field types
        self.bem_patterns = {
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
            
            # Insured information
            "ADDR_SAME": "insured-information_address-same__checkbox",
            
            # Joint owner information patterns will use prefix-specific naming
            
            # Name change fields
            "NAME_CHANGE_FORMER_NAME": "name-change_former-name",
            "NAME_CHANGE_NEW_NAME": "name-change_new-name",
            
            # Dividend options
            "CHANGE_DIVIDEND_OPTION": "dividend-option_change-request",
            "DIVIDEND_OPTION_OTHER": "dividend-option_other-specify",
            
            # Premium payments
            "CHANGE_PREMIUM_PAYMENT": "premium-payments_change-request",
            "PREMIUM_PAYMENT_AMOUNT": "premium-payments_amount",
            
            # Signatures
            "SIGNATURE_FULL_NAME": "signatures_owner-name",
            "SIGNATURE_DATE": "signatures_owner-date",
            "Signature2": "signatures_owner-signature",
            "Signature3": "signatures_joint-owner-signature",
        }
        
        # Prefix-specific BEM blocks
        self.prefix_bem_blocks = {
            "OWNER.": "owner-information",
            "PREMIUM_PAYOR.": "premium-payor",
            "POLICY_OWNER.": "policy-owner",
            "PRIMARY_INSURED.": "primary-insured",
            "INSURED.": "insured-information",
            "JOINT_OWNER.": "joint-owner",
        }
    
    def generate_comprehensive_mapping(self, pdf_path: Path) -> Dict:
        """Generate comprehensive BEM mapping for all detected fields."""
        # Run enhanced field detection
        detection_result = self.detector.detect_all_fields(pdf_path)
        
        # Generate BEM mappings
        bem_mappings = {}
        field_details = []
        radio_groups = {}
        
        # Process all detected fields
        for field_name in sorted(detection_result.all_fields):
            bem_name = self._generate_bem_name(field_name, detection_result)
            bem_mappings[field_name] = bem_name
            
            # Create field detail
            field_detail = {
                "original_name": field_name,
                "bem_name": bem_name,
                "field_type": detection_result.field_types.get(field_name, "text"),
                "accessible": field_name in detection_result.accessible_fields,
                "sources": detection_result.field_sources.get(field_name, []),
                "normalized": field_name in detection_result.field_prefixes,
                "prefix": detection_result.field_prefixes.get(field_name, ""),
            }
            
            # Add section based on BEM name
            section = bem_name.split('_')[0] if '_' in bem_name else bem_name.split('-')[0]
            field_detail["section"] = section
            
            field_details.append(field_detail)
        
        # Process radio groups
        for group_name, options in detection_result.radio_groups.items():
            if group_name in bem_mappings:
                group_bem_name = bem_mappings[group_name]
                option_names = []
                
                for option in options:
                    if option in bem_mappings:
                        option_bem = bem_mappings[option]
                        # Extract option name from BEM name
                        if '__' in option_bem:
                            option_name = option_bem.split('__')[1]
                        elif '_' in option_bem:
                            parts = option_bem.split('_')
                            option_name = parts[-1] if len(parts) > 1 else option_bem
                        else:
                            option_name = option_bem
                        option_names.append(option_name)
                
                radio_groups[group_bem_name] = option_names
        
        # Create comprehensive mapping
        mapping = {
            "filename": pdf_path.name,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_fields_found": len(detection_result.all_fields),
            "total_fields_mapped": len(bem_mappings),
            "accessible_fields": len(detection_result.accessible_fields),
            "form_context": f"Comprehensive mapping for {pdf_path.name} with enhanced field detection",
            "bem_mappings": bem_mappings,
            "radio_groups": radio_groups,
            "field_details": field_details,
            "detection_summary": detection_result.get_detection_summary(),
            "field_normalization": {
                "normalized_count": len(detection_result.field_prefixes),
                "prefixes_found": list(set(detection_result.field_prefixes.values())),
            }
        }
        
        return mapping
    
    def _generate_bem_name(self, field_name: str, detection_result) -> str:
        """Generate BEM name for a field based on its characteristics."""
        # Handle radio group containers
        if field_name.endswith("--group"):
            return field_name  # Keep group names as-is
        
        # Check if we have a direct pattern match
        if field_name in self.bem_patterns:
            return self.bem_patterns[field_name]
        
        # Handle normalized fields (with prefixes)
        prefix = detection_result.field_prefixes.get(field_name, "")
        if prefix:
            # Get the base field name
            base_name = field_name[len(prefix):]
            
            # Get the BEM block for this prefix
            bem_block = self.prefix_bem_blocks.get(prefix, "unknown")
            
            # Generate element name from base field name
            element_name = self._normalize_element_name(base_name)
            
            # Determine field type
            field_type = detection_result.field_types.get(field_name, "text")
            
            # Generate BEM name
            bem_name = f"{bem_block}_{element_name}"
            
            # Add modifier for specific field types
            if field_type == "checkbox":
                bem_name += "__checkbox"
            elif field_type == "signature":
                # Special handling for signatures
                if "signature" in element_name and "date" not in element_name and "name" not in element_name:
                    bem_name = f"signatures_{bem_block.replace('-', '-')}-signature"
                else:
                    bem_name = f"signatures_{bem_block.replace('-', '-')}-{element_name}"
            elif field_type == "date":
                if "signature" in element_name:
                    bem_name = f"signatures_{bem_block.replace('-', '-')}-date"
            
            return bem_name
        
        # Handle fields without prefixes
        return self._generate_bem_name_without_prefix(field_name, detection_result)
    
    def _generate_bem_name_without_prefix(self, field_name: str, detection_result) -> str:
        """Generate BEM name for fields without prefixes."""
        field_type = detection_result.field_types.get(field_name, "text")
        field_lower = field_name.lower()
        
        # Name change fields
        if "name_change" in field_lower or "NAME_CHANGE" in field_name:
            element_name = self._normalize_element_name(field_name.replace("NAME_CHANGE_", ""))
            return f"name-change_{element_name}"
        
        # Dividend option fields
        if "dividend" in field_lower or "DIVIDEND" in field_name:
            if "other" in field_lower:
                return "dividend-option_other-specify"
            else:
                return "dividend-option_change-request"
        
        # Premium payment fields
        if "premium" in field_lower or "payment" in field_lower:
            if "amount" in field_lower:
                return "premium-payments_amount"
            else:
                return "premium-payments_change-request"
        
        # Billing frequency
        if "billing" in field_lower and "frequency" in field_lower:
            return "billing-frequency--group"
        
        # Stop payments
        if "stop" in field_lower and "payment" in field_lower:
            return "stop-payments--group"
        
        # Signature fields
        if field_type == "signature":
            if "joint" in field_lower:
                return "signatures_joint-owner-signature"
            else:
                return "signatures_owner-signature"
        
        # Default: use field name as element
        element_name = self._normalize_element_name(field_name)
        return f"form_{element_name}"
    
    def _normalize_element_name(self, field_name: str) -> str:
        """Normalize field name to valid BEM element name."""
        # Convert to lowercase
        normalized = field_name.lower()
        
        # Replace underscores with hyphens
        normalized = normalized.replace('_', '-')
        
        # Handle special cases first
        replacements = {
            'addr': 'address',
            'ssn': 'social-security-number',
            'signature-full-name': 'name',
            'signature-date': 'date',
            'full-name': 'full-name',
            'first-name': 'first-name',
            'last-name': 'last-name',
            'contract-number': 'contract-number',
        }
        
        # Apply direct replacements
        for old, new in replacements.items():
            if old in normalized:
                normalized = normalized.replace(old, new)
        
        # Handle specific field patterns
        if normalized == 'full':
            normalized = 'full-name'
        elif normalized == 'first':
            normalized = 'first-name'
        elif normalized == 'last':
            normalized = 'last-name'
        elif normalized == 'address':
            normalized = 'address'
        elif 'signature' in normalized and 'name' not in normalized and 'date' not in normalized:
            normalized = 'signature'
        
        # Fix common typos
        normalized = normalized.replace('addressess', 'address')
        
        return normalized


def main():
    if len(sys.argv) != 2:
        print("Usage: python create_comprehensive_mapping.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Setup logging
    setup_logging(level=logging.INFO)
    
    # Generate comprehensive mapping
    generator = ComprehensiveMappingGenerator()
    
    print(f"🔍 Analyzing PDF: {pdf_path}")
    mapping = generator.generate_comprehensive_mapping(pdf_path)
    
    # Save mapping
    output_file = pdf_path.with_stem(f"{pdf_path.stem}_comprehensive_bem_mapping").with_suffix('.json')
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"✅ Comprehensive mapping created: {output_file}")
    print(f"📊 Fields analyzed: {mapping['total_fields_found']}")
    print(f"📋 Fields mapped: {mapping['total_fields_mapped']}")
    print(f"🔧 Accessible fields: {mapping['accessible_fields']}")
    print(f"📑 Radio groups: {len(mapping['radio_groups'])}")
    
    # Print summary
    detection_summary = mapping['detection_summary']
    print(f"\n📈 Detection Summary:")
    for method, count in detection_summary.items():
        if count > 0:
            print(f"  {method}: {count} fields")
    
    normalization = mapping['field_normalization']
    if normalization['normalized_count'] > 0:
        print(f"\n🔧 Field Normalization:")
        print(f"  Normalized fields: {normalization['normalized_count']}")
        print(f"  Prefixes found: {', '.join(normalization['prefixes_found'])}")


if __name__ == "__main__":
    main()
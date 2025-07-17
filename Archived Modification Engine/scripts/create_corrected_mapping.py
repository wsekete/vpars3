#!/usr/bin/env python3
"""
Create corrected BEM mapping based on actual PDF field names
"""
import json
from pathlib import Path

# Actual PDF field names from the LIFE-1528-Q_BLANK.pdf
actual_pdf_fields = [
    "ADDRESS", "ADDR_SAME", "CHANGE_DIVIDEND_OPTION", "CHANGE_PREMIUM_PAYMENT",
    "CITY", "CONTRACT_NUMBER", "COUNTY", "DIVIDEND_OPTION_OTHER", "EMAIL",
    "FIRST_NAME", "FULL_NAME", "LAST_NAME", "NAME_CHANGE_FORMER_NAME",
    "NAME_CHANGE_NEW_NAME", "PHONE", "PREMIUM_PAYMENT_AMOUNT", "SIGNATURE_DATE",
    "SIGNATURE_FULL_NAME", "SSN", "STATE", "Signature2", "Signature3", "ZIP",
    "address-change--group", "billing-frequency--group", "name-change--group",
    "name-change_reason--group", "stop-payments--group"
]

# Create corrected BEM mapping
corrected_mapping = {
    "filename": "LIFE-1528-Q_BLANK.pdf",
    "analysis_timestamp": "2025-07-16T15:35:00Z",
    "total_fields_found": len(actual_pdf_fields),
    "total_fields_mapped": len(actual_pdf_fields),
    "form_context": "Nationwide Life Insurance Company service request form",
    "bem_mappings": {
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
        
        # Name change section
        "name-change--group": "name-change--group",
        "name-change_reason--group": "name-change_reason--group",
        "NAME_CHANGE_FORMER_NAME": "name-change_former-name",
        "NAME_CHANGE_NEW_NAME": "name-change_new-name",
        
        # Address change section
        "address-change--group": "address-change--group",
        
        # Dividend options
        "CHANGE_DIVIDEND_OPTION": "dividend-option_change-request",
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
    },
    "radio_groups": {
        "name-change--group": ["owner", "insured", "payor"],
        "name-change_reason--group": ["marriage", "divorce", "court-action", "correction"],
        "address-change--group": ["owner", "insured", "payor"],
        "billing-frequency--group": ["annual", "semiannual", "quarterly"],
        "stop-payments--group": ["ach", "direct-bill"]
    },
    "field_details": []
}

# Add field details
for original_name, bem_name in corrected_mapping["bem_mappings"].items():
    # Determine field type based on field name and BEM name
    if original_name.endswith("--group"):
        field_type = "radio_group"
    elif "__checkbox" in bem_name:
        field_type = "checkbox"
    elif "signature" in bem_name.lower() and "name" not in bem_name.lower() and "date" not in bem_name.lower():
        field_type = "signature"
    elif "date" in bem_name.lower():
        field_type = "date"
    else:
        field_type = "text"
    
    # Determine section
    if "owner-information" in bem_name:
        section = "owner_information"
    elif "name-change" in bem_name:
        section = "name_change"
    elif "address-change" in bem_name:
        section = "address_change"
    elif "dividend-option" in bem_name:
        section = "dividend_options"
    elif "billing-frequency" in bem_name:
        section = "billing_frequency"
    elif "stop-payments" in bem_name:
        section = "stop_payments"
    elif "premium-payments" in bem_name:
        section = "premium_payments"
    elif "signatures" in bem_name:
        section = "signatures"
    else:
        section = "other"
    
    corrected_mapping["field_details"].append({
        "original_name": original_name,
        "bem_name": bem_name,
        "field_type": field_type,
        "section": section,
        "confidence": "high",
        "reasoning": f"Mapped from actual PDF field '{original_name}' to BEM name '{bem_name}'"
    })

# Save corrected mapping
output_file = Path("/Users/wseke/Desktop/corrected_bem_mapping.json")
with open(output_file, 'w') as f:
    json.dump(corrected_mapping, f, indent=2)

print(f"Corrected BEM mapping saved to: {output_file}")
print(f"Total fields mapped: {len(corrected_mapping['bem_mappings'])}")
print("\nMapping summary:")
for original, bem in sorted(corrected_mapping["bem_mappings"].items()):
    print(f"  {original} → {bem}")
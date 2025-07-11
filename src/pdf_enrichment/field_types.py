"""
Field type definitions and enums for PDF form processing.
Based on the analysis of the Clean Field Data CSV.
"""

from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Enum for all supported PDF field types."""
    
    # Core field types
    TEXT_FIELD = "TextField"
    CHECKBOX = "Checkbox"
    SIGNATURE = "Signature"
    SIGNATURE_DATE = "SignatureDate"
    RADIO_GROUP = "RadioGroup"
    RADIO_BUTTON = "RadioButton"
    GROUP = "Group"
    
    # Specialized field types
    TEXT_FIELD_NUMBER_GROUP = "TextFieldNumberGroup"
    BENEFICIARIES = "Beneficiaries"
    SIGNATURE_TEXT_FIELD = "SignatureTextField"
    PAYMENT_METHOD = "PaymentMethod"
    BENEFICIARY_RELATIONSHIP_DROPDOWN = "BeneficiaryRelationshipDropdown"
    DROPDOWN = "Dropdown"
    WITHDRAWAL_AMOUNT = "WithdrawalAmount"
    GILICO_WITHDRAWAL_AMOUNT = "GilicoWithdrawalAmount"


class FieldPosition(BaseModel):
    """Position and dimensions of a field on a PDF page."""
    
    x: float = Field(description="X coordinate from bottom-left origin")
    y: float = Field(description="Y coordinate from bottom-left origin")
    width: float = Field(description="Field width in points")
    height: float = Field(description="Field height in points")
    page: int = Field(description="Page number (0-indexed)")


class FormField(BaseModel):
    """Complete representation of a PDF form field."""
    
    id: int = Field(description="Unique field identifier")
    type: FieldType = Field(description="Field type")
    form_id: int = Field(description="Parent form identifier")
    section_id: Optional[int] = Field(description="Section identifier")
    parent_id: Optional[int] = Field(description="Parent field identifier for grouped fields")
    order: Optional[float] = Field(description="Display order within section")
    label: str = Field(description="Human-readable field label")
    api_name: str = Field(description="Current API name (may need BEM conversion)")
    custom: bool = Field(description="Whether field is custom-created")
    uuid: str = Field(description="Unique field UUID")
    position: FieldPosition = Field(description="Field position and dimensions")
    unified_field_id: Optional[int] = Field(description="Unified field identifier")
    
    # Additional metadata
    bem_name: Optional[str] = Field(None, description="Generated BEM-style name")
    confidence: Optional[str] = Field(None, description="BEM name generation confidence")
    section_name: Optional[str] = Field(None, description="Inferred section name")
    reasoning: Optional[str] = Field(None, description="BEM naming reasoning")


class BEMNamingResult(BaseModel):
    """Result of BEM naming analysis for a field."""
    
    original_name: str = Field(description="Original field name")
    bem_name: str = Field(description="Generated BEM-style name")
    confidence: str = Field(description="Generation confidence: high, medium, low")
    reasoning: str = Field(description="Explanation of naming decision")
    section: str = Field(description="Inferred form section")
    field_type: FieldType = Field(description="Field type")
    
    # Validation flags
    is_radio_group: bool = Field(False, description="Whether field is a radio group container")
    needs_review: bool = Field(False, description="Whether field needs manual review")
    conflicts_with: Optional[List[str]] = Field(None, description="Conflicting field names")


class FormAnalysis(BaseModel):
    """Complete analysis result for a PDF form."""
    
    filename: str = Field(description="Source PDF filename")
    form_type: Optional[str] = Field(None, description="Detected form type")
    form_id: Optional[str] = Field(None, description="Form identifier")
    total_fields: int = Field(description="Total number of fields")
    
    # Field analysis
    fields: List[FormField] = Field(description="All form fields")
    bem_mappings: List[BEMNamingResult] = Field(description="BEM naming results")
    
    # Quality metrics
    confidence_summary: Dict[str, int] = Field(
        description="Count of fields by confidence level"
    )
    field_type_distribution: Dict[FieldType, int] = Field(
        description="Count of fields by type"
    )
    
    # Validation results
    naming_conflicts: List[str] = Field(default_factory=list, description="Conflicting BEM names")
    missing_sections: List[str] = Field(default_factory=list, description="Fields without sections")
    review_required: List[str] = Field(default_factory=list, description="Fields requiring review")


class BatchAnalysis(BaseModel):
    """Analysis results for multiple PDF forms."""
    
    generated_at: str = Field(description="Analysis timestamp")
    analyst: str = Field(description="Analysis engine identifier")
    forms: List[FormAnalysis] = Field(description="Individual form analyses")
    
    # Cross-form analysis
    common_patterns: Dict[str, List[str]] = Field(
        default_factory=dict, description="Common naming patterns across forms"
    )
    naming_consistency: Dict[str, float] = Field(
        default_factory=dict, description="Consistency scores for similar fields"
    )
    
    # Summary statistics
    total_forms: int = Field(description="Total number of forms analyzed")
    total_fields: int = Field(description="Total number of fields across all forms")
    overall_confidence: Dict[str, int] = Field(
        description="Overall confidence distribution"
    )


class FieldModificationResult(BaseModel):
    """Result of PDF field modification operation."""
    
    original_pdf_path: str = Field(description="Path to original PDF")
    modified_pdf_path: str = Field(description="Path to modified PDF")
    modifications: List[Dict[str, Union[str, int]]] = Field(
        description="List of field modifications made"
    )
    
    # Validation results
    success: bool = Field(description="Whether modification was successful")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Any warnings")
    
    # Metadata
    timestamp: str = Field(description="Modification timestamp")
    field_count_before: int = Field(description="Field count before modification")
    field_count_after: int = Field(description="Field count after modification")


# Type aliases for convenience
FieldID = Union[int, str]
BEMName = str
FieldMapping = Dict[str, str]

# Constants for field categorization
INTERACTIVE_FIELD_TYPES = {
    FieldType.TEXT_FIELD,
    FieldType.CHECKBOX,
    FieldType.RADIO_GROUP,
    FieldType.RADIO_BUTTON,
    FieldType.DROPDOWN,
    FieldType.SIGNATURE,
}

SIGNATURE_FIELD_TYPES = {
    FieldType.SIGNATURE,
    FieldType.SIGNATURE_DATE,
    FieldType.SIGNATURE_TEXT_FIELD,
}

GROUPED_FIELD_TYPES = {
    FieldType.RADIO_GROUP,
    FieldType.RADIO_BUTTON,
    FieldType.GROUP,
}

# BEM naming patterns
BEM_PATTERNS = {
    "block_element": r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*_[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
    "block_element__modifier": r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*_[a-z][a-z0-9]*(?:-[a-z0-9]+)*__[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
    "radio_group": r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*_[a-z][a-z0-9]*(?:-[a-z0-9]+)*--group$",
}

# Common form sections for BEM block generation
COMMON_FORM_SECTIONS = {
    "owner-information": ["owner", "policy holder", "insured", "account holder"],
    "beneficiary": ["beneficiary", "contingent", "primary beneficiary"],
    "address": ["address", "contact", "mailing", "residence"],
    "payment": ["payment", "billing", "bank", "financial"],
    "withdrawal": ["withdrawal", "distribution", "payout"],
    "signature": ["signature", "sign", "authorization", "consent"],
    "change-request": ["change", "modification", "update", "amendment"],
    "employment": ["employment", "occupation", "employer", "income"],
    "medical": ["medical", "health", "physician", "condition"],
    "investment": ["investment", "allocation", "portfolio", "funds"],
}

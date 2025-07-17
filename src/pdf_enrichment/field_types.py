"""
Field type definitions and enums for PDF form processing.
Simplified for Claude Desktop integration.
"""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class FieldType(str, Enum):
    """Enum for all supported PDF field types."""

    # Core field types
    TEXT_FIELD = "TextField"
    CHECKBOX = "Checkbox"
    SIGNATURE = "Signature"
    RADIO_GROUP = "RadioGroup"
    RADIO_BUTTON = "RadioButton"
    DROPDOWN = "Dropdown"
    BUTTON = "Button"
    LISTBOX = "ListBox"


class FieldPosition(BaseModel):
    """Position and dimensions of a field on a PDF page."""

    x: float = Field(description="X coordinate from bottom-left origin")
    y: float = Field(description="Y coordinate from bottom-left origin")
    width: float = Field(description="Field width in points")
    height: float = Field(description="Field height in points")
    page: int = Field(description="Page number (0-indexed)")


class FormField(BaseModel):
    """Simplified representation of a PDF form field for Claude Desktop processing."""

    id: int = Field(description="Unique field identifier")
    name: str = Field(description="Original field name from PDF")
    field_type: FieldType = Field(description="Field type")
    label: str = Field(description="Human-readable field label")
    position: FieldPosition = Field(description="Field position and dimensions")

    # Optional field properties
    required: Optional[bool] = Field(default=False, description="Whether field is required")
    choices: Optional[List[str]] = Field(default=None, description="Choices for dropdown/radio fields")
    max_length: Optional[int] = Field(default=None, description="Maximum text length")
    multiline: Optional[bool] = Field(default=False, description="Whether text field is multiline")
    readonly: Optional[bool] = Field(default=False, description="Whether field is readonly")

    @field_validator('required', 'multiline', 'readonly', mode='before')
    @classmethod
    def validate_bool_fields(cls, v):
        """Convert None values to False for boolean fields."""
        if v is None:
            return False
        return v


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
FieldMapping = Dict[str, str]

"""
PDF Enrichment Platform

Generate BEM-style field names for PDF forms using Claude Desktop integration.
"""

from .field_types import (
    FieldType,
    FormField,
)

__version__ = "0.1.0"
__all__ = [
    "FieldType",
    "FormField",
]

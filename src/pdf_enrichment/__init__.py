"""
PDF Enrichment Platform

Extract PDF form fields and modify them with Claude Desktop integration.
"""

from .field_analyzer import FieldAnalyzer
from .field_types import (
    FieldModificationResult,
    FieldType,
    FormField,
)
from .pdf_modifier import PDFModifier

__version__ = "0.1.0"
__all__ = [
    "FieldAnalyzer",
    "PDFModifier", 
    "FormField",
    "FieldType",
    "FieldModificationResult",
]

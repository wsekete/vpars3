"""
PDF Enrichment Platform

Transform PDF forms into structured APIs with BEM-style field naming.
"""

from .field_analyzer import FieldAnalyzer
from .field_types import (
    BatchAnalysis,
    BEMNamingResult,
    FieldModificationResult,
    FieldType,
    FormAnalysis,
    FormField,
)
from .pdf_modifier import PDFModifier
from .preview_generator import PreviewGenerator

__version__ = "0.1.0"
__all__ = [
    "FieldAnalyzer",
    "PDFModifier", 
    "PreviewGenerator",
    "FormField",
    "FieldType",
    "BEMNamingResult",
    "FormAnalysis",
    "BatchAnalysis",
    "FieldModificationResult",
]

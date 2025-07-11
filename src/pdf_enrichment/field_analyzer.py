"""
PDF Form Field Analyzer

Extracts form field information from PDF files for Claude Desktop processing.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List

from PyPDFForm import PdfWrapper

from .field_types import (
    FieldPosition,
    FieldType,
    FormField,
)

logger = logging.getLogger(__name__)


class FieldAnalyzer:
    """Extracts form field information from PDF files."""
    
    def __init__(self) -> None:
        self.field_cache: Dict[str, List[FormField]] = {}
    
    async def extract_form_fields(self, pdf_path: Path) -> List[FormField]:
        """
        Extract form fields from PDF using PyPDFForm.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of form fields with their properties
        """
        try:
            # Check cache first
            cache_key = str(pdf_path)
            if cache_key in self.field_cache:
                return self.field_cache[cache_key]
            
            # Load PDF with PyPDFForm
            pdf = PdfWrapper(str(pdf_path))
            
            # Extract field information
            form_fields = []
            field_id = 0
            
            for field_name, widget in pdf.widgets.items():
                try:
                    # Determine field type
                    field_type = self._determine_field_type(widget)
                    
                    # Extract position information
                    position = self._extract_field_position(widget)
                    
                    # Create form field
                    form_field = FormField(
                        id=field_id,
                        name=field_name,
                        field_type=field_type,
                        label=self._extract_field_label(widget, field_name),
                        position=position,
                        required=getattr(widget, 'required', False),
                        choices=getattr(widget, 'choices', None),
                        max_length=getattr(widget, 'max_length', None),
                        multiline=getattr(widget, 'multiline', False),
                        readonly=getattr(widget, 'readonly', False),
                    )
                    
                    form_fields.append(form_field)
                    field_id += 1
                    
                except (AttributeError, ValueError) as e:
                    logger.warning(f"Error processing field {field_name}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing field {field_name}: {e}")
                    continue
            
            # Cache result
            self.field_cache[cache_key] = form_fields
            
            logger.info(f"Extracted {len(form_fields)} fields from {pdf_path}")
            return form_fields
            
        except FileNotFoundError as e:
            logger.error(f"PDF file not found: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {pdf_path}") from e
        except PermissionError as e:
            logger.error(f"Permission denied accessing PDF: {pdf_path}")
            raise PermissionError(f"Permission denied accessing PDF: {pdf_path}") from e
        except Exception as e:
            logger.exception(f"Error extracting fields from {pdf_path}")
            raise RuntimeError(f"Failed to extract form fields: {str(e)}") from e
    
    def _determine_field_type(self, widget: any) -> FieldType:
        """Determine field type from PyPDFForm widget."""
        widget_type = type(widget).__name__
        
        # Map PyPDFForm widget types to our FieldType enum
        type_mapping = {
            "Text": FieldType.TEXT_FIELD,
            "Checkbox": FieldType.CHECKBOX,
            "Radio": FieldType.RADIO_BUTTON,
            "Dropdown": FieldType.DROPDOWN,
            "Signature": FieldType.SIGNATURE,
            "Button": FieldType.BUTTON,
            "ListBox": FieldType.LISTBOX,
        }
        
        return type_mapping.get(widget_type, FieldType.TEXT_FIELD)
    
    def _extract_field_position(self, widget: any) -> FieldPosition:
        """Extract field position from PyPDFForm widget."""
        try:
            # Get widget rectangle (coordinates may vary by widget type)
            rect = getattr(widget, 'rect', None)
            if rect and len(rect) >= 4:
                return FieldPosition(
                    x=float(rect[0]),
                    y=float(rect[1]),
                    width=float(rect[2] - rect[0]),
                    height=float(rect[3] - rect[1]),
                    page=getattr(widget, 'page', 0),
                )
            else:
                # Fallback to default position
                return FieldPosition(x=0, y=0, width=100, height=20, page=0)
                
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"Error extracting position: {e}")
            return FieldPosition(x=0, y=0, width=100, height=20, page=0)
        except Exception as e:
            logger.error(f"Unexpected error extracting position: {e}")
            return FieldPosition(x=0, y=0, width=100, height=20, page=0)
    
    def _extract_field_label(self, widget: any, field_name: str) -> str:
        """Extract human-readable label from widget or field name."""
        # Try to get label from widget properties
        label = getattr(widget, 'label', None)
        if label:
            return label
        
        # Try to get tooltip or title
        tooltip = getattr(widget, 'tooltip', None)
        if tooltip:
            return tooltip
        
        # Fall back to cleaning up the field name
        return self._clean_field_name(field_name)
    
    def _clean_field_name(self, field_name: str) -> str:
        """Clean up field name to create a human-readable label."""
        # Remove common prefixes and suffixes
        cleaned = re.sub(r'^(Text|Checkbox|Radio|Dropdown|Signature)_?', '', field_name)
        cleaned = re.sub(r'_?(Field|Box|Button)$', '', cleaned)
        
        # Replace underscores and camelCase with spaces
        cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
        cleaned = re.sub(r'[_-]', ' ', cleaned)
        
        # Capitalize words
        cleaned = ' '.join(word.capitalize() for word in cleaned.split())
        
        return cleaned or field_name
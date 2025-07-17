"""
PDF Form Field Analyzer

Extracts form field information from PDF files for Claude Desktop processing.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

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

                    # Create form field with safe attribute extraction
                    form_field = FormField(
                        id=field_id,
                        name=field_name,
                        field_type=field_type,
                        label=self._extract_field_label(widget, field_name),
                        position=position,
                        required=self._safe_get_bool_attr(widget, 'required', False),
                        choices=getattr(widget, 'choices', None),
                        max_length=getattr(widget, 'max_length', None),
                        multiline=self._safe_get_bool_attr(widget, 'multiline', False),
                        readonly=self._safe_get_bool_attr(widget, 'readonly', False),
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
            raise RuntimeError(f"Failed to extract form fields: {e!s}") from e

    def _safe_get_bool_attr(self, widget: any, attr_name: str, default: bool) -> bool:
        """Safely get boolean attribute from widget, handling None values."""
        value = getattr(widget, attr_name, default)
        if value is None:
            return default
        return bool(value)

    def _determine_field_type(self, widget: any) -> FieldType:
        """Smart field type detection using multiple signals."""
        detector = SmartFieldTypeDetector()
        return detector.detect_field_type(widget)

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

    def detect_radio_groups(self, form_fields: List[FormField]) -> Dict[str, List[str]]:
        """Detect radio groups using multi-strategy approach."""
        detector = RadioGroupDetector()
        return detector.detect_radio_groups(form_fields)


class RadioGroupDetector:
    """Enhanced radio group detection with multiple strategies."""

    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".RadioGroupDetector")

    def detect_radio_groups(self, form_fields: List[FormField]) -> Dict[str, List[str]]:
        """Enhanced radio group detection with multiple strategies."""

        # Filter only radio button fields
        radio_fields = [f for f in form_fields if f.field_type == FieldType.RADIO_BUTTON]

        if not radio_fields:
            self.logger.info("No radio button fields found")
            return {}

        self.logger.info(f"Analyzing {len(radio_fields)} radio button fields for grouping")

        # Strategy 1: Name pattern matching
        groups_by_pattern = self._detect_by_naming_pattern(radio_fields)

        # Strategy 2: Visual positioning
        groups_by_position = self._detect_by_position(radio_fields)

        # Strategy 3: Field type analysis (already filtered to radio buttons)
        groups_by_labels = self._detect_by_labels(radio_fields)

        # Combine and validate detection results
        combined_groups = self._merge_detection_results(
            groups_by_pattern, groups_by_position, groups_by_labels
        )

        self.logger.info(f"Detected {len(combined_groups)} radio groups")
        return combined_groups

    def _detect_by_naming_pattern(self, radio_fields: List[FormField]) -> Dict[str, List[str]]:
        """Detect radio groups by naming patterns."""
        groups = {}

        # Common naming patterns for radio groups
        patterns = [
            # Pattern: base_name_1, base_name_2, etc.
            r'^(.+?)_(\d+)$',
            # Pattern: base_name_option1, base_name_option2, etc.
            r'^(.+?)_?(option|choice|item)_?(\d+)$',
            # Pattern: prefix_category_suffix
            r'^(.+?)_([a-zA-Z]+)$',
            # Pattern: category_1, category_2, etc.
            r'^([a-zA-Z_]+?)(\d+)$'
        ]

        for pattern in patterns:
            for field in radio_fields:
                match = re.match(pattern, field.name, re.IGNORECASE)
                if match:
                    base_name = match.group(1).lower().strip('_')
                    option_name = field.name

                    if base_name not in groups:
                        groups[base_name] = []

                    if option_name not in groups[base_name]:
                        groups[base_name].append(option_name)

        # Filter out groups with only one item
        groups = {k: v for k, v in groups.items() if len(v) > 1}

        self.logger.debug(f"Pattern detection found {len(groups)} groups")
        return groups

    def _detect_by_position(self, radio_fields: List[FormField]) -> Dict[str, List[str]]:
        """Detect radio groups by visual positioning."""
        groups = {}

        # Group fields by page and proximity
        page_groups = {}
        for field in radio_fields:
            page = field.position.page
            if page not in page_groups:
                page_groups[page] = []
            page_groups[page].append(field)

        group_id = 0
        for page, fields in page_groups.items():
            # Sort fields by position (top to bottom, left to right)
            fields.sort(key=lambda f: (f.position.y, f.position.x))

            # Group fields that are close to each other
            current_group = []
            last_y = None
            y_threshold = 50  # pixels

            for field in fields:
                if last_y is None or abs(field.position.y - last_y) <= y_threshold:
                    current_group.append(field)
                else:
                    # Start new group if far apart
                    if len(current_group) > 1:
                        group_name = f"position_group_{group_id}"
                        groups[group_name] = [f.name for f in current_group]
                        group_id += 1
                    current_group = [field]

                last_y = field.position.y

            # Don't forget the last group
            if len(current_group) > 1:
                group_name = f"position_group_{group_id}"
                groups[group_name] = [f.name for f in current_group]
                group_id += 1

        self.logger.debug(f"Position detection found {len(groups)} groups")
        return groups

    def _detect_by_labels(self, radio_fields: List[FormField]) -> Dict[str, List[str]]:
        """Detect radio groups by analyzing field labels for common categories."""
        groups = {}

        # Common radio group categories
        category_patterns = {
            'gender': ['male', 'female', 'other', 'm', 'f'],
            'payment_method': ['ach', 'check', 'wire', 'credit', 'debit', 'cash'],
            'frequency': ['monthly', 'quarterly', 'annual', 'weekly', 'daily'],
            'yes_no': ['yes', 'no', 'y', 'n', 'true', 'false'],
            'dividend': ['cash', 'reduce', 'accumulate', 'paid'],
            'withdrawal': ['systematic', 'lump', 'partial', 'full'],
            'marital_status': ['single', 'married', 'divorced', 'widowed'],
            'employment': ['employed', 'retired', 'unemployed', 'student']
        }

        for category, keywords in category_patterns.items():
            category_fields = []

            for field in radio_fields:
                field_text = (field.name + ' ' + field.label).lower()

                # Check if any keyword appears in the field name or label
                for keyword in keywords:
                    if keyword in field_text:
                        category_fields.append(field.name)
                        break

            if len(category_fields) > 1:
                groups[category] = category_fields

        self.logger.debug(f"Label detection found {len(groups)} groups")
        return groups

    def _merge_detection_results(self,
                               pattern_groups: Dict[str, List[str]],
                               position_groups: Dict[str, List[str]],
                               label_groups: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Merge results from different detection strategies."""

        # Start with pattern-based groups (most reliable)
        merged_groups = dict(pattern_groups)

        # Add position-based groups that don't conflict
        for pos_group_name, pos_fields in position_groups.items():
            # Check if any of these fields are already in a pattern group
            already_grouped = any(
                field in existing_fields
                for existing_fields in merged_groups.values()
                for field in pos_fields
            )

            if not already_grouped:
                merged_groups[pos_group_name] = pos_fields

        # Add label-based groups that don't conflict
        for label_group_name, label_fields in label_groups.items():
            # Check if any of these fields are already grouped
            already_grouped = any(
                field in existing_fields
                for existing_fields in merged_groups.values()
                for field in label_fields
            )

            if not already_grouped:
                merged_groups[label_group_name] = label_fields

        # Validate and clean up groups
        validated_groups = {}
        for group_name, field_names in merged_groups.items():
            # Remove duplicates and ensure minimum group size
            unique_fields = list(set(field_names))
            if len(unique_fields) > 1:
                validated_groups[group_name] = unique_fields

        self.logger.info(f"Final merged groups: {len(validated_groups)}")
        return validated_groups


class SmartFieldTypeDetector:
    """Smart field type detection using multiple signals."""

    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".SmartFieldTypeDetector")

    def detect_field_type(self, widget: any) -> FieldType:
        """Smart field type detection using multiple signals."""

        # Signal 1: Widget type analysis (primary signal)
        type_by_widget = self._analyze_widget_type(widget)

        # Signal 2: Field name pattern analysis
        field_name = getattr(widget, 'name', '') or ''
        type_by_name = self._analyze_field_name(field_name)

        # Signal 3: Field properties analysis
        type_by_properties = self._analyze_field_properties(widget)

        # Signal 4: Widget attributes analysis
        type_by_attributes = self._analyze_widget_attributes(widget)

        # Combine signals with confidence scoring
        return self._combine_type_signals(
            type_by_widget, type_by_name, type_by_properties, type_by_attributes
        )

    def _analyze_widget_type(self, widget: any) -> Tuple[FieldType, float]:
        """Analyze widget type (primary signal)."""
        widget_type = type(widget).__name__

        # Map PyPDFForm widget types to our FieldType enum with confidence
        type_mapping = {
            "Text": (FieldType.TEXT_FIELD, 0.9),
            "Checkbox": (FieldType.CHECKBOX, 0.9),
            "Radio": (FieldType.RADIO_BUTTON, 0.9),
            "Dropdown": (FieldType.DROPDOWN, 0.9),
            "Signature": (FieldType.SIGNATURE, 0.9),
            "Button": (FieldType.BUTTON, 0.9),
            "ListBox": (FieldType.LISTBOX, 0.9),
        }

        return type_mapping.get(widget_type, (FieldType.TEXT_FIELD, 0.5))

    def _analyze_field_name(self, field_name: str) -> Tuple[FieldType, float]:
        """Analyze field name patterns."""
        field_name_lower = field_name.lower()

        # Signature field patterns
        signature_patterns = ['signature', 'sign', 'autograph', 'signed']
        if any(pattern in field_name_lower for pattern in signature_patterns):
            return (FieldType.SIGNATURE, 0.8)

        # Date field patterns
        date_patterns = ['date', 'day', 'month', 'year', 'time', 'timestamp']
        if any(pattern in field_name_lower for pattern in date_patterns):
            return (FieldType.TEXT_FIELD, 0.7)  # Dates are typically text fields

        # Checkbox patterns
        checkbox_patterns = ['check', 'box', 'option', 'select', 'yes', 'no', 'agree', 'consent']
        if any(pattern in field_name_lower for pattern in checkbox_patterns):
            return (FieldType.CHECKBOX, 0.6)

        # Radio button patterns
        radio_patterns = ['radio', 'choice', 'group', 'option']
        if any(pattern in field_name_lower for pattern in radio_patterns):
            return (FieldType.RADIO_BUTTON, 0.6)

        # Dropdown patterns
        dropdown_patterns = ['dropdown', 'select', 'list', 'menu', 'combo']
        if any(pattern in field_name_lower for pattern in dropdown_patterns):
            return (FieldType.DROPDOWN, 0.6)

        # Default to text field
        return (FieldType.TEXT_FIELD, 0.3)

    def _analyze_field_properties(self, widget: any) -> Tuple[FieldType, float]:
        """Analyze field properties and characteristics."""

        # Check for choices (indicates dropdown or radio)
        choices = getattr(widget, 'choices', None)
        if choices and len(choices) > 0:
            # If many choices, likely dropdown; if few, likely radio
            if len(choices) > 5:
                return (FieldType.DROPDOWN, 0.7)
            else:
                return (FieldType.RADIO_BUTTON, 0.6)

        # Check multiline property (text field specific)
        multiline = getattr(widget, 'multiline', None)
        if multiline is True:
            return (FieldType.TEXT_FIELD, 0.8)

        # Check max_length (text field specific)
        max_length = getattr(widget, 'max_length', None)
        if max_length is not None and max_length > 0:
            return (FieldType.TEXT_FIELD, 0.7)

        # Check readonly property
        readonly = getattr(widget, 'readonly', None)
        if readonly is True:
            # Readonly fields are often display-only text fields
            return (FieldType.TEXT_FIELD, 0.6)

        return (FieldType.TEXT_FIELD, 0.2)

    def _analyze_widget_attributes(self, widget: any) -> Tuple[FieldType, float]:
        """Analyze specific widget attributes for type hints."""

        # Check for button-specific attributes
        if hasattr(widget, 'action') or hasattr(widget, 'onclick'):
            return (FieldType.BUTTON, 0.7)

        # Check for signature-specific attributes
        if hasattr(widget, 'signature_type') or hasattr(widget, 'ink'):
            return (FieldType.SIGNATURE, 0.8)

        # Check for radio button grouping attributes
        if hasattr(widget, 'group') or hasattr(widget, 'radio_group'):
            return (FieldType.RADIO_BUTTON, 0.7)

        # Check for checkbox-specific attributes
        if hasattr(widget, 'checked') or hasattr(widget, 'check_state'):
            return (FieldType.CHECKBOX, 0.7)

        # Check for text field attributes
        if hasattr(widget, 'text_align') or hasattr(widget, 'font_size'):
            return (FieldType.TEXT_FIELD, 0.6)

        return (FieldType.TEXT_FIELD, 0.1)

    def _combine_type_signals(self,
                             widget_signal: Tuple[FieldType, float],
                             name_signal: Tuple[FieldType, float],
                             properties_signal: Tuple[FieldType, float],
                             attributes_signal: Tuple[FieldType, float]) -> FieldType:
        """Combine signals with confidence scoring."""

        # Create scoring dictionary
        scores = {}

        # Add weighted scores for each signal
        signals = [
            (widget_signal, 1.0),      # Widget type is most reliable
            (name_signal, 0.6),        # Name patterns are moderately reliable
            (properties_signal, 0.8),  # Properties are quite reliable
            (attributes_signal, 0.7)   # Attributes are reliable
        ]

        for (field_type, confidence), weight in signals:
            final_score = confidence * weight
            if field_type not in scores:
                scores[field_type] = 0
            scores[field_type] += final_score

        # Choose the field type with the highest score
        best_type = max(scores.items(), key=lambda x: x[1])

        self.logger.debug(f"Field type scores: {scores}, chosen: {best_type[0]}")
        return best_type[0]

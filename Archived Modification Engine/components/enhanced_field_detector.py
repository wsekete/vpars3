"""
Enhanced PDF Field Detection for Modification Engine

This module provides comprehensive field detection capabilities for the PDF modification
engine, using multiple detection methods to ensure all form fields are discovered.
This is separate from the simplified MCP server architecture.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class FieldDetectionResult:
    """Result of field detection including fields found and metadata."""
    
    def __init__(self):
        self.pypdfform_fields: List[str] = []
        self.pymupdf_fields: List[str] = []
        self.pypdf2_fields: List[str] = []
        self.annotation_fields: List[str] = []
        self.all_fields: Set[str] = set()
        self.field_sources: Dict[str, List[str]] = {}
        self.detection_errors: List[str] = []
        self.detection_warnings: List[str] = []
        
        # Enhanced field analysis
        self.normalized_fields: Dict[str, str] = {}  # normalized_name -> original_name
        self.field_prefixes: Dict[str, str] = {}     # field_name -> prefix
        self.field_types: Dict[str, str] = {}        # field_name -> detected_type
        self.radio_groups: Dict[str, List[str]] = {} # group_name -> [individual_options]
        self.accessible_fields: Set[str] = set()     # fields that can be modified
        
    def add_field(self, field_name: str, source: str) -> None:
        """Add a field with its detection source."""
        self.all_fields.add(field_name)
        if field_name not in self.field_sources:
            self.field_sources[field_name] = []
        self.field_sources[field_name].append(source)
        
    def get_field_count(self) -> int:
        """Get total number of unique fields detected."""
        return len(self.all_fields)
        
    def get_detection_summary(self) -> Dict[str, int]:
        """Get summary of fields detected by each method."""
        return {
            "pypdfform": len(self.pypdfform_fields),
            "pymupdf": len(self.pymupdf_fields),
            "pypdf2": len(self.pypdf2_fields),
            "annotations": len(self.annotation_fields),
            "total_unique": len(self.all_fields)
        }


class EnhancedFieldDetector:
    """Enhanced field detection using multiple methods for comprehensive coverage."""
    
    def __init__(self):
        self.detection_cache: Dict[str, FieldDetectionResult] = {}
        
        # Field normalization patterns
        self.field_prefixes = [
            "OWNER.",
            "PREMIUM_PAYOR.",
            "POLICY_OWNER.",
            "PRIMARY_INSURED.",
            "INSURED.",
            "JOINT_OWNER.",
        ]
        
    def detect_all_fields(self, pdf_path: Path) -> FieldDetectionResult:
        """
        Detect all form fields using multiple detection methods.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            FieldDetectionResult with all detected fields and metadata
        """
        cache_key = str(pdf_path)
        if cache_key in self.detection_cache:
            return self.detection_cache[cache_key]
            
        result = FieldDetectionResult()
        
        # Method 1: PyPDFForm (current primary method)
        try:
            pypdfform_fields = self._detect_pypdfform_fields(pdf_path)
            result.pypdfform_fields = pypdfform_fields
            for field in pypdfform_fields:
                result.add_field(field, "pypdfform")
            logger.info(f"PyPDFForm detected {len(pypdfform_fields)} fields")
        except Exception as e:
            error_msg = f"PyPDFForm detection failed: {e}"
            logger.error(error_msg)
            result.detection_errors.append(error_msg)
            
        # Method 2: PyMuPDF (fallback method)
        try:
            pymupdf_fields = self._detect_pymupdf_fields(pdf_path)
            result.pymupdf_fields = pymupdf_fields
            for field in pymupdf_fields:
                result.add_field(field, "pymupdf")
            logger.info(f"PyMuPDF detected {len(pymupdf_fields)} fields")
        except Exception as e:
            error_msg = f"PyMuPDF detection failed: {e}"
            logger.error(error_msg)
            result.detection_errors.append(error_msg)
            
        # Method 3: pypdf2 (raw PDF dictionary access)
        try:
            pypdf2_fields = self._detect_pypdf2_fields(pdf_path)
            result.pypdf2_fields = pypdf2_fields
            for field in pypdf2_fields:
                result.add_field(field, "pypdf2")
            logger.info(f"pypdf2 detected {len(pypdf2_fields)} fields")
        except Exception as e:
            error_msg = f"pypdf2 detection failed: {e}"
            logger.error(error_msg)
            result.detection_errors.append(error_msg)
            
        # Method 4: Annotation-based detection
        try:
            annotation_fields = self._detect_annotation_fields(pdf_path)
            result.annotation_fields = annotation_fields
            for field in annotation_fields:
                result.add_field(field, "annotations")
            logger.info(f"Annotation detection found {len(annotation_fields)} fields")
        except Exception as e:
            error_msg = f"Annotation detection failed: {e}"
            logger.error(error_msg)
            result.detection_errors.append(error_msg)
            
        # Enhanced field processing
        self._process_field_normalization(result)
        self._analyze_field_types(result)
        self._detect_radio_groups(result)
        self._check_field_accessibility(result, pdf_path)
        
        # Cache and return result
        self.detection_cache[cache_key] = result
        logger.info(f"Total unique fields detected: {result.get_field_count()}")
        logger.info(f"Normalized fields: {len(result.normalized_fields)}")
        logger.info(f"Radio groups found: {len(result.radio_groups)}")
        
        return result
    
    def _detect_pypdfform_fields(self, pdf_path: Path) -> List[str]:
        """Detect fields using PyPDFForm (current primary method)."""
        try:
            from PyPDFForm import PdfWrapper
            pdf = PdfWrapper(str(pdf_path))
            return list(pdf.widgets.keys())
        except ImportError:
            logger.warning("PyPDFForm not available")
            return []
        except Exception as e:
            logger.error(f"PyPDFForm field detection error: {e}")
            return []
    
    def _detect_pymupdf_fields(self, pdf_path: Path) -> List[str]:
        """Detect fields using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(str(pdf_path))
            fields = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get form fields from page
                form_fields = page.widgets()
                for field in form_fields:
                    field_name = field.field_name
                    if field_name and field_name not in fields:
                        fields.append(field_name)
                        
            doc.close()
            return fields
            
        except ImportError:
            logger.warning("PyMuPDF not available")
            return []
        except Exception as e:
            logger.error(f"PyMuPDF field detection error: {e}")
            return []
    
    def _detect_pypdf2_fields(self, pdf_path: Path) -> List[str]:
        """Detect fields using pypdf2/PyPDF2 raw dictionary access."""
        try:
            import pypdf
            
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                fields = []
                
                # Try to access the form fields from the document root
                if reader.trailer.get('/Root') and reader.trailer['/Root'].get('/AcroForm'):
                    acro_form = reader.trailer['/Root']['/AcroForm']
                    if acro_form.get('/Fields'):
                        fields_array = acro_form['/Fields']
                        
                        for field_ref in fields_array:
                            field_obj = field_ref.get_object()
                            field_name = field_obj.get('/T')
                            if field_name:
                                field_name_str = str(field_name)
                                # Clean up field name (remove parentheses and quotes)
                                field_name_str = field_name_str.strip('()')
                                if field_name_str not in fields:
                                    fields.append(field_name_str)
                                    
                                # Also check for child fields
                                if field_obj.get('/Kids'):
                                    kids = field_obj['/Kids']
                                    for kid_ref in kids:
                                        kid_obj = kid_ref.get_object()
                                        kid_name = kid_obj.get('/T')
                                        if kid_name:
                                            kid_name_str = str(kid_name).strip('()')
                                            full_name = f"{field_name_str}.{kid_name_str}"
                                            if full_name not in fields:
                                                fields.append(full_name)
                
                return fields
                
        except ImportError:
            logger.warning("pypdf not available")
            return []
        except Exception as e:
            logger.error(f"pypdf2 field detection error: {e}")
            return []
    
    def _detect_annotation_fields(self, pdf_path: Path) -> List[str]:
        """Detect fields from page annotations."""
        try:
            import fitz  # PyMuPDF for annotation access
            
            doc = fitz.open(str(pdf_path))
            fields = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get annotations from page
                annotations = page.annots()
                for annot in annotations:
                    # Check if annotation is a form field
                    annot_dict = annot.info
                    if annot_dict.get("type") == "Widget":
                        field_name = annot_dict.get("title") or annot_dict.get("name")
                        if field_name and field_name not in fields:
                            fields.append(field_name)
                            
            doc.close()
            return fields
            
        except ImportError:
            logger.warning("PyMuPDF not available for annotation detection")
            return []
        except Exception as e:
            logger.error(f"Annotation field detection error: {e}")
            return []
    
    def generate_field_report(self, result: FieldDetectionResult) -> str:
        """Generate a comprehensive field detection report."""
        report_lines = []
        
        report_lines.append("# Enhanced Field Detection Report")
        report_lines.append("")
        
        # Summary
        summary = result.get_detection_summary()
        report_lines.append("## Detection Summary")
        report_lines.append(f"- **PyPDFForm fields**: {summary['pypdfform']}")
        report_lines.append(f"- **PyMuPDF fields**: {summary['pymupdf']}")
        report_lines.append(f"- **pypdf2 fields**: {summary['pypdf2']}")
        report_lines.append(f"- **Annotation fields**: {summary['annotations']}")
        report_lines.append(f"- **Total unique fields**: {summary['total_unique']}")
        report_lines.append("")
        
        # Fields by detection method
        if result.pypdfform_fields:
            report_lines.append("## PyPDFForm Fields")
            for field in sorted(result.pypdfform_fields):
                report_lines.append(f"- {field}")
            report_lines.append("")
        
        if result.pymupdf_fields:
            report_lines.append("## PyMuPDF Fields")
            for field in sorted(result.pymupdf_fields):
                report_lines.append(f"- {field}")
            report_lines.append("")
        
        if result.pypdf2_fields:
            report_lines.append("## pypdf2 Fields")
            for field in sorted(result.pypdf2_fields):
                report_lines.append(f"- {field}")
            report_lines.append("")
        
        if result.annotation_fields:
            report_lines.append("## Annotation Fields")
            for field in sorted(result.annotation_fields):
                report_lines.append(f"- {field}")
            report_lines.append("")
        
        # Field normalization analysis
        if result.field_prefixes:
            report_lines.append("## Field Normalization")
            report_lines.append("Fields with prefixes that were normalized:")
            for field, prefix in result.field_prefixes.items():
                normalized = field[len(prefix):]
                report_lines.append(f"- **{field}** → **{normalized}** (prefix: `{prefix}`)")
            report_lines.append("")
        
        # Radio group analysis
        if result.radio_groups:
            report_lines.append("## Radio Groups Detected")
            for group, options in result.radio_groups.items():
                report_lines.append(f"- **{group}**:")
                for option in options:
                    report_lines.append(f"  - {option}")
            report_lines.append("")
        
        # Field accessibility
        if result.accessible_fields:
            report_lines.append("## Field Accessibility")
            accessible_count = len(result.accessible_fields)
            total_count = len(result.all_fields)
            report_lines.append(f"**Accessible for modification**: {accessible_count}/{total_count} fields")
            report_lines.append("")
            
            inaccessible_fields = result.all_fields - result.accessible_fields
            if inaccessible_fields:
                report_lines.append("### Inaccessible Fields")
                for field in sorted(inaccessible_fields):
                    field_type = result.field_types.get(field, "unknown")
                    report_lines.append(f"- **{field}** (type: {field_type})")
                report_lines.append("")
        
        # Field types summary
        if result.field_types:
            type_counts = {}
            for field_type in result.field_types.values():
                type_counts[field_type] = type_counts.get(field_type, 0) + 1
            
            report_lines.append("## Field Types Summary")
            for field_type, count in sorted(type_counts.items()):
                report_lines.append(f"- **{field_type}**: {count} fields")
            report_lines.append("")
        
        # Field sources
        report_lines.append("## Field Detection Sources")
        for field in sorted(result.all_fields):
            sources = ", ".join(result.field_sources[field])
            field_type = result.field_types.get(field, "unknown")
            accessible = "✅" if field in result.accessible_fields else "❌"
            report_lines.append(f"- **{field}** ({field_type}) {accessible}: {sources}")
        report_lines.append("")
        
        # Errors and warnings
        if result.detection_errors:
            report_lines.append("## Detection Errors")
            for error in result.detection_errors:
                report_lines.append(f"- ❌ {error}")
            report_lines.append("")
            
        if result.detection_warnings:
            report_lines.append("## Detection Warnings")
            for warning in result.detection_warnings:
                report_lines.append(f"- ⚠️ {warning}")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def suggest_missing_fields(self, 
                             detected_fields: Set[str], 
                             expected_fields: Set[str]) -> Dict[str, List[str]]:
        """
        Suggest mappings for missing fields based on similarity.
        
        Args:
            detected_fields: Set of fields actually detected
            expected_fields: Set of fields expected from mapping
            
        Returns:
            Dictionary mapping missing fields to suggested alternatives
        """
        missing_fields = expected_fields - detected_fields
        suggestions = {}
        
        for missing_field in missing_fields:
            # Find similar fields using string similarity
            similar_fields = []
            for detected_field in detected_fields:
                similarity = self._calculate_similarity(missing_field, detected_field)
                if similarity > 0.3:  # Threshold for similarity
                    similar_fields.append((detected_field, similarity))
            
            # Sort by similarity score
            similar_fields.sort(key=lambda x: x[1], reverse=True)
            suggestions[missing_field] = [field for field, _ in similar_fields[:3]]
        
        return suggestions
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        # Simple character-based similarity
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        # Calculate Jaccard similarity
        set1 = set(str1_lower)
        set2 = set(str2_lower)
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _process_field_normalization(self, result: FieldDetectionResult) -> None:
        """Process field name normalization to handle prefixes."""
        for field_name in result.all_fields:
            normalized_name = field_name
            prefix = ""
            
            # Check for known prefixes
            for prefix_pattern in self.field_prefixes:
                if field_name.startswith(prefix_pattern):
                    prefix = prefix_pattern
                    normalized_name = field_name[len(prefix_pattern):]
                    break
            
            # Store normalization info
            if prefix:
                result.field_prefixes[field_name] = prefix
                result.normalized_fields[normalized_name] = field_name
                logger.debug(f"Normalized '{field_name}' -> '{normalized_name}' (prefix: '{prefix}')")
            else:
                result.normalized_fields[field_name] = field_name
    
    def _analyze_field_types(self, result: FieldDetectionResult) -> None:
        """Analyze and categorize field types."""
        for field_name in result.all_fields:
            field_type = self._determine_field_type(field_name)
            result.field_types[field_name] = field_type
            
    def _determine_field_type(self, field_name: str) -> str:
        """Determine field type based on field name patterns."""
        field_lower = field_name.lower()
        
        # Radio group containers
        if field_name.endswith("--group"):
            return "radio_group"
        
        # Checkbox indicators
        if any(indicator in field_lower for indicator in ["_same", "addr_same", "check"]):
            return "checkbox"
        
        # Signature fields
        if "signature" in field_lower and "date" not in field_lower and "name" not in field_lower:
            return "signature"
        
        # Date fields
        if "date" in field_lower or field_name.endswith("_DATE"):
            return "date"
        
        # Payment/dividend options (likely checkboxes or radio buttons)
        if any(keyword in field_lower for keyword in ["dividend", "payment", "billing", "option"]):
            return "option"
        
        # Default to text field
        return "text"
    
    def _detect_radio_groups(self, result: FieldDetectionResult) -> None:
        """Detect radio groups and their individual options."""
        # Find radio group containers
        group_containers = [field for field in result.all_fields if field.endswith("--group")]
        
        for group_container in group_containers:
            group_base = group_container.replace("--group", "")
            individual_options = []
            
            # Look for related individual fields
            for field_name in result.all_fields:
                if field_name != group_container and group_base in field_name:
                    # Check if it's an individual option (not another group)
                    if not field_name.endswith("--group"):
                        individual_options.append(field_name)
            
            # Store radio group info
            if individual_options:
                result.radio_groups[group_container] = individual_options
                logger.debug(f"Radio group '{group_container}' has options: {individual_options}")
            
        # Special handling for dividend options
        self._detect_dividend_options(result)
    
    def _detect_dividend_options(self, result: FieldDetectionResult) -> None:
        """Detect individual dividend option fields."""
        dividend_fields = []
        
        # Look for dividend-related fields
        for field_name in result.all_fields:
            if "dividend" in field_name.lower() or "DIVIDEND" in field_name:
                dividend_fields.append(field_name)
        
        # Check if we have individual dividend options or just generic fields
        if len(dividend_fields) <= 2:  # Only generic fields like CHANGE_DIVIDEND_OPTION
            # Try to find more specific dividend options
            logger.warning("Only generic dividend fields found, may be missing individual options")
            
            # Look for fields that might be dividend options but not named clearly
            potential_options = []
            for field_name in result.all_fields:
                field_lower = field_name.lower()
                if any(keyword in field_lower for keyword in ["option", "choice", "select"]):
                    potential_options.append(field_name)
            
            if potential_options:
                logger.info(f"Potential dividend option fields: {potential_options}")
    
    def _check_field_accessibility(self, result: FieldDetectionResult, pdf_path: Path) -> None:
        """Check which fields are accessible for modification."""
        # Fields accessible through PyPDFForm are definitely modifiable
        result.accessible_fields.update(result.pypdfform_fields)
        
        # Check if normalized fields from other detection methods match PyPDFForm fields
        pypdfform_set = set(result.pypdfform_fields)
        
        for field_name in result.all_fields:
            if field_name not in pypdfform_set:
                # Check if the normalized version exists in PyPDFForm
                normalized_name = field_name
                for prefix_pattern in self.field_prefixes:
                    if field_name.startswith(prefix_pattern):
                        normalized_name = field_name[len(prefix_pattern):]
                        break
                
                if normalized_name in pypdfform_set:
                    result.accessible_fields.add(field_name)
                    logger.debug(f"Field '{field_name}' accessible via normalized name '{normalized_name}'")
        
        logger.info(f"Accessible fields: {len(result.accessible_fields)} out of {len(result.all_fields)}")
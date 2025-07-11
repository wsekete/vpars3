"""
PDF Form Field Analyzer

Analyzes PDF forms to extract field information and generate BEM-style names
using intelligent pattern recognition and financial services conventions.
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PyPDFForm import PdfWrapper
from pydantic import ValidationError

from .bem_naming import BEMNamingEngine
from .field_types import (
    BatchAnalysis,
    BEMNamingResult,
    FieldPosition,
    FieldType,
    FormAnalysis,
    FormField,
    COMMON_FORM_SECTIONS,
    GROUPED_FIELD_TYPES,
    INTERACTIVE_FIELD_TYPES,
)
from .utils import sanitize_filename, calculate_confidence_score

logger = logging.getLogger(__name__)


class FieldAnalyzer:
    """Analyzes PDF forms and generates BEM-style field names."""
    
    def __init__(self) -> None:
        self.bem_engine = BEMNamingEngine()
        self.field_cache: Dict[str, List[FormField]] = {}
        self.analysis_cache: Dict[str, FormAnalysis] = {}
    
    async def analyze_form(
        self,
        pdf_path: Path,
        analysis_mode: str = "comprehensive",
        custom_sections: Optional[List[str]] = None
    ) -> FormAnalysis:
        """
        Analyze a PDF form and generate BEM field names.
        
        Args:
            pdf_path: Path to the PDF file
            analysis_mode: 'quick' or 'comprehensive'
            custom_sections: Custom section names to prioritize
            
        Returns:
            Complete form analysis with BEM naming results
        """
        try:
            logger.info(f"Analyzing form: {pdf_path}")
            
            # Check cache first
            cache_key = f"{pdf_path}_{analysis_mode}"
            if cache_key in self.analysis_cache:
                logger.info("Using cached analysis")
                return self.analysis_cache[cache_key]
            
            # Extract form fields
            form_fields = await self._extract_form_fields(pdf_path)
            
            # Detect form type and metadata
            form_metadata = await self._detect_form_metadata(pdf_path, form_fields)
            
            # Generate BEM names
            bem_results = await self._generate_bem_names(
                form_fields=form_fields,
                form_metadata=form_metadata,
                analysis_mode=analysis_mode,
                custom_sections=custom_sections
            )
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(bem_results)
            
            # Create analysis result
            analysis = FormAnalysis(
                filename=pdf_path.name,
                form_type=form_metadata.get("form_type"),
                form_id=form_metadata.get("form_id"),
                total_fields=len(form_fields),
                fields=form_fields,
                bem_mappings=bem_results,
                confidence_summary=quality_metrics["confidence_summary"],
                field_type_distribution=quality_metrics["field_type_distribution"],
                naming_conflicts=quality_metrics["naming_conflicts"],
                missing_sections=quality_metrics["missing_sections"],
                review_required=quality_metrics["review_required"],
            )
            
            # Cache result
            self.analysis_cache[cache_key] = analysis
            
            logger.info(f"Analysis complete: {len(form_fields)} fields, {len(bem_results)} BEM names")
            return analysis
            
        except Exception as e:
            logger.exception(f"Error analyzing form {pdf_path}")
            raise RuntimeError(f"Failed to analyze form: {str(e)}") from e
    
    async def batch_analyze_forms(
        self,
        pdf_paths: List[Path],
        consistency_check: bool = True
    ) -> BatchAnalysis:
        """
        Analyze multiple PDF forms in batch.
        
        Args:
            pdf_paths: List of PDF file paths
            consistency_check: Whether to check naming consistency
            
        Returns:
            Batch analysis results
        """
        try:
            logger.info(f"Starting batch analysis of {len(pdf_paths)} forms")
            
            # Analyze all forms concurrently
            analysis_tasks = [
                self.analyze_form(pdf_path, analysis_mode="comprehensive")
                for pdf_path in pdf_paths
            ]
            
            form_analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Filter out failed analyses
            successful_analyses = []
            for i, result in enumerate(form_analyses):
                if isinstance(result, Exception):
                    logger.error(f"Failed to analyze {pdf_paths[i]}: {result}")
                else:
                    successful_analyses.append(result)
            
            # Calculate cross-form metrics
            cross_form_metrics = self._calculate_cross_form_metrics(
                successful_analyses, consistency_check
            )
            
            # Create batch analysis result
            batch_analysis = BatchAnalysis(
                generated_at=datetime.now().isoformat(),
                analyst="claude-sonnet-4",
                forms=successful_analyses,
                common_patterns=cross_form_metrics["common_patterns"],
                naming_consistency=cross_form_metrics["naming_consistency"],
                total_forms=len(successful_analyses),
                total_fields=sum(analysis.total_fields for analysis in successful_analyses),
                overall_confidence=cross_form_metrics["overall_confidence"],
            )
            
            logger.info(f"Batch analysis complete: {len(successful_analyses)} successful")
            return batch_analysis
            
        except Exception as e:
            logger.exception("Error in batch analysis")
            raise RuntimeError(f"Failed to perform batch analysis: {str(e)}") from e
    
    async def _extract_form_fields(self, pdf_path: Path) -> List[FormField]:
        """Extract form fields from PDF using PyPDFForm."""
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
                        type=field_type,
                        form_id=0,  # Will be populated from metadata
                        section_id=None,
                        parent_id=None,
                        order=None,
                        label=self._extract_field_label(widget, field_name),
                        api_name=field_name,
                        custom=False,
                        uuid=f"field_{field_id}",
                        position=position,
                        unified_field_id=None,
                    )
                    
                    form_fields.append(form_field)
                    field_id += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing field {field_name}: {e}")
                    continue
            
            # Cache result
            self.field_cache[cache_key] = form_fields
            
            logger.info(f"Extracted {len(form_fields)} fields from {pdf_path}")
            return form_fields
            
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
        }
        
        return type_mapping.get(widget_type, FieldType.TEXT_FIELD)
    
    def _extract_field_position(self, widget: any) -> FieldPosition:
        """Extract field position from PyPDFForm widget."""
        try:
            # Get widget rectangle (coordinates may vary by widget type)
            rect = getattr(widget, 'rect', None)
            if rect:
                return FieldPosition(
                    x=float(rect[0]),
                    y=float(rect[1]),
                    width=float(rect[2] - rect[0]),
                    height=float(rect[3] - rect[1]),
                    page=0,  # Default to first page
                )
            else:
                # Fallback to default position
                return FieldPosition(x=0, y=0, width=100, height=20, page=0)
                
        except Exception as e:
            logger.warning(f"Error extracting position: {e}")
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
    
    async def _detect_form_metadata(
        self,
        pdf_path: Path,
        form_fields: List[FormField]
    ) -> Dict[str, any]:
        """Detect form type and metadata from PDF content."""
        try:
            metadata = {
                "form_type": None,
                "form_id": None,
                "sections": [],
                "patterns": [],
            }
            
            # Analyze field names for patterns
            field_names = [field.api_name for field in form_fields]
            labels = [field.label for field in form_fields]
            
            # Detect form type from field patterns
            form_type = self._detect_form_type(field_names, labels)
            metadata["form_type"] = form_type
            
            # Extract form ID from filename or fields
            form_id = self._extract_form_id(pdf_path, field_names)
            metadata["form_id"] = form_id
            
            # Detect sections
            sections = self._detect_sections(field_names, labels)
            metadata["sections"] = sections
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Error detecting form metadata: {e}")
            return {"form_type": None, "form_id": None, "sections": [], "patterns": []}
    
    def _detect_form_type(self, field_names: List[str], labels: List[str]) -> Optional[str]:
        """Detect form type from field names and labels."""
        all_text = " ".join(field_names + labels).lower()
        
        # Common form type patterns
        form_patterns = {
            "Life Policy Owner's Service Request": [
                "owner", "policy", "service", "request", "life", "beneficiary"
            ],
            "Change of Address": [
                "address", "change", "mailing", "residence", "contact"
            ],
            "Withdrawal Request": [
                "withdrawal", "distribution", "amount", "frequency", "payment"
            ],
            "Name Change Request": [
                "name", "change", "marriage", "divorce", "legal"
            ],
            "Beneficiary Designation": [
                "beneficiary", "primary", "contingent", "designation", "percentage"
            ],
        }
        
        # Find best matching form type
        best_match = None
        best_score = 0
        
        for form_type, keywords in form_patterns.items():
            score = sum(1 for keyword in keywords if keyword in all_text)
            if score > best_score:
                best_score = score
                best_match = form_type
        
        return best_match if best_score >= 2 else None
    
    def _extract_form_id(self, pdf_path: Path, field_names: List[str]) -> Optional[str]:
        """Extract form ID from filename or field names."""
        # Try to extract from filename
        filename = pdf_path.stem
        
        # Look for common form ID patterns
        form_id_patterns = [
            r'(\d{4}[A-Z]?)',  # 1234A format
            r'([A-Z]{2,4}-\d{4})',  # ABC-1234 format
            r'(Form[_-]?\d+)',  # Form123 format
        ]
        
        for pattern in form_id_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Try to extract from field names
        for field_name in field_names:
            for pattern in form_id_patterns:
                match = re.search(pattern, field_name, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    
    def _detect_sections(self, field_names: List[str], labels: List[str]) -> List[str]:
        """Detect form sections from field names and labels."""
        sections = set()
        
        # Check field names and labels for section indicators
        for text in field_names + labels:
            text_lower = text.lower()
            
            # Check against common section patterns
            for section_name, keywords in COMMON_FORM_SECTIONS.items():
                if any(keyword in text_lower for keyword in keywords):
                    sections.add(section_name)
        
        return sorted(sections)
    
    async def _generate_bem_names(
        self,
        form_fields: List[FormField],
        form_metadata: Dict[str, any],
        analysis_mode: str,
        custom_sections: Optional[List[str]] = None
    ) -> List[BEMNamingResult]:
        """Generate BEM names for form fields."""
        try:
            logger.info(f"Generating BEM names for {len(form_fields)} fields")
            
            # Group fields by detected sections
            sections = custom_sections or form_metadata.get("sections", [])
            
            # Generate BEM names using the naming engine
            bem_results = []
            
            for field in form_fields:
                try:
                    # Determine field section
                    field_section = self._determine_field_section(field, sections)
                    
                    # Generate BEM name
                    bem_name = self.bem_engine.generate_bem_name(
                        field=field,
                        section=field_section,
                        context={
                            "form_type": form_metadata.get("form_type"),
                            "form_id": form_metadata.get("form_id"),
                            "existing_names": [r.bem_name for r in bem_results],
                        }
                    )
                    
                    # Calculate confidence
                    confidence = self._calculate_naming_confidence(field, bem_name, field_section)
                    
                    # Create result
                    result = BEMNamingResult(
                        original_name=field.api_name,
                        bem_name=bem_name,
                        confidence=confidence,
                        reasoning=self._generate_naming_reasoning(field, bem_name, field_section),
                        section=field_section,
                        field_type=field.type,
                        is_radio_group=field.type in GROUPED_FIELD_TYPES,
                        needs_review=confidence == "low",
                    )
                    
                    bem_results.append(result)
                    
                except Exception as e:
                    logger.warning(f"Error generating BEM name for {field.api_name}: {e}")
                    # Create fallback result
                    bem_results.append(BEMNamingResult(
                        original_name=field.api_name,
                        bem_name=field.api_name,
                        confidence="low",
                        reasoning="Failed to generate BEM name",
                        section="unknown",
                        field_type=field.type,
                        needs_review=True,
                    ))
            
            # Check for naming conflicts
            self._check_naming_conflicts(bem_results)
            
            logger.info(f"Generated {len(bem_results)} BEM names")
            return bem_results
            
        except Exception as e:
            logger.exception("Error generating BEM names")
            raise RuntimeError(f"Failed to generate BEM names: {str(e)}") from e
    
    def _determine_field_section(self, field: FormField, sections: List[str]) -> str:
        """Determine which section a field belongs to."""
        field_text = f"{field.api_name} {field.label}".lower()
        
        # Check against known sections
        for section in sections:
            if section in COMMON_FORM_SECTIONS:
                keywords = COMMON_FORM_SECTIONS[section]
                if any(keyword in field_text for keyword in keywords):
                    return section
        
        # Check against generic patterns
        if any(word in field_text for word in ["name", "first", "last", "owner"]):
            return "owner-information"
        elif any(word in field_text for word in ["address", "street", "city", "state"]):
            return "address"
        elif any(word in field_text for word in ["sign", "signature", "date"]):
            return "signatures"
        elif any(word in field_text for word in ["beneficiary", "contingent"]):
            return "beneficiary"
        elif any(word in field_text for word in ["payment", "bank", "account"]):
            return "payment"
        else:
            return "general"
    
    def _calculate_naming_confidence(
        self, field: FormField, bem_name: str, section: str
    ) -> str:
        """Calculate confidence level for BEM name generation."""
        score = 0
        
        # Field type confidence
        if field.type in INTERACTIVE_FIELD_TYPES:
            score += 2
        else:
            score += 1
        
        # Section confidence
        if section in COMMON_FORM_SECTIONS:
            score += 2
        elif section != "unknown":
            score += 1
        
        # BEM format confidence
        if self.bem_engine.validate_bem_name(bem_name):
            score += 2
        
        # Label quality confidence
        if field.label and len(field.label) > 3:
            score += 1
        
        # Convert score to confidence level
        if score >= 6:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"
    
    def _generate_naming_reasoning(
        self, field: FormField, bem_name: str, section: str
    ) -> str:
        """Generate explanation for BEM naming decision."""
        parts = []
        
        # Section reasoning
        if section in COMMON_FORM_SECTIONS:
            parts.append(f"Categorized as '{section}' based on field context")
        
        # Field type reasoning
        if field.type in GROUPED_FIELD_TYPES:
            parts.append(f"Grouped field type ({field.type.value}) with appropriate suffix")
        
        # BEM format reasoning
        if "_" in bem_name:
            parts.append("Follows BEM block_element format")
        if "__" in bem_name:
            parts.append("Includes modifier for field variation")
        if "--group" in bem_name:
            parts.append("Uses --group suffix for radio button container")
        
        return ". ".join(parts) if parts else "Standard field naming applied"
    
    def _check_naming_conflicts(self, bem_results: List[BEMNamingResult]) -> None:
        """Check for naming conflicts and mark fields that need review."""
        name_counts = {}
        
        # Count occurrences of each name
        for result in bem_results:
            name_counts[result.bem_name] = name_counts.get(result.bem_name, 0) + 1
        
        # Mark conflicting names
        for result in bem_results:
            if name_counts[result.bem_name] > 1:
                result.needs_review = True
                result.conflicts_with = [
                    other.original_name for other in bem_results
                    if other.bem_name == result.bem_name and other.original_name != result.original_name
                ]
                if result.confidence != "low":
                    result.confidence = "medium"  # Downgrade confidence for conflicts
    
    def _calculate_quality_metrics(self, bem_results: List[BEMNamingResult]) -> Dict[str, any]:
        """Calculate quality metrics for BEM naming results."""
        metrics = {
            "confidence_summary": {"high": 0, "medium": 0, "low": 0},
            "field_type_distribution": {},
            "naming_conflicts": [],
            "missing_sections": [],
            "review_required": [],
        }
        
        # Count confidence levels
        for result in bem_results:
            metrics["confidence_summary"][result.confidence] += 1
        
        # Count field types
        for result in bem_results:
            field_type = result.field_type
            metrics["field_type_distribution"][field_type] = (
                metrics["field_type_distribution"].get(field_type, 0) + 1
            )
        
        # Collect conflicts and review items
        for result in bem_results:
            if result.conflicts_with:
                metrics["naming_conflicts"].append(result.original_name)
            
            if result.section == "unknown":
                metrics["missing_sections"].append(result.original_name)
            
            if result.needs_review:
                metrics["review_required"].append(result.original_name)
        
        return metrics
    
    def _calculate_cross_form_metrics(
        self, analyses: List[FormAnalysis], consistency_check: bool
    ) -> Dict[str, any]:
        """Calculate cross-form consistency metrics."""
        metrics = {
            "common_patterns": {},
            "naming_consistency": {},
            "overall_confidence": {"high": 0, "medium": 0, "low": 0},
        }
        
        # Aggregate confidence scores
        for analysis in analyses:
            for level, count in analysis.confidence_summary.items():
                metrics["overall_confidence"][level] += count
        
        if not consistency_check:
            return metrics
        
        # Find common naming patterns
        all_bem_names = []
        for analysis in analyses:
            all_bem_names.extend([result.bem_name for result in analysis.bem_mappings])
        
        # Group by BEM patterns
        pattern_groups = {}
        for name in all_bem_names:
            # Extract pattern (block_element part)
            if "_" in name:
                pattern = name.split("__")[0]  # Remove modifiers
                pattern_groups[pattern] = pattern_groups.get(pattern, 0) + 1
        
        # Keep patterns that appear in multiple forms
        metrics["common_patterns"] = {
            pattern: count for pattern, count in pattern_groups.items()
            if count > 1
        }
        
        # Calculate naming consistency scores
        if len(analyses) > 1:
            similar_fields = self._find_similar_fields(analyses)
            for field_group, names in similar_fields.items():
                if len(names) > 1:
                    # Calculate consistency score (0-1)
                    unique_names = set(names)
                    consistency_score = 1.0 - (len(unique_names) - 1) / len(names)
                    metrics["naming_consistency"][field_group] = consistency_score
        
        return metrics
    
    def _find_similar_fields(self, analyses: List[FormAnalysis]) -> Dict[str, List[str]]:
        """Find similar fields across forms for consistency checking."""
        similar_fields = {}
        
        # Group fields by label similarity
        for analysis in analyses:
            for result in analysis.bem_mappings:
                # Create a normalized key for grouping
                label_key = self._normalize_label(result.original_name)
                
                if label_key not in similar_fields:
                    similar_fields[label_key] = []
                
                similar_fields[label_key].append(result.bem_name)
        
        # Only return groups with multiple entries
        return {
            key: names for key, names in similar_fields.items()
            if len(names) > 1
        }
    
    def _normalize_label(self, label: str) -> str:
        """Normalize field label for similarity matching."""
        # Remove common prefixes/suffixes and normalize
        normalized = label.lower()
        normalized = re.sub(r'^(text|input|field|box|button)_?', '', normalized)
        normalized = re.sub(r'_?(field|box|button|input)$', '', normalized)
        normalized = re.sub(r'[_\-\s]+', '_', normalized)
        normalized = re.sub(r'^\d+_?', '', normalized)  # Remove leading numbers
        
        return normalized.strip('_')

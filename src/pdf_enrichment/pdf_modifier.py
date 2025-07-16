"""
PDF Field Modifier

Modifies PDF form fields using PyPDFForm while preserving all field properties,
positions, and types. Supports BEM name mapping and validation.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from PyPDFForm import PdfWrapper

from .field_types import FieldModificationResult, FieldType
from .utils import backup_file, validate_file_path

logger = logging.getLogger(__name__)


class PDFModifier:
    """Modifies PDF form fields while preserving all properties."""
    
    def __init__(self) -> None:
        self.modification_cache: Dict[str, FieldModificationResult] = {}
        
        # Field property preservation settings
        self.preserve_properties = {
            "font": True,
            "font_size": True,
            "font_color": True,
            "bg_color": True,
            "border_color": True,
            "border_width": True,
            "alignment": True,
            "size": True,
            "position": True,
            "readonly": True,
            "required": True,
            "choices": True,
            "max_length": True,
            "multiline": True,
            "button_style": True,
            "tick_color": True,
        }
    
    async def modify_fields(
        self,
        pdf_path: Path,
        field_mappings: Dict[str, str],
        output_path: Optional[Path] = None,
        preserve_original: bool = True,
        validate_mappings: bool = True,
        create_backup: bool = True,
    ) -> FieldModificationResult:
        """
        Modify PDF form fields using BEM name mappings.
        
        Args:
            pdf_path: Path to the source PDF file
            field_mappings: Dictionary mapping original field names to new BEM names
            output_path: Path for the modified PDF (optional)
            preserve_original: Whether to keep the original file unchanged
            validate_mappings: Whether to validate BEM name format
            create_backup: Whether to create a backup of the original
            
        Returns:
            FieldModificationResult with modification details and status
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # Validate input parameters
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            if not field_mappings:
                raise ValueError("No field mappings provided")
            
            # Set up output path
            if output_path is None:
                output_path = pdf_path.with_stem(f"{pdf_path.stem}_bem_renamed")
            
            # Validate file paths
            validate_file_path(pdf_path)
            validate_file_path(output_path.parent, create_if_missing=True)
            
            logger.info(f"Starting field modification: {pdf_path} -> {output_path}")
            
            # Create backup if requested
            backup_path = None
            if create_backup and not preserve_original:
                backup_path = backup_file(pdf_path)
                logger.info(f"Created backup: {backup_path}")
            
            # Load PDF with PyPDFForm
            try:
                pdf = PdfWrapper(str(pdf_path))
                logger.info(f"Successfully loaded PDF: {pdf_path}")
            except Exception as e:
                logger.error(f"Failed to load PDF {pdf_path}: {str(e)}")
                raise RuntimeError(f"Failed to load PDF: {str(e)}") from e
            
            # Get initial field count and analyze form structure
            field_count_before = len(pdf.widgets)
            logger.info(f"PDF has {field_count_before} form fields")
            
            # Log actual field names for debugging
            actual_field_names = list(pdf.widgets.keys())
            logger.info(f"Actual PDF field names: {actual_field_names[:10]}{'...' if len(actual_field_names) > 10 else ''}")
            
            # Log PyPDFForm method availability
            logger.info(f"PyPDFForm methods available: update_widget_key={hasattr(pdf, 'update_widget_key')}, "
                       f"commit_widget_key_updates={hasattr(pdf, 'commit_widget_key_updates')}")
            
            # Log field mappings to be applied
            logger.info(f"Attempting to apply {len(field_mappings)} field mappings")
            for original, bem_name in list(field_mappings.items())[:5]:
                logger.debug(f"  Mapping: '{original}' → '{bem_name}'")
            if len(field_mappings) > 5:
                logger.debug(f"  ... and {len(field_mappings) - 5} more mappings")
            
            # Validate field mappings
            if validate_mappings:
                logger.info("Validating field mappings...")
                validation_errors = self._validate_field_mappings(pdf, field_mappings)
                if validation_errors:
                    logger.error(f"Field mapping validation failed: {validation_errors}")
                    raise ValueError(f"Invalid field mappings: {'; '.join(validation_errors)}")
                else:
                    logger.info("Field mapping validation passed")
            
            # Perform field modifications
            logger.info("Starting field modification process...")
            modifications, errors, warnings = await self._apply_field_modifications(
                pdf, field_mappings
            )
            
            logger.info(f"Field modification completed: {len(modifications)} successful, {len(errors)} errors, {len(warnings)} warnings")
            if errors:
                logger.error(f"Modification errors: {errors}")
            if warnings:
                logger.warning(f"Modification warnings: {warnings}")
            
            # Save modified PDF
            logger.info(f"Saving modified PDF to: {output_path}")
            try:
                if preserve_original:
                    logger.debug("Preserving original, creating copy for modification")
                    # Copy original to output path first
                    shutil.copy2(pdf_path, output_path)
                    # Create new PDF wrapper for the copy
                    pdf_copy = PdfWrapper(str(output_path))
                    # Apply modifications to the copy
                    _, _, _ = await self._apply_field_modifications(pdf_copy, field_mappings)
                    pdf_copy.write(str(output_path))
                else:
                    logger.debug("Modifying original PDF directly")
                    # Write directly to output path
                    pdf.write(str(output_path))
                
                logger.info(f"Successfully saved modified PDF: {output_path}")
            except Exception as e:
                logger.error(f"Failed to save modified PDF: {str(e)}")
                raise RuntimeError(f"Failed to save modified PDF: {str(e)}") from e
            
            # Verify modifications
            try:
                verification_pdf = PdfWrapper(str(output_path))
                field_count_after = len(verification_pdf.widgets)
                logger.info(f"Verification: Modified PDF has {field_count_after} fields")
            except Exception as e:
                logger.error(f"Failed to verify modified PDF: {str(e)}")
                field_count_after = 0
            
            # Create result
            result = FieldModificationResult(
                original_pdf_path=str(pdf_path),
                modified_pdf_path=str(output_path),
                modifications=modifications,
                success=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                timestamp=timestamp,
                field_count_before=field_count_before,
                field_count_after=field_count_after,
            )
            
            # Cache result
            cache_key = f"{pdf_path}_{hash(frozenset(field_mappings.items()))}"
            self.modification_cache[cache_key] = result
            
            logger.info(f"Field modification completed: {len(modifications)} changes, {len(errors)} errors")
            return result
            
        except FileNotFoundError as e:
            logger.error(f"PDF file not found: {pdf_path}")
            return FieldModificationResult(
                original_pdf_path=str(pdf_path),
                modified_pdf_path=str(output_path) if output_path else "",
                modifications=[],
                success=False,
                errors=[f"PDF file not found: {pdf_path}"],
                warnings=[],
                timestamp=timestamp,
                field_count_before=0,
                field_count_after=0,
            )
        except PermissionError as e:
            logger.error(f"Permission denied accessing PDF: {pdf_path}")
            return FieldModificationResult(
                original_pdf_path=str(pdf_path),
                modified_pdf_path=str(output_path) if output_path else "",
                modifications=[],
                success=False,
                errors=[f"Permission denied accessing PDF: {pdf_path}"],
                warnings=[],
                timestamp=timestamp,
                field_count_before=0,
                field_count_after=0,
            )
        except ValueError as e:
            logger.error(f"Invalid field mappings for {pdf_path}: {e}")
            return FieldModificationResult(
                original_pdf_path=str(pdf_path),
                modified_pdf_path=str(output_path) if output_path else "",
                modifications=[],
                success=False,
                errors=[f"Invalid field mappings: {str(e)}"],
                warnings=[],
                timestamp=timestamp,
                field_count_before=0,
                field_count_after=0,
            )
        except Exception as e:
            logger.exception(f"Error modifying fields in {pdf_path}")
            return FieldModificationResult(
                original_pdf_path=str(pdf_path),
                modified_pdf_path=str(output_path) if output_path else "",
                modifications=[],
                success=False,
                errors=[str(e)],
                warnings=[],
                timestamp=timestamp,
                field_count_before=0,
                field_count_after=0,
            )
    
    def _validate_field_mappings(
        self, pdf: PdfWrapper, field_mappings: Dict[str, str]
    ) -> List[str]:
        """Validate field mappings against the PDF form."""
        errors = []
        
        # Get existing field names
        existing_fields = set(pdf.widgets.keys())
        logger.info(f"PDF contains {len(existing_fields)} fields: {sorted(list(existing_fields))[:10]}{'...' if len(existing_fields) > 10 else ''}")
        
        # Check for missing source fields
        missing_fields = []
        for original_name in field_mappings:
            if original_name not in existing_fields:
                missing_fields.append(original_name)
                errors.append(f"Source field '{original_name}' not found in PDF")
        
        if missing_fields:
            logger.error(f"Missing source fields: {missing_fields[:5]}{'...' if len(missing_fields) > 5 else ''}")
            
            # Try to find similar field names
            for missing_field in missing_fields[:5]:
                similar_fields = [field for field in existing_fields if missing_field.lower() in field.lower() or field.lower() in missing_field.lower()]
                if similar_fields:
                    logger.info(f"Possible matches for '{missing_field}': {similar_fields[:3]}")
        
        # Check for duplicate target names
        target_names = list(field_mappings.values())
        duplicates = set(name for name in target_names if target_names.count(name) > 1)
        if duplicates:
            logger.error(f"Duplicate target names found: {duplicates}")
            errors.append(f"Duplicate target names: {', '.join(duplicates)}")
        
        # Check for invalid BEM names
        invalid_names = []
        for original_name, bem_name in field_mappings.items():
            if not self._is_valid_bem_name(bem_name):
                invalid_names.append(f"'{original_name}' -> '{bem_name}'")
        
        if invalid_names:
            logger.error(f"Invalid BEM names: {invalid_names[:3]}{'...' if len(invalid_names) > 3 else ''}")
            errors.append(f"Invalid BEM names: {'; '.join(invalid_names)}")
        
        # Log validation summary
        valid_mappings = len(field_mappings) - len(missing_fields)
        logger.info(f"Field validation summary: {valid_mappings}/{len(field_mappings)} mappings are valid")
        
        return errors
    
    def _is_valid_bem_name(self, name: str) -> bool:
        """Check if a name follows BEM conventions."""
        import re
        
        # Flexible BEM pattern supporting full hierarchy:
        # - block (e.g., dividend-option)
        # - block_element (e.g., dividend-option_cash)
        # - block__modifier (e.g., dividend-option__cash)
        # - block_element__modifier (e.g., name-change_reason__marriage)
        # - block--group (e.g., dividend-option--group)
        # - block_element--group (e.g., payment-method_options--group)
        # 
        # Pattern breakdown:
        # - ^[a-z][a-z0-9-]*           : block (starts with letter, allows hyphens)
        # - (?:_[a-z][a-z0-9-]*)?      : optional element (underscore + name)
        # - (?:__[a-z][a-z0-9-]*|--group)? : optional modifier OR group suffix
        # - $                          : end of string
        
        bem_pattern = r'^[a-z][a-z0-9-]*(?:_[a-z][a-z0-9-]*)?(?:__[a-z][a-z0-9-]*|--group)?$'
        
        return re.match(bem_pattern, name) is not None
    
    async def _apply_field_modifications(
        self, pdf: PdfWrapper, field_mappings: Dict[str, str]
    ) -> Tuple[List[Dict[str, Union[str, int]]], List[str], List[str]]:
        """Apply field modifications to the PDF."""
        modifications = []
        errors = []
        warnings = []
        
        # Process each field mapping
        total_mappings = len(field_mappings)
        processed_count = 0
        
        for original_name, bem_name in field_mappings.items():
            processed_count += 1
            logger.debug(f"Processing field {processed_count}/{total_mappings}: '{original_name}' → '{bem_name}'")
            
            try:
                # Check if field exists
                if original_name not in pdf.widgets:
                    error_msg = f"Field '{original_name}' not found in PDF"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Get the widget
                widget = pdf.widgets[original_name]
                logger.debug(f"Found widget for '{original_name}': {type(widget).__name__}")
                
                # Store original properties
                original_properties = self._extract_widget_properties(widget)
                logger.debug(f"Extracted {len(original_properties)} properties from '{original_name}'")
                
                # Determine field type
                field_type = self._get_field_type_from_widget(widget)
                logger.debug(f"Field type for '{original_name}': {field_type.value}")
                
                # Check if update_widget_key method exists
                if not hasattr(pdf, 'update_widget_key'):
                    error_msg = f"PyPDFForm method 'update_widget_key' not available"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    break
                
                # Update field key using PyPDFForm's method
                try:
                    logger.debug(f"Calling pdf.update_widget_key('{original_name}', '{bem_name}')")
                    pdf.update_widget_key(original_name, bem_name)
                    
                    # Verify the change was applied
                    if bem_name in pdf.widgets:
                        logger.debug(f"Successfully renamed field: '{original_name}' → '{bem_name}'")
                        
                        # Restore properties to the renamed widget
                        new_widget = pdf.widgets[bem_name]
                        self._restore_widget_properties(new_widget, original_properties)
                        
                        # Record successful modification
                        modifications.append({
                            "old": original_name,
                            "new": bem_name,
                            "type": field_type.value,
                            "page": original_properties.get("page", 0),
                            "preserved_properties": len(original_properties),
                        })
                        
                        logger.info(f"✅ Successfully renamed '{original_name}' to '{bem_name}'")
                    else:
                        error_msg = f"Failed to rename '{original_name}' to '{bem_name}': field not found after rename"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                except AttributeError as e:
                    error_msg = f"PyPDFForm method error for '{original_name}' → '{bem_name}': {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                except ValueError as e:
                    error_msg = f"Invalid value for '{original_name}' → '{bem_name}': {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error renaming '{original_name}' to '{bem_name}': {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    logger.exception(f"Unexpected error during field rename: {original_name} -> {bem_name}")
                    
            except (AttributeError, ValueError, TypeError) as e:
                error_msg = f"Error processing field '{original_name}': {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error processing field '{original_name}': {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                logger.exception(f"Unexpected error processing field: {original_name}")
        
        logger.info(f"Field processing complete: {len(modifications)} successful, {len(errors)} failed")
        
        # Commit all widget key updates
        if hasattr(pdf, 'commit_widget_key_updates'):
            try:
                logger.info("Committing widget key updates...")
                pdf.commit_widget_key_updates()
                logger.info("Widget key updates committed successfully")
            except (AttributeError, ValueError) as e:
                warning_msg = f"Warning during commit: {str(e)}"
                logger.warning(warning_msg)
                warnings.append(warning_msg)
            except Exception as e:
                warning_msg = f"Unexpected error during commit: {str(e)}"
                logger.error(warning_msg)
                warnings.append(warning_msg)
                logger.exception("Unexpected error during widget key updates commit")
        else:
            warning_msg = "PyPDFForm method 'commit_widget_key_updates' not available"
            logger.warning(warning_msg)
            warnings.append(warning_msg)
        
        return modifications, errors, warnings
    
    def _extract_widget_properties(self, widget: any) -> Dict[str, any]:
        """Extract all properties from a widget for preservation."""
        properties = {}
        
        # Try to extract each property we want to preserve
        for prop_name in self.preserve_properties:
            if self.preserve_properties[prop_name]:
                try:
                    value = getattr(widget, prop_name, None)
                    if value is not None:
                        properties[prop_name] = value
                except Exception as e:
                    logger.debug(f"Could not extract property {prop_name}: {e}")
        
        # Try to extract additional properties
        additional_props = [
            "rect", "bbox", "rotation", "quadding", "flags", "annotation_flags",
            "border_style", "border_dash", "border_effect", "parent", "kids",
            "default_value", "value", "export_value", "choices", "ti", "tu",
            "tm", "ff", "q", "bs", "mk", "ap", "as", "blend_mode", "ca", "ca_ns",
            "da", "dr", "quadding", "rc", "ds", "rv", "opt", "top_index", "i",
            "lock", "sv", "dv", "aa", "bl", "ca", "ca_ns", "e", "f", "fb", "fs",
            "g", "le", "lw", "ml", "ri", "s", "ss", "w", "sound", "movie",
            "screen", "widget", "highlight", "popup", "ink", "file_attachment",
            "stamp", "caret", "text", "free_text", "line", "square", "circle",
            "polygon", "poly_line", "watermark", "threed", "redact", "printer_mark",
            "trap_net", "unknown",
        ]
        
        for prop_name in additional_props:
            try:
                value = getattr(widget, prop_name, None)
                if value is not None:
                    properties[prop_name] = value
            except Exception:
                pass  # Ignore missing properties
        
        return properties
    
    def _restore_widget_properties(self, widget: any, properties: Dict[str, any]) -> None:
        """Restore properties to a widget after renaming."""
        for prop_name, value in properties.items():
            try:
                # Only restore if the property exists and is settable
                if hasattr(widget, prop_name):
                    setattr(widget, prop_name, value)
            except Exception as e:
                logger.debug(f"Could not restore property {prop_name}: {e}")
    
    def _get_field_type_from_widget(self, widget: any) -> FieldType:
        """Determine field type from PyPDFForm widget."""
        widget_type = type(widget).__name__
        
        # Map PyPDFForm widget types to our FieldType enum
        type_mapping = {
            "Text": FieldType.TEXT_FIELD,
            "Checkbox": FieldType.CHECKBOX,
            "Radio": FieldType.RADIO_BUTTON,
            "Dropdown": FieldType.DROPDOWN,
            "Signature": FieldType.SIGNATURE,
            "ListBox": FieldType.DROPDOWN,
            "Button": FieldType.CHECKBOX,  # Could be button or checkbox
            "TextField": FieldType.TEXT_FIELD,
            "CheckboxField": FieldType.CHECKBOX,
            "RadioField": FieldType.RADIO_BUTTON,
            "DropdownField": FieldType.DROPDOWN,
            "SignatureField": FieldType.SIGNATURE,
        }
        
        return type_mapping.get(widget_type, FieldType.TEXT_FIELD)
    
    def validate_modification_result(
        self, result: FieldModificationResult, expected_mappings: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """Validate that modifications were applied correctly."""
        validation_errors = []
        
        try:
            # Check that output file exists
            if not Path(result.modified_pdf_path).exists():
                validation_errors.append("Modified PDF file does not exist")
                return False, validation_errors
            
            # Load the modified PDF
            modified_pdf = PdfWrapper(result.modified_pdf_path)
            modified_fields = set(modified_pdf.widgets.keys())
            
            # Check that all expected fields are present
            for original_name, bem_name in expected_mappings.items():
                if bem_name not in modified_fields:
                    validation_errors.append(f"Expected field '{bem_name}' not found in modified PDF")
            
            # Check field count consistency
            if result.field_count_after != len(modified_fields):
                validation_errors.append(
                    f"Field count mismatch: expected {result.field_count_after}, "
                    f"found {len(modified_fields)}"
                )
            
            # Check that no original field names remain (unless they weren't mapped)
            original_names = set(expected_mappings.keys())
            remaining_original = original_names.intersection(modified_fields)
            if remaining_original:
                validation_errors.append(
                    f"Original field names still present: {', '.join(remaining_original)}"
                )
            
        except Exception as e:
            validation_errors.append(f"Validation error: {str(e)}")
        
        return len(validation_errors) == 0, validation_errors
    
    def get_field_differences(
        self, original_pdf_path: Path, modified_pdf_path: Path
    ) -> Dict[str, any]:
        """Compare fields between original and modified PDFs."""
        try:
            original_pdf = PdfWrapper(str(original_pdf_path))
            modified_pdf = PdfWrapper(str(modified_pdf_path))
            
            original_fields = set(original_pdf.widgets.keys())
            modified_fields = set(modified_pdf.widgets.keys())
            
            return {
                "original_count": len(original_fields),
                "modified_count": len(modified_fields),
                "added_fields": list(modified_fields - original_fields),
                "removed_fields": list(original_fields - modified_fields),
                "common_fields": list(original_fields & modified_fields),
                "field_mappings": self._infer_field_mappings(original_fields, modified_fields),
            }
            
        except Exception as e:
            logger.exception("Error comparing PDF fields")
            return {
                "error": str(e),
                "original_count": 0,
                "modified_count": 0,
                "added_fields": [],
                "removed_fields": [],
                "common_fields": [],
                "field_mappings": {},
            }
    
    def _infer_field_mappings(
        self, original_fields: set, modified_fields: set
    ) -> Dict[str, str]:
        """Infer field mappings by comparing field names."""
        mappings = {}
        
        # Simple heuristic: match fields that are similar
        for original_name in original_fields:
            if original_name not in modified_fields:
                # Find the most similar field in modified fields
                best_match = None
                best_score = 0
                
                for modified_name in modified_fields:
                    if modified_name not in original_fields:
                        # Calculate similarity score
                        score = self._calculate_name_similarity(original_name, modified_name)
                        if score > best_score:
                            best_score = score
                            best_match = modified_name
                
                if best_match and best_score > 0.3:  # Threshold for similarity
                    mappings[original_name] = best_match
        
        return mappings
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two field names."""
        # Simple similarity based on character overlap
        set1 = set(name1.lower())
        set2 = set(name2.lower())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def create_field_mapping_report(
        self, result: FieldModificationResult, include_properties: bool = False
    ) -> str:
        """Create a human-readable report of field modifications."""
        report_lines = []
        
        report_lines.append("# PDF Field Modification Report")
        report_lines.append(f"**Generated:** {result.timestamp}")
        report_lines.append(f"**Original PDF:** {result.original_pdf_path}")
        report_lines.append(f"**Modified PDF:** {result.modified_pdf_path}")
        report_lines.append("")
        
        # Summary
        report_lines.append("## Summary")
        report_lines.append(f"- **Status:** {'✅ Success' if result.success else '❌ Failed'}")
        report_lines.append(f"- **Fields Modified:** {len(result.modifications)}")
        report_lines.append(f"- **Fields Before:** {result.field_count_before}")
        report_lines.append(f"- **Fields After:** {result.field_count_after}")
        report_lines.append(f"- **Errors:** {len(result.errors)}")
        report_lines.append(f"- **Warnings:** {len(result.warnings)}")
        report_lines.append("")
        
        # Modifications
        if result.modifications:
            report_lines.append("## Field Modifications")
            report_lines.append("| Original Name | New BEM Name | Type | Page | Properties |")
            report_lines.append("|---------------|--------------|------|------|------------|")
            
            for mod in result.modifications:
                properties_count = mod.get("preserved_properties", "N/A")
                report_lines.append(
                    f"| `{mod['old']}` | `{mod['new']}` | {mod['type']} | "
                    f"{mod.get('page', 'N/A')} | {properties_count} |"
                )
            report_lines.append("")
        
        # Errors
        if result.errors:
            report_lines.append("## Errors")
            for error in result.errors:
                report_lines.append(f"- ❌ {error}")
            report_lines.append("")
        
        # Warnings
        if result.warnings:
            report_lines.append("## Warnings")
            for warning in result.warnings:
                report_lines.append(f"- ⚠️ {warning}")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    async def batch_modify_fields(
        self,
        pdf_paths: List[Path],
        field_mappings_list: List[Dict[str, str]],
        output_directory: Optional[Path] = None,
        preserve_originals: bool = True,
    ) -> List[FieldModificationResult]:
        """Modify multiple PDFs in batch."""
        if len(pdf_paths) != len(field_mappings_list):
            raise ValueError("Number of PDFs must match number of field mapping dictionaries")
        
        results = []
        
        for i, (pdf_path, field_mappings) in enumerate(zip(pdf_paths, field_mappings_list)):
            try:
                # Set output path
                if output_directory:
                    output_path = output_directory / f"{pdf_path.stem}_bem_renamed.pdf"
                else:
                    output_path = pdf_path.with_stem(f"{pdf_path.stem}_bem_renamed")
                
                # Modify fields
                result = await self.modify_fields(
                    pdf_path=pdf_path,
                    field_mappings=field_mappings,
                    output_path=output_path,
                    preserve_original=preserve_originals,
                )
                
                results.append(result)
                
            except Exception as e:
                logger.exception(f"Error processing PDF {i+1}: {pdf_path}")
                
                # Create error result
                error_result = FieldModificationResult(
                    original_pdf_path=str(pdf_path),
                    modified_pdf_path="",
                    modifications=[],
                    success=False,
                    errors=[str(e)],
                    warnings=[],
                    timestamp=datetime.now().isoformat(),
                    field_count_before=0,
                    field_count_after=0,
                )
                results.append(error_result)
        
        return results

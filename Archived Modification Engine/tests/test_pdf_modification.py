"""
Test PDF modification functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.pdf_enrichment.pdf_modifier import PDFModifier
from src.pdf_enrichment.field_types import FieldModificationResult, FieldType


class TestPDFModifier:
    """Test cases for PDF modifier."""
    
    def test_pdf_modifier_initialization(self):
        """Test PDF modifier can be initialized."""
        modifier = PDFModifier()
        assert modifier is not None
        assert hasattr(modifier, 'modification_cache')
        assert hasattr(modifier, 'preserve_properties')
        assert isinstance(modifier.modification_cache, dict)
    
    @patch('src.pdf_enrichment.pdf_modifier.PdfWrapper')
    @patch('src.pdf_enrichment.pdf_modifier.validate_file_path')
    async def test_modify_fields_success(self, mock_validate, mock_pdf_wrapper):
        """Test successful field modification."""
        # Mock file validation
        mock_validate.return_value = True
        
        # Mock PDF wrapper
        mock_pdf = Mock()
        mock_widget = Mock()
        mock_pdf.widgets = {'old_field': mock_widget}
        mock_pdf_wrapper.return_value = mock_pdf
        
        modifier = PDFModifier()
        pdf_path = Path("/test/path/test.pdf")
        field_mappings = {'old_field': 'new-field_name'}
        
        with patch.object(pdf_path, 'exists', return_value=True):
            with patch.object(modifier, '_apply_field_modifications') as mock_apply:
                mock_apply.return_value = (
                    [{'old': 'old_field', 'new': 'new-field_name', 'type': 'TextField', 'page': 0, 'preserved_properties': 5}],
                    [],
                    []
                )
                
                result = await modifier.modify_fields(pdf_path, field_mappings)
        
        assert result.success == True
        assert len(result.modifications) == 1
        assert result.modifications[0]['old'] == 'old_field'
        assert result.modifications[0]['new'] == 'new-field_name'
        assert len(result.errors) == 0
    
    async def test_modify_fields_file_not_found(self):
        """Test modification with non-existent file."""
        modifier = PDFModifier()
        pdf_path = Path("/nonexistent/path/test.pdf")
        field_mappings = {'old_field': 'new-field_name'}
        
        result = await modifier.modify_fields(pdf_path, field_mappings)
        
        assert result.success == False
        assert len(result.errors) == 1
        assert "PDF file not found" in result.errors[0]
    
    async def test_modify_fields_empty_mappings(self):
        """Test modification with empty field mappings."""
        modifier = PDFModifier()
        pdf_path = Path("/test/path/test.pdf")
        field_mappings = {}
        
        with patch.object(pdf_path, 'exists', return_value=True):
            result = await modifier.modify_fields(pdf_path, field_mappings)
        
        assert result.success == False
        assert len(result.errors) == 1
        assert "No field mappings provided" in result.errors[0]
    
    def test_validate_field_mappings(self):
        """Test field mapping validation."""
        modifier = PDFModifier()
        
        # Mock PDF with widgets
        mock_pdf = Mock()
        mock_pdf.widgets = {'field1': Mock(), 'field2': Mock()}
        
        # Valid mappings
        valid_mappings = {'field1': 'new-field_name', 'field2': 'another-field_name'}
        errors = modifier._validate_field_mappings(mock_pdf, valid_mappings)
        assert len(errors) == 0
        
        # Invalid mappings - missing source field
        invalid_mappings = {'nonexistent': 'new-field_name'}
        errors = modifier._validate_field_mappings(mock_pdf, invalid_mappings)
        assert len(errors) == 1
        assert "not found in PDF" in errors[0]
        
        # Invalid mappings - duplicate target names
        duplicate_mappings = {'field1': 'same-name', 'field2': 'same-name'}
        errors = modifier._validate_field_mappings(mock_pdf, duplicate_mappings)
        assert len(errors) == 1
        assert "Duplicate target names" in errors[0]
    
    def test_is_valid_bem_name(self):
        """Test BEM name validation."""
        modifier = PDFModifier()
        
        # Valid BEM names
        valid_names = [
            'owner-information_first-name',
            'payment_account-number',
            'beneficiary_name__primary',
            'withdrawal-option_frequency--group',
        ]
        
        for name in valid_names:
            assert modifier._is_valid_bem_name(name), f"Expected {name} to be valid"
        
        # Invalid BEM names
        invalid_names = [
            '',  # Empty
            'invalid',  # No underscore
            'Invalid_Name',  # Uppercase
            'field-name',  # No underscore
            'field_name_extra_underscore',  # Too many underscores
        ]
        
        for name in invalid_names:
            assert not modifier._is_valid_bem_name(name), f"Expected {name} to be invalid"
    
    async def test_apply_field_modifications(self):
        """Test field modification application."""
        modifier = PDFModifier()
        
        # Mock PDF with widgets
        mock_widget = Mock()
        mock_pdf = Mock()
        mock_pdf.widgets = {'old_field': mock_widget}
        
        field_mappings = {'old_field': 'new-field_name'}
        
        with patch.object(modifier, '_extract_widget_properties', return_value={'font': 'Arial'}):
            with patch.object(modifier, '_get_field_type_from_widget', return_value=FieldType.TEXT_FIELD):
                with patch.object(mock_pdf, 'update_widget_key'):
                    with patch.object(mock_pdf, 'commit_widget_key_updates'):
                        # Mock successful rename
                        mock_pdf.widgets = {'new-field_name': mock_widget}
                        
                        modifications, errors, warnings = await modifier._apply_field_modifications(mock_pdf, field_mappings)
        
        assert len(modifications) == 1
        assert modifications[0]['old'] == 'old_field'
        assert modifications[0]['new'] == 'new-field_name'
        assert len(errors) == 0
    
    def test_get_field_type_from_widget(self):
        """Test field type determination from widget."""
        modifier = PDFModifier()
        
        test_cases = [
            ('Text', FieldType.TEXT_FIELD),
            ('Checkbox', FieldType.CHECKBOX),
            ('Radio', FieldType.RADIO_BUTTON),
            ('Dropdown', FieldType.DROPDOWN),
            ('Signature', FieldType.SIGNATURE),
            ('Unknown', FieldType.TEXT_FIELD),  # Default fallback
        ]
        
        for widget_type, expected_field_type in test_cases:
            mock_widget = Mock()
            with patch.object(type(mock_widget), '__name__', widget_type):
                result = modifier._get_field_type_from_widget(mock_widget)
                assert result == expected_field_type
    
    def test_validate_modification_result(self):
        """Test modification result validation."""
        modifier = PDFModifier()
        
        # Create a mock result
        result = FieldModificationResult(
            original_pdf_path="/test/original.pdf",
            modified_pdf_path="/test/modified.pdf",
            modifications=[],
            success=True,
            errors=[],
            warnings=[],
            timestamp=datetime.now().isoformat(),
            field_count_before=2,
            field_count_after=2,
        )
        
        expected_mappings = {'old_field': 'new-field_name'}
        
        with patch('src.pdf_enrichment.pdf_modifier.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            
            with patch('src.pdf_enrichment.pdf_modifier.PdfWrapper') as mock_wrapper:
                mock_pdf = Mock()
                mock_pdf.widgets = {'new-field_name': Mock()}
                mock_wrapper.return_value = mock_pdf
                
                is_valid, validation_errors = modifier.validate_modification_result(result, expected_mappings)
        
        assert is_valid == True
        assert len(validation_errors) == 0
    
    def test_create_field_mapping_report(self):
        """Test field mapping report creation."""
        modifier = PDFModifier()
        
        result = FieldModificationResult(
            original_pdf_path="/test/original.pdf",
            modified_pdf_path="/test/modified.pdf",
            modifications=[
                {'old': 'old_field', 'new': 'new-field_name', 'type': 'TextField', 'page': 0, 'preserved_properties': 5}
            ],
            success=True,
            errors=[],
            warnings=[],
            timestamp="2024-01-01T12:00:00",
            field_count_before=2,
            field_count_after=2,
        )
        
        report = modifier.create_field_mapping_report(result)
        
        assert "# PDF Field Modification Report" in report
        assert "✅ Success" in report
        assert "old_field" in report
        assert "new-field_name" in report
        assert "TextField" in report


if __name__ == "__main__":
    pytest.main([__file__])
"""
Test field extraction functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.pdf_enrichment.field_analyzer import FieldAnalyzer
from src.pdf_enrichment.field_types import FieldType, FormField, FieldPosition


class TestFieldAnalyzer:
    """Test cases for field analyzer."""
    
    def test_field_analyzer_initialization(self):
        """Test field analyzer can be initialized."""
        analyzer = FieldAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, 'field_cache')
        assert isinstance(analyzer.field_cache, dict)
    
    @patch('src.pdf_enrichment.field_analyzer.PdfWrapper')
    async def test_extract_form_fields_success(self, mock_pdf_wrapper):
        """Test successful field extraction."""
        # Mock PDF wrapper and widget
        mock_widget = Mock()
        mock_widget.rect = [100, 200, 250, 225]
        mock_widget.label = "Test Field"
        mock_widget.required = False
        mock_widget.choices = None
        mock_widget.max_length = None
        mock_widget.multiline = False
        mock_widget.readonly = False
        
        mock_pdf = Mock()
        mock_pdf.widgets = {'test_field': mock_widget}
        mock_pdf_wrapper.return_value = mock_pdf
        
        analyzer = FieldAnalyzer()
        pdf_path = Path("/test/path/test.pdf")
        
        with patch.object(type(mock_widget), '__name__', 'Text'):
            fields = await analyzer.extract_form_fields(pdf_path)
        
        assert len(fields) == 1
        assert fields[0].name == 'test_field'
        assert fields[0].field_type == FieldType.TEXT_FIELD
        assert fields[0].label == 'Test Field'
    
    @patch('src.pdf_enrichment.field_analyzer.PdfWrapper')
    async def test_extract_form_fields_caching(self, mock_pdf_wrapper):
        """Test field extraction caching."""
        mock_pdf = Mock()
        mock_pdf.widgets = {}
        mock_pdf_wrapper.return_value = mock_pdf
        
        analyzer = FieldAnalyzer()
        pdf_path = Path("/test/path/test.pdf")
        
        # First call
        fields1 = await analyzer.extract_form_fields(pdf_path)
        # Second call should use cache
        fields2 = await analyzer.extract_form_fields(pdf_path)
        
        assert fields1 == fields2
        assert mock_pdf_wrapper.call_count == 1  # Should only be called once
    
    async def test_extract_form_fields_file_not_found(self):
        """Test field extraction with non-existent file."""
        analyzer = FieldAnalyzer()
        pdf_path = Path("/nonexistent/path/test.pdf")
        
        with pytest.raises(FileNotFoundError):
            await analyzer.extract_form_fields(pdf_path)
    
    def test_determine_field_type(self):
        """Test field type determination."""
        analyzer = FieldAnalyzer()
        
        # Test different widget types
        test_cases = [
            ('Text', FieldType.TEXT_FIELD),
            ('Checkbox', FieldType.CHECKBOX),
            ('Radio', FieldType.RADIO_BUTTON),
            ('Dropdown', FieldType.DROPDOWN),
            ('Signature', FieldType.SIGNATURE),
            ('Button', FieldType.BUTTON),
            ('ListBox', FieldType.LISTBOX),
            ('Unknown', FieldType.TEXT_FIELD),  # Default fallback
        ]
        
        for widget_type, expected_field_type in test_cases:
            mock_widget = Mock()
            with patch.object(type(mock_widget), '__name__', widget_type):
                result = analyzer._determine_field_type(mock_widget)
                assert result == expected_field_type
    
    def test_extract_field_position(self):
        """Test field position extraction."""
        analyzer = FieldAnalyzer()
        
        # Test with valid rect
        mock_widget = Mock()
        mock_widget.rect = [100, 200, 250, 225]
        mock_widget.page = 1
        
        position = analyzer._extract_field_position(mock_widget)
        assert position.x == 100
        assert position.y == 200
        assert position.width == 150
        assert position.height == 25
        assert position.page == 1
        
        # Test with invalid rect
        mock_widget.rect = None
        position = analyzer._extract_field_position(mock_widget)
        assert position.x == 0
        assert position.y == 0
        assert position.width == 100
        assert position.height == 20
        assert position.page == 0
    
    def test_extract_field_label(self):
        """Test field label extraction."""
        analyzer = FieldAnalyzer()
        
        # Test with widget label
        mock_widget = Mock()
        mock_widget.label = "Test Label"
        mock_widget.tooltip = None
        
        label = analyzer._extract_field_label(mock_widget, "test_field")
        assert label == "Test Label"
        
        # Test with tooltip
        mock_widget.label = None
        mock_widget.tooltip = "Test Tooltip"
        
        label = analyzer._extract_field_label(mock_widget, "test_field")
        assert label == "Test Tooltip"
        
        # Test with fallback to field name
        mock_widget.label = None
        mock_widget.tooltip = None
        
        label = analyzer._extract_field_label(mock_widget, "test_field_name")
        assert label == "Test Field Name"
    
    def test_clean_field_name(self):
        """Test field name cleaning."""
        analyzer = FieldAnalyzer()
        
        test_cases = [
            ("Text_first_name", "First Name"),
            ("firstName", "First Name"),
            ("first_name_Field", "First Name"),
            ("testField", "Test Field"),
            ("simple", "Simple"),
            ("", ""),
        ]
        
        for input_name, expected in test_cases:
            result = analyzer._clean_field_name(input_name)
            assert result == expected, f"Expected {input_name} -> {expected}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__])
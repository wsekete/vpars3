"""
Test MCP server functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.pdf_enrichment.mcp_server import PDFEnrichmentServer, ExtractPDFFieldsInput, ModifyFormFieldsInput
from src.pdf_enrichment.field_types import FormField, FieldType, FieldPosition, FieldModificationResult


class TestPDFEnrichmentServer:
    """Test cases for MCP server."""
    
    def test_server_initialization(self):
        """Test MCP server can be initialized."""
        server = PDFEnrichmentServer()
        assert server is not None
        assert hasattr(server, 'server')
        assert hasattr(server, 'field_analyzer')
        assert hasattr(server, 'pdf_modifier')
        assert hasattr(server, 'modification_results')
    
    async def test_extract_pdf_fields_success(self):
        """Test successful PDF field extraction."""
        server = PDFEnrichmentServer()
        
        # Mock field analyzer
        mock_field = FormField(
            id=1,
            name="test_field",
            field_type=FieldType.TEXT_FIELD,
            label="Test Field",
            position=FieldPosition(x=100, y=200, width=150, height=25, page=0),
            required=False,
            choices=None,
            max_length=None,
            multiline=False,
            readonly=False,
        )
        
        with patch.object(server.field_analyzer, 'extract_form_fields', return_value=[mock_field]):
            with patch('src.pdf_enrichment.mcp_server.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.name = "test.pdf"
                
                input_data = ExtractPDFFieldsInput(pdf_filename="test.pdf")
                result = await server._extract_pdf_fields(input_data)
        
        assert result.content[0].text.startswith("## 📋 PDF Field Extraction Complete")
        assert "test.pdf" in result.content[0].text
        assert "1" in result.content[0].text  # Total fields
        assert "test_field" in result.content[1].text  # JSON output
    
    async def test_extract_pdf_fields_file_not_found(self):
        """Test PDF field extraction with non-existent file."""
        server = PDFEnrichmentServer()
        
        with patch('src.pdf_enrichment.mcp_server.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            input_data = ExtractPDFFieldsInput(pdf_filename="nonexistent.pdf")
            result = await server._extract_pdf_fields(input_data)
        
        assert "❌ PDF file not found" in result.content[0].text
        assert "nonexistent.pdf" in result.content[0].text
    
    async def test_modify_form_fields_success(self):
        """Test successful form field modification."""
        server = PDFEnrichmentServer()
        
        # Mock modification result
        mock_result = FieldModificationResult(
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
        
        with patch.object(server.pdf_modifier, 'modify_fields', return_value=mock_result):
            with patch('src.pdf_enrichment.mcp_server.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.with_stem.return_value = Path("/test/modified.pdf")
                
                input_data = ModifyFormFieldsInput(
                    pdf_filename="test.pdf",
                    field_mappings={'old_field': 'new-field_name'},
                    output_filename=None,
                    preserve_original=True
                )
                result = await server._modify_form_fields(input_data)
        
        assert "✅ PDF Field Modification Complete" in result.content[0].text
        assert "old_field" in result.content[0].text
        assert "new-field_name" in result.content[0].text
    
    async def test_modify_form_fields_file_not_found(self):
        """Test form field modification with non-existent file."""
        server = PDFEnrichmentServer()
        
        with patch('src.pdf_enrichment.mcp_server.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            input_data = ModifyFormFieldsInput(
                pdf_filename="nonexistent.pdf",
                field_mappings={'old_field': 'new-field_name'}
            )
            result = await server._modify_form_fields(input_data)
        
        assert "❌ PDF file not found" in result.content[0].text
        assert "nonexistent.pdf" in result.content[0].text
    
    async def test_modify_form_fields_failure(self):
        """Test form field modification failure."""
        server = PDFEnrichmentServer()
        
        # Mock modification result with errors
        mock_result = FieldModificationResult(
            original_pdf_path="/test/original.pdf",
            modified_pdf_path="/test/modified.pdf",
            modifications=[],
            success=False,
            errors=["Field 'old_field' not found"],
            warnings=[],
            timestamp="2024-01-01T12:00:00",
            field_count_before=2,
            field_count_after=2,
        )
        
        with patch.object(server.pdf_modifier, 'modify_fields', return_value=mock_result):
            with patch('src.pdf_enrichment.mcp_server.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.with_stem.return_value = Path("/test/modified.pdf")
                
                input_data = ModifyFormFieldsInput(
                    pdf_filename="test.pdf",
                    field_mappings={'old_field': 'new-field_name'}
                )
                result = await server._modify_form_fields(input_data)
        
        assert "❌ PDF Field Modification Failed" in result.content[0].text
        assert "Field 'old_field' not found" in result.content[0].text
    
    def test_format_field_summary(self):
        """Test field summary formatting."""
        server = PDFEnrichmentServer()
        
        mock_fields = [
            FormField(
                id=1,
                name="test_field",
                field_type=FieldType.TEXT_FIELD,
                label="Test Field",
                position=FieldPosition(x=100, y=200, width=150, height=25, page=0),
                required=False,
                choices=None,
                max_length=None,
                multiline=False,
                readonly=False,
            ),
            FormField(
                id=2,
                name="checkbox_field",
                field_type=FieldType.CHECKBOX,
                label="Checkbox Field",
                position=FieldPosition(x=200, y=300, width=20, height=20, page=0),
                required=False,
                choices=None,
                max_length=None,
                multiline=False,
                readonly=False,
            ),
        ]
        
        summary = server._format_field_summary(mock_fields, "test.pdf")
        
        assert "## 📋 PDF Field Extraction Complete" in summary
        assert "test.pdf" in summary
        assert "2" in summary  # Total fields
        assert "TextField" in summary
        assert "Checkbox" in summary
        assert "test_field" in summary
        assert "checkbox_field" in summary
    
    def test_format_modification_summary(self):
        """Test modification summary formatting."""
        server = PDFEnrichmentServer()
        
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
        
        summary = server._format_modification_summary(result)
        
        assert "## ✅ PDF Field Modification Complete" in summary
        assert "original.pdf" in summary
        assert "modified.pdf" in summary
        assert "old_field" in summary
        assert "new-field_name" in summary
        assert "TextField" in summary
        assert "Your PDF is ready for download" in summary


if __name__ == "__main__":
    pytest.main([__file__])
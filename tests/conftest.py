"""
Test configuration and fixtures for PDF enrichment tests.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Generator, List

import pytest
import pytest_asyncio
from PyPDFForm import PdfWrapper

from src.pdf_enrichment.field_types import (
    BEMNamingResult,
    FieldModificationResult,
    FieldPosition,
    FieldType,
    FormAnalysis,
    FormField,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_form_field() -> FormField:
    """Create a sample form field for testing."""
    return FormField(
        id=1,
        type=FieldType.TEXT_FIELD,
        form_id=1,
        section_id=1,
        parent_id=None,
        order=1.0,
        label="First Name",
        api_name="firstName",
        custom=False,
        uuid="field_1",
        position=FieldPosition(x=100, y=200, width=150, height=25, page=0),
        unified_field_id=1,
    )


@pytest.fixture
def sample_bem_result() -> BEMNamingResult:
    """Create a sample BEM naming result for testing."""
    return BEMNamingResult(
        original_name="firstName",
        bem_name="owner-information_first-name",
        confidence="high",
        reasoning="Standard personal information field",
        section="owner-information",
        field_type=FieldType.TEXT_FIELD,
        is_radio_group=False,
        needs_review=False,
    )


@pytest.fixture
def sample_form_analysis() -> FormAnalysis:
    """Create a sample form analysis for testing."""
    field = FormField(
        id=1,
        type=FieldType.TEXT_FIELD,
        form_id=1,
        section_id=1,
        parent_id=None,
        order=1.0,
        label="First Name",
        api_name="firstName",
        custom=False,
        uuid="field_1",
        position=FieldPosition(x=100, y=200, width=150, height=25, page=0),
        unified_field_id=1,
    )
    
    bem_result = BEMNamingResult(
        original_name="firstName",
        bem_name="owner-information_first-name",
        confidence="high",
        reasoning="Standard personal information field",
        section="owner-information",
        field_type=FieldType.TEXT_FIELD,
        is_radio_group=False,
        needs_review=False,
    )
    
    return FormAnalysis(
        filename="test_form.pdf",
        form_type="Test Form",
        form_id="TEST-001",
        total_fields=1,
        fields=[field],
        bem_mappings=[bem_result],
        confidence_summary={"high": 1, "medium": 0, "low": 0},
        field_type_distribution={FieldType.TEXT_FIELD: 1},
        naming_conflicts=[],
        missing_sections=[],
        review_required=[],
    )


@pytest.fixture
def sample_field_mappings() -> Dict[str, str]:
    """Create sample field mappings for testing."""
    return {
        "firstName": "owner-information_first-name",
        "lastName": "owner-information_last-name",
        "email": "contact-information_email-address",
        "signature": "signatures_owner",
    }


@pytest.fixture
def sample_modification_result() -> FieldModificationResult:
    """Create a sample modification result for testing."""
    return FieldModificationResult(
        original_pdf_path="/tmp/test.pdf",
        modified_pdf_path="/tmp/test_modified.pdf",
        modifications=[
            {
                "old": "firstName",
                "new": "owner-information_first-name",
                "type": "TextField",
                "page": 0,
                "preserved_properties": 5,
            }
        ],
        success=True,
        errors=[],
        warnings=[],
        timestamp="2024-01-01T00:00:00",
        field_count_before=4,
        field_count_after=4,
    )


@pytest.fixture
def mock_pdf_wrapper(monkeypatch):
    """Mock PyPDFForm.PdfWrapper for testing without actual PDF files."""
    class MockWidget:
        def __init__(self, name: str, widget_type: str = "Text"):
            self.name = name
            self.widget_type = widget_type
            self.rect = [0, 0, 100, 20]
            self.font = "Helvetica"
            self.font_size = 12
    
    class MockPdfWrapper:
        def __init__(self, pdf_path: str):
            self.pdf_path = pdf_path
            self.widgets = {
                "firstName": MockWidget("firstName"),
                "lastName": MockWidget("lastName"),
                "email": MockWidget("email"),
                "signature": MockWidget("signature", "Signature"),
            }
            self.schema = {
                "type": "object",
                "properties": {
                    "firstName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "email": {"type": "string"},
                    "signature": {"type": "string"},
                }
            }
        
        def update_widget_key(self, old_name: str, new_name: str) -> None:
            if old_name in self.widgets:
                widget = self.widgets.pop(old_name)
                widget.name = new_name
                self.widgets[new_name] = widget
        
        def commit_widget_key_updates(self) -> "MockPdfWrapper":
            return self
        
        def write(self, path: str) -> None:
            pass
    
    monkeypatch.setattr("PyPDFForm.PdfWrapper", MockPdfWrapper)
    return MockPdfWrapper


@pytest.fixture
def create_test_pdf(temp_dir: Path) -> callable:
    """Factory function to create test PDF files."""
    def _create_pdf(filename: str, fields: Dict[str, str]) -> Path:
        pdf_path = temp_dir / filename
        
        # Create a simple test PDF with the given fields
        # In a real implementation, this would create an actual PDF
        # For testing, we'll create a JSON file with field definitions
        test_data = {
            "filename": filename,
            "fields": fields,
            "metadata": {
                "created": "2024-01-01T00:00:00",
                "form_type": "Test Form",
            }
        }
        
        # Write as JSON for testing purposes
        json_path = pdf_path.with_suffix(".json")
        json_path.write_text(json.dumps(test_data, indent=2))
        
        return json_path
    
    return _create_pdf


@pytest.fixture
def sample_pdf_files(create_test_pdf) -> List[Path]:
    """Create multiple sample PDF files for batch testing."""
    files = []
    
    # Form 1: Owner information form
    files.append(create_test_pdf("owner_info.pdf", {
        "firstName": "First Name",
        "lastName": "Last Name",
        "middleName": "Middle Name",
        "dateOfBirth": "Date of Birth",
        "ssn": "Social Security Number",
    }))
    
    # Form 2: Address form
    files.append(create_test_pdf("address.pdf", {
        "streetAddress": "Street Address",
        "city": "City",
        "state": "State",
        "zipCode": "ZIP Code",
        "country": "Country",
    }))
    
    # Form 3: Payment form
    files.append(create_test_pdf("payment.pdf", {
        "accountNumber": "Account Number",
        "routingNumber": "Routing Number",
        "bankName": "Bank Name",
        "paymentAmount": "Payment Amount",
    }))
    
    return files


@pytest_asyncio.fixture
async def field_analyzer():
    """Create a field analyzer instance for testing."""
    from src.pdf_enrichment.field_analyzer import FieldAnalyzer
    return FieldAnalyzer()


@pytest_asyncio.fixture
async def pdf_modifier():
    """Create a PDF modifier instance for testing."""
    from src.pdf_enrichment.pdf_modifier import PDFModifier
    return PDFModifier()


@pytest_asyncio.fixture
async def preview_generator():
    """Create a preview generator instance for testing."""
    from src.pdf_enrichment.preview_generator import PreviewGenerator
    return PreviewGenerator()


# Test data constants
SAMPLE_BEM_NAMES = [
    "owner-information_first-name",
    "owner-information_last-name",
    "contact-information_email-address",
    "contact-information_phone-number",
    "address-information_street-address",
    "address-information_city",
    "address-information_state",
    "address-information_zip-code",
    "payment-information_account-number",
    "payment-information_routing-number",
    "beneficiary-information_primary-name",
    "beneficiary-information_contingent-name",
    "withdrawal-option_frequency--group",
    "withdrawal-option_frequency__monthly",
    "withdrawal-option_frequency__quarterly",
    "withdrawal-option_amount",
    "withdrawal-option_amount__gross",
    "withdrawal-option_amount__net",
    "signatures_owner",
    "signatures_owner-date",
    "signatures_witness",
]

INVALID_BEM_NAMES = [
    "",  # Empty
    "invalid",  # No underscore
    "Invalid_Name",  # Uppercase
    "block_",  # Missing element
    "_element",  # Missing block
    "block_element_modifier",  # Wrong separator
    "block-element__modifier",  # Wrong block-element separator
    "class_name",  # Reserved word
    "block_element__",  # Empty modifier
    "block_element--",  # Wrong group suffix
]

FIELD_TYPE_MAPPINGS = {
    "Text": FieldType.TEXT_FIELD,
    "Checkbox": FieldType.CHECKBOX,
    "Radio": FieldType.RADIO_BUTTON,
    "Dropdown": FieldType.DROPDOWN,
    "Signature": FieldType.SIGNATURE,
}

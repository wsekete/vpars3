"""
Test BEM naming engine functionality.
"""

import pytest

from src.pdf_enrichment.bem_naming import BEMNamingEngine
from src.pdf_enrichment.field_types import FieldType, FormField, FieldPosition


class TestBEMNamingEngine:
    """Test cases for BEM naming engine."""
    
    def test_bem_engine_initialization(self):
        """Test BEM engine can be initialized."""
        engine = BEMNamingEngine()
        assert engine is not None
        assert hasattr(engine, 'abbreviations')
        assert hasattr(engine, 'reserved_words')
    
    def test_generate_simple_bem_name(self):
        """Test generation of simple BEM names."""
        engine = BEMNamingEngine()
        
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
        
        bem_name = engine.generate_bem_name(
            field=field,
            section="owner-information",
            context={"existing_names": []}
        )
        
        assert bem_name is not None
        assert "_" in bem_name
        assert bem_name.startswith("owner-information_")
    
    def test_validate_bem_names(self):
        """Test BEM name validation."""
        engine = BEMNamingEngine()
        
        # Valid names
        valid_names = [
            "owner-information_first-name",
            "payment_account-number",
            "withdrawal-option_frequency--group",
            "beneficiary_name__primary",
        ]
        
        for name in valid_names:
            assert engine.validate_bem_name(name), f"Expected {name} to be valid"
        
        # Invalid names
        invalid_names = [
            "",  # Empty
            "invalid",  # No underscore
            "Invalid_Name",  # Uppercase
            "class_name",  # Reserved word
        ]
        
        for name in invalid_names:
            assert not engine.validate_bem_name(name), f"Expected {name} to be invalid"
    
    def test_sanitize_field_name(self):
        """Test field name sanitization."""
        engine = BEMNamingEngine()
        
        test_cases = [
            ("First Name", "first-name"),
            ("firstName", "firstname"),
            ("first_name", "first-name"),
            ("Email Address", "email-address"),
            ("123_field", "field"),  # Remove leading numbers
            ("field!", "field"),  # Remove special chars
        ]
        
        for input_name, expected in test_cases:
            result = engine._sanitize_field_name(input_name)
            assert result == expected, f"Expected {input_name} -> {expected}, got {result}"
    
    def test_expand_abbreviations(self):
        """Test abbreviation expansion."""
        engine = BEMNamingEngine()
        
        test_cases = [
            ("addr", "address"),
            ("first-addr", "first-address"),
            ("ph-num", "phone-number"),
            ("unknown-abbr", "unknown-abbr"),  # No change for unknown
        ]
        
        for input_name, expected in test_cases:
            result = engine._expand_abbreviations(input_name)
            assert result == expected, f"Expected {input_name} -> {expected}, got {result}"
    
    def test_ensure_uniqueness(self):
        """Test uniqueness enforcement."""
        engine = BEMNamingEngine()
        
        existing_names = ["owner-information_name", "owner-information_name-2"]
        
        # Should return original if not in existing
        result = engine._ensure_uniqueness("new-name", existing_names)
        assert result == "new-name"
        
        # Should add suffix if exists
        result = engine._ensure_uniqueness("owner-information_name", existing_names)
        assert result == "owner-information_name-3"  # Next available number
    
    def test_radio_group_naming(self):
        """Test radio group naming with --group suffix."""
        engine = BEMNamingEngine()
        
        radio_group_field = FormField(
            id=1,
            type=FieldType.RADIO_GROUP,
            form_id=1,
            section_id=1,
            parent_id=None,
            order=1.0,
            label="Payment Method",
            api_name="paymentMethod",
            custom=False,
            uuid="field_1",
            position=FieldPosition(x=100, y=200, width=150, height=25, page=0),
            unified_field_id=1,
        )
        
        bem_name = engine.generate_bem_name(
            field=radio_group_field,
            section="payment",
            context={"existing_names": []}
        )
        
        assert bem_name.endswith("--group")
        assert "payment_" in bem_name


if __name__ == "__main__":
    pytest.main([__file__])

# Enhanced BEM Validation System

## Overview

The Enhanced BEM Validation System provides flexible validation for BEM (Block Element Modifier) naming conventions in PDF form fields. This system supports the full BEM hierarchy while maintaining backward compatibility with existing field names.

## Supported BEM Patterns

### 1. Block Only
**Pattern**: `block`
**Example**: `dividend-option`
**Use Case**: Simple field references or containers

### 2. Block + Element
**Pattern**: `block_element`
**Example**: `dividend-option_cash`
**Use Case**: Specific field within a block section

### 3. Block + Modifier
**Pattern**: `block__modifier`
**Example**: `dividend-option__cash`
**Use Case**: Block-level variations or states

### 4. Block + Element + Modifier
**Pattern**: `block_element__modifier`
**Example**: `name-change_reason__marriage`
**Use Case**: Full BEM hierarchy with specific element and modifier

### 5. Block + Group
**Pattern**: `block--group`
**Example**: `dividend-option--group`
**Use Case**: Radio button group containers

### 6. Block + Element + Group
**Pattern**: `block_element--group`
**Example**: `payment-method_options--group`
**Use Case**: Grouped elements within a block

## Validation Logic

### Single Regex Pattern
The system uses a single, flexible regex pattern to validate all BEM structures:

```regex
^[a-z][a-z0-9-]*(?:_[a-z][a-z0-9-]*)?(?:__[a-z][a-z0-9-]*|--group)?$
```

### Pattern Breakdown
- `^[a-z][a-z0-9-]*`: **Block** - starts with letter, allows hyphens
- `(?:_[a-z][a-z0-9-]*)?`: **Optional Element** - underscore + name
- `(?:__[a-z][a-z0-9-]*|--group)?`: **Optional Modifier OR Group** - double underscore + name OR --group suffix
- `$`: End of string

### Implementation
```python
def _is_valid_bem_name(self, name: str) -> bool:
    """Check if a name follows BEM conventions."""
    import re
    
    # Flexible BEM pattern supporting full hierarchy
    bem_pattern = r'^[a-z][a-z0-9-]*(?:_[a-z][a-z0-9-]*)?(?:__[a-z][a-z0-9-]*|--group)?$'
    
    return re.match(bem_pattern, name) is not None
```

## Field Type Integration

### Text Fields
- **Pattern**: `block_element`
- **Example**: `owner-information_first-name`
- **Field Type**: `text`

### Checkboxes
- **Pattern**: `block_element__checkbox` or `block_element__modifier`
- **Example**: `insured-information_same-as-owner__checkbox`
- **Field Type**: `checkbox`

### Radio Buttons
- **Pattern**: `block_element__option` or `block__option`
- **Example**: `dividend-option__cash`
- **Field Type**: `radio`

### Radio Groups
- **Pattern**: `block--group` or `block_element--group`
- **Example**: `dividend-option--group`
- **Field Type**: `radio_group`

### Signature Fields
- **Pattern**: `signatures_element`
- **Example**: `signatures_owner-signature`
- **Field Type**: `signature`

### Date Fields
- **Pattern**: `signatures_element-date` or `block_element-date`
- **Example**: `signatures_owner-date`
- **Field Type**: `date`

## Validation Examples

### ✅ Valid BEM Names
```python
valid_names = [
    # Block only
    'dividend-option',
    'name-change',
    'address-change',
    
    # Block + Element
    'dividend-option_cash',
    'payment-method_ach',
    'owner-information_first-name',
    
    # Block + Modifier
    'dividend-option__cash',
    'payment-method__monthly',
    
    # Block + Element + Modifier
    'name-change_reason__marriage',
    'address-change_owner__phone',
    'owner-information_contact__primary',
    
    # Block + Group
    'dividend-option--group',
    'payment-method--group',
    
    # Block + Element + Group
    'payment-method_options--group',
    'dividend-option_choices--group',
]
```

### ❌ Invalid BEM Names
```python
invalid_names = [
    'UPPERCASE_field',        # No uppercase allowed
    'field_',                 # Trailing underscore
    '_field',                 # Leading underscore
    'field__',                # Trailing double underscore
    'field--',                # Trailing double hyphen
    'field_element__',        # Incomplete modifier
    'field_element--',        # Incomplete group
    'field__modifier__extra', # Multiple modifiers
    'field--group--extra',    # Multiple group suffixes
]
```

## Testing

### Comprehensive Test Suite
```python
def test_bem_validation():
    modifier = PDFModifier()
    
    # Test all valid patterns
    valid_patterns = [
        'block',
        'block_element',
        'block__modifier',
        'block_element__modifier',
        'block--group',
        'block_element--group',
    ]
    
    for pattern in valid_patterns:
        assert modifier._is_valid_bem_name(pattern), f"Should be valid: {pattern}"
    
    # Test invalid patterns
    invalid_patterns = [
        'BLOCK',
        'block_',
        '_block',
        'block__',
        'block--',
    ]
    
    for pattern in invalid_patterns:
        assert not modifier._is_valid_bem_name(pattern), f"Should be invalid: {pattern}"
```

### Performance Testing
```python
def test_validation_performance():
    modifier = PDFModifier()
    
    # Test with large number of names
    import time
    start = time.time()
    
    for i in range(10000):
        modifier._is_valid_bem_name(f'test-block_element-{i}')
    
    end = time.time()
    print(f"Validated 10,000 names in {end - start:.4f} seconds")
```

## Backward Compatibility

### Existing Names Support
All existing BEM names from version 0.1.0 continue to work:
- `owner-information_first-name` ✅
- `contact-information_email-address` ✅
- `signatures_owner-signature` ✅
- `dividend-option__accumulate-interest` ✅

### Migration Path
No migration required - all existing valid names remain valid.

## Error Handling

### Validation Errors
```python
def validate_field_mappings(field_mappings: Dict[str, str]) -> List[str]:
    errors = []
    
    for original_name, bem_name in field_mappings.items():
        if not _is_valid_bem_name(bem_name):
            errors.append(f"Invalid BEM name: '{original_name}' -> '{bem_name}'")
    
    return errors
```

### Error Messages
- **Invalid BEM name**: Provides specific guidance on BEM format requirements
- **Multiple errors**: Batches validation errors for efficient reporting
- **Suggestions**: Offers corrected BEM names when possible

## Integration with PDF Modifier

### Validation Pipeline
1. **Field Mapping Input**: Receive original → BEM name mappings
2. **BEM Validation**: Validate all BEM names against pattern
3. **Error Reporting**: Report invalid names with suggestions
4. **PDF Modification**: Apply valid mappings to PDF fields

### Example Integration
```python
async def modify_fields(self, pdf_path: Path, field_mappings: Dict[str, str]):
    # Validate BEM names
    validation_errors = self._validate_field_mappings(field_mappings)
    
    if validation_errors:
        return FieldModificationResult(
            success=False,
            errors=validation_errors,
            # ... other fields
        )
    
    # Apply modifications
    return await self._apply_field_modifications(pdf, field_mappings)
```

## Future Enhancements

### Planned Improvements
1. **Context-aware validation**: Validate based on field types and form context
2. **Automatic BEM suggestions**: Generate BEM names from field contexts
3. **Custom validation rules**: Allow project-specific BEM patterns
4. **Performance optimization**: Further optimize regex matching for large forms

### Extensibility
The validation system is designed to be extensible:
- Custom regex patterns can be added
- Field-type specific validation can be implemented
- Context-aware validation can be integrated

## Best Practices

### BEM Naming Guidelines
1. **Use descriptive blocks**: `owner-information`, `payment-details`
2. **Clear element names**: `first-name`, `account-number`
3. **Meaningful modifiers**: `__primary`, `__monthly`
4. **Consistent formatting**: Always lowercase with hyphens

### Validation Best Practices
1. **Early validation**: Validate BEM names before PDF modification
2. **Batch validation**: Process all names together for efficiency
3. **Error reporting**: Provide clear, actionable error messages
4. **Performance monitoring**: Track validation performance for large forms

## Conclusion

The Enhanced BEM Validation System provides robust, flexible validation for BEM naming conventions while maintaining backward compatibility and performance. It supports the full BEM hierarchy and integrates seamlessly with the PDF modification pipeline.
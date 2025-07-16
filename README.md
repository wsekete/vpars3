# PDF Field BEM Renamer

🚀 **Enhanced PDF form field renaming with intelligent BEM-style naming**

Transform PDF forms by analyzing field names and generating consistent BEM-style field names using financial services conventions. **Version 0.2.0** includes major improvements to BEM validation, field type support, and signature field handling.

## ✨ Key Features

- **🧠 AI-Powered Analysis** - Claude Desktop analyzes PDF forms and generates BEM names
- **📄 JSON Export** - Clean JSON output with all field mappings
- **🔧 Standalone Modifier** - External tool applies changes using PyPDFForm
- **🏷️ Enhanced BEM Convention** - Flexible `block_element__modifier` style names with full hierarchy support
- **💾 Auto-Save** - Modified PDFs saved with `__parsed.pdf` suffix
- **🖊️ Signature Field Support** - Proper handling of signature fields and date fields
- **📊 Field Type Detection** - Support for text, checkbox, radio, dropdown, signature, and date fields
- **🔘 Radio Group Enhancement** - Improved radio button group detection and mapping

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/pdf-enrichment-platform.git
cd pdf-enrichment-platform

# Install with uv (recommended)
uv install
```

### 2. Claude Desktop Setup

Add to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pdf-enrichment": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "pdf_enrichment.mcp_server"
      ],
      "cwd": "/path/to/pdf-enrichment-platform"
    }
  }
}
```

### 3. Simple 2-Step Workflow

#### Step 1: Generate BEM Names (in Claude Desktop)
1. **Upload your PDF** to Claude Desktop
2. **Use the tool**: `generate_bem_names_and_export_json`
3. **Copy the JSON output** from the response

#### Step 2: Modify PDF (external command)
```bash
# Run the standalone modifier
python scripts/pdf_bem_modifier.py --pdf ~/Desktop/your-form.pdf --json mappings.json

# Result: ~/Desktop/your-form__parsed.pdf
```

## 🛠️ Tool Overview

### Claude Desktop Tool: `generate_bem_names_and_export_json`
- Analyzes uploaded PDF form fields
- Generates BEM-style names using financial services conventions
- Outputs comprehensive JSON with all field mappings
- Includes validation and field count verification

### Standalone Script: `pdf_bem_modifier.py`
- Takes original PDF and JSON mappings as input
- Uses PyPDFForm to rename fields while preserving properties
- Saves modified PDF with `__parsed.pdf` suffix in same directory
- Provides detailed progress and error reporting

## 🎯 Enhanced BEM Naming Convention

### Flexible Hierarchy Support
- **Block**: Form sections (`owner-information`, `beneficiary`, `payment`)
- **Element**: Individual fields (`first-name`, `amount`, `signature`)
- **Modifier**: Field variations (`__monthly`, `__gross`, `__primary`)
- **Special**: Radio groups (`--group`)

### Supported BEM Patterns
- `block` (e.g., `dividend-option`)
- `block_element` (e.g., `dividend-option_cash`)
- `block__modifier` (e.g., `dividend-option__cash`)
- `block_element__modifier` (e.g., `name-change_reason__marriage`)
- `block--group` (e.g., `dividend-option--group`)
- `block_element--group` (e.g., `payment-method_options--group`)

### Examples
```
owner-information_first-name
owner-information_last-name
beneficiary_withdrawal-frequency__monthly
payment-method--group
payment-method__ach
signatures_owner-signature
name-change_reason__marriage
dividend-option__accumulate-interest
```

### Field Type Support
- **Text Fields**: `owner-information_first-name` (field_type: "text")
- **Checkboxes**: `insured-information_same-as-owner__checkbox` (field_type: "checkbox")
- **Radio Buttons**: `dividend-option__cash` (field_type: "radio")
- **Radio Groups**: `dividend-option--group` (field_type: "radio_group")
- **Signature Fields**: `signatures_owner-signature` (field_type: "signature")
- **Date Fields**: `signatures_owner-date` (field_type: "date")
- **Dropdown Fields**: `billing-frequency__annual` (field_type: "dropdown")

## 📋 Sample JSON Output

```json
{
  "source_filename": "Life-1528-Q.pdf",
  "analysis_timestamp": "2024-01-15T10:30:00Z",
  "total_fields": 67,
  "bem_mappings": {
    "first_name": "owner-information_first-name",
    "last_name": "owner-information_last-name",
    "policy_number": "owner-information_policy-number",
    "dividend_accumulate": "dividend-option__accumulate-interest",
    "dividend_reduce_premium": "dividend-option__reduce-premium",
    "payment_method_ach": "payment-method__ach",
    "owner_signature": "signatures_owner-signature",
    "owner_signature_date": "signatures_owner-date"
  }
}
```

## 🔧 Command Line Usage

```bash
# Basic usage
python scripts/pdf_bem_modifier.py --pdf form.pdf --json mappings.json

# With specific output directory
python scripts/pdf_bem_modifier.py --pdf form.pdf --json mappings.json --output ~/Documents/

# Dry run (preview changes without modifying)
python scripts/pdf_bem_modifier.py --pdf form.pdf --json mappings.json --dry-run
```

## 📊 Project Structure

```
pdf-enrichment-platform/
├── src/pdf_enrichment/
│   ├── mcp_server.py          # Single Claude Desktop tool
│   ├── field_analyzer.py      # PDF field analysis
│   ├── pdf_modifier.py        # PDF modification logic
│   ├── field_types.py         # Type definitions
│   └── utils.py               # Utility functions
├── scripts/
│   └── pdf_bem_modifier.py    # Standalone PDF modifier
├── tests/                     # Test suite
└── examples/                  # Sample files
```

## 🧪 Testing

```bash
# Run tests
uv run pytest

# Test with sample PDF
python scripts/pdf_bem_modifier.py --pdf examples/sample_form.pdf --json examples/sample_mappings.json --dry-run
```

## 🐛 Troubleshooting

### Common Issues

**Claude Desktop not finding tool:**
```bash
# Verify MCP server
python -m pdf_enrichment.mcp_server_v2

# Check config path
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**PDF modification errors:**
```bash
# Check file permissions
ls -la your-file.pdf

# Verify PyPDFForm installation
python -c "import PyPDFForm; print('OK')"
```

**Missing output file:**
- Check that input PDF path is correct
- Ensure you have write permissions to the directory
- Verify JSON mappings file exists and is valid

**BEM validation errors:**
```bash
# Test BEM name validation
python -c "
from src.pdf_enrichment.pdf_modifier import PDFModifier
modifier = PDFModifier()
print(modifier._is_valid_bem_name('owner-information_first-name'))  # Should be True
"
```

**Field detection issues:**
- Ensure PDF has fillable form fields (not just scanned image)
- Check for proper field names in the PDF
- Verify field types are correctly identified

### Known Limitations

- **Manual field mapping**: Automatic field detection needs improvement
- **Radio group detection**: May require manual verification
- **JSON format**: Occasional formatting issues with complex mappings
- **Field type validation**: Some boolean property validation errors

### Performance Notes

- **Large PDFs**: Processing time increases with form complexity
- **Memory usage**: Complex forms with many fields may use more memory
- **Validation time**: BEM name validation is fast but field detection can be slow

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Simple, clean PDF field renaming with BEM conventions! 🚀**
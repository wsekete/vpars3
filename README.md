# PDF Field BEM Renamer

🚀 **Simple 2-step workflow to rename PDF form fields with intelligent BEM-style naming**

Transform PDF forms by analyzing field names and generating consistent BEM-style field names using financial services conventions.

## ✨ Key Features

- **🧠 AI-Powered Analysis** - Claude Desktop analyzes PDF forms and generates BEM names
- **📄 JSON Export** - Clean JSON output with all field mappings
- **🔧 Standalone Modifier** - External tool applies changes using PyPDFForm
- **🏷️ BEM Convention** - Consistent `block_element__modifier` style names
- **💾 Auto-Save** - Modified PDFs saved with `__parsed.pdf` suffix

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

## 🎯 BEM Naming Convention

### Format
- **Block**: Form sections (`owner-information`, `beneficiary`, `payment`)
- **Element**: Individual fields (`first-name`, `amount`, `signature`)
- **Modifier**: Field variations (`__monthly`, `__gross`, `__primary`)
- **Special**: Radio groups (`--group`)

### Examples
```
owner-information_first-name
owner-information_last-name
beneficiary_withdrawal-frequency__monthly
payment-method--group
payment-method__ach
signatures_owner-signature
```

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
python -m pdf_enrichment.mcp_server

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Simple, clean PDF field renaming with BEM conventions! 🚀**
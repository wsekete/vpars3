# PDF Field BEM Renamer

🚀 **Claude Desktop tool for generating BEM-style field names from PDF forms**

Analyze PDF forms and generate consistent BEM-style field names using financial services conventions. This tool integrates with Claude Desktop to provide AI-powered field analysis and BEM name generation.

## ✨ Key Features

- **🧠 AI-Powered Analysis** - Claude Desktop analyzes PDF forms and generates BEM names
- **📄 JSON Export** - Clean JSON output with all field mappings
- **🏷️ BEM Convention** - Flexible `block_element__modifier` style names with full hierarchy support
- **🖊️ Signature Field Support** - Proper handling of signature fields and date fields
- **📊 Field Type Detection** - Support for text, checkbox, radio, dropdown, signature, and date fields
- **🔘 Radio Group Enhancement** - Improved radio button group detection and mapping
- **🗂️ Archived Modification Engine** - Advanced PDF modification tools preserved in archive folder

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
        "src.pdf_enrichment.mcp_server_simple"
      ],
      "cwd": "/path/to/vpars3"
    }
  }
}
```

### 3. Simple Usage

#### Generate BEM Names (in Claude Desktop)
1. **Upload your PDF** to Claude Desktop
2. **Use the tool**: `generate_BEM_names` (optional context parameter)
3. **Copy the JSON output** from the response

The tool will analyze the PDF and generate a complete BEM mapping with downloadable JSON artifact.

#### Optional: PDF Modification
For PDF modification capabilities, see the **Archived Modification Engine** folder which contains advanced tools for applying BEM names to PDF files.

## 🛠️ Tool Overview

### Claude Desktop Tool: `generate_BEM_names`
- Analyzes uploaded PDF form fields
- Generates BEM-style names using financial services conventions
- Outputs comprehensive JSON with all field mappings
- Includes validation and field count verification
- Provides downloadable JSON artifact for external use

### Additional Tool: `generate_unified_fields`
- **generate_unified_fields**: Generates enriched Unified Field definitions from BEM mappings for application integration

### Archived Modification Engine
Advanced PDF modification tools are preserved in the `Archived Modification Engine` folder for future development.

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

## 🧩 Unified Fields Generation

The `generate_unified_fields` tool transforms BEM mappings into enriched Unified Field (UF) definitions for application integration across insurance and annuity forms.

### Input Format
```json
{
  "bem_mappings": {
    "owner_first_name": "owner-information_first-name",
    "dividend_option__cash": "dividend-option__cash",
    "payment_method--group": "payment-method--group"
  }
}
```

### Output Format
```json
[
  {
    "api_name": "owner_first_name",
    "name": "Owner: First Name",
    "description": "First name of the policy owner",
    "type": "text field",
    "label": "First Name"
  },
  {
    "api_name": "dividend_option__cash",
    "name": "Dividend Option: Cash",
    "description": "Option to receive dividends as cash payment",
    "type": "radio button",
    "label": "Cash"
  }
]
```

### Field Types Supported
- **text field**: Standard input fields
- **radio button**: Individual radio button options
- **radio group**: Radio button group containers
- **checkbox**: Boolean/toggle options
- **group**: Section containers
- **slider**: Range or percentage inputs

## 🔧 Usage

This tool is designed to work through Claude Desktop. For command line usage and PDF modification capabilities, see the **Archived Modification Engine** folder which contains standalone scripts and advanced features.

### Basic Workflow
1. Upload PDF to Claude Desktop
2. Use `generate_BEM_names` tool to create BEM mappings
3. Use `generate_unified_fields` tool to create enriched field definitions
4. Download the generated JSON artifacts

For PDF modification capabilities, see the **Archived Modification Engine** folder.

## 📊 Project Structure

```
vpars3/
├── src/pdf_enrichment/
│   ├── mcp_server_simple.py   # Main Claude Desktop tool
│   ├── field_types.py         # Type definitions
│   └── utils.py               # Utility functions
├── Archived Modification Engine/
│   ├── mcp_servers/           # Enhanced MCP servers
│   ├── scripts/               # Standalone PDF modification tools
│   ├── components/            # Advanced field detection and modification
│   ├── documentation/         # Technical documentation
│   └── tests/                 # Test suite
├── docs/                      # Core documentation
└── examples/                  # Sample files
```

## 🧪 Testing

```bash
# Test the MCP server
python -m src.pdf_enrichment.mcp_server_simple

# For advanced testing, see the Archived Modification Engine folder
```

## 🐛 Troubleshooting

### Common Issues

**Claude Desktop not finding tool:**
```bash
# Verify MCP server
python -m src.pdf_enrichment.mcp_server_simple

# Check config path
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Tool not generating BEM names:**
- Ensure PDF has fillable form fields (not just scanned image)
- Check for proper field names in the PDF
- Verify field types are correctly identified
- Upload PDF directly to Claude Desktop

**JSON output issues:**
- Copy the entire JSON output from the tool response
- Check for proper JSON formatting
- Verify all required fields are present

### Advanced Troubleshooting

For advanced PDF modification and field detection issues, see the **Archived Modification Engine** folder which contains comprehensive troubleshooting guides and advanced diagnostic tools.

### Performance Notes

- **Large PDFs**: Processing time increases with form complexity
- **Memory usage**: Complex forms with many fields may use more memory
- **Tool responsiveness**: BEM name generation is optimized for Claude Desktop integration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Simple Claude Desktop tool for BEM field name generation! 🚀**
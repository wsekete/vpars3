# PDF Enrichment Platform

🚀 **Transform PDF forms into structured APIs with intelligent BEM-style field naming**

This platform automates the conversion of static PDF forms into cleanly structured APIs by analyzing form fields, generating consistent BEM-style names using financial services conventions, and modifying PDFs while preserving all field properties.

## ✨ Key Features

- **🧠 Intelligent Field Analysis** - AI-powered analysis of PDF forms using Claude's natural language processing
- **🏷️ BEM Naming Convention** - Generates consistent `block_element__modifier` style names
- **🔧 Property Preservation** - Maintains all field properties, positions, and types during renaming
- **📊 Batch Processing** - Analyze and modify multiple PDFs simultaneously
- **🎯 Quality Metrics** - Confidence scoring and validation for all generated names
- **🔍 Visual Previews** - Interactive HTML previews of field changes
- **📋 Claude Desktop Integration** - Seamless workflow with Claude Desktop MCP tools
- **🚀 Financial Services Optimized** - Specialized naming patterns for financial forms

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/pdf-enrichment-platform.git
cd pdf-enrichment-platform

# Install with uv (recommended)
uv install

# Or with pip
pip install -e .
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

### 3. Basic Usage

1. **Upload PDF** to Claude Desktop
2. **Generate BEM Names**: Use `🚀 generate_bem_names` tool
3. **Review Results**: Edit names in the interactive table
4. **Apply Changes**: Use `🔧 modify_form_fields` tool
5. **Download**: Get your renamed PDF

## 🛠️ MCP Tools

### 🚀 generate_bem_names
Analyzes PDF forms and generates BEM-style field names using financial services conventions.

```json
{
  "pdf_filename": "form.pdf",
  "analysis_mode": "comprehensive",
  "custom_sections": ["owner-information", "beneficiary"]
}
```

### 🔧 modify_form_fields
Renames PDF form fields while preserving all properties and positions.

```json
{
  "pdf_filename": "form.pdf",
  "field_mappings": {
    "firstName": "owner-information_first-name",
    "lastName": "owner-information_last-name"
  },
  "preserve_original": true
}
```

### 📊 batch_analyze_forms
Analyzes multiple PDFs with consistency checking across forms.

```json
{
  "pdf_filenames": ["form1.pdf", "form2.pdf"],
  "consistency_check": true,
  "generate_summary": true
}
```

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
beneficiary_withdrawal-frequency__annually
payment-method--group
payment-method_type__ach
payment-method_type__wire
signatures_owner-signature
signatures_owner-date
```

## 📋 Field Types Supported

| Type | Description | BEM Pattern |
|------|-------------|-------------|
| **TextField** | Text input fields | `block_element` |
| **Checkbox** | Individual checkboxes | `block_element` |
| **RadioGroup** | Radio button containers | `block_element--group` |
| **RadioButton** | Individual radio options | `block_element__option` |
| **Dropdown** | Dropdown/select fields | `block_element` |
| **Signature** | Signature fields | `block_signature` |
| **SignatureDate** | Signature date fields | `block_signature-date` |

## 🏗️ Architecture

### Phase 1: MCP Tools & Analysis
- **Field Analysis Engine**: Extracts and categorizes PDF form fields
- **BEM Naming Engine**: Generates consistent names using financial patterns
- **Claude Integration**: Seamless workflow with Claude Desktop

### Phase 2: PDF Modification
- **Property Preservation**: Maintains all field attributes during renaming
- **Validation System**: Ensures no fields are lost or corrupted
- **Preview Generation**: Creates visual previews of changes

### Phase 3: Integration & Deployment
- **CLI Interface**: Batch processing capabilities
- **Web Interface**: Browser-based form review
- **API Integration**: ReTool and external system connectivity

## 📊 Project Structure

```
pdf-enrichment-platform/
├── src/pdf_enrichment/
│   ├── mcp_server.py          # Main MCP server
│   ├── field_analyzer.py      # PDF field analysis
│   ├── pdf_modifier.py        # PDF field modification
│   ├── field_types.py         # Type definitions
│   ├── bem_naming.py          # BEM naming engine
│   ├── preview_generator.py   # HTML preview generation
│   └── utils.py               # Utility functions
├── src/cli/
│   ├── main.py                # CLI interface
│   └── batch_processor.py     # Batch operations
├── src/web/
│   ├── app.py                 # FastAPI web interface
│   └── templates/             # HTML templates
├── tests/                     # Test suite
├── docs/                      # Documentation
└── examples/                  # Sample files
```

## 🔧 CLI Usage

```bash
# Single PDF analysis
pdf-enrichment analyze form.pdf

# Batch processing
pdf-enrichment batch-analyze *.pdf

# Apply BEM renaming
pdf-enrichment modify form.pdf --mappings mappings.json

# Generate preview
pdf-enrichment preview form.pdf --output preview.html
```

## 🌐 Web Interface

Launch the web interface for interactive form review:

```bash
# Start web server
pdf-enrichment web --port 8000

# Open browser
open http://localhost:8000
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/pdf_enrichment

# Run specific test categories
uv run pytest tests/test_field_analyzer.py
uv run pytest tests/test_pdf_modifier.py
```

## 📈 Quality Metrics

### Confidence Scoring
- **High (≥80%)**: Well-identified fields with clear sections
- **Medium (50-79%)**: Reasonable matches requiring minor review
- **Low (<50%)**: Ambiguous fields needing manual attention

### Validation Checks
- ✅ BEM format compliance
- ✅ Field count preservation
- ✅ Property retention
- ✅ Naming conflict detection
- ✅ Cross-form consistency

## 🔍 Examples

### Input PDF Fields
```
firstName
lastName
streetAddress
city
state
zipCode
primaryBeneficiary
contingentBeneficiary
signatureDate
```

### Generated BEM Names
```
owner-information_first-name
owner-information_last-name
address-information_street-address
address-information_city
address-information_state
address-information_zip-code
beneficiary_primary-name
beneficiary_contingent-name
signatures_owner-date
```

### Confidence Analysis
```
High Confidence: 7 fields (77.8%)
Medium Confidence: 2 fields (22.2%)
Low Confidence: 0 fields (0.0%)
```

## 🚀 Advanced Features

### Custom Section Mapping
```python
custom_sections = {
    "applicant": "owner-information",
    "beneficiaries": "beneficiary",
    "banking": "payment-information"
}
```

### Field Property Preservation
```python
preserve_properties = {
    "font": True,
    "font_size": True,
    "position": True,
    "validation": True,
    "required": True
}
```

### Batch Consistency Checking
```python
consistency_rules = {
    "similar_fields": True,
    "naming_patterns": True,
    "cross_form_validation": True
}
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and install
git clone https://github.com/yourorg/pdf-enrichment-platform.git
cd pdf-enrichment-platform
uv install --dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest
```

### Code Quality

- **Formatting**: `uv run ruff format .`
- **Linting**: `uv run ruff check .`
- **Type Checking**: `uv run pyright`
- **Testing**: `uv run pytest`

## 📚 Documentation

- [Setup Guide](docs/setup.md)
- [Claude Desktop Integration](docs/claude_desktop_config.md)
- [API Reference](docs/api_reference.md)
- [BEM Naming Conventions](docs/bem_conventions.md)
- [Field Analysis Guide](docs/field_analysis.md)

## 🐛 Troubleshooting

### Common Issues

**Claude Desktop not finding tools:**
```bash
# Verify MCP server path
python -m pdf_enrichment.mcp_server

# Check Claude Desktop config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**PDF modification errors:**
```bash
# Check PDF file permissions
ls -la your-file.pdf

# Verify PyPDFForm installation
python -c "import PyPDFForm; print('OK')"
```

**Field analysis failures:**
```bash
# Enable debug logging
export PDF_ENRICHMENT_LOG_LEVEL=DEBUG

# Test with sample PDF
pdf-enrichment analyze examples/sample_form.pdf --debug
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PyPDFForm** - PDF form manipulation library
- **Claude Desktop** - AI-powered form analysis
- **MCP Protocol** - Tool integration framework
- **Financial Services Community** - Domain expertise and conventions

## 🔗 Links

- [GitHub Repository](https://github.com/yourorg/pdf-enrichment-platform)
- [Documentation](https://pdf-enrichment-platform.readthedocs.io)
- [Issue Tracker](https://github.com/yourorg/pdf-enrichment-platform/issues)
- [Discussions](https://github.com/yourorg/pdf-enrichment-platform/discussions)

---

**Transform your PDF forms into structured APIs with intelligent BEM naming! 🚀**
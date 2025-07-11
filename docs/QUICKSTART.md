# PDF Enrichment Platform

## Quick Start Guide

### Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/pdf-enrichment-platform.git
cd pdf-enrichment-platform

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -r requirements.txt
```

### Claude Desktop Integration

1. **Configure Claude Desktop**:

```json
{
  "mcpServers": {
    "pdf-enrichment": {
      "command": "python",
      "args": [
        "/path/to/vpars3/src/pdf_enrichment/mcp_server.py"
      ],
      "cwd": "/path/to/vpars3",
      "env": {
        "PYTHONPATH": "/path/to/vpars3"
      }
    }
  }
}
```

2. **Restart Claude Desktop**

3. **Use the Tools**:
   - Upload a PDF to Claude Desktop
   - Look for `🚀 generate_bem_field_names` in the tools menu
   - Enter the PDF filename
   - Review and edit the generated BEM names
   - Use `modify_form_fields` to apply changes

### Command Line Usage

#### Analyze a PDF Form

```bash
# Basic analysis
uv run pdf-enrichment analyze form.pdf

# Comprehensive analysis with custom sections
uv run pdf-enrichment analyze form.pdf \
  --analysis-mode comprehensive \
  --custom-sections "owner-information,payment-details" \
  --output analysis.json

# Generate HTML preview
uv run pdf-enrichment analyze form.pdf --format html --output report.html
```

#### Modify PDF Fields

```bash
# Create field mappings JSON
cat > mappings.json << EOF
{
  "firstName": "owner-information_first-name",
  "lastName": "owner-information_last-name",
  "email": "contact-information_email-address"
}
EOF

# Apply modifications
uv run pdf-enrichment modify form.pdf mappings.json \
  --output modified_form.pdf \
  --preserve-original \
  --validate
```

#### Batch Analysis

```bash
# Analyze multiple forms
uv run pdf-enrichment batch-analyze *.pdf \
  --output-dir batch_results \
  --consistency-check \
  --format html
```

#### Start Web Server

```bash
# Start HTTP server for web interface
uv run pdf-enrichment serve --host 0.0.0.0 --port 8000

# Or start MCP server (stdio mode)
uv run pdf-enrichment serve --stdio
```

### Web Interface

Access the web interface at `http://localhost:8000/templates/upload` to:

- Upload and analyze PDF forms
- Generate interactive field reviews
- Download modified PDFs
- Validate BEM names

### API Usage

#### Python API

```python
import asyncio
from pathlib import Path
from pdf_enrichment import FieldAnalyzer, PDFModifier

async def main():
    # Analyze a form
    analyzer = FieldAnalyzer()
    analysis = await analyzer.analyze_form(
        pdf_path=Path("form.pdf"),
        analysis_mode="comprehensive"
    )
    
    print(f"Found {analysis.total_fields} fields")
    print(f"High confidence: {analysis.confidence_summary['high']}")
    
    # Generate field mappings
    mappings = {
        result.original_name: result.bem_name 
        for result in analysis.bem_mappings
    }
    
    # Modify the PDF
    modifier = PDFModifier()
    result = await modifier.modify_fields(
        pdf_path=Path("form.pdf"),
        field_mappings=mappings,
        output_path=Path("modified_form.pdf")
    )
    
    if result.success:
        print(f"✅ Modified {len(result.modifications)} fields")
    else:
        print(f"❌ Errors: {result.errors}")

asyncio.run(main())
```

#### REST API

```bash
# Analyze PDF
curl -X POST http://localhost:8000/analyze \
  -F "file=@form.pdf" \
  -F "analysis_mode=comprehensive"

# Modify PDF
curl -X POST http://localhost:8000/modify \
  -F "file=@form.pdf" \
  -F 'field_mappings={"firstName":"owner-information_first-name"}' \
  --output modified_form.pdf
```

## BEM Naming Conventions

### Format Rules

- **Block**: Form section (`owner-information`, `payment-details`)
- **Element**: Field purpose (`first-name`, `account-number`)
- **Modifier**: Field variation (`__monthly`, `__gross`)
- **Radio Groups**: Container suffix (`--group`)

### Examples

```
✅ Valid BEM Names:
- owner-information_first-name
- payment-details_account-number
- withdrawal-option_frequency--group
- withdrawal-option_frequency__monthly
- beneficiary-information_relationship__spouse

❌ Invalid BEM Names:
- FirstName (no underscore, uppercase)
- owner_information_name (wrong separator)
- class_name (reserved word)
- payment- (incomplete)
```

### Field Type Mapping

| Field Type | Example BEM Name | Notes |
|------------|------------------|-------|
| TextField | `owner-information_first-name` | Standard text input |
| Checkbox | `preferences_email-notifications` | Boolean choice |
| RadioGroup | `payment-method--group` | Container with `--group` |
| RadioButton | `payment-method__credit-card` | Individual option |
| Signature | `signatures_owner` | Signature field |
| Dropdown | `beneficiary_relationship` | Select dropdown |

## Architecture

### Component Overview

```
pdf-enrichment-platform/
├── src/pdf_enrichment/
│   ├── field_analyzer.py      # PDF analysis engine
│   ├── bem_naming.py          # BEM name generation
│   ├── pdf_modifier.py        # PDF field modification
│   ├── preview_generator.py   # HTML preview generation
│   ├── mcp_server.py          # MCP server for Claude Desktop
│   └── field_types.py         # Data models
├── src/cli/                   # Command line interface
├── src/web/                   # Web application
└── tests/                     # Test suite
```

### Data Flow

1. **PDF Upload** → Field extraction with PyPDFForm
2. **Analysis** → BEM name generation with confidence scoring
3. **Review** → Interactive HTML table for editing
4. **Modification** → Apply field renaming while preserving properties
5. **Validation** → Ensure BEM compliance and field integrity

### Key Features

- **Intelligent Field Detection**: Analyzes field context and purpose
- **BEM Name Generation**: Financial services naming conventions
- **Property Preservation**: Maintains fonts, colors, positions
- **Confidence Scoring**: High/medium/low confidence levels
- **Conflict Detection**: Identifies naming conflicts
- **Batch Processing**: Handle multiple forms consistently
- **Interactive Preview**: Edit BEM names before applying

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/yourorg/pdf-enrichment-platform.git
cd pdf-enrichment-platform
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Format and lint
uv run ruff format .
uv run ruff check . --fix
uv run pyright
```

### Project Structure

```
vpars3/
├── src/
│   ├── pdf_enrichment/        # Core PDF processing
│   ├── cli/                   # Command line interface
│   ├── web/                   # Web application
│   └── retool/                # Retool integration (optional)
├── tests/                     # Test suite
├── docs/                      # Documentation
├── examples/                  # Example files
├── scripts/                   # Utility scripts
├── pyproject.toml            # Project configuration
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_bem_naming.py

# Run tests for specific functionality
uv run pytest -k "test_field_analysis"
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following the coding standards
4. Run tests: `uv run pytest`
5. Run formatting: `uv run ruff format . && uv run ruff check . --fix`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Submit a pull request

### Code Standards

- **Python 3.9+** required
- **Type hints** for all functions
- **Docstrings** for public APIs
- **Tests** for new features
- **Ruff** for formatting and linting
- **Pyright** for type checking

## Troubleshooting

### Common Issues

#### PyPDFForm Installation

```bash
# If PyPDFForm fails to install
pip install --upgrade pip setuptools wheel
pip install PyPDFForm
```

#### Claude Desktop Connection

1. Check the configuration file path:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Verify Python path and PYTHONPATH in config
3. Restart Claude Desktop after configuration changes
4. Check logs for connection errors

#### PDF Processing Errors

```python
# Debug PDF issues
from PyPDFForm import PdfWrapper

try:
    pdf = PdfWrapper("problematic_form.pdf")
    print(f"Fields found: {len(pdf.widgets)}")
    for name, widget in pdf.widgets.items():
        print(f"- {name}: {type(widget).__name__}")
except Exception as e:
    print(f"Error: {e}")
```

#### Memory Issues with Large PDFs

```bash
# Increase memory limit for large files
export PYTHONMAXMEMORYSIZE=4GB
uv run pdf-enrichment analyze large_form.pdf --analysis-mode quick
```

### Performance Optimization

- Use `--analysis-mode quick` for faster processing
- Process PDFs in smaller batches
- Enable caching for repeated analysis
- Use async processing for better concurrency

### Logging and Debugging

```bash
# Enable verbose logging
uv run pdf-enrichment --verbose analyze form.pdf

# Set log level via environment
export PDF_ENRICHMENT_LOG_LEVEL=DEBUG
uv run pdf-enrichment analyze form.pdf

# Log to file
uv run pdf-enrichment --log-file debug.log analyze form.pdf
```

## Support

- **Documentation**: [GitHub Wiki](https://github.com/yourorg/pdf-enrichment-platform/wiki)
- **Issues**: [GitHub Issues](https://github.com/yourorg/pdf-enrichment-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourorg/pdf-enrichment-platform/discussions)
- **Email**: dev@yourorg.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

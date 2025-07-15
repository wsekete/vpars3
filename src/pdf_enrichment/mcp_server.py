"""
MCP Server for PDF Form Field BEM Renaming

Simple single-tool server that analyzes PDF forms and generates BEM-style field names
with JSON export for use with external PDF modification tools.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ImageContent,
    ListPromptsResult,
    ListResourcesResult,
    ListToolsResult,
    ServerCapabilities,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pdf_enrichment.field_analyzer import FieldAnalyzer
from src.pdf_enrichment.utils import setup_logging


# Configure logging
logger = logging.getLogger(__name__)


class GenerateBEMNamesInput(BaseModel):
    """Input for generate_bem_names_and_export_json tool."""
    
    pdf_filename: str = Field(description="Name of the PDF file uploaded to Claude Desktop")
    custom_context: Optional[str] = Field(
        None,
        description="Optional context about the PDF form (e.g., 'Life Insurance Service Request', 'Retirement Plan Form')"
    )


class PDFEnrichmentServer:
    """Simple MCP Server for PDF Form Field BEM Naming."""
    
    def __init__(self) -> None:
        self.server = Server("pdf-enrichment", version="0.2.0")
        self.field_analyzer = FieldAnalyzer()
        
        # Register single tool
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register the single MCP tool."""
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="generate_bem_names_and_export_json",
                        description=(
                            "🚀 Analyze PDF form fields and generate BEM-style names with JSON export. "
                            "This tool extracts all form fields, analyzes them for structure and purpose, "
                            "then generates comprehensive BEM naming mappings that can be used with "
                            "external PDF modification tools."
                        ),
                        inputSchema=GenerateBEMNamesInput.model_json_schema(),
                    ),
                ]
            )
        
        @self.server.list_prompts()
        async def list_prompts():
            """List available prompts."""
            return ListPromptsResult(prompts=[])
        
        @self.server.list_resources()
        async def list_resources():
            """List available resources."""
            return ListResourcesResult(resources=[])
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if name == "generate_bem_names_and_export_json":
                    return await self._generate_bem_names_and_export_json(
                        GenerateBEMNamesInput(**arguments)
                    )
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except ValueError as e:
                logger.error(f"Invalid arguments for tool {name}: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ Invalid arguments for {name}: {str(e)}"
                        )
                    ]
                )
            except Exception as e:
                logger.exception(f"Error in tool {name}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ Error executing {name}: {str(e)}"
                        )
                    ]
                )
    
    async def _generate_bem_names_and_export_json(self, input_data: GenerateBEMNamesInput) -> CallToolResult:
        """Generate BEM field names and export as JSON."""
        try:
            # Try to find PDF file in common locations
            pdf_path = await self._find_pdf_file(input_data.pdf_filename)
            if not pdf_path:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"""❌ **PDF File Not Found**: `{input_data.pdf_filename}`

**Searched locations:**
- Current directory: `./{input_data.pdf_filename}`
- Downloads: `~/Downloads/{input_data.pdf_filename}`
- Desktop: `~/Desktop/{input_data.pdf_filename}`

**💡 Solutions:**
1. Upload the PDF to Claude Desktop (it will be in Downloads)
2. Ensure the filename is exact (case-sensitive)
3. Use the full filename including `.pdf` extension"""
                        )
                    ]
                )
            
            # Extract form fields
            logger.info(f"Extracting form fields from {pdf_path}")
            form_fields = await self.field_analyzer.extract_form_fields(pdf_path)
            
            if not form_fields:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"""❌ **No Form Fields Found**

The PDF `{input_data.pdf_filename}` appears to have no fillable form fields.

**This could mean:**
- The PDF is a scanned image (not interactive)
- The PDF has no AcroForm fields
- The PDF uses a different form technology

**💡 Try:**
- Using a different PDF with interactive form fields
- Converting scanned PDFs to fillable forms first"""
                        )
                    ]
                )
            
            # Generate embedded BEM naming prompt
            bem_analysis_prompt = self._create_bem_analysis_prompt(form_fields, pdf_path.name, input_data.custom_context)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=bem_analysis_prompt
                    )
                ]
            )
        
        except FileNotFoundError as e:
            logger.error(f"PDF file not found: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ PDF file not found: {input_data.pdf_filename}"
                    )
                ]
            )
        except Exception as e:
            logger.exception("Error generating BEM names")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Failed to analyze PDF: {str(e)}"
                    )
                ]
            )
    
    async def _find_pdf_file(self, filename: str) -> Optional[Path]:
        """Find PDF file in common locations."""
        search_locations = [
            Path(filename),
            Path.home() / "Downloads" / filename,
            Path.home() / "Desktop" / filename,
            Path(".") / filename,
        ]
        
        for location in search_locations:
            if location.exists() and location.suffix.lower() == '.pdf':
                return location
        
        return None
    
    def _create_bem_analysis_prompt(self, form_fields: List, filename: str, custom_context: Optional[str]) -> str:
        """Create comprehensive BEM analysis prompt with embedded field data."""
        
        # Create field summary for the prompt
        field_summary = []
        for i, field in enumerate(form_fields[:50], 1):  # Limit to 50 for prompt size
            field_summary.append(f"{i}. **{field.name}** (Type: {field.field_type.value})")
        
        if len(form_fields) > 50:
            field_summary.append(f"... and {len(form_fields) - 50} more fields")
        
        field_list = "\n".join(field_summary)
        context_info = custom_context or "PDF form"
        
        prompt = f"""# 🚀 BEM Field Name Generation for {filename}

I've analyzed this PDF form and found **{len(form_fields)} form fields**. Please generate comprehensive BEM-style field names for ALL fields using financial services conventions.

**Context**: {context_info}

## 📋 Discovered Form Fields

{field_list}

## 🚨 CRITICAL REQUIREMENTS

### ✅ COMPLETE FIELD MAPPING
**YOU MUST include EVERY SINGLE form field listed above. No exceptions.**
- ❌ **DO NOT omit any fields**, even if they seem redundant
- ❌ **DO NOT take shortcuts** or provide "sample" mappings  
- ❌ **DO NOT skip fields** because they're unclear
- ✅ **INCLUDE ALL {len(form_fields)} FIELDS** in your final JSON

### 🏷️ BEM Format Rules
- **Structure**: `block_element` or `block_element__modifier`
- **Separators**: Use `_` between block and element, `__` before modifiers
- **Case**: Lowercase only, use hyphens for multi-word phrases
- **Radio Groups**: Use `--group` suffix for containers, `__option` for individual buttons

### 📊 Financial Services Blocks
Use these common blocks for financial forms:
- `owner-information` - Policy/account owner details
- `insured-information` - Person being insured
- `beneficiary` - Beneficiary information  
- `address-information` - Mailing/residential addresses
- `payment-information` - Banking/payment details
- `dividend-option` - Dividend selections
- `withdrawal-option` - Withdrawal preferences
- `contact-information` - Phone/email details
- `signatures` - Signature and date fields
- `policy-details` - Policy-specific information

### 🔍 Radio Button Detection
Look for fields with similar names that represent choices:
- Same base name with numbers: `option_1`, `option_2`, `option_3`
- Similar patterns: `payment_ach`, `payment_check`, `payment_wire`
- Create BOTH the group (`payment-method--group`) AND individual options (`payment-method__ach`)

## 📤 REQUIRED OUTPUT FORMAT

You MUST provide your response in this exact format:

### Field Discovery Summary
**Total fields analyzed: {len(form_fields)}**
**BEM mappings created: [YOUR_COUNT]**

### Complete BEM Mapping (JSON)
```json
{{
  "source_filename": "{filename}",
  "analysis_timestamp": "[CURRENT_TIMESTAMP]",
  "total_fields": {len(form_fields)},
  "form_context": "{context_info}",
  "bem_mappings": {{
    "original_field_name_1": "bem_field_name_1",
    "original_field_name_2": "bem_field_name_2"
  }}
}}
```

### Validation Checklist
- [ ] All {len(form_fields)} fields included
- [ ] BEM format compliance checked
- [ ] Radio groups properly identified
- [ ] Financial services conventions applied
- [ ] JSON format validated

## 🎯 Examples of Good BEM Names

**Basic Fields:**
- `firstName` → `owner-information_first-name`
- `policyNumber` → `policy-details_policy-number` 
- `emailAddress` → `contact-information_email-address`

**Radio Groups:**
- `dividendOption1` → `dividend-option__accumulate-interest`
- `dividendOption2` → `dividend-option__reduce-premium`
- (Plus `dividend-option--group` for the container)

**Signatures:**
- `ownerSignature` → `signatures_owner-signature`
- `ownerSignatureDate` → `signatures_owner-date`

## 🚀 START ANALYSIS

Please analyze ALL {len(form_fields)} fields above and provide the complete BEM mapping in the required JSON format. Remember: **EVERY field must be included - no exceptions!**"""

        return prompt
    
    async def run(self) -> None:
        """Run the MCP server."""
        setup_logging(level=logging.INFO)
        logger.info("Starting PDF BEM Naming MCP Server (v0.2.0)...")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("Connected to stdio streams")
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="pdf-enrichment",
                        server_version="0.2.0",
                        capabilities=ServerCapabilities(
                            tools={},
                            resources={},
                            prompts={},
                            experimental={}
                        )
                    ),
                )
        except Exception as e:
            logger.exception(f"Error running MCP server: {e}")
            raise


async def main() -> None:
    """Main entry point."""
    server = PDFEnrichmentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
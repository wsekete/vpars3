#!/usr/bin/env python3
"""
MCP Server for PDF Form Field BEM Renaming

Class-based server that analyzes PDF forms and generates BEM-style field names
with JSON export for use with external PDF modification tools.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import (
    CallToolResult,
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
from src.pdf_enrichment.pdf_modifier import PDFModifier
from src.pdf_enrichment.utils import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


class GenerateBEMNamesInput(BaseModel):
    """Input for generate_bem_names tool."""
    
    pdf_filename: str = Field(description="Name of the PDF file uploaded to Claude Desktop")
    custom_context: Optional[str] = Field(
        None,
        description="Optional context about the PDF form (e.g., 'Life Insurance Service Request', 'Retirement Plan Form')"
    )


class ExtractPDFFieldsInput(BaseModel):
    """Input for extract_pdf_fields tool."""
    
    pdf_filename: str = Field(description="Name of the PDF file to analyze")
    detailed_analysis: bool = Field(
        True,
        description="Whether to provide detailed field analysis"
    )


class ModifyFormFieldsInput(BaseModel):
    """Input for modify_form_fields tool."""
    
    pdf_filename: str = Field(description="Name of the PDF file to modify")
    field_mappings: Dict[str, str] = Field(
        description="Mapping of original field names to new BEM names"
    )
    output_filename: Optional[str] = Field(
        None,
        description="Output filename (defaults to {original}_bem_renamed.pdf)"
    )
    preserve_original: bool = Field(
        True,
        description="Whether to preserve the original PDF file"
    )


class PDFEnrichmentServer:
    """Class-based MCP Server for PDF Form Field BEM Naming."""
    
    def __init__(self) -> None:
        self.server = Server("pdf-enrichment")
        self.field_analyzer = FieldAnalyzer()
        self.pdf_modifier = PDFModifier()
        
        # Server state
        self.analysis_cache: Dict[str, Any] = {}
        self.modification_results: Dict[str, Any] = {}
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register MCP tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="generate_bem_names",
                        description="🚀 Analyze PDF form fields and generate BEM-style names. This tool extracts all form fields, analyzes them for structure and purpose, then generates comprehensive BEM naming mappings with JSON output for use with external PDF modification tools.",
                        inputSchema=GenerateBEMNamesInput.model_json_schema(),
                    ),
                ]
            )
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if name == "generate_bem_names":
                    return await self._generate_bem_names(GenerateBEMNamesInput(**arguments))
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
    
    async def _generate_bem_names(self, input_data: GenerateBEMNamesInput) -> CallToolResult:
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
            
            # Cache analysis result
            self.analysis_cache[input_data.pdf_filename] = {
                'form_fields': form_fields,
                'pdf_path': pdf_path,
                'custom_context': input_data.custom_context
            }
            
            # Generate embedded BEM naming prompt
            bem_analysis_prompt = self._create_bem_analysis_prompt(
                form_fields, pdf_path.name, input_data.custom_context
            )
            
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
    
    async def _extract_pdf_fields(self, input_data: ExtractPDFFieldsInput) -> CallToolResult:
        """Extract PDF form fields (for test compatibility)."""
        try:
            pdf_path = await self._find_pdf_file(input_data.pdf_filename)
            if not pdf_path:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ PDF file not found: {input_data.pdf_filename}"
                        )
                    ]
                )
            
            form_fields = await self.field_analyzer.extract_form_fields(pdf_path)
            
            if not form_fields:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ No form fields found in {input_data.pdf_filename}"
                        )
                    ]
                )
            
            # Format field summary
            field_summary = self._format_field_summary(form_fields, input_data.pdf_filename)
            
            # Generate JSON output
            json_output = {
                "filename": input_data.pdf_filename,
                "total_fields": len(form_fields),
                "fields": [
                    {
                        "name": field.name,
                        "type": field.field_type.value,
                        "position": {
                            "x": field.position.x,
                            "y": field.position.y,
                            "width": field.position.width,
                            "height": field.position.height,
                            "page": field.position.page
                        },
                        "required": field.required,
                        "readonly": field.readonly
                    }
                    for field in form_fields
                ]
            }
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=field_summary
                    ),
                    TextContent(
                        type="text",
                        text=f"```json\n{json.dumps(json_output, indent=2)}\n```"
                    )
                ]
            )
            
        except Exception as e:
            logger.exception("Error extracting PDF fields")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Failed to extract fields: {str(e)}"
                    )
                ]
            )
    
    async def _modify_form_fields(self, input_data: ModifyFormFieldsInput) -> CallToolResult:
        """Modify PDF form fields (for test compatibility)."""
        try:
            pdf_path = await self._find_pdf_file(input_data.pdf_filename)
            if not pdf_path:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ PDF file not found: {input_data.pdf_filename}"
                        )
                    ]
                )
            
            # Generate output filename
            if input_data.output_filename:
                output_path = Path(input_data.output_filename)
            else:
                output_path = pdf_path.with_stem(f"{pdf_path.stem}_bem_renamed")
            
            # Perform field modifications
            logger.info(f"Modifying fields in {pdf_path}")
            modification_result = await self.pdf_modifier.modify_fields(
                pdf_path=pdf_path,
                field_mappings=input_data.field_mappings,
                output_path=output_path,
                preserve_original=input_data.preserve_original
            )
            
            # Cache modification result
            self.modification_results[input_data.pdf_filename] = modification_result
            
            # Format modification summary
            if modification_result.success:
                summary = self._format_modification_summary(modification_result)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=summary
                        )
                    ]
                )
            else:
                error_text = "## ❌ PDF Field Modification Failed\n\n"
                error_text += f"**Original PDF:** {input_data.pdf_filename}\n"
                error_text += f"**Errors:** {len(modification_result.errors)}\n\n"
                
                for error in modification_result.errors:
                    error_text += f"- {error}\n"
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=error_text
                        )
                    ]
                )
        
        except Exception as e:
            logger.exception("Error modifying form fields")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Failed to modify fields: {str(e)}"
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
    
    def _format_field_summary(self, form_fields: List, filename: str) -> str:
        """Format field summary for display."""
        summary = f"## 📋 PDF Field Extraction Complete\n\n"
        summary += f"**PDF:** {filename}\n"
        summary += f"**Total Fields:** {len(form_fields)}\n\n"
        
        # Group fields by type
        field_types = {}
        for field in form_fields:
            field_type = field.field_type.value
            if field_type not in field_types:
                field_types[field_type] = []
            field_types[field_type].append(field)
        
        summary += "### Field Types:\n"
        for field_type, fields in field_types.items():
            summary += f"- **{field_type}:** {len(fields)} fields\n"
        
        summary += "\n### Field Details:\n"
        for i, field in enumerate(form_fields[:20], 1):  # Limit to first 20
            summary += f"{i}. **{field.name}** ({field.field_type.value})\n"
        
        if len(form_fields) > 20:
            summary += f"... and {len(form_fields) - 20} more fields\n"
        
        return summary
    
    def _format_modification_summary(self, result) -> str:
        """Format modification summary for display."""
        summary = f"## ✅ PDF Field Modification Complete\n\n"
        summary += f"**Original PDF:** {Path(result.original_pdf_path).name}\n"
        summary += f"**Modified PDF:** {Path(result.modified_pdf_path).name}\n"
        summary += f"**Fields Modified:** {len(result.modifications)}\n"
        summary += f"**Timestamp:** {result.timestamp}\n\n"
        
        if result.modifications:
            summary += "### Modifications:\n"
            for mod in result.modifications:
                summary += f"- **{mod['old']}** → **{mod['new']}** ({mod['type']})\n"
        
        if result.warnings:
            summary += "\n### Warnings:\n"
            for warning in result.warnings:
                summary += f"- {warning}\n"
        
        summary += "\n**Your PDF is ready for download!**"
        return summary
    
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


async def main():
    """Main entry point."""
    server = PDFEnrichmentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
"""
MCP Server for PDF Form Field Enrichment

This server provides tools for analyzing PDF forms and generating BEM-style field names
using Claude's natural language processing capabilities.
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
from src.pdf_enrichment.field_types import FormField, FieldModificationResult
from src.pdf_enrichment.pdf_modifier import PDFModifier
from src.pdf_enrichment.utils import setup_logging


# Configure logging
logger = logging.getLogger(__name__)


class ExtractPDFFieldsInput(BaseModel):
    """Input for extract_pdf_fields tool."""
    
    pdf_filename: str = Field(description="Name of the PDF file uploaded to Claude Desktop")


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
    """MCP Server for PDF Form Field Enrichment."""
    
    def __init__(self) -> None:
        self.server = Server("pdf-enrichment", version="0.1.0")
        self.field_analyzer = FieldAnalyzer()
        self.pdf_modifier = PDFModifier()
        
        # Register tools
        self._register_tools()
        
        # Server state
        self.modification_results: Dict[str, FieldModificationResult] = {}
    
    def _register_tools(self) -> None:
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="extract_pdf_fields",
                        description=(
                            "📋 Extract form field information from PDF files. Returns a "
                            "structured list of all form fields with their types, names, and "
                            "properties for Claude Desktop to analyze and generate BEM names."
                        ),
                        inputSchema=ExtractPDFFieldsInput.model_json_schema(),
                    ),
                    Tool(
                        name="modify_form_fields",
                        description=(
                            "🔧 Modify PDF form fields using BEM name mappings. Renames fields "
                            "while preserving all properties, positions, and types. Creates a "
                            "new PDF with properly named fields."
                        ),
                        inputSchema=ModifyFormFieldsInput.model_json_schema(),
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
                if name == "extract_pdf_fields":
                    return await self._extract_pdf_fields(
                        ExtractPDFFieldsInput(**arguments)
                    )
                elif name == "modify_form_fields":
                    return await self._modify_form_fields(
                        ModifyFormFieldsInput(**arguments)
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
    
    async def _extract_pdf_fields(self, input_data: ExtractPDFFieldsInput) -> CallToolResult:
        """Extract form field information from PDF files."""
        try:
            # Read PDF file
            pdf_path = Path(input_data.pdf_filename)
            if not pdf_path.exists():
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ PDF file not found: {input_data.pdf_filename}"
                        )
                    ]
                )
            
            # Extract form fields (simplified)
            logger.info(f"Extracting form fields from {pdf_path}")
            form_fields = await self.field_analyzer.extract_form_fields(pdf_path)
            
            # Create field summary
            field_summary = self._format_field_summary(form_fields, pdf_path.name)
            
            # Generate downloadable JSON with field data
            json_output = {
                "filename": pdf_path.name,
                "total_fields": len(form_fields),
                "fields": [field.model_dump() for field in form_fields]
            }
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=field_summary
                    ),
                    TextContent(
                        type="text",
                        text=f"📥 **Field Data (JSON)**\n\n```json\n{json.dumps(json_output, indent=2)}\n```"
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
        except PermissionError as e:
            logger.error(f"Permission denied accessing PDF: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Permission denied accessing PDF file: {input_data.pdf_filename}"
                    )
                ]
            )
        except Exception as e:
            logger.exception("Error extracting PDF fields")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Failed to extract PDF fields: {str(e)}"
                    )
                ]
            )
    
    async def _modify_form_fields(self, input_data: ModifyFormFieldsInput) -> CallToolResult:
        """Modify PDF form fields using BEM mappings."""
        try:
            # Validate input
            pdf_path = Path(input_data.pdf_filename)
            if not pdf_path.exists():
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
            
            # Generate success summary
            success_text = self._format_modification_summary(modification_result)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=success_text
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
        except PermissionError as e:
            logger.error(f"Permission denied accessing PDF: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Permission denied accessing PDF file: {input_data.pdf_filename}"
                    )
                ]
            )
        except ValueError as e:
            logger.error(f"Invalid field mappings: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Invalid field mappings: {str(e)}"
                    )
                ]
            )
        except Exception as e:
            logger.exception("Error modifying form fields")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Failed to modify form fields: {str(e)}"
                    )
                ]
            )
    
    
    def _format_field_summary(self, fields: List[FormField], filename: str) -> str:
        """Format field extraction summary."""
        # Count field types
        field_type_counts = {}
        for field in fields:
            field_type = field.field_type.value
            field_type_counts[field_type] = field_type_counts.get(field_type, 0) + 1
        
        # Get top field types
        top_types = sorted(
            field_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Sample field names
        sample_fields = fields[:10]
        
        summary = f"""## 📋 PDF Field Extraction Complete

**Form:** {filename}
**Total Fields:** {len(fields)}

### 📊 Field Type Distribution
{chr(10).join(f"- **{field_type}:** {count} fields" for field_type, count in top_types)}

### 📝 Sample Field Names
{chr(10).join(f"- `{field.name}` ({field.field_type.value})" for field in sample_fields)}

---
**Next Steps:**
1. Review the field data in the JSON below
2. Generate BEM names for these fields
3. Use the `modify_form_fields` tool to apply your generated names
"""
        
        return summary
    
    def _format_modification_summary(self, result: FieldModificationResult) -> str:
        """Format field modification summary."""
        if result.success:
            summary = f"""## ✅ PDF Field Modification Complete

**Original:** {result.original_pdf_path}
**Modified:** {result.modified_pdf_path}
**Fields Modified:** {len(result.modifications)}
**Timestamp:** {result.timestamp}

### 📝 Field Changes Summary
{chr(10).join(f"- `{mod['old']}` → `{mod['new']}` ({mod['type']})" for mod in result.modifications[:10])}

{f"...and {len(result.modifications) - 10} more fields" if len(result.modifications) > 10 else ""}

### 🎯 Validation Results
- **Fields Before:** {result.field_count_before}
- **Fields After:** {result.field_count_after}
- **Errors:** {len(result.errors)}
- **Warnings:** {len(result.warnings)}

{f"### ⚠️ Warnings{chr(10)}{chr(10).join(f'- {warning}' for warning in result.warnings)}" if result.warnings else ""}

---
**✅ Your PDF is ready for download or further processing!**
"""
        else:
            summary = f"""## ❌ PDF Field Modification Failed

**File:** {result.original_pdf_path}
**Timestamp:** {result.timestamp}

### 🚨 Errors
{chr(10).join(f"- {error}" for error in result.errors)}

{f"### ⚠️ Warnings{chr(10)}{chr(10).join(f'- {warning}' for warning in result.warnings)}" if result.warnings else ""}

---
**Please review the errors above and try again.**
"""
        
        return summary
    
    
    async def run(self) -> None:
        """Run the MCP server."""
        setup_logging(level=logging.INFO)
        logger.info("Starting PDF Enrichment MCP Server...")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("Connected to stdio streams")
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="pdf-enrichment",
                        server_version="0.1.0",
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

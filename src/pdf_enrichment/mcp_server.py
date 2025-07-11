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
    ListToolsResult,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from .field_analyzer import FieldAnalyzer
from .field_types import BEMNamingResult, FormAnalysis, FieldModificationResult
from .pdf_modifier import PDFModifier
from .preview_generator import PreviewGenerator
from .utils import setup_logging


# Configure logging
logger = logging.getLogger(__name__)


class GenerateBEMNamesInput(BaseModel):
    """Input for generate_bem_names tool."""
    
    pdf_filename: str = Field(description="Name of the PDF file uploaded to Claude Desktop")
    analysis_mode: str = Field(
        default="comprehensive",
        description="Analysis mode: 'quick' for basic analysis, 'comprehensive' for detailed analysis"
    )
    custom_sections: Optional[List[str]] = Field(
        None,
        description="Custom section names to prioritize in BEM naming"
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


class BatchAnalysisInput(BaseModel):
    """Input for batch_analyze_forms tool."""
    
    pdf_filenames: List[str] = Field(
        description="List of PDF filenames to analyze in batch"
    )
    consistency_check: bool = Field(
        True,
        description="Whether to check naming consistency across forms"
    )
    generate_summary: bool = Field(
        True,
        description="Whether to generate a summary report"
    )


class PDFEnrichmentServer:
    """MCP Server for PDF Form Field Enrichment."""
    
    def __init__(self) -> None:
        self.server = Server("pdf-enrichment")
        self.field_analyzer = FieldAnalyzer()
        self.pdf_modifier = PDFModifier()
        self.preview_generator = PreviewGenerator()
        
        # Register tools
        self._register_tools()
        
        # Server state
        self.analysis_cache: Dict[str, FormAnalysis] = {}
        self.modification_results: Dict[str, FieldModificationResult] = {}
    
    def _register_tools(self) -> None:
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="generate_bem_names",
                        description=(
                            "🚀 Generate BEM-style field names for PDF forms using financial "
                            "services naming conventions. Analyzes form structure and creates "
                            "consistent, meaningful API names."
                        ),
                        inputSchema=GenerateBEMNamesInput.model_json_schema(),
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
                    Tool(
                        name="batch_analyze_forms",
                        description=(
                            "📊 Analyze multiple PDF forms in batch, generating consistent BEM "
                            "names across all forms. Includes cross-form consistency checking "
                            "and summary reporting."
                        ),
                        inputSchema=BatchAnalysisInput.model_json_schema(),
                    ),
                ]
            )
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if name == "generate_bem_names":
                    return await self._generate_bem_names(
                        GenerateBEMNamesInput(**arguments)
                    )
                elif name == "modify_form_fields":
                    return await self._modify_form_fields(
                        ModifyFormFieldsInput(**arguments)
                    )
                elif name == "batch_analyze_forms":
                    return await self._batch_analyze_forms(
                        BatchAnalysisInput(**arguments)
                    )
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
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
        """Generate BEM names for PDF form fields."""
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
            
            # Analyze form structure
            logger.info(f"Analyzing form structure for {pdf_path}")
            form_analysis = await self.field_analyzer.analyze_form(
                pdf_path=pdf_path,
                analysis_mode=input_data.analysis_mode,
                custom_sections=input_data.custom_sections
            )
            
            # Cache analysis result
            self.analysis_cache[input_data.pdf_filename] = form_analysis
            
            # Generate HTML preview
            html_preview = self.preview_generator.generate_field_review_html(
                form_analysis=form_analysis
            )
            
            # Create summary text
            summary_text = self._format_analysis_summary(form_analysis)
            
            # Generate downloadable JSON
            json_output = form_analysis.model_dump(mode="json")
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=summary_text
                    ),
                    TextContent(
                        type="text",
                        text=f"📄 **Interactive Field Review**\n\n{html_preview}"
                    ),
                    TextContent(
                        type="text",
                        text=f"📥 **Download JSON Mapping**\n\n```json\n{json.dumps(json_output, indent=2)}\n```"
                    )
                ]
            )
        
        except Exception as e:
            logger.exception("Error generating BEM names")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Failed to generate BEM names: {str(e)}"
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
            
            # Generate visual preview if successful
            preview_content = []
            if modification_result.success:
                try:
                    preview_html = self.preview_generator.generate_modification_preview(
                        modification_result=modification_result
                    )
                    preview_content.append(
                        TextContent(
                            type="text",
                            text=f"🎯 **Field Modification Preview**\n\n{preview_html}"
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate preview: {e}")
                    preview_content.append(
                        TextContent(
                            type="text",
                            text="⚠️ Preview generation failed, but PDF modification was successful."
                        )
                    )
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=success_text
                    ),
                    *preview_content
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
    
    async def _batch_analyze_forms(self, input_data: BatchAnalysisInput) -> CallToolResult:
        """Analyze multiple PDF forms in batch."""
        try:
            # Validate all files exist
            pdf_paths = []
            missing_files = []
            
            for filename in input_data.pdf_filenames:
                pdf_path = Path(filename)
                if pdf_path.exists():
                    pdf_paths.append(pdf_path)
                else:
                    missing_files.append(filename)
            
            if missing_files:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ Missing PDF files: {', '.join(missing_files)}"
                        )
                    ]
                )
            
            # Analyze all forms
            logger.info(f"Batch analyzing {len(pdf_paths)} forms")
            batch_analysis = await self.field_analyzer.batch_analyze_forms(
                pdf_paths=pdf_paths,
                consistency_check=input_data.consistency_check
            )
            
            # Generate batch summary
            summary_text = self._format_batch_summary(batch_analysis)
            
            # Generate batch review HTML
            if input_data.generate_summary:
                batch_html = self.preview_generator.generate_batch_review_html(
                    batch_analysis=batch_analysis
                )
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=summary_text
                        ),
                        TextContent(
                            type="text",
                            text=f"📋 **Batch Analysis Report**\n\n{batch_html}"
                        ),
                        TextContent(
                            type="text",
                            text=f"📥 **Download Batch Results**\n\n```json\n{json.dumps(batch_analysis.model_dump(), indent=2)}\n```"
                        )
                    ]
                )
            else:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=summary_text
                        )
                    ]
                )
        
        except Exception as e:
            logger.exception("Error in batch analysis")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"❌ Failed to perform batch analysis: {str(e)}"
                    )
                ]
            )
    
    def _format_analysis_summary(self, analysis: FormAnalysis) -> str:
        """Format form analysis summary."""
        confidence_high = analysis.confidence_summary.get("high", 0)
        confidence_medium = analysis.confidence_summary.get("medium", 0)
        confidence_low = analysis.confidence_summary.get("low", 0)
        
        # Get top field types
        top_types = sorted(
            analysis.field_type_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        summary = f"""## 🚀 BEM Field Analysis Complete

**Form:** {analysis.filename}
**Total Fields:** {analysis.total_fields}
**Form Type:** {analysis.form_type or 'Auto-detected'}

### 📊 Confidence Distribution
- **High Confidence:** {confidence_high} fields ({confidence_high/analysis.total_fields*100:.1f}%)
- **Medium Confidence:** {confidence_medium} fields ({confidence_medium/analysis.total_fields*100:.1f}%)
- **Low Confidence:** {confidence_low} fields ({confidence_low/analysis.total_fields*100:.1f}%)

### 📋 Field Type Distribution
{chr(10).join(f"- **{field_type.value}:** {count} fields" for field_type, count in top_types)}

### 🎯 Quality Metrics
- **Naming Conflicts:** {len(analysis.naming_conflicts)} fields
- **Missing Sections:** {len(analysis.missing_sections)} fields
- **Review Required:** {len(analysis.review_required)} fields

### 📝 Sample BEM Names
{chr(10).join(f"- `{bem.original_name}` → `{bem.bem_name}` ({bem.confidence})" for bem in analysis.bem_mappings[:5])}

---
**Next Steps:**
1. Review the interactive field table below
2. Edit any BEM names that need adjustment
3. Use the `modify_form_fields` tool to apply changes
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
    
    def _format_batch_summary(self, batch_analysis: Any) -> str:
        """Format batch analysis summary."""
        total_confidence = batch_analysis.overall_confidence
        
        summary = f"""## 📊 Batch Analysis Complete

**Forms Analyzed:** {batch_analysis.total_forms}
**Total Fields:** {batch_analysis.total_fields}
**Analysis Time:** {batch_analysis.generated_at}

### 🎯 Overall Confidence
- **High:** {total_confidence.get('high', 0)} fields ({total_confidence.get('high', 0)/batch_analysis.total_fields*100:.1f}%)
- **Medium:** {total_confidence.get('medium', 0)} fields ({total_confidence.get('medium', 0)/batch_analysis.total_fields*100:.1f}%)
- **Low:** {total_confidence.get('low', 0)} fields ({total_confidence.get('low', 0)/batch_analysis.total_fields*100:.1f}%)

### 📋 Form Summary
{chr(10).join(f"- **{form.filename}**: {form.total_fields} fields, {form.form_type or 'Auto-detected'}" for form in batch_analysis.forms[:10])}

### 🔄 Consistency Analysis
- **Common Patterns:** {len(batch_analysis.common_patterns)} patterns identified
- **Naming Consistency:** {len(batch_analysis.naming_consistency)} similarity scores calculated

---
**Review the detailed analysis below for each form.**
"""
        
        return summary
    
    async def run(self) -> None:
        """Run the MCP server."""
        setup_logging(level=logging.INFO)
        logger.info("Starting PDF Enrichment MCP Server...")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="pdf-enrichment",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(),
                ),
            )


async def main() -> None:
    """Main entry point."""
    server = PDFEnrichmentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())

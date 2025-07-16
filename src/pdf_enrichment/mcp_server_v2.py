#!/usr/bin/env python3
"""
MCP Server for PDF Form Field Enrichment - Version 2
Rewritten to fix the ListToolsResult validation errors
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListPromptsResult,
    ListResourcesResult,
    ListToolsResult,
    ServerCapabilities,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from src.pdf_enrichment.field_types import FieldModificationResult
from src.pdf_enrichment.pdf_modifier import PDFModifier
from src.pdf_enrichment.utils import setup_logging


# Configure logging
logger = logging.getLogger(__name__)


class GenerateBEMNamesInput(BaseModel):
    """Input for generate_BEM_names tool."""
    context: Optional[str] = Field(
        None, 
        description="Optional context about the PDF form (e.g., form type, organization)"
    )


class ModifyFormFieldsInput(BaseModel):
    """Input for modify_form_fields tool."""
    field_mappings: Dict[str, str] = Field(
        description="Mapping of original field names to new BEM names (from generate_BEM_names output)"
    )
    output_filename: Optional[str] = Field(
        None,
        description="Output filename (defaults to 'BEM_renamed.pdf')"
    )


class PDFEnrichmentServer:
    """MCP Server for PDF Form Field Enrichment."""
    
    def __init__(self) -> None:
        self.server = Server("pdf-enrichment", version="0.1.0")
        self.pdf_modifier = PDFModifier()
        
        # Register handlers
        self._register_handlers()
        
        # Server state
        self.modification_results: Dict[str, FieldModificationResult] = {}
    
    def _register_handlers(self) -> None:
        """Register all MCP handlers."""
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools."""
            return [
                Tool(
                    name="generate_BEM_names",
                    description="📋 Generate BEM-style field names for PDF forms using Claude Desktop",
                    inputSchema=GenerateBEMNamesInput.model_json_schema(),
                ),
                Tool(
                    name="modify_form_fields",
                    description="🔧 Apply BEM field mappings to uploaded PDF and download modified version to Downloads folder",
                    inputSchema=ModifyFormFieldsInput.model_json_schema(),
                ),
            ]
        
        @self.server.list_prompts()
        async def list_prompts():
            """List available prompts."""
            return []
        
        @self.server.list_resources()
        async def list_resources():
            """List available resources."""
            return []
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]):
            """Handle tool calls."""
            if name == "generate_BEM_names":
                return await self._generate_bem_names(GenerateBEMNamesInput(**arguments))
            elif name == "modify_form_fields":
                return await self._modify_form_fields(ModifyFormFieldsInput(**arguments))
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _generate_bem_names(self, input_data: GenerateBEMNamesInput):
        """Generate BEM-style field names for PDF forms."""
        logger.info("Generating BEM names for uploaded PDF")
        
        # Get optional context
        context_info = input_data.context or "the uploaded PDF form"
        
        # Return the BEM naming prompt for Claude Desktop to execute
        bem_prompt = f"""# BEM Field Name Generation for Uploaded PDF

You are a PDF form field analyzer. For the PDF form uploaded in this conversation, generate consistent BEM-style API names for AcroFields based on financial services conventions.

{f"**Context**: {context_info}" if input_data.context else ""}

## 🚨 CRITICAL REQUIREMENT: COMPLETE FIELD MAPPING
**YOU MUST include EVERY SINGLE form field found in the PDF. No exceptions.**

### Field Discovery Process (MANDATORY):
1. **SCAN THE ENTIRE PDF** - Don't skip any pages or sections
2. **INVENTORY ALL FIELDS** - Including text fields, checkboxes, radio buttons, dropdowns, signatures, date fields, etc.
3. **COUNT TOTAL FIELDS** - Keep track of how many fields you find
4. **VERIFY COMPLETENESS** - Ensure your final mapping matches the total count

### Completeness Requirements:
- ❌ **DO NOT omit any fields**, even if they seem redundant or similar
- ❌ **DO NOT take shortcuts** or provide "sample" mappings
- ❌ **DO NOT skip fields** because they're unclear or complex
- ✅ **INCLUDE EVERY FIELD** found in the PDF, no matter how many there are
- ✅ **If a field is unclear**, include it with a note rather than skipping it
- ✅ **Include empty or optional fields** that may not have visible labels

## BEM Format Rules:
- **Structure**: `block_element__modifier`
- **Separators**: `_` between block and element, `__` before modifiers
- **Groups**: Use `--group` suffix for radio button containers/parents
- **Radio Buttons**: Individual radio buttons use the group name + specific value
- **Case**: Use lowercase only, hyphenate multi-word phrases

## 🔘 ENHANCED Radio Group Detection (Critical):
Radio buttons are often the most complex and easily missed fields. Follow these enhanced detection steps:

### 1. **Multi-Pass Radio Detection**:
   - **First Pass**: Look for obvious radio button symbols (○, ●, ◯, etc.)
   - **Second Pass**: Look for groups of similar fields with related labels
   - **Third Pass**: Check for fields with names like "option1", "choice_a", "selection_1"
   - **Fourth Pass**: Look for fields grouped visually in columns or rows

### 2. **Radio Group Identification Patterns**:
   - **Same Base Name**: `dividend_option_1`, `dividend_option_2`, `dividend_option_3`
   - **Similar Labels**: "Cash", "Reduce Premium", "Accumulate Interest" (for dividend options)
   - **Visual Grouping**: Radio buttons aligned vertically or horizontally
   - **Logical Groups**: "Payment Method", "Frequency", "Gender", "Yes/No" options

### 3. **Radio Group Naming Strategy**:
   - **Group Container**: `section_category--group` (e.g., `dividend-option--group`)
   - **Individual Radios**: `section_category__descriptive-name` (e.g., `dividend-option__cash`, `dividend-option__reduce-premium`)
   - **BOTH are required**: Create the group container AND all individual radio options
   - **CRITICAL**: Radio buttons should NOT use `__checkbox` suffix - they use `__option-name` format

### 4. **Common Radio Group Categories in Financial Forms**:
   - **Payment Methods**: ACH, Check, Wire, Credit Card
   - **Frequencies**: Monthly, Quarterly, Semi-Annual, Annual
   - **Dividend Options**: Cash, Reduce Premium, Accumulate Interest, Paid-Up Additional
   - **Gender**: Male, Female, Other
   - **Yes/No Questions**: Joint Owner, Beneficiary Same as Owner, etc.
   - **Withdrawal Options**: Systematic, Lump Sum, Partial

## Analysis Steps:
1. **COMPREHENSIVE SCAN** - Go through every page, every section, every visible field
2. **FIELD INVENTORY** - Create a complete list of all fields found
3. **SECTION IDENTIFICATION** - Group fields by form sections (owner-info, address, payment, etc.)
4. **ENHANCED RADIO DETECTION** - Use the multi-pass detection method above
5. **RADIO GROUP MAPPING** - Create group containers and individual options
6. **BEM NAME GENERATION** - Use field labels and context for element names
7. **MODIFIER ASSIGNMENT** - Add modifiers where needed (__primary, __alternate, etc.)
8. **CONSISTENCY CHECK** - Maintain consistent naming across similar fields
9. **COMPLETENESS VERIFICATION** - Ensure every discovered field is mapped

## MANDATORY Verification Steps:
Before providing your final output, you MUST:
1. **Count your mapped fields** and verify it matches your discovered field count
2. **Include field count summary**: "Field Discovery: Found X total fields, Mapped Y fields"
3. **If counts don't match**: Review the PDF again and include ALL missing fields
4. **Double-check for missed radio groups**: Look specifically for option groups you might have missed
5. **CRITICAL RADIO GROUP VALIDATION**:
   - For each radio group in `radio_groups`, ensure the group container (ending in `--group`) exists in `bem_mappings`
   - For each radio group, ensure all individual options are in `bem_mappings` using `__option-name` format
   - Verify radio buttons are marked as "radio" field type (NOT "checkbox")
   - Ensure consistency between `radio_groups` and `bem_mappings` sections

## Output Format:
Please provide:

### 1. Field Discovery Summary
**Field Discovery: Found [X] total fields, Mapped [Y] fields**
*(These numbers MUST match)*

### 2. Review Table (ALL FIELDS)
| Original Field Name | Proposed BEM Name | Field Type | Section | Confidence |
|---------------------|-------------------|------------|---------|------------|
| ... | ... | ... | ... | ... |
*(Include EVERY field found - no exceptions)*

### 3. 📥 DOWNLOADABLE ARTIFACT: Complete BEM Mapping JSON
**IMPORTANT**: Create this JSON as a downloadable artifact (not just a code block) so the user can save it directly to their computer.

The JSON should contain:
```json
{{
  "filename": "[PDF filename from upload]",
  "analysis_timestamp": "[current timestamp]",
  "total_fields_found": [X],
  "total_fields_mapped": [Y],
  "form_context": "{context_info}",
  "bem_mappings": {{
    "original_field_name_1": "bem_field_name_1",
    "original_field_name_2": "bem_field_name_2",
    "dividend_option_group": "dividend-option--group",
    "dividend_option_cash": "dividend-option__cash",
    "dividend_option_reduce_premium": "dividend-option__reduce-premium"
  }},
  "radio_groups": {{
    "group_name--group": ["option1", "option2", "option3"]
  }},
  "field_details": [
    {{
      "original_name": "original_field_name",
      "bem_name": "bem_field_name",
      "field_type": "text|checkbox|radio|radio_group|dropdown|signature|date",
      "section": "section_name",
      "confidence": "high|medium|low",
      "reasoning": "explanation of naming choice"
    }}
  ]
}}
```

## Enhanced BEM Examples:
- **Text Fields**: `owner-information_first-name`, `contact-details_email-address`
- **Checkboxes**: `beneficiary_withdrawal-frequency__monthly`
- **Radio Groups**: `dividend-option--group` (container) + `dividend-option__cash`, `dividend-option__reduce-premium`
- **Payment Methods**: `payment-method--group` + `payment-method__ach`, `payment-method__check`, `payment-method__wire`
- **Signatures**: `signatures_owner-signature`, `signatures_owner-date`
- **Date Fields**: `effective-date_policy-change`, `signatures_owner-date`

## 🖊️ SIGNATURE FIELD REQUIREMENTS:
Signature fields are critical in financial forms and must be properly identified:

### Signature Field Patterns:
- **Owner Signature**: `signatures_owner-signature` (field_type: "signature")
- **Owner Date**: `signatures_owner-date` (field_type: "date")  
- **Joint Owner Signature**: `signatures_joint-owner-signature` (field_type: "signature")
- **Joint Owner Date**: `signatures_joint-owner-date` (field_type: "date")
- **Witness Signature**: `signatures_witness-signature` (field_type: "signature")
- **Witness Date**: `signatures_witness-date` (field_type: "date")

### Signature Field Validation:
- ✅ All signature fields must use `signatures_` block
- ✅ Signature fields must have field_type: "signature"
- ✅ Date fields accompanying signatures must have field_type: "date"
- ✅ Use descriptive element names: `_owner-signature`, `_joint-owner-signature`

## 🚨 CRITICAL RADIO GROUP MAPPING REQUIREMENTS:

### ✅ CORRECT Radio Group Mapping:
For a dividend option radio group, you MUST include:
```json
// In bem_mappings:
"dividend_option_group": "dividend-option--group",           // Group container
"dividend_option_cash": "dividend-option__cash",             // Individual option
"dividend_option_reduce_premium": "dividend-option__reduce-premium", // Individual option
"dividend_option_accumulate": "dividend-option__accumulate-interest", // Individual option

// In radio_groups:
"dividend-option--group": ["cash", "reduce_premium", "accumulate_interest"]

// In field_details:
{{
  "original_name": "dividend_option_cash",
  "bem_name": "dividend-option__cash",
  "field_type": "radio",  // NOT "checkbox"
  "section": "dividend_options",
  "confidence": "high"
}}
```

### ❌ WRONG Radio Group Mapping (DO NOT DO THIS):
```json
// WRONG - using __checkbox suffix:
"dividend_option_cash": "dividend-option_cash__checkbox",

// WRONG - missing group container:
// (missing "dividend_option_group": "dividend-option--group")

// WRONG - field_type marked as checkbox:
"field_type": "checkbox"  // Should be "radio" for radio buttons
```

### VALIDATION CHECKLIST:
Before submitting, verify:
- [ ] Every radio group has a group container field ending in `--group`
- [ ] Every radio button uses `__option-name` format (NOT `__checkbox`)
- [ ] Radio buttons are marked as "radio" field type (NOT "checkbox")
- [ ] `radio_groups` section matches `bem_mappings` section
- [ ] Both group containers AND individual options are in `bem_mappings`
- [ ] Signature fields are properly identified with field_type: "signature"
- [ ] Date fields (especially signature dates) have field_type: "date"
- [ ] Checkbox fields are marked as "checkbox" field type (NOT "radio")
- [ ] Text fields are marked as "text" field type
- [ ] Dropdown fields are marked as "dropdown" field type

### FIELD TYPE EXAMPLES:
- **Text**: `"field_type": "text"` (name, address, policy number fields)
- **Checkbox**: `"field_type": "checkbox"` (independent yes/no options)
- **Radio**: `"field_type": "radio"` (individual radio button options)
- **Radio Group**: `"field_type": "radio_group"` (radio group containers)
- **Dropdown**: `"field_type": "dropdown"` (select lists)
- **Signature**: `"field_type": "signature"` (signature fields)
- **Date**: `"field_type": "date"` (date fields, especially signature dates)

**🎯 FINAL INSTRUCTION: Analyze the uploaded PDF form and generate BEM field names for EVERY SINGLE FIELD. Pay special attention to radio button groups - use the enhanced detection method to ensure you find ALL radio groups and their individual options. Create a downloadable JSON artifact with the complete mapping.**"""
        
        return [
            TextContent(
                type="text",
                text=bem_prompt
            )
        ]
    
    async def _modify_form_fields(self, input_data: ModifyFormFieldsInput):
        """Modify PDF form fields using BEM mappings."""
        logger.info("Modifying uploaded PDF with BEM field mappings")
        
        try:
            # Find uploaded PDF file in common locations
            pdf_file_path = await self._find_uploaded_pdf()
            
            if not pdf_file_path:
                return [
                    TextContent(
                        type="text",
                        text=self._get_file_not_found_instructions(input_data)
                    )
                ]
            
            # Set up output path in Downloads folder
            downloads_folder = Path.home() / "Downloads"
            downloads_folder.mkdir(exist_ok=True)
            
            # Generate output filename
            if input_data.output_filename:
                output_filename = input_data.output_filename
            else:
                original_stem = pdf_file_path.stem
                output_filename = f"{original_stem}_BEM_renamed.pdf"
            
            output_path = downloads_folder / output_filename
            
            # Perform PDF modification
            logger.info(f"Modifying PDF: {pdf_file_path} -> {output_path}")
            modification_result = await self.pdf_modifier.modify_fields(
                pdf_path=pdf_file_path,
                field_mappings=input_data.field_mappings,
                output_path=output_path,
                preserve_original=True
            )
            
            if modification_result.success:
                success_message = f"""# ✅ PDF Field Modification Complete!

**Original PDF:** {pdf_file_path.name}
**Modified PDF:** {output_path}
**Fields Modified:** {len(modification_result.modifications)}

## 🎯 What Was Done:
- Applied **{len(input_data.field_mappings)}** BEM field name mappings
- Preserved all field types and functionality
- Maintained form structure and visual layout
- Saved modified PDF to your Downloads folder

## 📥 Download Location:
The modified PDF is ready at: **{output_path}**

## 📝 Field Changes Summary:
{chr(10).join(f"- `{mod['old']}` → `{mod['new']}` ({mod['type']})" for mod in modification_result.modifications[:10])}
{f"...and {len(modification_result.modifications) - 10} more field mappings applied" if len(modification_result.modifications) > 10 else ""}

## 🎉 Success!
Your PDF now has properly named BEM fields and is ready for use in your applications!"""
            
            else:
                success_message = f"""# ❌ PDF Field Modification Failed

**Error:** {modification_result.errors[0] if modification_result.errors else 'Unknown error'}

## 🔧 What to Try:
1. Ensure the PDF is not password protected
2. Check that the PDF contains form fields
3. Verify the field mappings are correct

## 📋 Your Field Mappings:
{chr(10).join(f"- `{original}` → `{bem_name}`" for original, bem_name in list(input_data.field_mappings.items())[:5])}
{f"... and {len(input_data.field_mappings) - 5} more mappings" if len(input_data.field_mappings) > 5 else ""}"""
            
            return [
                TextContent(
                    type="text",
                    text=success_message
                )
            ]
            
        except Exception as e:
            logger.exception("Error in PDF modification")
            return [
                TextContent(
                    type="text",
                    text=f"""# ❌ PDF Modification Error

**Error:** {str(e)}

## 🔧 Troubleshooting:
1. Ensure you have uploaded a PDF file to this conversation
2. Check that the PDF is not corrupted or password-protected
3. Verify the field mappings are in the correct format

## 📋 Your Field Mappings ({len(input_data.field_mappings)} total):
{chr(10).join(f"- `{original}` → `{bem_name}`" for original, bem_name in list(input_data.field_mappings.items())[:5])}
{f"... and {len(input_data.field_mappings) - 5} more mappings" if len(input_data.field_mappings) > 5 else ""}"""
                )
            ]
    
    async def _find_uploaded_pdf(self) -> Optional[Path]:
        """Find uploaded PDF file in common locations."""
        from datetime import datetime, timedelta
        
        # Common locations where Claude Desktop might store uploaded files
        search_locations = [
            Path.home() / "Downloads",
            Path.home() / "Desktop", 
            Path("/tmp"),
            Path("/var/tmp"),
        ]
        
        # Add macOS temp folders if they exist
        var_folders = Path("/var/folders")
        if var_folders.exists():
            for temp_folder in var_folders.glob("*/T/TemporaryItems/NSIRD_*"):
                if temp_folder.is_dir():
                    search_locations.append(temp_folder)
        
        pdf_files = []
        
        for location in search_locations:
            if location.exists() and location.is_dir():
                try:
                    # Find PDF files modified in the last hour (recently uploaded)
                    one_hour_ago = datetime.now() - timedelta(hours=1)
                    
                    for pdf_file in location.glob("*.pdf"):
                        if pdf_file.is_file():
                            mod_time = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                            if mod_time > one_hour_ago:
                                pdf_files.append((pdf_file, mod_time))
                except (PermissionError, OSError):
                    # Skip locations we can't read
                    continue
        
        if pdf_files:
            # Return the most recently modified PDF file
            pdf_files.sort(key=lambda x: x[1], reverse=True)
            return pdf_files[0][0]
        
        return None
    
    def _get_file_not_found_instructions(self, input_data: ModifyFormFieldsInput) -> str:
        """Get instructions when PDF file is not found."""
        return f"""# 📋 PDF File Not Found

I have your **{len(input_data.field_mappings)}** BEM field mappings ready to apply, but I couldn't locate the uploaded PDF file automatically.

## 🔧 How to Apply Your Mappings:

### Option 1: Save PDF to Downloads/Desktop
1. **Save the uploaded PDF** from this conversation to your Downloads or Desktop folder
2. **Run this tool again** - it will automatically find and process the PDF

### Option 2: Use the Field Mappings JSON
```json
{{
  "field_mappings": {{
    {chr(10).join(f'    "{original}": "{bem_name}"{"," if i < len(input_data.field_mappings) - 1 else ""}' for i, (original, bem_name) in enumerate(input_data.field_mappings.items()))}
  }},
  "total_mappings": {len(input_data.field_mappings)},
  "output_filename": "{input_data.output_filename or 'BEM_renamed.pdf'}"
}}
```

## 📝 Your BEM Field Mappings:
{chr(10).join(f"- `{original}` → `{bem_name}`" for original, bem_name in list(input_data.field_mappings.items())[:10])}
{f"... and {len(input_data.field_mappings) - 10} more mappings" if len(input_data.field_mappings) > 10 else ""}

## 🎯 What These Mappings Will Do:
- Rename all form fields to use BEM naming conventions
- Preserve field types and functionality (text, radio, checkbox, etc.)
- Maintain form structure and visual layout
- Create a downloadable PDF with properly named fields

**Try saving the PDF to your Downloads folder and running this tool again!**"""
    
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
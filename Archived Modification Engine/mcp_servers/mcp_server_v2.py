#!/usr/bin/env python3
"""
MCP Server for PDF Form Field Enrichment - Version 2
Rewritten to fix the ListToolsResult validation errors
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    ServerCapabilities,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field
from src.pdf_enrichment.field_analyzer import FieldAnalyzer
from src.pdf_enrichment.field_types import FieldModificationResult, FormField
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


class ValidateBEMJSONInput(BaseModel):
    """Input for validate_bem_json tool."""
    json_content: str = Field(
        description="JSON content to validate (BEM mapping JSON from generate_BEM_names)"
    )


class PDFEnrichmentServer:
    """MCP Server for PDF Form Field Enrichment."""

    def __init__(self) -> None:
        self.server = Server("pdf-enrichment", version="0.1.0")
        self.pdf_modifier = PDFModifier()
        self.field_analyzer = FieldAnalyzer()

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
                    name="validate_bem_json",
                    description="✅ Validate and clean BEM mapping JSON before applying to PDF",
                    inputSchema=ValidateBEMJSONInput.model_json_schema(),
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
            elif name == "validate_bem_json":
                return await self._validate_bem_json(ValidateBEMJSONInput(**arguments))
            elif name == "modify_form_fields":
                return await self._modify_form_fields(ModifyFormFieldsInput(**arguments))
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _generate_bem_names(self, input_data: GenerateBEMNamesInput):
        """Generate BEM-style field names for PDF forms."""
        logger.info("Generating BEM names for uploaded PDF")

        # Get optional context
        context_info = input_data.context or "the uploaded PDF form"

        # Find uploaded PDF file
        pdf_file_path = await self._find_uploaded_pdf()

        if not pdf_file_path:
            # Enhanced diagnostic information
            diagnostic_info = await self._get_pdf_search_diagnostic()
            
            return [
                TextContent(
                    type="text",
                    text=f"""# 📋 PDF File Not Found for BEM Generation

I couldn't locate the uploaded PDF file automatically. Here's what I found:

{diagnostic_info}

## 🔧 Solutions:
1. **Save the PDF** from this conversation to your Downloads or Desktop folder
2. **Run this tool again** - it will automatically find and analyze the PDF
3. **Check the locations above** - the PDF might be in a different location

## 🚀 What This Tool Does:
- Automatically extracts ALL form fields from your PDF
- Generates BEM-style field names based on actual field names
- Creates a comprehensive mapping with field types and locations
- Provides a downloadable JSON with complete field mappings

**Try saving the PDF to your Downloads folder and running this tool again!**"""
                )
            ]

        # Extract actual form fields from PDF
        try:
            logger.info(f"Extracting fields from: {pdf_file_path}")
            form_fields = await self.field_analyzer.extract_form_fields(pdf_file_path)
            logger.info(f"Extracted {len(form_fields)} fields from PDF")
        except Exception as e:
            logger.error(f"Error extracting fields: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"""# ❌ Error Extracting PDF Fields

Failed to extract form fields from: {pdf_file_path}

**Error:** {e!s}

## 🔧 Troubleshooting:
1. Ensure the PDF file is a valid form with fillable fields
2. Check that the PDF is not password protected
3. Try re-uploading the PDF to this conversation
4. Verify the PDF is not corrupted

Please upload a valid PDF form and try again."""
                )
            ]

        # Generate field summary for the prompt
        field_summary = self._generate_field_summary(form_fields, pdf_file_path)

        # Detect radio groups
        radio_groups = self.field_analyzer.detect_radio_groups(form_fields)
        radio_summary = self._generate_radio_group_summary(radio_groups)

        # Return the BEM naming prompt for Claude Desktop to execute
        bem_prompt = f"""# BEM Field Name Generation for Uploaded PDF: {pdf_file_path.name}

✅ **AUTOMATED FIELD EXTRACTION COMPLETE!**

I have automatically extracted **{len(form_fields)}** form fields from your PDF. Below is the complete field inventory with actual field names, types, and positions.

You are a PDF form field analyzer. For the PDF form uploaded in this conversation, generate consistent BEM-style API names for AcroFields based on financial services conventions.

## 📋 EXTRACTED FIELD INVENTORY ({len(form_fields)} total fields):
{field_summary}

{radio_summary}

{f"**Context**: {context_info}" if input_data.context else ""}

## 🚨 CRITICAL REQUIREMENT: COMPLETE FIELD MAPPING
**YOU MUST include EVERY SINGLE form field found in the PDF. No exceptions.**

### ✅ FIELD EXTRACTION COMPLETE:
The automated field extraction has already identified **{len(form_fields)}** form fields from your PDF. All field names, types, and positions are listed above.

### Your Task:
1. **USE THE EXTRACTED FIELD LIST** - All {len(form_fields)} fields are already identified above
2. **GENERATE BEM NAMES** - Create BEM-style names for each extracted field
3. **MAINTAIN FIELD TYPES** - Use the correct field types from the extraction
4. **VERIFY COMPLETENESS** - Ensure your final mapping includes all {len(form_fields)} fields

### Completeness Requirements:
- ✅ **All {len(form_fields)} fields are already discovered** - use the list above
- ✅ **INCLUDE EVERY FIELD** from the extracted list - no exceptions
- ❌ **DO NOT omit any fields** from the extracted list
- ❌ **DO NOT add fields** that weren't in the extracted list
- ✅ **Use the exact field names** from the "Field Name" column above

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
**Field Discovery: Found {len(form_fields)} total fields, Mapped [Y] fields**
*(Y MUST equal {len(form_fields)})*

### 2. Review Table (ALL {len(form_fields)} FIELDS)
| Original Field Name | Proposed BEM Name | Field Type | Section | Confidence |
|---------------------|-------------------|------------|---------|------------|
*(Include ALL {len(form_fields)} fields from the extraction list above)*

### 3. 📥 DOWNLOADABLE ARTIFACT: Complete BEM Mapping JSON
**IMPORTANT**: Create this JSON as a downloadable artifact (not just a code block) so the user can save it directly to their computer.

The JSON should contain:
```json
{{
  "filename": "{pdf_file_path.name}",
  "analysis_timestamp": "[current timestamp]",
  "total_fields_found": {len(form_fields)},
  "total_fields_mapped": {len(form_fields)},
  "form_context": "{context_info}",
  "bem_mappings": {{
    // Map each field from the extracted list above
    // Use EXACT field names from the "Field Name" column
    // Example for extracted fields:
    {self._generate_example_bem_mappings(form_fields[:3] if len(form_fields) > 3 else form_fields)}
  }},
  "radio_groups": {{
    // Only include if radio button fields were found
    "group_name--group": ["option1", "option2", "option3"]
  }},
  "field_details": [
    // Include ALL {len(form_fields)} fields from the extraction
    {{
      "original_name": "exact_field_name_from_extraction",
      "bem_name": "your_generated_bem_name",
      "field_type": "use_type_from_extraction",
      "section": "inferred_section_name",
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

    async def _validate_bem_json(self, input_data: ValidateBEMJSONInput):
        """Validate and clean BEM mapping JSON."""
        logger.info("Validating BEM mapping JSON")

        try:
            # Validate and clean the JSON
            validated_data = self._validate_bem_mapping_json(input_data.json_content)

            # Create clean JSON output
            clean_json = self._create_validated_json_output(validated_data)

            # Count mappings
            mapping_count = len(validated_data.get('bem_mappings', {}))

            # Check for radio groups
            radio_groups = validated_data.get('radio_groups', {})
            radio_group_count = len(radio_groups)

            success_message = f"""# ✅ BEM Mapping JSON Validation Successful!

## 📊 Validation Summary:
- **Total Mappings**: {mapping_count}
- **Radio Groups**: {radio_group_count}
- **Filename**: {validated_data.get('filename', 'Unknown')}
- **Fields Found**: {validated_data.get('total_fields_found', 'Unknown')}

## 🔧 Validation Checks Passed:
- ✅ Valid JSON format
- ✅ Required fields present
- ✅ Mapping structure correct
- ✅ All mapping values are strings
- ✅ No extra data or corruption
- ✅ Timestamp added if missing

## 📥 Clean JSON Output:
```json
{clean_json}
```

## 🎯 Next Steps:
Your BEM mapping JSON is valid and ready to use! You can now:
1. Copy the clean JSON above
2. Use the `modify_form_fields` tool with the field mappings
3. The mappings will be applied to your PDF automatically

**The JSON has been cleaned and validated - ready for PDF modification!**"""

            return [
                TextContent(
                    type="text",
                    text=success_message
                )
            ]

        except Exception as e:
            error_message = f"""# ❌ BEM Mapping JSON Validation Failed

**Error**: {e!s}

## 🔧 Common Issues and Solutions:

### JSON Format Errors:
- Ensure all strings are properly quoted
- Remove any trailing commas
- Check for missing or extra braces
- Remove any comments (// text)

### Missing Required Fields:
- `filename`: PDF filename
- `total_fields_found`: Number of fields
- `bem_mappings`: Dictionary of field mappings

### Invalid Mappings:
- All mapping keys and values must be strings
- Use exact field names from PDF
- Follow BEM naming conventions

## 💡 Tips:
1. Copy the JSON from the generate_BEM_names output
2. Ensure it's properly formatted as valid JSON
3. Check that all required fields are present
4. Remove any extra text after the closing brace

Please fix the JSON format and try validation again."""

            return [
                TextContent(
                    type="text",
                    text=error_message
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

**Error:** {e!s}

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
                    # Find PDF files modified in the last 24 hours (recently uploaded)
                    one_day_ago = datetime.now() - timedelta(hours=24)

                    for pdf_file in location.glob("*.pdf"):
                        if pdf_file.is_file():
                            mod_time = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                            if mod_time > one_day_ago:
                                pdf_files.append((pdf_file, mod_time))
                except (PermissionError, OSError):
                    # Skip locations we can't read
                    continue

        if pdf_files:
            # Return the most recently modified PDF file
            pdf_files.sort(key=lambda x: x[1], reverse=True)
            return pdf_files[0][0]

        return None

    async def _get_pdf_search_diagnostic(self) -> str:
        """Get diagnostic information about PDF file search."""
        from datetime import datetime, timedelta
        
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

        diagnostic_lines = ["## 🔍 PDF Search Diagnostic:"]
        
        one_day_ago = datetime.now() - timedelta(hours=24)
        total_pdfs_found = 0
        
        for location in search_locations:
            if location.exists() and location.is_dir():
                try:
                    pdf_files = []
                    for pdf_file in location.glob("*.pdf"):
                        if pdf_file.is_file():
                            mod_time = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                            if mod_time > one_day_ago:
                                pdf_files.append((pdf_file, mod_time))
                    
                    if pdf_files:
                        total_pdfs_found += len(pdf_files)
                        diagnostic_lines.append(f"- **{location}**: {len(pdf_files)} recent PDF(s) found")
                        for pdf_file, mod_time in pdf_files[:3]:  # Show first 3
                            diagnostic_lines.append(f"  - {pdf_file.name} (modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
                        if len(pdf_files) > 3:
                            diagnostic_lines.append(f"  - ... and {len(pdf_files) - 3} more")
                    else:
                        diagnostic_lines.append(f"- **{location}**: No recent PDFs found")
                except (PermissionError, OSError):
                    diagnostic_lines.append(f"- **{location}**: Permission denied")
            else:
                diagnostic_lines.append(f"- **{location}**: Directory doesn't exist")
        
        diagnostic_lines.append(f"\n**Total recent PDFs found**: {total_pdfs_found}")
        diagnostic_lines.append("**Search criteria**: Modified within last 24 hours")
        
        return "\n".join(diagnostic_lines)

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

    def _generate_field_summary(self, form_fields: List[FormField], pdf_file_path: Path) -> str:
        """Generate a summary of extracted form fields."""
        if not form_fields:
            return "No form fields found in PDF."

        # Group fields by type for better organization
        field_types = {}
        for field in form_fields:
            field_type = field.field_type.value
            if field_type not in field_types:
                field_types[field_type] = []
            field_types[field_type].append(field)

        summary_lines = []

        # Add field type summary
        summary_lines.append("### Field Type Summary:")
        for field_type, fields in field_types.items():
            summary_lines.append(f"- **{field_type}**: {len(fields)} fields")

        summary_lines.append("")
        summary_lines.append("### Complete Field List:")
        summary_lines.append("| Field Name | Type | Label | Page | Position |")
        summary_lines.append("|------------|------|-------|------|----------|")

        for field in form_fields:
            summary_lines.append(
                f"| `{field.name}` | {field.field_type.value} | {field.label} | {field.position.page + 1} | ({field.position.x:.0f}, {field.position.y:.0f}) |"
            )

        return "\n".join(summary_lines)

    def _generate_radio_group_summary(self, radio_groups: Dict[str, List[str]]) -> str:
        """Generate a summary of detected radio groups."""
        if not radio_groups:
            return "### 🔘 Radio Group Detection:\n**No radio groups detected** (no radio button fields found or no logical groupings identified)"

        summary_lines = [
            f"### 🔘 RADIO GROUP DETECTION ({len(radio_groups)} groups detected):",
            "**✅ AUTOMATIC GROUPING COMPLETE!**",
            "",
            "The enhanced multi-strategy radio detection has identified the following radio button groups:"
        ]

        for group_name, field_names in radio_groups.items():
            summary_lines.append("")
            summary_lines.append(f"**Group: {group_name}**")
            summary_lines.append(f"- **Fields**: {', '.join(f'`{name}`' for name in field_names)}")
            summary_lines.append(f"- **Count**: {len(field_names)} radio buttons")
            summary_lines.append(f"- **BEM Mapping Required**: `{group_name}--group` (container) + individual option mappings")

        summary_lines.extend([
            "",
            "### 🎯 Radio Group Mapping Instructions:",
            "For each group above, you MUST create:",
            "1. **Group Container**: `section_category--group` (e.g., `payment-method--group`)",
            "2. **Individual Options**: `section_category__option-name` (e.g., `payment-method__ach`, `payment-method__check`)",
            "",
            "**CRITICAL**: Use the EXACT field names listed above in your mappings."
        ])

        return "\n".join(summary_lines)

    def _generate_example_bem_mappings(self, fields: List[FormField]) -> str:
        """Generate example BEM mappings for the first few fields."""
        if not fields:
            return '"field_name_1": "section_field-name"'

        examples = []
        for field in fields:
            # Generate a simple BEM name based on the field name
            bem_name = self._suggest_bem_name(field.name)
            examples.append(f'"{field.name}": "{bem_name}"')

        return ",\n    ".join(examples)

    def _suggest_bem_name(self, field_name: str) -> str:
        """Suggest a BEM name for a field (simple example)."""
        # This is a basic example - Claude will generate the actual names
        clean_name = field_name.lower().replace("_", "-")
        if "name" in clean_name:
            return f"owner-information_{clean_name}"
        elif "address" in clean_name:
            return f"contact-details_{clean_name}"
        elif "signature" in clean_name:
            return f"signatures_{clean_name}"
        else:
            return f"form-data_{clean_name}"

    def _validate_bem_mapping_json(self, json_string: str) -> Dict[str, Any]:
        """Validate and clean BEM mapping JSON."""
        try:
            # First attempt to parse the JSON
            data = json.loads(json_string)

            # Validate required fields
            required_fields = ['filename', 'total_fields_found', 'bem_mappings']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Validate bem_mappings structure
            if not isinstance(data['bem_mappings'], dict):
                raise ValueError("bem_mappings must be a dictionary")

            # Ensure all mapping values are strings
            for key, value in data['bem_mappings'].items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError(f"Invalid mapping: {key} -> {value}")

            # Add timestamp if missing
            if 'analysis_timestamp' not in data:
                data['analysis_timestamp'] = datetime.now().isoformat()

            return data

        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            cleaned_json = self._clean_json_string(json_string)
            try:
                data = json.loads(cleaned_json)
                return self._validate_bem_mapping_json(cleaned_json)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format: {e!s}")

    def _clean_json_string(self, json_string: str) -> str:
        """Clean common JSON formatting issues."""
        # Remove any extra data after the closing brace
        json_string = json_string.strip()

        # Find the last closing brace
        brace_count = 0
        last_brace_pos = -1

        for i, char in enumerate(json_string):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    last_brace_pos = i
                    break

        if last_brace_pos != -1:
            # Trim everything after the last closing brace
            json_string = json_string[:last_brace_pos + 1]

        # Remove any trailing commas
        json_string = json_string.replace(',}', '}').replace(',]', ']')

        # Remove any comments (not valid JSON)
        lines = json_string.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove lines that start with // (comments)
            if not line.strip().startswith('//'):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _create_validated_json_output(self, data: Dict[str, Any]) -> str:
        """Create clean, validated JSON output."""
        try:
            # Validate the data structure
            validated_data = self._validate_bem_mapping_json(json.dumps(data))

            # Create clean JSON string
            json_string = json.dumps(validated_data, indent=2, ensure_ascii=False)

            # Validate by parsing back
            json.loads(json_string)  # Will raise if invalid

            return json_string

        except Exception as e:
            raise ValueError(f"Failed to create valid JSON: {e!s}")

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

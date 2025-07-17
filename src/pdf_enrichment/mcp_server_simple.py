#!/usr/bin/env python3
"""
Simplified MCP Server for PDF Form Field Enrichment
Relies on Claude Desktop's built-in PDF analysis capabilities
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
    ServerCapabilities,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from src.pdf_enrichment.utils import setup_logging


# Configure logging
logger = logging.getLogger(__name__)


class GenerateBEMNamesInput(BaseModel):
    """Input for generate_BEM_names tool."""
    context: Optional[str] = Field(
        None, 
        description="Optional context about the PDF form (e.g., form type, organization)"
    )


class ValidateBEMJSONInput(BaseModel):
    """Input for validate_bem_json tool."""
    json_content: str = Field(
        description="JSON content to validate (BEM mapping JSON from generate_BEM_names)"
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


class GenerateUnifiedFieldsInput(BaseModel):
    """Input for generate_unified_fields tool."""
    bem_mappings: Dict[str, str] = Field(
        description="BEM mappings with API names as keys and BEM-style AcroField names as values"
    )


class SimplePDFEnrichmentServer:
    """Simplified MCP Server for PDF Form Field Enrichment."""
    
    def __init__(self) -> None:
        self.server = Server("pdf-enrichment", version="0.1.0")
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register all MCP handlers."""
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools."""
            return [
                Tool(
                    name="generate_BEM_names",
                    description="📋 Generate BEM-style field names for PDF forms using Claude Desktop's built-in analysis",
                    inputSchema=GenerateBEMNamesInput.model_json_schema(),
                ),
                Tool(
                    name="validate_bem_json",
                    description="✅ Validate and clean BEM mapping JSON before applying to PDF",
                    inputSchema=ValidateBEMJSONInput.model_json_schema(),
                ),
                Tool(
                    name="modify_form_fields",
                    description="🔧 Apply BEM field mappings to uploaded PDF (requires actual PDF file)",
                    inputSchema=ModifyFormFieldsInput.model_json_schema(),
                ),
                Tool(
                    name="generate_unified_fields",
                    description="🧩 Generate enriched Unified Field definitions from BEM mappings for application integration",
                    inputSchema=GenerateUnifiedFieldsInput.model_json_schema(),
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
            elif name == "generate_unified_fields":
                return await self._generate_unified_fields(GenerateUnifiedFieldsInput(**arguments))
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
**YOU MUST analyze the uploaded PDF and include EVERY SINGLE form field found. No exceptions.**

### Your Task:
1. **ANALYZE THE UPLOADED PDF** - Extract all form fields from the PDF
2. **IDENTIFY FIELD TYPES** - Determine if each field is text, checkbox, radio, dropdown, signature, etc.
3. **DETECT RADIO GROUPS** - Look for radio button groups using multiple strategies:
   - Name pattern matching (e.g., option_1, option_2)
   - Visual positioning (fields close together)
   - Label analysis (related options like Male/Female, Yes/No)
4. **GENERATE BEM NAMES** - Create BEM-style names for each field
5. **VERIFY COMPLETENESS** - Ensure your final mapping includes ALL fields found

### Field Discovery Process:
1. **SCAN THE ENTIRE PDF** - Don't skip any pages or sections
2. **INVENTORY ALL FIELDS** - Including text, checkbox, radio, dropdown, signature fields
3. **COUNT TOTAL FIELDS** - Keep track of how many fields you find
4. **VERIFY COMPLETENESS** - Ensure your final mapping matches the total count

## BEM Format Rules:
- **Structure**: `block_element__modifier`
- **Separators**: `_` between block and element, `__` before modifiers
- **Groups**: Use `--group` suffix for radio button containers/parents
- **Radio Buttons**: Individual radio buttons use the group name + specific value
- **Case**: Use lowercase only, hyphenate multi-word phrases

## 🔘 Enhanced Radio Group Detection:
Radio buttons are often the most complex fields. Look for:

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
**Field Discovery: Found X total fields, Mapped Y fields**
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
  "total_fields_found": X,
  "total_fields_mapped": Y,
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
    
    async def _validate_bem_json(self, input_data: ValidateBEMJSONInput):
        """Validate and clean BEM mapping JSON."""
        logger.info("Validating BEM mapping JSON")
        
        # Simple validation prompt for Claude Desktop
        validation_prompt = f"""# BEM Mapping JSON Validation

Please validate and clean the following BEM mapping JSON:

```json
{input_data.json_content}
```

## Validation Requirements:
1. **JSON Format**: Must be valid JSON
2. **Required Fields**: Must have `filename`, `total_fields_found`, `bem_mappings`
3. **BEM Names**: All BEM names must follow proper conventions
4. **Radio Groups**: Radio group mappings must be consistent
5. **Field Types**: Field types must be valid (text, checkbox, radio, etc.)

## Your Task:
1. **Parse and validate** the JSON
2. **Fix any formatting issues**
3. **Clean up any corruption**
4. **Verify BEM naming conventions**
5. **Return the cleaned JSON**

If there are errors, explain them and provide the corrected version."""
        
        return [
            TextContent(
                type="text",
                text=validation_prompt
            )
        ]
    
    async def _modify_form_fields(self, input_data: ModifyFormFieldsInput):
        """Modify PDF form fields using BEM mappings."""
        logger.info("Modifying uploaded PDF with BEM field mappings")
        
        # Simple instructions for manual PDF modification
        modification_prompt = f"""# PDF Field Modification Instructions

You have **{len(input_data.field_mappings)}** BEM field mappings to apply to your PDF.

## 📋 Your Field Mappings:
{self._format_field_mappings(input_data.field_mappings)}

## 🔧 Manual Application Process:
1. **Use a PDF editor** (like Adobe Acrobat Pro, PDFtk, or similar tool)
2. **Apply the field name mappings** shown above
3. **Preserve all field properties** (type, size, position, etc.)
4. **Test the modified PDF** to ensure functionality

## 💡 Alternative Approach:
If you need automated PDF modification, you'll need to:
1. **Save the PDF locally** to your computer
2. **Use a PDF processing script** with the mappings above
3. **Apply the BEM names programmatically**

**Note**: This tool provides the mapping instructions. The actual PDF modification requires external tools or scripts."""
        
        return [
            TextContent(
                type="text",
                text=modification_prompt
            )
        ]
    
    def _format_field_mappings(self, mappings: Dict[str, str]) -> str:
        """Format field mappings for display."""
        lines = []
        for i, (original, bem_name) in enumerate(mappings.items(), 1):
            lines.append(f"{i}. `{original}` → `{bem_name}`")
            if i >= 10:  # Limit display to first 10
                lines.append(f"... and {len(mappings) - 10} more mappings")
                break
        return "\n".join(lines)
    
    async def _generate_unified_fields(self, input_data: GenerateUnifiedFieldsInput):
        """Generate enriched Unified Field definitions from BEM mappings."""
        logger.info("Generating unified fields from BEM mappings")
        
        # Create the MCP-compliant prompt for unified fields generation
        unified_fields_prompt = f"""# 🧩 Unified Fields Generation from BEM Mappings

You are operating under **Model Context Protocol (MCP)** to generate enriched Unified Field (UF) definitions from BEM-formatted PDF field mappings.

## 📥 Input Data
You have **{len(input_data.bem_mappings)}** BEM field mappings to process:

```json
{json.dumps(input_data.bem_mappings, indent=2)}
```

## 🎯 Your Task
Generate enriched Unified Field definitions that normalize these PDF form fields for application integration across hundreds of annuity and insurance forms.

## 📤 Required Output Format
Return a JSON array with enriched Unified Field objects. For each input mapping, create:

```json
{{
  "api_name": "snake_case_api_name",
  "name": "Human-readable UI Label",
  "description": "Brief description of what this field captures",
  "type": "text field | radio button | radio group | checkbox | group | slider",
  "label": "Exact UI-facing label text as shown on the form"
}}
```

## 🧠 Processing Rules

### 1. **API Name** (use as-is)
- Keep the key from input mappings exactly as provided
- Should already be in snake_case format

### 2. **Name** (humanize from API name)
- Convert snake_case to readable format with proper capitalization
- Use colons to separate logical groups and fields
- Examples:
  - `owner_first_name` → `"Owner: First Name"`
  - `status_income__spouse_retirement` → `"Household Income: Spouse / Partner's Retirement"`
  - `payment_method__ach` → `"Payment Method: ACH"`

### 3. **Description** (brief but informative)
- Provide context about what the field captures
- Use insurance/annuity domain knowledge
- Examples:
  - `"First name of the policy owner"`
  - `"Retirement income from spouse or partner used to fund this annuity"`
  - `"Electronic bank transfer payment method"`

### 4. **Type** (infer from BEM patterns)
- Use these rules to determine field type:
  - **Radio Group**: Ends with `--group` → `"radio group"`
  - **Radio Button**: Contains `__` with option values → `"radio button"`
  - **Text Field**: Standard fields with `_amount`, `_value`, `_city`, `_name` → `"text field"`
  - **Checkbox**: Boolean-style options, standalone yes/no → `"checkbox"`
  - **Group**: Section containers ending in `--custom` → `"group"`
  - **Slider**: Range or percentage fields → `"slider"`

### 5. **Label** (extract from BEM value)
- Use the BEM-style value from input (clean up formatting)
- Remove BEM syntax but preserve semantic meaning
- Examples:
  - `"owner-information_first-name"` → `"First Name"`
  - `"dividend-option__accumulate-interest"` → `"Accumulate Interest"`

## 🎯 Examples

### Input:
```json
{{
  "owner_first_name": "owner-information_first-name",
  "dividend_option__cash": "dividend-option__cash",
  "payment_method--group": "payment-method--group"
}}
```

### Expected Output:
```json
[
  {{
    "api_name": "owner_first_name",
    "name": "Owner: First Name",
    "description": "First name of the policy owner",
    "type": "text field",
    "label": "First Name"
  }},
  {{
    "api_name": "dividend_option__cash",
    "name": "Dividend Option: Cash",
    "description": "Option to receive dividends as cash payment",
    "type": "radio button",
    "label": "Cash"
  }},
  {{
    "api_name": "payment_method--group",
    "name": "Payment Method",
    "description": "Group of payment method options",
    "type": "radio group",
    "label": "Payment Method"
  }}
]
```

## 📋 Quality Requirements

- **Consistency**: Use consistent formatting and terminology
- **Accuracy**: Don't hallucinate field structure beyond given context
- **Completeness**: Process ALL {len(input_data.bem_mappings)} input mappings
- **Domain Knowledge**: Apply insurance/annuity field conventions
- **JSON Format**: Return valid JSON array only

## 🚀 Generate Results

Please process the {len(input_data.bem_mappings)} BEM mappings above and return the enriched Unified Field definitions as a JSON array. Focus on creating clear, consistent field definitions that will work across multiple insurance and annuity forms."""

        return [
            TextContent(
                type="text",
                text=unified_fields_prompt
            )
        ]
    
    async def run(self) -> None:
        """Run the MCP server."""
        setup_logging(level=logging.INFO)
        logger.info("Starting Simplified PDF Enrichment MCP Server...")
        
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
                        ),
                    ),
                )
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise


async def main() -> None:
    """Main entry point."""
    server = SimplePDFEnrichmentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
"""
Preview Generator for PDF Form Field Analysis

Generates HTML previews and visualizations for BEM field analysis results,
field modification summaries, and batch analysis reports.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .field_types import (
    BatchAnalysis,
    BEMNamingResult,
    FieldModificationResult,
    FieldType,
    FormAnalysis,
)

logger = logging.getLogger(__name__)


class PreviewGenerator:
    """Generates HTML previews and reports for PDF analysis results."""
    
    def __init__(self) -> None:
        self.template_cache: Dict[str, str] = {}
    
    def generate_field_review_html(self, form_analysis: FormAnalysis) -> str:
        """
        Generate interactive HTML table for field review and editing.
        
        Args:
            form_analysis: Complete form analysis results
            
        Returns:
            HTML string with interactive field review table
        """
        try:
            # Build table rows
            table_rows = []
            
            for i, result in enumerate(form_analysis.bem_mappings):
                field_type_icon = self._get_field_type_icon(result.field_type)
                
                # Build editable row
                row = f"""
                <tr class="field-row" data-index="{i}">
                    <td class="field-id">{i + 1}</td>
                    <td class="original-name" title="{result.original_name}">
                        <code>{self._truncate_text(result.original_name, 25)}</code>
                    </td>
                    <td class="bem-name-cell">
                        <input type="text" class="bem-name-input" 
                               value="{result.bem_name}" 
                               data-original="{result.bem_name}"
                               onchange="validateBEMName(this)">
                    </td>
                    <td class="field-type">
                        <span class="type-badge">
                            {field_type_icon} {result.field_type.value}
                        </span>
                    </td>
                    <td class="section">
                        <span class="section-badge">{result.section}</span>
                    </td>
                    <td class="confidence">
                        <span class="confidence-badge confidence-{result.confidence}">
                            {result.confidence.upper()}
                        </span>
                    </td>
                    <td class="actions">
                        <button class="btn-edit" onclick="editField({i})" title="Edit field">
                            ✏️
                        </button>
                        <button class="btn-reset" onclick="resetField({i})" title="Reset to original">
                            🔄
                        </button>
                    </td>
                </tr>
                """
                table_rows.append(row)
            
            # Build complete HTML
            html = f"""
            <div class="field-review-container">
                <div class="review-header">
                    <h3>📋 Field Review & Editing</h3>
                    <p>Review and edit the generated BEM field names. Click on any BEM name to edit it directly.</p>
                    
                    <div class="stats-summary">
                        <div class="stat">
                            <span class="stat-value">{form_analysis.total_fields}</span>
                            <span class="stat-label">Total Fields</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">{form_analysis.confidence_summary.get('high', 0)}</span>
                            <span class="stat-label">High Confidence</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">{len(form_analysis.naming_conflicts)}</span>
                            <span class="stat-label">Conflicts</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">{len(form_analysis.review_required)}</span>
                            <span class="stat-label">Need Review</span>
                        </div>
                    </div>
                </div>
                
                <div class="table-container">
                    <table class="field-review-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Original Name</th>
                                <th>BEM Name (Editable)</th>
                                <th>Type</th>
                                <th>Section</th>
                                <th>Confidence</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(table_rows)}
                        </tbody>
                    </table>
                </div>
                
                <div class="review-actions">
                    <button class="btn-primary" onclick="exportModifications()">
                        📥 Export Field Mappings
                    </button>
                    <button class="btn-secondary" onclick="validateAllFields()">
                        ✅ Validate All Names
                    </button>
                    <button class="btn-secondary" onclick="resetAllFields()">
                        🔄 Reset All Changes
                    </button>
                </div>
                
                <div class="validation-summary" id="validation-summary" style="display: none;">
                    <h4>🔍 Validation Results</h4>
                    <div id="validation-results"></div>
                </div>
            </div>
            
            {self._get_review_styles()}
            {self._get_review_scripts()}
            """
            
            return html
            
        except Exception as e:
            logger.exception("Error generating field review HTML")
            return f"<p>❌ Error generating field review: {str(e)}</p>"
    
    def generate_modification_preview(
        self, modification_result: FieldModificationResult
    ) -> str:
        """Generate HTML preview of field modification results."""
        try:
            if not modification_result.success:
                return self._generate_error_preview(modification_result)
            
            # Build modification table
            modification_rows = []
            
            for i, mod in enumerate(modification_result.modifications):
                status_icon = "✅" if mod.get("success", True) else "❌"
                
                row = f"""
                <tr class="modification-row">
                    <td class="mod-index">{i + 1}</td>
                    <td class="mod-status">{status_icon}</td>
                    <td class="old-name">
                        <code>{self._truncate_text(mod['old'], 30)}</code>
                    </td>
                    <td class="new-name">
                        <code>{self._truncate_text(mod['new'], 30)}</code>
                    </td>
                    <td class="field-type">
                        <span class="type-badge">
                            {self._get_field_type_icon(mod.get('type', 'Unknown'))} 
                            {mod.get('type', 'Unknown')}
                        </span>
                    </td>
                    <td class="page-num">{mod.get('page', 'N/A')}</td>
                </tr>
                """
                modification_rows.append(row)
            
            return f"""
            <div class="modification-preview">
                <h3>✅ Field Modification Complete</h3>
                <div class="modifications-table">
                    <table class="mod-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Status</th>
                                <th>Original Name</th>
                                <th>New BEM Name</th>
                                <th>Type</th>
                                <th>Page</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(modification_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
            """
            
        except Exception as e:
            logger.exception("Error generating modification preview")
            return f"<p>❌ Error generating modification preview: {str(e)}</p>"
    
    def generate_batch_review_html(self, batch_analysis: BatchAnalysis) -> str:
        """Generate HTML review for batch analysis results."""
        try:
            form_cards = []
            
            for form in batch_analysis.forms:
                confidence_high = form.confidence_summary.get("high", 0)
                confidence_total = form.total_fields
                confidence_percent = (confidence_high / confidence_total * 100) if confidence_total > 0 else 0
                
                card = f"""
                <div class="form-card">
                    <h4>{form.filename}</h4>
                    <p>Fields: {form.total_fields}</p>
                    <p>High Confidence: {confidence_percent:.1f}%</p>
                </div>
                """
                form_cards.append(card)
            
            return f"""
            <div class="batch-review">
                <h3>📊 Batch Analysis Report</h3>
                <p>Total Forms: {batch_analysis.total_forms}</p>
                <div class="form-cards">
                    {''.join(form_cards)}
                </div>
            </div>
            """
            
        except Exception as e:
            logger.exception("Error generating batch review HTML")
            return f"<p>❌ Error generating batch review: {str(e)}</p>"
    
    def _generate_error_preview(self, modification_result: FieldModificationResult) -> str:
        """Generate error preview for failed modifications."""
        error_list = "\n".join(f"<li>{error}</li>" for error in modification_result.errors)
        
        return f"""
        <div class="error-preview">
            <h3>❌ Field Modification Failed</h3>
            <ul>{error_list}</ul>
        </div>
        """
    
    def _get_field_type_icon(self, field_type: Any) -> str:
        """Get icon for field type."""
        if isinstance(field_type, FieldType):
            field_type = field_type.value
        
        icons = {
            "TextField": "📝",
            "Checkbox": "☑️",
            "RadioGroup": "🔘",
            "RadioButton": "🔘",
            "Signature": "✍️",
            "Dropdown": "📋",
            "Group": "📁"
        }
        return icons.get(field_type, "📄")
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _get_review_styles(self) -> str:
        """Get CSS styles for field review."""
        return """
        <style>
        .field-review-container {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .stats-summary {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-value {
            display: block;
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .stat-label {
            display: block;
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
        }
        
        .field-review-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        
        .field-review-table th,
        .field-review-table td {
            padding: 12px 8px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        
        .field-review-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        
        .bem-name-input {
            width: 100%;
            padding: 6px 8px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
        }
        
        .type-badge, .section-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        
        .type-badge {
            background: #e9ecef;
            color: #495057;
        }
        
        .section-badge {
            background: #d4edda;
            color: #155724;
        }
        
        .confidence-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .confidence-high {
            background: #d4edda;
            color: #155724;
        }
        
        .confidence-medium {
            background: #fff3cd;
            color: #856404;
        }
        
        .confidence-low {
            background: #f8d7da;
            color: #721c24;
        }
        
        .btn-primary, .btn-secondary {
            padding: 10px 20px;
            margin: 0 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 500;
        }
        
        .btn-primary {
            background: #007bff;
            color: white;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        </style>
        """
    
    def _get_review_scripts(self) -> str:
        """Get JavaScript for field review functionality."""
        return """
        <script>
        function validateBEMName(input) {
            const bemName = input.value;
            const patterns = {
                'block_element': /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*_[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/,
                'block_element__modifier': /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*_[a-z][a-z0-9]*(?:-[a-z0-9]+)*__[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/,
                'radio_group': /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*_[a-z][a-z0-9]*(?:-[a-z0-9]+)*--group$/
            };
            
            const isValid = Object.values(patterns).some(pattern => pattern.test(bemName));
            
            if (isValid) {
                input.style.borderColor = '#28a745';
                input.style.backgroundColor = '#d4edda';
            } else {
                input.style.borderColor = '#dc3545';
                input.style.backgroundColor = '#f8d7da';
            }
        }
        
        function editField(index) {
            const input = document.querySelector(`tr[data-index="${index}"] .bem-name-input`);
            input.focus();
            input.select();
        }
        
        function resetField(index) {
            const input = document.querySelector(`tr[data-index="${index}"] .bem-name-input`);
            const originalValue = input.getAttribute('data-original');
            input.value = originalValue;
            validateBEMName(input);
        }
        
        function exportModifications() {
            const mappings = {};
            const inputs = document.querySelectorAll('.bem-name-input');
            
            inputs.forEach((input, index) => {
                const row = input.closest('tr');
                const originalName = row.querySelector('.original-name code').textContent;
                mappings[originalName] = input.value;
            });
            
            const jsonData = JSON.stringify(mappings, null, 2);
            const blob = new Blob([jsonData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'field_mappings.json';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        function validateAllFields() {
            const inputs = document.querySelectorAll('.bem-name-input');
            inputs.forEach(validateBEMName);
        }
        
        function resetAllFields() {
            const inputs = document.querySelectorAll('.bem-name-input');
            inputs.forEach(input => {
                const originalValue = input.getAttribute('data-original');
                input.value = originalValue;
                validateBEMName(input);
            });
        }
        </script>
        """

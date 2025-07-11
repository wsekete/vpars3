"""
Command Line Interface for PDF Enrichment Platform

Provides CLI commands for PDF form analysis, BEM field naming, and modification.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import click
from pydantic import ValidationError

from ..pdf_enrichment import FieldAnalyzer, PDFModifier, PreviewGenerator
from ..pdf_enrichment.utils import setup_logging, validate_file_path


logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    help="Log file path"
)
def main(verbose: bool, log_file: Optional[Path]) -> None:
    """PDF Enrichment Platform CLI - Transform PDF forms into structured APIs."""
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level, log_file=log_file)


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file for analysis results"
)
@click.option(
    "--analysis-mode",
    type=click.Choice(["quick", "comprehensive"]),
    default="comprehensive",
    help="Analysis mode"
)
@click.option(
    "--custom-sections",
    multiple=True,
    help="Custom section names to prioritize"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "html", "text"]),
    default="json",
    help="Output format"
)
def analyze(
    pdf_path: Path,
    output: Optional[Path],
    analysis_mode: str,
    custom_sections: tuple,
    output_format: str,
) -> None:
    """Analyze PDF form and generate BEM field names."""
    async def run_analysis():
        try:
            click.echo(f"Analyzing PDF: {pdf_path}")
            
            # Initialize analyzer
            analyzer = FieldAnalyzer()
            
            # Run analysis
            analysis = await analyzer.analyze_form(
                pdf_path=pdf_path,
                analysis_mode=analysis_mode,
                custom_sections=list(custom_sections) if custom_sections else None
            )
            
            # Generate output
            if output_format == "json":
                output_data = analysis.model_dump(mode="json")
                output_text = json.dumps(output_data, indent=2)
            elif output_format == "html":
                preview_gen = PreviewGenerator()
                output_text = preview_gen.generate_field_review_html(analysis)
            else:  # text
                output_text = _format_analysis_as_text(analysis)
            
            # Write to file or stdout
            if output:
                output.write_text(output_text, encoding="utf-8")
                click.echo(f"Analysis saved to: {output}")
            else:
                click.echo(output_text)
            
            # Summary
            click.echo(f"\n✅ Analysis complete:")
            click.echo(f"   - Total fields: {analysis.total_fields}")
            click.echo(f"   - High confidence: {analysis.confidence_summary.get('high', 0)}")
            click.echo(f"   - Naming conflicts: {len(analysis.naming_conflicts)}")
            click.echo(f"   - Review required: {len(analysis.review_required)}")
            
        except Exception as e:
            logger.exception("Error during analysis")
            click.echo(f"❌ Analysis failed: {str(e)}", err=True)
            raise click.Abort()
    
    asyncio.run(run_analysis())


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.argument("mappings_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output PDF file path"
)
@click.option(
    "--preserve-original/--no-preserve-original",
    default=True,
    help="Whether to preserve the original file"
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Whether to validate BEM names"
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Whether to create a backup"
)
def modify(
    pdf_path: Path,
    mappings_file: Path,
    output: Optional[Path],
    preserve_original: bool,
    validate: bool,
    backup: bool,
) -> None:
    """Modify PDF form fields using BEM name mappings."""
    async def run_modification():
        try:
            click.echo(f"Modifying PDF: {pdf_path}")
            
            # Load field mappings
            try:
                mappings_data = json.loads(mappings_file.read_text())
            except json.JSONDecodeError as e:
                click.echo(f"❌ Invalid JSON in mappings file: {e}", err=True)
                raise click.Abort()
            
            # Initialize modifier
            modifier = PDFModifier()
            
            # Set output path
            if output is None:
                output = pdf_path.with_stem(f"{pdf_path.stem}_bem_renamed")
            
            # Run modification
            result = await modifier.modify_fields(
                pdf_path=pdf_path,
                field_mappings=mappings_data,
                output_path=output,
                preserve_original=preserve_original,
                validate_mappings=validate,
                create_backup=backup,
            )
            
            # Report results
            if result.success:
                click.echo(f"✅ Modification complete: {output}")
                click.echo(f"   - Fields modified: {len(result.modifications)}")
                click.echo(f"   - Fields before: {result.field_count_before}")
                click.echo(f"   - Fields after: {result.field_count_after}")
                
                if result.warnings:
                    click.echo(f"   - Warnings: {len(result.warnings)}")
                    for warning in result.warnings:
                        click.echo(f"     ⚠️  {warning}")
            else:
                click.echo(f"❌ Modification failed:")
                for error in result.errors:
                    click.echo(f"   - {error}")
                raise click.Abort()
            
        except Exception as e:
            logger.exception("Error during modification")
            click.echo(f"❌ Modification failed: {str(e)}", err=True)
            raise click.Abort()
    
    asyncio.run(run_modification())


@main.command()
@click.argument("pdf_paths", nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option(
    "--output-dir", "-d",
    type=click.Path(path_type=Path),
    help="Output directory for results"
)
@click.option(
    "--consistency-check/--no-consistency-check",
    default=True,
    help="Whether to check naming consistency across forms"
)
@click.option(
    "--generate-summary/--no-generate-summary",
    default=True,
    help="Whether to generate a summary report"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "html"]),
    default="json",
    help="Output format"
)
def batch_analyze(
    pdf_paths: tuple,
    output_dir: Optional[Path],
    consistency_check: bool,
    generate_summary: bool,
    output_format: str,
) -> None:
    """Analyze multiple PDF forms in batch."""
    async def run_batch_analysis():
        try:
            click.echo(f"Batch analyzing {len(pdf_paths)} PDFs...")
            
            # Initialize analyzer
            analyzer = FieldAnalyzer()
            
            # Run batch analysis
            batch_analysis = await analyzer.batch_analyze_forms(
                pdf_paths=list(pdf_paths),
                consistency_check=consistency_check
            )
            
            # Set up output directory
            if output_dir is None:
                output_dir = Path.cwd() / "batch_analysis_results"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate outputs
            if output_format == "json":
                output_data = batch_analysis.model_dump(mode="json")
                output_file = output_dir / "batch_analysis.json"
                output_file.write_text(json.dumps(output_data, indent=2))
                click.echo(f"Results saved to: {output_file}")
            
            if output_format == "html" or generate_summary:
                preview_gen = PreviewGenerator()
                html_output = preview_gen.generate_batch_review_html(batch_analysis)
                html_file = output_dir / "batch_analysis.html"
                html_file.write_text(html_output)
                click.echo(f"HTML report saved to: {html_file}")
            
            # Summary
            click.echo(f"\n✅ Batch analysis complete:")
            click.echo(f"   - Forms processed: {batch_analysis.total_forms}")
            click.echo(f"   - Total fields: {batch_analysis.total_fields}")
            click.echo(f"   - Overall confidence:")
            for level, count in batch_analysis.overall_confidence.items():
                percentage = (count / batch_analysis.total_fields * 100) if batch_analysis.total_fields > 0 else 0
                click.echo(f"     - {level.capitalize()}: {count} ({percentage:.1f}%)")
            
        except Exception as e:
            logger.exception("Error during batch analysis")
            click.echo(f"❌ Batch analysis failed: {str(e)}", err=True)
            raise click.Abort()
    
    asyncio.run(run_batch_analysis())


@main.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind the MCP server to"
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to bind the MCP server to"
)
@click.option(
    "--stdio/--no-stdio",
    default=True,
    help="Whether to use stdio transport (default for MCP)"
)
def serve(host: str, port: int, stdio: bool) -> None:
    """Start the MCP server for PDF enrichment."""
    try:
        if stdio:
            # Use stdio transport (standard for MCP)
            from ..pdf_enrichment.mcp_server import main as mcp_main
            click.echo("Starting MCP server with stdio transport...")
            asyncio.run(mcp_main())
        else:
            # Use HTTP transport (for development/testing)
            import uvicorn
            click.echo(f"Starting HTTP server on {host}:{port}...")
            uvicorn.run(
                "pdf_enrichment.web.app:app",
                host=host,
                port=port,
                reload=True,
                log_level="info"
            )
            
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")
    except Exception as e:
        logger.exception("Error starting server")
        click.echo(f"❌ Server failed to start: {str(e)}", err=True)
        raise click.Abort()


@main.command()
@click.argument("bem_name", type=str)
def validate_bem(bem_name: str) -> None:
    """Validate a BEM field name format."""
    from ..pdf_enrichment.utils import validate_bem_name_format
    
    is_valid, message = validate_bem_name_format(bem_name)
    
    if is_valid:
        click.echo(f"✅ Valid BEM name: {bem_name}")
        click.echo(f"   {message}")
    else:
        click.echo(f"❌ Invalid BEM name: {bem_name}")
        click.echo(f"   {message}")
        raise click.Abort()


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
def inspect(pdf_path: Path) -> None:
    """Inspect PDF form fields without analysis."""
    try:
        from PyPDFForm import PdfWrapper
        
        click.echo(f"Inspecting PDF: {pdf_path}")
        
        # Load PDF
        pdf = PdfWrapper(str(pdf_path))
        
        # Display basic info
        click.echo(f"\n📄 PDF Information:")
        click.echo(f"   - Total fields: {len(pdf.widgets)}")
        
        # Display field details
        if pdf.widgets:
            click.echo(f"\n📋 Field Details:")
            for i, (field_name, widget) in enumerate(pdf.widgets.items(), 1):
                widget_type = type(widget).__name__
                click.echo(f"   {i:2d}. {field_name} ({widget_type})")
        else:
            click.echo("   No form fields found")
        
        # Display schema
        try:
            schema = pdf.schema
            click.echo(f"\n🔧 JSON Schema:")
            click.echo(json.dumps(schema, indent=2))
        except Exception as e:
            click.echo(f"   ⚠️  Could not generate schema: {e}")
        
    except Exception as e:
        logger.exception("Error inspecting PDF")
        click.echo(f"❌ Inspection failed: {str(e)}", err=True)
        raise click.Abort()


def _format_analysis_as_text(analysis) -> str:
    """Format analysis results as readable text."""
    lines = []
    
    lines.append(f"PDF Form Analysis: {analysis.filename}")
    lines.append("=" * 50)
    lines.append(f"Form Type: {analysis.form_type or 'Auto-detected'}")
    lines.append(f"Total Fields: {analysis.total_fields}")
    lines.append("")
    
    # Confidence summary
    lines.append("Confidence Distribution:")
    for level, count in analysis.confidence_summary.items():
        percentage = (count / analysis.total_fields * 100) if analysis.total_fields > 0 else 0
        lines.append(f"  {level.capitalize()}: {count} ({percentage:.1f}%)")
    lines.append("")
    
    # Field type distribution
    lines.append("Field Type Distribution:")
    for field_type, count in analysis.field_type_distribution.items():
        lines.append(f"  {field_type.value}: {count}")
    lines.append("")
    
    # BEM mappings
    lines.append("BEM Field Mappings:")
    lines.append("-" * 30)
    for i, mapping in enumerate(analysis.bem_mappings, 1):
        lines.append(f"{i:2d}. {mapping.original_name} → {mapping.bem_name}")
        lines.append(f"    Type: {mapping.field_type.value}")
        lines.append(f"    Section: {mapping.section}")
        lines.append(f"    Confidence: {mapping.confidence}")
        if mapping.reasoning:
            lines.append(f"    Reasoning: {mapping.reasoning}")
        lines.append("")
    
    # Issues
    if analysis.naming_conflicts:
        lines.append("⚠️  Naming Conflicts:")
        for conflict in analysis.naming_conflicts:
            lines.append(f"  - {conflict}")
        lines.append("")
    
    if analysis.review_required:
        lines.append("🔍 Fields Requiring Review:")
        for field in analysis.review_required:
            lines.append(f"  - {field}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()

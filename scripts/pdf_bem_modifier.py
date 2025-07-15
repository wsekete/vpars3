#!/usr/bin/env python3
"""
PDF BEM Modifier - Standalone Tool

Takes a PDF file and BEM field mappings JSON to rename form fields while preserving
all properties. Saves the modified PDF with __parsed.pdf suffix.
"""

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pdf_enrichment.pdf_modifier import PDFModifier
from src.pdf_enrichment.utils import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


class PDFBEMModifier:
    """Standalone PDF BEM field modifier."""
    
    def __init__(self):
        self.pdf_modifier = PDFModifier()
    
    def load_json_mappings(self, json_path: Path) -> Dict[str, str]:
        """Load BEM field mappings from JSON file."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract bem_mappings from the JSON structure
            if 'bem_mappings' in data:
                mappings = data['bem_mappings']
                logger.info(f"Loaded {len(mappings)} field mappings from {json_path}")
                return mappings
            else:
                # Assume the entire JSON is the mappings
                logger.info(f"Loaded {len(data)} field mappings from {json_path}")
                return data
                
        except FileNotFoundError:
            logger.error(f"JSON file not found: {json_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading JSON mappings: {e}")
            raise
    
    def validate_pdf_file(self, pdf_path: Path) -> bool:
        """Validate that the PDF file exists and is readable."""
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return False
        
        if not pdf_path.suffix.lower() == '.pdf':
            logger.error(f"File is not a PDF: {pdf_path}")
            return False
        
        try:
            with open(pdf_path, 'rb') as f:
                # Try to read first few bytes to check if it's a valid PDF
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    logger.error(f"File does not appear to be a valid PDF: {pdf_path}")
                    return False
        except Exception as e:
            logger.error(f"Error reading PDF file {pdf_path}: {e}")
            return False
        
        return True
    
    def generate_output_path(self, pdf_path: Path, output_dir: Path = None) -> Path:
        """Generate output path with __parsed.pdf suffix."""
        if output_dir:
            return output_dir / f"{pdf_path.stem}__parsed.pdf"
        else:
            return pdf_path.parent / f"{pdf_path.stem}__parsed.pdf"
    
    async def modify_pdf(
        self, 
        pdf_path: Path, 
        json_path: Path, 
        output_dir: Path = None, 
        dry_run: bool = False
    ) -> bool:
        """Modify PDF with BEM field mappings."""
        try:
            # Validate inputs
            if not self.validate_pdf_file(pdf_path):
                return False
            
            # Load field mappings
            logger.info(f"Loading field mappings from {json_path}")
            field_mappings = self.load_json_mappings(json_path)
            
            if not field_mappings:
                logger.error("No field mappings found in JSON file")
                return False
            
            # Generate output path
            output_path = self.generate_output_path(pdf_path, output_dir)
            
            if dry_run:
                logger.info("=== DRY RUN MODE ===")
                logger.info(f"Would modify: {pdf_path}")
                logger.info(f"Would create: {output_path}")
                logger.info(f"Field mappings to apply: {len(field_mappings)}")
                
                # Show first few mappings
                for i, (original, bem_name) in enumerate(field_mappings.items()):
                    if i < 5:
                        logger.info(f"  {original} → {bem_name}")
                    elif i == 5:
                        logger.info(f"  ... and {len(field_mappings) - 5} more mappings")
                        break
                
                logger.info("=== DRY RUN COMPLETE ===")
                return True
            
            # Perform the modification
            logger.info(f"Modifying PDF: {pdf_path}")
            logger.info(f"Applying {len(field_mappings)} field mappings")
            
            modification_result = await self.pdf_modifier.modify_fields(
                pdf_path=pdf_path,
                field_mappings=field_mappings,
                output_path=output_path,
                preserve_original=True,
                validate_mappings=True,
                create_backup=False
            )
            
            if modification_result.success:
                logger.info("✅ PDF modification successful!")
                logger.info(f"📄 Modified PDF saved: {output_path}")
                logger.info(f"📊 Fields modified: {len(modification_result.modifications)}")
                logger.info(f"📈 Success rate: {len(modification_result.modifications) / len(field_mappings) * 100:.1f}%")
                
                if modification_result.warnings:
                    logger.warning("⚠️ Warnings:")
                    for warning in modification_result.warnings:
                        logger.warning(f"  - {warning}")
                
                return True
            else:
                logger.error("❌ PDF modification failed!")
                logger.error("Errors:")
                for error in modification_result.errors:
                    logger.error(f"  - {error}")
                return False
                
        except Exception as e:
            logger.exception(f"Error modifying PDF: {e}")
            return False
    
    def print_usage_examples(self):
        """Print usage examples."""
        print("\n🚀 PDF BEM Modifier - Usage Examples:")
        print("\n1. Basic usage:")
        print("   python scripts/pdf_bem_modifier.py --pdf form.pdf --json mappings.json")
        
        print("\n2. With custom output directory:")
        print("   python scripts/pdf_bem_modifier.py --pdf form.pdf --json mappings.json --output ~/Documents/")
        
        print("\n3. Dry run (preview changes):")
        print("   python scripts/pdf_bem_modifier.py --pdf form.pdf --json mappings.json --dry-run")
        
        print("\n4. With verbose logging:")
        print("   python scripts/pdf_bem_modifier.py --pdf form.pdf --json mappings.json --verbose")
        
        print("\n📋 JSON Format Expected:")
        print("""   {
     "source_filename": "form.pdf",
     "total_fields": 67,
     "bem_mappings": {
       "firstName": "owner-information_first-name",
       "lastName": "owner-information_last-name"
     }
   }""")
        
        print("\n💡 Output: Creates form__parsed.pdf in the same directory as the input PDF")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Modify PDF form fields using BEM naming conventions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pdf form.pdf --json mappings.json
  %(prog)s --pdf ~/Desktop/form.pdf --json mappings.json --output ~/Documents/
  %(prog)s --pdf form.pdf --json mappings.json --dry-run
        """
    )
    
    parser.add_argument(
        '--pdf',
        type=Path,
        help='Path to the PDF file to modify'
    )
    
    parser.add_argument(
        '--json',
        type=Path,
        help='Path to the JSON file containing BEM field mappings'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Output directory (default: same as input PDF)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying the PDF'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--examples',
        action='store_true',
        help='Show usage examples and exit'
    )
    
    args = parser.parse_args()
    
    # Show examples if requested
    if args.examples:
        modifier = PDFBEMModifier()
        modifier.print_usage_examples()
        return 0
    
    # Validate required arguments
    if not args.pdf:
        parser.error("--pdf is required")
    if not args.json:
        parser.error("--json is required")
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Create modifier instance
    modifier = PDFBEMModifier()
    
    # Validate arguments
    if not args.pdf.exists():
        logger.error(f"PDF file not found: {args.pdf}")
        return 1
    
    if not args.json.exists():
        logger.error(f"JSON file not found: {args.json}")
        return 1
    
    if args.output and not args.output.exists():
        logger.error(f"Output directory not found: {args.output}")
        return 1
    
    # Run the modification
    try:
        import asyncio
        success = asyncio.run(modifier.modify_pdf(
            pdf_path=args.pdf,
            json_path=args.json,
            output_dir=args.output,
            dry_run=args.dry_run
        ))
        
        if success:
            if not args.dry_run:
                output_path = modifier.generate_output_path(args.pdf, args.output)
                print(f"\n✅ Success! Modified PDF saved as: {output_path}")
            return 0
        else:
            print(f"\n❌ Failed to modify PDF. Check logs for details.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
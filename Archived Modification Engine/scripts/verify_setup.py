#!/usr/bin/env python3
"""
Setup verification script for PDF Enrichment Platform.

This script verifies that all components are properly installed and configured.
"""

import sys
import subprocess
from pathlib import Path
import importlib


def check_python_version():
    """Check Python version compatibility."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version >= (3, 9):
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (requires 3.9+)")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        "mcp",
        "PyPDFForm", 
        "pydantic",
        "fastapi",
        "click",
        "jinja2",
        "pillow",
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (missing)")
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages


def check_project_structure():
    """Check if project structure is correct."""
    print("\n📁 Checking project structure...")
    
    required_paths = [
        "src/pdf_enrichment/__init__.py",
        "src/pdf_enrichment/field_analyzer.py",
        "src/pdf_enrichment/bem_naming.py",
        "src/pdf_enrichment/pdf_modifier.py",
        "src/pdf_enrichment/mcp_server.py",
        "src/cli/main.py",
        "tests/conftest.py",
        "pyproject.toml",
        "requirements.txt",
    ]
    
    missing_files = []
    project_root = Path(__file__).parent
    
    for path_str in required_paths:
        path = project_root / path_str
        if path.exists():
            print(f"   ✅ {path_str}")
        else:
            print(f"   ❌ {path_str} (missing)")
            missing_files.append(path_str)
    
    return len(missing_files) == 0, missing_files


def check_cli_functionality():
    """Check if CLI commands work."""
    print("\n🔧 Checking CLI functionality...")
    
    try:
        # Test help command
        result = subprocess.run(
            [sys.executable, "-m", "src.cli.main", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("   ✅ CLI help command works")
            return True
        else:
            print(f"   ❌ CLI help failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ CLI test failed: {e}")
        return False


def check_bem_naming():
    """Check BEM naming engine functionality."""
    print("\n🏷️  Checking BEM naming engine...")
    
    try:
        from src.pdf_enrichment.bem_naming import BEMNamingEngine
        from src.pdf_enrichment.field_types import FormField, FieldType, FieldPosition
        
        engine = BEMNamingEngine()
        
        # Test field creation
        field = FormField(
            id=1,
            type=FieldType.TEXT_FIELD,
            form_id=1,
            section_id=1,
            parent_id=None,
            order=1.0,
            label="First Name",
            api_name="firstName",
            custom=False,
            uuid="field_1",
            position=FieldPosition(x=100, y=200, width=150, height=25, page=0),
            unified_field_id=1,
        )
        
        # Test BEM name generation
        bem_name = engine.generate_bem_name(
            field=field,
            section="owner-information",
            context={"existing_names": []}
        )
        
        if bem_name and "_" in bem_name:
            print(f"   ✅ BEM generation works: {bem_name}")
            
            # Test validation
            is_valid = engine.validate_bem_name(bem_name)
            if is_valid:
                print(f"   ✅ BEM validation works")
                return True
            else:
                print(f"   ❌ BEM validation failed for: {bem_name}")
                return False
        else:
            print(f"   ❌ BEM generation failed: {bem_name}")
            return False
            
    except Exception as e:
        print(f"   ❌ BEM naming test failed: {e}")
        return False


def check_mcp_server():
    """Check if MCP server can be imported."""
    print("\n🔌 Checking MCP server...")
    
    try:
        from src.pdf_enrichment.mcp_server import PDFEnrichmentServer
        
        server = PDFEnrichmentServer()
        print("   ✅ MCP server can be instantiated")
        
        # Check if server has required methods
        required_methods = ["run", "_generate_bem_names", "_modify_form_fields"]
        for method in required_methods:
            if hasattr(server, method):
                print(f"   ✅ Method {method} exists")
            else:
                print(f"   ❌ Method {method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ MCP server test failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("🚀 PDF Enrichment Platform - Setup Verification")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", lambda: check_dependencies()[0]),
        ("Project Structure", lambda: check_project_structure()[0]),
        ("CLI Functionality", check_cli_functionality),
        ("BEM Naming Engine", check_bem_naming),
        ("MCP Server", check_mcp_server),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ {check_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Configure Claude Desktop (see claude_desktop_config.json)")
        print("2. Upload a PDF to Claude Desktop")
        print("3. Use the generate_bem_field_names tool")
        print("4. Review and modify field names")
        print("5. Apply changes with modify_form_fields tool")
        return True
    else:
        print("❌ Some checks failed. Please review the errors above.")
        
        # Suggest installation commands
        deps_passed, missing = check_dependencies()
        if not deps_passed:
            print(f"\nTo install missing dependencies:")
            print(f"   uv sync")
            print(f"   # or")
            print(f"   pip install {' '.join(missing)}")
        
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

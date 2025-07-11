#!/usr/bin/env python3
"""
Test script to verify MCP server functionality.
Run this to debug MCP server issues.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_mcp_server():
    """Test if MCP server can start properly."""
    try:
        print("🔍 Testing MCP server...")
        
        # Test imports
        print("📦 Testing imports...")
        from src.pdf_enrichment.mcp_server import PDFEnrichmentServer
        print("✅ MCP server import successful")
        
        # Test server creation
        print("🚀 Creating server...")
        server = PDFEnrichmentServer()
        print("✅ Server created successfully")
        
        # Test tool registration
        print("🔧 Testing tool registration...")
        print(f"✅ Server has {len(server.server._tools)} tools registered")
        
        print("🎉 All tests passed! MCP server should work with Claude Desktop.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    sys.exit(0 if success else 1)
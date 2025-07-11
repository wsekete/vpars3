#!/usr/bin/env python3
"""
Simple MCP server using the direct approach without decorators
"""

import asyncio
import logging
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    ListToolsResult,
    ServerCapabilities,
    Tool,
)
from pydantic import BaseModel, Field


class TestInput(BaseModel):
    """Test input for debugging."""
    message: str = Field(description="Test message")


async def main() -> None:
    """Main entry point."""
    server = Server("test", version="0.1.0")
    
    # Try different approach - not using decorators
    async def handle_list_tools():
        tools = [
            Tool(
                name="test_tool",
                description="A simple test tool",
                inputSchema=TestInput.model_json_schema(),
            ),
        ]
        return ListToolsResult(tools=tools)
    
    # Manually set the handler
    server._tools_handler = handle_list_tools
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="test",
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
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    import sys
    asyncio.run(main())
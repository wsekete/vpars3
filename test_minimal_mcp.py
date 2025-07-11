#!/usr/bin/env python3
"""
Minimal test MCP server to debug the tools/list issue
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


class TestServer:
    """Minimal MCP server for testing."""
    
    def __init__(self) -> None:
        self.server = Server("test", version="0.1.0")
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="test_tool",
                        description="A simple test tool",
                        inputSchema=TestInput.model_json_schema(),
                    ),
                ]
            )
    
    async def run(self) -> None:
        """Run the MCP server."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
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


async def main() -> None:
    """Main entry point."""
    server = TestServer()
    await server.run()


if __name__ == "__main__":
    import sys
    asyncio.run(main())
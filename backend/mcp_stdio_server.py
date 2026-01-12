#!/usr/bin/env python3
"""
Sherlock MCP Server - Stdio Transport

This is a standalone MCP server that communicates via stdin/stdout.
Use this with MCP clients like Cursor, Claude Desktop, etc.

Usage:
    python mcp_stdio_server.py

Configuration for Cursor (~/.cursor/mcp.json or settings):
{
    "mcpServers": {
        "sherlock": {
            "command": "python",
            "args": ["C:/path/to/sherlock/backend/mcp_stdio_server.py"],
            "env": {
                "PYTHONPATH": "C:/path/to/sherlock/backend"
            }
        }
    }
}
"""

import sys
import json
import asyncio
import os
from pathlib import Path

# Add backend to path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set environment for imports
os.chdir(backend_dir)

from services.mcp_service import MCPService


def log_debug(msg: str):
    """Log debug message to stderr."""
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)


class StdioMCPServer:
    """MCP Server using stdio transport."""

    def __init__(self):
        self.mcp_service = MCPService()
        log_debug("MCP Service initialized")

    async def handle_message(self, message: dict) -> dict | None:
        """Handle a single JSON-RPC message."""
        return await self.mcp_service.handle_message(message)

    def write_response(self, response: dict):
        """Write a JSON-RPC response to stdout."""
        response_str = json.dumps(response)
        # MCP stdio uses newline-delimited JSON
        sys.stdout.write(response_str + "\n")
        sys.stdout.flush()
        log_debug(f"Sent response: {response.get('id', 'notification')}")

    async def process_line(self, line: str):
        """Process a single line of input."""
        line = line.strip()
        if not line:
            return

        log_debug(f"Received: {line[:100]}...")

        try:
            message = json.loads(line)
        except json.JSONDecodeError as e:
            log_debug(f"JSON parse error: {e}")
            self.write_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            })
            return

        try:
            response = await self.handle_message(message)
            if response:
                self.write_response(response)
        except Exception as e:
            log_debug(f"Handler error: {e}")
            self.write_response({
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32603, "message": str(e)}
            })

    async def run_async(self):
        """Run the server with async stdin reading."""
        log_debug("Starting async stdio server")

        # For Windows compatibility, use a thread for stdin reading
        loop = asyncio.get_event_loop()

        while True:
            try:
                # Read line in thread pool to avoid blocking
                line = await loop.run_in_executor(None, sys.stdin.readline)

                if not line:
                    log_debug("EOF received, exiting")
                    break

                await self.process_line(line)

            except Exception as e:
                log_debug(f"Error in main loop: {e}")
                continue

    def run_sync(self):
        """Run the server synchronously (simpler, more compatible)."""
        log_debug("Starting sync stdio server")

        for line in sys.stdin:
            try:
                asyncio.run(self.process_line(line))
            except Exception as e:
                log_debug(f"Error processing line: {e}")
                self.write_response({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                })


def main():
    """Main entry point."""
    log_debug(f"Starting Sherlock MCP Server")
    log_debug(f"Working directory: {os.getcwd()}")
    log_debug(f"Python path: {sys.path[:3]}")

    server = StdioMCPServer()

    try:
        # Use sync mode for better Windows compatibility
        server.run_sync()
    except KeyboardInterrupt:
        log_debug("Interrupted, exiting")
    except Exception as e:
        log_debug(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

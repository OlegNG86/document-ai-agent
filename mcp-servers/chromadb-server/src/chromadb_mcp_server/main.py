"""Main entry point for ChromaDB MCP Server."""

import asyncio
import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional

from chromadb_mcp_server.core.config import ConfigManager, ServerConfig, ToolConfig
from chromadb_mcp_server.core.mcp_server import MCPServer


async def start_sse_server(server_config: ServerConfig, tool_config: ToolConfig) -> None:
    """Start SSE server for MCP over SSE."""
    mcp_server = MCPServer(server_config, tool_config)
    
    try:
        await mcp_server.run_sse(server_config.host, server_config.port)
    except Exception as e:
        logging.error(f"SSE server error: {e}")
        raise


async def start_stdio_server(server_config: ServerConfig, tool_config: ToolConfig) -> None:
    """Start stdio server for traditional MCP."""
    mcp_server = MCPServer(server_config, tool_config)
    
    try:
        await mcp_server.run_stdio()
    except Exception as e:
        logging.error(f"Stdio server error: {e}")
        raise


async def main(mode: str = None, host: str = None, port: int = None, config_path: str = None) -> None:
    """Main entry point."""
    try:
        # Load and validate configuration
        config_manager = ConfigManager(Path(config_path) if config_path else None)
        server_config, tool_config = config_manager.validate_and_load()
        
        # Override with command line arguments
        if mode:
            server_config.mode = mode
        if host:
            server_config.host = host
        if port:
            server_config.port = port
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, server_config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"Starting {server_config.name} v{server_config.version} in {server_config.mode} mode")
        
        if server_config.mode == "sse":
            await start_sse_server(server_config, tool_config)
        else:
            await start_stdio_server(server_config, tool_config)
            
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        raise


def cli_main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="ChromaDB MCP Server")
    parser.add_argument("--mode", choices=["stdio", "sse"], help="Server mode")
    parser.add_argument("--host", help="Host to bind to (SSE mode only)")
    parser.add_argument("--port", type=int, help="Port to bind to (SSE mode only)")
    parser.add_argument("--config", help="Path to configuration file")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.mode, args.host, args.port, args.config))
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
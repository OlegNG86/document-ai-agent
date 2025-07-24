"""Main entry point for ChromaDB MCP Server."""

import asyncio
import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional

from chromadb_mcp_server.core.config import ConfigManager, ServerConfig, ToolConfig


async def start_http_server(server_config: ServerConfig, tool_config: ToolConfig) -> None:
    """Start HTTP server for MCP over HTTP."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import uvicorn
    
    app = FastAPI(
        title=server_config.name,
        version=server_config.version,
        description="ChromaDB MCP Server - HTTP API"
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy",
            "service": server_config.name,
            "version": server_config.version,
            "tools": {
                "chromadb": {
                    "enabled": tool_config.chromadb.enabled,
                    "host": tool_config.chromadb.host,
                    "port": tool_config.chromadb.port
                }
            }
        })
    
    @app.get("/mcp/tools")
    async def list_tools():
        """List available MCP tools."""
        # TODO: Implement in next tasks
        return JSONResponse({
            "tools": [
                {
                    "name": "chromadb_search",
                    "description": "Search documents in ChromaDB",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "collection": {"type": "string"},
                            "n_results": {"type": "integer", "default": 5}
                        },
                        "required": ["query", "collection"]
                    }
                }
            ]
        })
    
    @app.post("/mcp/tools/{tool_name}")
    async def call_tool(tool_name: str, request: dict):
        """Call a specific MCP tool."""
        # TODO: Implement in next tasks
        return JSONResponse({
            "content": [
                {
                    "type": "text",
                    "text": f"Tool {tool_name} called with: {request}"
                }
            ]
        })
    
    print(f"Starting HTTP server on {server_config.host}:{server_config.port}")
    await uvicorn.run(
        app,
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level.lower()
    )


async def start_stdio_server(server_config: ServerConfig, tool_config: ToolConfig) -> None:
    """Start stdio server for traditional MCP."""
    print(f"Starting {server_config.name} v{server_config.version} in stdio mode")
    print("Configuration loaded successfully")
    print("Server structure initialized")
    
    # Log configuration details
    logging.info(f"Server: {server_config.name} v{server_config.version}")
    logging.info(f"Log level: {server_config.log_level}")
    logging.info(f"ChromaDB tool enabled: {tool_config.chromadb.enabled}")
    if tool_config.chromadb.enabled:
        logging.info(f"ChromaDB host: {tool_config.chromadb.host}:{tool_config.chromadb.port}")
        logging.info(f"Embedding provider: {tool_config.chromadb.embedding.provider}")
        logging.info(f"Chunk size: {tool_config.chromadb.chunking.size}")
    
    # TODO: Initialize MCP server in next tasks
    print("Ready for MCP server implementation...")
    
    # Keep server running
    while True:
        await asyncio.sleep(1)


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
        
        if server_config.mode == "http":
            await start_http_server(server_config, tool_config)
        else:
            await start_stdio_server(server_config, tool_config)
            
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        raise


def cli_main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="ChromaDB MCP Server")
    parser.add_argument("--mode", choices=["stdio", "http"], help="Server mode")
    parser.add_argument("--host", help="Host to bind to (HTTP mode only)")
    parser.add_argument("--port", type=int, help="Port to bind to (HTTP mode only)")
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
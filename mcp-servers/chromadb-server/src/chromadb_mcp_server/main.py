"""Main entry point for ChromaDB MCP Server."""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class ServerConfig(BaseModel):
    """Server configuration model."""
    name: str = "chromadb-mcp-server"
    version: str = "0.1.0"
    log_level: str = "INFO"
    mode: str = "stdio"  # stdio or http
    host: str = "localhost"
    port: int = 3000


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from YAML file with environment variable substitution."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        return {"server": {"name": "chromadb-mcp-server", "version": "0.1.0"}}
    
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple environment variable substitution
    import re
    def replace_env_vars(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) else ""
        return os.getenv(var_name, default_value)
    
    content = re.sub(r'\$\{([^}:]+)(?::([^}]*))?\}', replace_env_vars, content)
    
    return yaml.safe_load(content)


async def start_http_server(config: ServerConfig) -> None:
    """Start HTTP server for MCP over HTTP."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import uvicorn
    
    app = FastAPI(
        title=config.name,
        version=config.version,
        description="ChromaDB MCP Server - HTTP API"
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy",
            "service": config.name,
            "version": config.version
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
    
    print(f"Starting HTTP server on {config.host}:{config.port}")
    await uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )


async def start_stdio_server(config: ServerConfig) -> None:
    """Start stdio server for traditional MCP."""
    print(f"Starting {config.name} v{config.version} in stdio mode")
    print("Configuration loaded successfully")
    print("Server structure initialized")
    
    # TODO: Initialize MCP server in next tasks
    print("Ready for MCP server implementation...")
    
    # Keep server running
    while True:
        await asyncio.sleep(1)


async def main(mode: str = None, host: str = None, port: int = None) -> None:
    """Main entry point."""
    config_data = load_config()
    server_config = config_data.get("server", {})
    
    # Override with command line arguments
    if mode:
        server_config["mode"] = mode
    if host:
        server_config["host"] = host
    if port:
        server_config["port"] = port
    
    config = ServerConfig(**server_config)
    
    print(f"Starting {config.name} v{config.version} in {config.mode} mode")
    
    if config.mode == "http":
        await start_http_server(config)
    else:
        await start_stdio_server(config)


def cli_main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="ChromaDB MCP Server")
    parser.add_argument("--mode", choices=["stdio", "http"], help="Server mode")
    parser.add_argument("--host", help="Host to bind to (HTTP mode only)")
    parser.add_argument("--port", type=int, help="Port to bind to (HTTP mode only)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.mode, args.host, args.port))
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
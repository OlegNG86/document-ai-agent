"""Main entry point for ChromaDB MCP Server."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class ServerConfig(BaseModel):
    """Server configuration model."""
    name: str = "chromadb-mcp-server"
    version: str = "0.1.0"
    log_level: str = "INFO"


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        return {"server": {"name": "chromadb-mcp-server", "version": "0.1.0"}}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def main() -> None:
    """Main entry point."""
    config_data = load_config()
    config = ServerConfig(**config_data.get("server", {}))
    
    print(f"Starting {config.name} v{config.version}")
    print("Configuration loaded successfully")
    print("Server structure initialized")
    
    # TODO: Initialize MCP server in next tasks
    print("Ready for MCP server implementation...")


def cli_main() -> None:
    """CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
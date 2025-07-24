#!/usr/bin/env python3
"""Test script to verify configuration loading."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from chromadb_mcp_server.core.config import ConfigManager

def test_config_loading():
    """Test configuration loading."""
    try:
        config_manager = ConfigManager()
        server_config, tool_config = config_manager.validate_and_load()
        
        print("✅ Configuration loaded successfully!")
        print(f"Server: {server_config.name} v{server_config.version}")
        print(f"Mode: {server_config.mode}")
        print(f"Log level: {server_config.log_level}")
        print(f"ChromaDB enabled: {tool_config.chromadb.enabled}")
        print(f"ChromaDB host: {tool_config.chromadb.host}:{tool_config.chromadb.port}")
        print(f"Embedding provider: {tool_config.chromadb.embedding.provider}")
        print(f"Embedding model: {tool_config.chromadb.embedding.model}")
        print(f"Chunk size: {tool_config.chromadb.chunking.size}")
        print(f"Chunk overlap: {tool_config.chromadb.chunking.overlap}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)
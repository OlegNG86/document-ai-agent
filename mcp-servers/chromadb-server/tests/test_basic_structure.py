"""Basic tests for project structure and configuration."""

import pytest
from pathlib import Path

from chromadb_mcp_server.main import load_config, ServerConfig


def test_project_structure():
    """Test that basic project structure exists."""
    base_path = Path(__file__).parent.parent
    
    # Check main directories
    assert (base_path / "src" / "chromadb_mcp_server").exists()
    assert (base_path / "tests").exists()
    assert (base_path / "config").exists()
    
    # Check main modules
    assert (base_path / "src" / "chromadb_mcp_server" / "__init__.py").exists()
    assert (base_path / "src" / "chromadb_mcp_server" / "main.py").exists()
    assert (base_path / "src" / "chromadb_mcp_server" / "__main__.py").exists()
    
    # Check submodules
    assert (base_path / "src" / "chromadb_mcp_server" / "core").exists()
    assert (base_path / "src" / "chromadb_mcp_server" / "tools").exists()
    assert (base_path / "src" / "chromadb_mcp_server" / "services").exists()


def test_config_loading():
    """Test configuration loading."""
    config_data = load_config()
    
    assert "server" in config_data
    server_config = ServerConfig(**config_data["server"])
    
    assert server_config.name == "chromadb-mcp-server"
    assert server_config.version == "0.1.0"
    assert server_config.log_level == "INFO"


def test_config_with_missing_file():
    """Test configuration loading with missing file."""
    config_data = load_config(Path("/nonexistent/config.yaml"))
    
    assert "server" in config_data
    server_config = ServerConfig(**config_data["server"])
    
    assert server_config.name == "chromadb-mcp-server"
    assert server_config.version == "0.1.0"
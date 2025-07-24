"""Unit tests for configuration models and management."""

import os
import tempfile
import pytest
from pathlib import Path
from pydantic import ValidationError
import yaml

from chromadb_mcp_server.core.config import (
    ServerConfig,
    ChromaDBConfig,
    ToolConfig,
    EmbeddingConfig,
    OllamaConfig,
    ChunkingConfig,
    SearchConfig,
    ConfigManager
)


class TestEmbeddingConfig:
    """Test EmbeddingConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = EmbeddingConfig()
        assert config.provider == "ollama"
        assert config.model == "nomic-embed-text:latest"
        assert config.host == "http://localhost:11434"
        assert config.api_key is None
    
    def test_valid_providers(self):
        """Test valid embedding providers."""
        valid_providers = ["openai", "ollama", "huggingface"]
        for provider in valid_providers:
            config = EmbeddingConfig(provider=provider)
            assert config.provider == provider
    
    def test_invalid_provider(self):
        """Test invalid embedding provider raises error."""
        with pytest.raises(ValidationError) as exc_info:
            EmbeddingConfig(provider="invalid_provider")
        assert "Provider must be one of" in str(exc_info.value)
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key"
        )
        assert config.provider == "openai"
        assert config.model == "text-embedding-3-small"
        assert config.api_key == "test-key"


class TestOllamaConfig:
    """Test OllamaConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = OllamaConfig()
        assert config.host == "http://localhost:11434"
        assert config.default_model == "qwen2.5vl:latest"
        assert config.complex_model == "qwen2.5vl:72b"
        assert config.embedding_model == "nomic-embed-text:latest"
        assert config.timeout == 30
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = OllamaConfig(
            host="http://remote:11434",
            default_model="llama2",
            timeout=60
        )
        assert config.host == "http://remote:11434"
        assert config.default_model == "llama2"
        assert config.timeout == 60


class TestChunkingConfig:
    """Test ChunkingConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ChunkingConfig()
        assert config.size == 1000
        assert config.overlap == 200
    
    def test_valid_values(self):
        """Test valid configuration values."""
        config = ChunkingConfig(size=2000, overlap=400)
        assert config.size == 2000
        assert config.overlap == 400
    
    def test_size_validation(self):
        """Test chunk size validation."""
        # Too small
        with pytest.raises(ValidationError):
            ChunkingConfig(size=50)
        
        # Too large
        with pytest.raises(ValidationError):
            ChunkingConfig(size=10000)
    
    def test_overlap_validation(self):
        """Test overlap validation."""
        # Negative overlap
        with pytest.raises(ValidationError):
            ChunkingConfig(overlap=-10)
        
        # Overlap >= size
        with pytest.raises(ValidationError):
            ChunkingConfig(size=1000, overlap=1000)
        
        with pytest.raises(ValidationError):
            ChunkingConfig(size=1000, overlap=1200)


class TestSearchConfig:
    """Test SearchConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = SearchConfig()
        assert config.max_results == 10
        assert config.similarity_threshold == 0.0
    
    def test_valid_values(self):
        """Test valid configuration values."""
        config = SearchConfig(max_results=20, similarity_threshold=0.5)
        assert config.max_results == 20
        assert config.similarity_threshold == 0.5
    
    def test_max_results_validation(self):
        """Test max results validation."""
        # Too small
        with pytest.raises(ValidationError):
            SearchConfig(max_results=0)
        
        # Too large
        with pytest.raises(ValidationError):
            SearchConfig(max_results=200)
    
    def test_similarity_threshold_validation(self):
        """Test similarity threshold validation."""
        # Negative threshold
        with pytest.raises(ValidationError):
            SearchConfig(similarity_threshold=-0.1)
        
        # Threshold > 1
        with pytest.raises(ValidationError):
            SearchConfig(similarity_threshold=1.5)


class TestChromaDBConfig:
    """Test ChromaDBConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ChromaDBConfig()
        assert config.enabled is True
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.collection_prefix == "mcp_"
        assert isinstance(config.embedding, EmbeddingConfig)
        assert isinstance(config.ollama, OllamaConfig)
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.search, SearchConfig)
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ChromaDBConfig(
            enabled=False,
            host="remote-host",
            port=9000,
            collection_prefix="test_"
        )
        assert config.enabled is False
        assert config.host == "remote-host"
        assert config.port == 9000
        assert config.collection_prefix == "test_"
    
    def test_port_validation(self):
        """Test port validation."""
        # Invalid port
        with pytest.raises(ValidationError):
            ChromaDBConfig(port=0)
        
        with pytest.raises(ValidationError):
            ChromaDBConfig(port=70000)
    
    def test_collection_prefix_validation(self):
        """Test collection prefix validation."""
        # Valid prefixes
        valid_prefixes = ["test_", "mcp_", "data123_", "A1_"]
        for prefix in valid_prefixes:
            config = ChromaDBConfig(collection_prefix=prefix)
            assert config.collection_prefix == prefix
        
        # Invalid prefixes
        invalid_prefixes = ["test-", "mcp.", "data@", "test space"]
        for prefix in invalid_prefixes:
            with pytest.raises(ValidationError):
                ChromaDBConfig(collection_prefix=prefix)


class TestServerConfig:
    """Test ServerConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ServerConfig()
        assert config.name == "chromadb-mcp-server"
        assert config.version == "0.1.0"
        assert config.log_level == "INFO"
        assert config.mode == "stdio"
        assert config.host == "localhost"
        assert config.port == 3000
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ServerConfig(
            name="test-server",
            version="1.0.0",
            log_level="DEBUG",
            mode="sse",
            host="0.0.0.0",
            port=8080
        )
        assert config.name == "test-server"
        assert config.version == "1.0.0"
        assert config.log_level == "DEBUG"
        assert config.mode == "sse"
        assert config.host == "0.0.0.0"
        assert config.port == 8080
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            config = ServerConfig(log_level=level)
            assert config.log_level == level
        
        # Case insensitive
        config = ServerConfig(log_level="debug")
        assert config.log_level == "DEBUG"
        
        # Invalid log level
        with pytest.raises(ValidationError):
            ServerConfig(log_level="INVALID")
    
    def test_mode_validation(self):
        """Test server mode validation."""
        # Valid modes
        valid_modes = ["stdio", "sse"]
        for mode in valid_modes:
            config = ServerConfig(mode=mode)
            assert config.mode == mode
        
        # Invalid mode
        with pytest.raises(ValidationError):
            ServerConfig(mode="invalid")
    
    def test_port_validation(self):
        """Test port validation."""
        # Invalid ports
        with pytest.raises(ValidationError):
            ServerConfig(port=0)
        
        with pytest.raises(ValidationError):
            ServerConfig(port=70000)


class TestToolConfig:
    """Test ToolConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ToolConfig()
        assert isinstance(config.chromadb, ChromaDBConfig)
    
    def test_custom_chromadb_config(self):
        """Test custom ChromaDB configuration."""
        chromadb_config = ChromaDBConfig(host="remote", port=9000)
        config = ToolConfig(chromadb=chromadb_config)
        assert config.chromadb.host == "remote"
        assert config.chromadb.port == 9000


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_init(self):
        """Test ConfigManager initialization."""
        manager = ConfigManager()
        assert manager.config_path is None
        
        path = Path("/test/config.yaml")
        manager = ConfigManager(path)
        assert manager.config_path == path
    
    def test_substitute_env_vars(self):
        """Test environment variable substitution."""
        manager = ConfigManager()
        
        # Set test environment variable
        os.environ["TEST_VAR"] = "test_value"
        os.environ["TEST_VAR2"] = "value2"
        
        # Test substitution
        content = "host: ${TEST_VAR}\nport: ${TEST_VAR2}\ndefault: ${MISSING_VAR:-default_value}"
        result = manager._substitute_env_vars(content)
        
        expected = "host: test_value\nport: value2\ndefault: default_value"
        assert result == expected
        
        # Clean up
        del os.environ["TEST_VAR"]
        del os.environ["TEST_VAR2"]
    
    def test_get_default_config(self):
        """Test default configuration generation."""
        manager = ConfigManager()
        config = manager._get_default_config()
        
        assert "server" in config
        assert "tools" in config
        assert config["server"]["name"] == "chromadb-mcp-server"
        assert config["tools"]["chromadb"]["enabled"] is True
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        manager = ConfigManager()
        non_existent_path = Path("/non/existent/config.yaml")
        
        config = manager.load_config_file(non_existent_path)
        
        # Should return default config
        assert "server" in config
        assert "tools" in config
    
    def test_load_config_file_success(self):
        """Test successful configuration file loading."""
        # Create temporary config file
        config_data = {
            "server": {
                "name": "test-server",
                "log_level": "DEBUG"
            },
            "tools": {
                "chromadb": {
                    "host": "test-host",
                    "port": 9000
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager()
            loaded_config = manager.load_config_file(temp_path)
            
            assert loaded_config["server"]["name"] == "test-server"
            assert loaded_config["server"]["log_level"] == "DEBUG"
            assert loaded_config["tools"]["chromadb"]["host"] == "test-host"
            assert loaded_config["tools"]["chromadb"]["port"] == 9000
        finally:
            temp_path.unlink()
    
    def test_load_config_with_env_vars(self):
        """Test configuration loading with environment variables."""
        # Set test environment variables
        os.environ["TEST_HOST"] = "env-host"
        os.environ["TEST_PORT"] = "8080"
        
        config_content = """
server:
  name: test-server
  host: ${TEST_HOST}
  port: ${TEST_PORT}
tools:
  chromadb:
    host: ${TEST_HOST:-localhost}
    port: ${MISSING_VAR:-9000}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager()
            loaded_config = manager.load_config_file(temp_path)
            
            assert loaded_config["server"]["host"] == "env-host"
            assert loaded_config["server"]["port"] == 8080  # YAML loads as integer
            assert loaded_config["tools"]["chromadb"]["host"] == "env-host"
            assert loaded_config["tools"]["chromadb"]["port"] == 9000
        finally:
            temp_path.unlink()
            del os.environ["TEST_HOST"]
            del os.environ["TEST_PORT"]
    
    def test_validate_and_load_success(self):
        """Test successful configuration validation and loading."""
        config_data = {
            "server": {
                "name": "test-server",
                "log_level": "DEBUG",
                "mode": "sse",
                "port": 8080
            },
            "tools": {
                "chromadb": {
                    "host": "test-host",
                    "port": 9000,
                    "collection_prefix": "test_"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager()
            server_config, tool_config = manager.validate_and_load(temp_path)
            
            assert isinstance(server_config, ServerConfig)
            assert isinstance(tool_config, ToolConfig)
            assert server_config.name == "test-server"
            assert server_config.log_level == "DEBUG"
            assert tool_config.chromadb.host == "test-host"
            assert tool_config.chromadb.port == 9000
        finally:
            temp_path.unlink()
    
    def test_validate_and_load_validation_error(self):
        """Test configuration validation error."""
        config_data = {
            "server": {
                "log_level": "INVALID_LEVEL"  # Invalid log level
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager()
            with pytest.raises(ValidationError):
                manager.validate_and_load(temp_path)
        finally:
            temp_path.unlink()
    
    def test_save_config(self):
        """Test configuration saving."""
        server_config = ServerConfig(name="test-server", log_level="DEBUG")
        tool_config = ToolConfig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager()
            manager.save_config(server_config, tool_config, temp_path)
            
            # Verify saved content
            with open(temp_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data["server"]["name"] == "test-server"
            assert saved_data["server"]["log_level"] == "DEBUG"
            assert "tools" in saved_data
        finally:
            temp_path.unlink()
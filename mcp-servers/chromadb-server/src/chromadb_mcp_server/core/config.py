"""Configuration models and management for the MCP server."""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


class EmbeddingConfig(BaseModel):
    """Configuration for embedding services."""
    provider: str = Field(default="ollama", description="Embedding provider (openai, ollama)")
    model: str = Field(default="nomic-embed-text:latest", description="Embedding model name")
    host: Optional[str] = Field(default="http://localhost:11434", description="Host for local providers")
    api_key: Optional[str] = Field(default=None, description="API key for external providers")
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        """Validate embedding provider."""
        allowed_providers = ['openai', 'ollama', 'huggingface']
        if v not in allowed_providers:
            raise ValueError(f"Provider must be one of: {allowed_providers}")
        return v


class OllamaConfig(BaseModel):
    """Configuration for Ollama integration."""
    host: str = Field(default="http://localhost:11434", description="Ollama host URL")
    default_model: str = Field(default="qwen2.5vl:latest", description="Default Ollama model")
    complex_model: str = Field(default="qwen2.5vl:72b", description="Complex task model")
    embedding_model: str = Field(default="nomic-embed-text:latest", description="Embedding model")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""
    size: int = Field(default=1000, ge=100, le=8000, description="Chunk size in characters")
    overlap: int = Field(default=200, ge=0, description="Overlap between chunks in characters")
    
    @field_validator('overlap')
    @classmethod
    def validate_overlap(cls, v, info):
        """Validate that overlap is less than chunk size."""
        if info.data and 'size' in info.data and v >= info.data['size']:
            raise ValueError("Overlap must be less than chunk size")
        return v


class SearchConfig(BaseModel):
    """Configuration for search operations."""
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum search results")
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class ChromaDBConfig(BaseModel):
    """Configuration for ChromaDB tool."""
    enabled: bool = Field(default=True, description="Whether ChromaDB tool is enabled")
    host: str = Field(default="localhost", description="ChromaDB host")
    port: int = Field(default=8000, ge=1, le=65535, description="ChromaDB port")
    collection_prefix: str = Field(default="mcp_", description="Prefix for collection names")
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    
    @field_validator('collection_prefix')
    @classmethod
    def validate_collection_prefix(cls, v):
        """Validate collection prefix format."""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Collection prefix must contain only alphanumeric characters and underscores")
        return v


class ToolConfig(BaseModel):
    """Configuration for individual tools."""
    chromadb: ChromaDBConfig = Field(default_factory=ChromaDBConfig)


class ServerConfig(BaseModel):
    """Main server configuration."""
    name: str = Field(default="chromadb-mcp-server", description="Server name")
    version: str = Field(default="0.1.0", description="Server version")
    log_level: str = Field(default="INFO", description="Logging level")
    mode: str = Field(default="stdio", description="Server mode (stdio or http)")
    host: str = Field(default="localhost", description="Host for HTTP mode")
    port: int = Field(default=3000, ge=1, le=65535, description="Port for HTTP mode")
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        """Validate server mode."""
        allowed_modes = ['stdio', 'sse']
        if v not in allowed_modes:
            raise ValueError(f"Mode must be one of: {allowed_modes}")
        return v


class ConfigManager:
    """Configuration manager for loading and validating configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in configuration content.
        
        Supports format: ${VAR_NAME} or ${VAR_NAME:-default_value}
        
        Args:
            content: Configuration file content
            
        Returns:
            Content with environment variables substituted
        """
        def replace_env_vars(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            return os.getenv(var_name, default_value)
        
        return re.sub(r'\$\{([^}:]+)(?::-([^}]*))?\}', replace_env_vars, content)
    
    def load_config_file(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file is not found
            yaml.YAMLError: If YAML parsing fails
        """
        if config_path is None:
            config_path = self.config_path
        
        if config_path is None:
            # Default config path
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "config.yaml"
        
        if not config_path.exists():
            self.logger.warning(f"Configuration file not found: {config_path}")
            return self._get_default_config()
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Substitute environment variables
            content = self._substitute_env_vars(content)
            
            config_data = yaml.safe_load(content)
            self.logger.info(f"Configuration loaded from: {config_path}")
            return config_data
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "server": {
                "name": "chromadb-mcp-server",
                "version": "0.1.0",
                "log_level": "INFO",
                "mode": "stdio",
                "host": "localhost",
                "port": 3000
            },
            "tools": {
                "chromadb": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 8000,
                    "collection_prefix": "mcp_",
                    "embedding": {
                        "provider": "ollama",
                        "model": "nomic-embed-text:latest",
                        "host": "http://localhost:11434"
                    },
                    "ollama": {
                        "host": "http://localhost:11434",
                        "default_model": "qwen2.5vl:latest",
                        "complex_model": "qwen2.5vl:72b",
                        "embedding_model": "nomic-embed-text:latest"
                    },
                    "chunking": {
                        "size": 1000,
                        "overlap": 200
                    },
                    "search": {
                        "max_results": 10
                    }
                }
            }
        }
    
    def validate_and_load(self, config_path: Optional[Path] = None) -> tuple[ServerConfig, ToolConfig]:
        """Load and validate configuration.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (ServerConfig, ToolConfig)
            
        Raises:
            ValidationError: If configuration validation fails
        """
        try:
            config_data = self.load_config_file(config_path)
            
            # Extract server and tools configuration
            server_data = config_data.get("server", {})
            tools_data = config_data.get("tools", {})
            
            # Validate and create configuration objects
            server_config = ServerConfig(**server_data)
            tool_config = ToolConfig(**tools_data)
            
            self.logger.info("Configuration validation successful")
            return server_config, tool_config
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
    
    def save_config(self, server_config: ServerConfig, tool_config: ToolConfig, 
                   config_path: Optional[Path] = None) -> None:
        """Save configuration to file.
        
        Args:
            server_config: Server configuration
            tool_config: Tool configuration
            config_path: Path to save configuration file
        """
        if config_path is None:
            config_path = self.config_path
        
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "config.yaml"
        
        config_data = {
            "server": server_config.model_dump(),
            "tools": tool_config.model_dump()
        }
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            raise
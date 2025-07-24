"""Base tool interface for MCP server tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all MCP server tools.
    
    This class defines the common interface that all tools must implement
    to be compatible with the MCP server architecture.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the tool with configuration.
        
        Args:
            config: Tool-specific configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of this tool.
        
        Returns:
            Tool name as string
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable description of this tool.
        
        Returns:
            Tool description as string
        """
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of this tool.
        
        Returns:
            Tool version as string
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if the tool has been initialized.
        
        Returns:
            True if tool is initialized, False otherwise
        """
        return self._initialized
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the tool with its configuration.
        
        This method should set up any required connections, validate
        configuration, and prepare the tool for use.
        
        Raises:
            Exception: If initialization fails
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources used by the tool.
        
        This method should close connections, release resources,
        and perform any necessary cleanup operations.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the tool.
        
        Returns:
            Dictionary containing health status information
        """
        pass
    
    def validate_config(self) -> bool:
        """Validate the tool's configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not isinstance(self.config, dict):
            self.logger.error("Configuration must be a dictionary")
            return False
        
        # Check if tool is enabled
        if not self.config.get("enabled", True):
            self.logger.info(f"Tool {self.name} is disabled in configuration")
            return False
        
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
"""Unit tests for BaseTool interface."""

import pytest
from typing import Any, Dict
from unittest.mock import AsyncMock

from chromadb_mcp_server.core.base_tool import BaseTool


class MockTool(BaseTool):
    """Mock implementation of BaseTool for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.initialize_called = False
        self.cleanup_called = False
        self.health_check_called = False
    
    @property
    def name(self) -> str:
        return "mock_tool"
    
    @property
    def description(self) -> str:
        return "A mock tool for testing"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    async def initialize(self) -> None:
        """Mock initialization."""
        if not self.validate_config():
            raise ValueError("Invalid configuration")
        self.initialize_called = True
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Mock cleanup."""
        self.cleanup_called = True
        self._initialized = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        self.health_check_called = True
        return {
            "status": "healthy",
            "name": self.name,
            "version": self.version,
            "initialized": self.is_initialized
        }


class TestBaseTool:
    """Test BaseTool abstract base class."""
    
    def test_init(self):
        """Test tool initialization."""
        config = {"enabled": True, "test_param": "value"}
        tool = MockTool(config)
        
        assert tool.config == config
        assert not tool.is_initialized
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert tool.version == "1.0.0"
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        config = {"enabled": True, "param1": "value1"}
        tool = MockTool(config)
        
        assert tool.validate_config() is True
    
    def test_validate_config_disabled(self):
        """Test configuration validation with disabled tool."""
        config = {"enabled": False}
        tool = MockTool(config)
        
        assert tool.validate_config() is False
    
    def test_validate_config_invalid_type(self):
        """Test configuration validation with invalid config type."""
        config = "invalid_config"  # Should be dict
        tool = MockTool(config)
        
        assert tool.validate_config() is False
    
    def test_validate_config_missing_enabled(self):
        """Test configuration validation with missing enabled flag."""
        config = {"param1": "value1"}  # No 'enabled' key
        tool = MockTool(config)
        
        # Should default to True (enabled)
        assert tool.validate_config() is True
    
    def test_get_config_value(self):
        """Test getting configuration values."""
        config = {"param1": "value1", "param2": 42}
        tool = MockTool(config)
        
        assert tool.get_config_value("param1") == "value1"
        assert tool.get_config_value("param2") == 42
        assert tool.get_config_value("missing_param") is None
        assert tool.get_config_value("missing_param", "default") == "default"
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test tool initialization."""
        config = {"enabled": True}
        tool = MockTool(config)
        
        assert not tool.is_initialized
        assert not tool.initialize_called
        
        await tool.initialize()
        
        assert tool.is_initialized
        assert tool.initialize_called
    
    @pytest.mark.asyncio
    async def test_initialize_invalid_config(self):
        """Test tool initialization with invalid config."""
        config = "invalid_config"
        tool = MockTool(config)
        
        with pytest.raises(ValueError, match="Invalid configuration"):
            await tool.initialize()
        
        assert not tool.is_initialized
        assert not tool.initialize_called
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test tool cleanup."""
        config = {"enabled": True}
        tool = MockTool(config)
        
        # Initialize first
        await tool.initialize()
        assert tool.is_initialized
        
        # Then cleanup
        await tool.cleanup()
        assert not tool.is_initialized
        assert tool.cleanup_called
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test tool health check."""
        config = {"enabled": True}
        tool = MockTool(config)
        
        health_status = await tool.health_check()
        
        assert tool.health_check_called
        assert health_status["status"] == "healthy"
        assert health_status["name"] == "mock_tool"
        assert health_status["version"] == "1.0.0"
        assert health_status["initialized"] is False
        
        # Test after initialization
        await tool.initialize()
        health_status = await tool.health_check()
        assert health_status["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test tool as async context manager."""
        config = {"enabled": True}
        tool = MockTool(config)
        
        assert not tool.is_initialized
        
        async with tool as ctx_tool:
            assert ctx_tool is tool
            assert tool.is_initialized
            assert tool.initialize_called
        
        assert not tool.is_initialized
        assert tool.cleanup_called
    
    @pytest.mark.asyncio
    async def test_async_context_manager_already_initialized(self):
        """Test context manager when tool is already initialized."""
        config = {"enabled": True}
        tool = MockTool(config)
        
        # Initialize manually first
        await tool.initialize()
        assert tool.is_initialized
        
        # Reset the flag to test context manager behavior
        tool.initialize_called = False
        
        async with tool as ctx_tool:
            assert ctx_tool is tool
            assert tool.is_initialized
            # Should not call initialize again
            assert not tool.initialize_called
        
        assert not tool.is_initialized
        assert tool.cleanup_called


class TestBaseToolAbstractMethods:
    """Test that BaseTool properly enforces abstract methods."""
    
    def test_cannot_instantiate_base_tool(self):
        """Test that BaseTool cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTool({})
    
    def test_must_implement_abstract_methods(self):
        """Test that subclasses must implement all abstract methods."""
        
        # Missing name property
        class IncompleteToolMissingName(BaseTool):
            @property
            def description(self) -> str:
                return "test"
            
            @property
            def version(self) -> str:
                return "1.0.0"
            
            async def initialize(self) -> None:
                pass
            
            async def cleanup(self) -> None:
                pass
            
            async def health_check(self) -> Dict[str, Any]:
                return {}
        
        with pytest.raises(TypeError):
            IncompleteToolMissingName({})
        
        # Missing initialize method
        class IncompleteToolMissingInitialize(BaseTool):
            @property
            def name(self) -> str:
                return "test"
            
            @property
            def description(self) -> str:
                return "test"
            
            @property
            def version(self) -> str:
                return "1.0.0"
            
            async def cleanup(self) -> None:
                pass
            
            async def health_check(self) -> Dict[str, Any]:
                return {}
        
        with pytest.raises(TypeError):
            IncompleteToolMissingInitialize({})
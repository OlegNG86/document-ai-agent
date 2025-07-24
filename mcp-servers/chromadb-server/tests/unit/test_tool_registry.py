"""Unit tests for tool registry."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from chromadb_mcp_server.core.tool_registry import ToolRegistry
from chromadb_mcp_server.core.base_tool import BaseTool


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    def __init__(self, config: Dict[str, Any], name: str = "mock_tool"):
        super().__init__(config)
        self._name = name
        self._version = "1.0.0"
        self._description = "Mock tool for testing"
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def version(self) -> str:
        return self._version
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def cleanup(self) -> None:
        self._initialized = False
    
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "initialized": self._initialized}


class FailingMockTool(MockTool):
    """Mock tool that fails initialization."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "failing_tool")
    
    async def initialize(self) -> None:
        raise Exception("Initialization failed")


@pytest.fixture
def registry():
    """Create a tool registry for testing."""
    return ToolRegistry()


@pytest.fixture
def mock_tool():
    """Create a mock tool for testing."""
    return MockTool({"enabled": True})


@pytest.fixture
def failing_tool():
    """Create a failing mock tool for testing."""
    return FailingMockTool({"enabled": True})


class TestToolRegistry:
    """Test cases for ToolRegistry."""
    
    def test_init(self, registry):
        """Test registry initialization."""
        assert len(registry) == 0
        assert registry.list_tools() == []
        assert registry.list_tool_classes() == []
    
    def test_register_tool_class(self, registry):
        """Test registering a tool class."""
        registry.register_tool_class(MockTool)
        
        assert "mock_tool" in registry.list_tool_classes()
    
    def test_register_tool_class_invalid(self, registry):
        """Test registering invalid tool class."""
        class InvalidTool:
            pass
        
        with pytest.raises(ValueError, match="must inherit from BaseTool"):
            registry.register_tool_class(InvalidTool)
    
    def test_register_tool_class_duplicate(self, registry):
        """Test registering duplicate tool class."""
        registry.register_tool_class(MockTool)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register_tool_class(MockTool)
    
    @pytest.mark.asyncio
    async def test_register_tool(self, registry, mock_tool):
        """Test registering a tool instance."""
        await registry.register_tool(mock_tool)
        
        assert "mock_tool" in registry
        assert len(registry) == 1
        assert mock_tool.is_initialized
    
    @pytest.mark.asyncio
    async def test_register_tool_invalid(self, registry):
        """Test registering invalid tool."""
        with pytest.raises(ValueError, match="must be an instance of BaseTool"):
            await registry.register_tool("not a tool")
    
    @pytest.mark.asyncio
    async def test_register_tool_duplicate(self, registry, mock_tool):
        """Test registering duplicate tool."""
        await registry.register_tool(mock_tool)
        
        duplicate_tool = MockTool({"enabled": True})
        with pytest.raises(ValueError, match="already registered"):
            await registry.register_tool(duplicate_tool)
    
    @pytest.mark.asyncio
    async def test_register_tool_initialization_failure(self, registry, failing_tool):
        """Test registering tool with initialization failure."""
        with pytest.raises(ValueError, match="initialization failed"):
            await registry.register_tool(failing_tool)
    
    @pytest.mark.asyncio
    async def test_create_and_register_tool(self, registry):
        """Test creating and registering tool from class."""
        registry.register_tool_class(MockTool)
        
        await registry.create_and_register_tool("mock_tool", {"enabled": True})
        
        assert "mock_tool" in registry
        assert len(registry) == 1
    
    @pytest.mark.asyncio
    async def test_create_and_register_tool_not_found(self, registry):
        """Test creating tool from unregistered class."""
        with pytest.raises(ValueError, match="not registered"):
            await registry.create_and_register_tool("unknown_tool", {})
    
    @pytest.mark.asyncio
    async def test_unregister_tool(self, registry, mock_tool):
        """Test unregistering a tool."""
        await registry.register_tool(mock_tool)
        
        unregistered = registry.unregister_tool("mock_tool")
        
        assert unregistered == mock_tool
        assert "mock_tool" not in registry
        assert len(registry) == 0
    
    def test_unregister_tool_not_found(self, registry):
        """Test unregistering non-existent tool."""
        result = registry.unregister_tool("unknown_tool")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_tool(self, registry, mock_tool):
        """Test getting a registered tool."""
        await registry.register_tool(mock_tool)
        
        retrieved = registry.get_tool("mock_tool")
        assert retrieved == mock_tool
    
    def test_get_tool_not_found(self, registry):
        """Test getting non-existent tool."""
        result = registry.get_tool("unknown_tool")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_tool_info(self, registry, mock_tool):
        """Test getting tool information."""
        await registry.register_tool(mock_tool)
        
        info = registry.get_tool_info("mock_tool")
        
        assert info is not None
        assert info["name"] == "mock_tool"
        assert info["description"] == "Mock tool for testing"
        assert info["version"] == "1.0.0"
        assert info["initialized"] is True
    
    def test_get_tool_info_not_found(self, registry):
        """Test getting info for non-existent tool."""
        result = registry.get_tool_info("unknown_tool")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_tools_info(self, registry, mock_tool):
        """Test getting all tools information."""
        await registry.register_tool(mock_tool)
        
        all_info = await registry.get_all_tools_info()
        
        assert len(all_info) == 1
        assert all_info[0]["name"] == "mock_tool"
        assert "health" in all_info[0]
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, registry, mock_tool):
        """Test health check for all tools."""
        await registry.register_tool(mock_tool)
        
        health_results = await registry.health_check_all()
        
        assert "mock_tool" in health_results
        assert health_results["mock_tool"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_all_with_error(self, registry):
        """Test health check with tool error."""
        # Create a tool that will fail health check
        error_tool = MockTool({"enabled": True}, "error_tool")
        error_tool.health_check = AsyncMock(side_effect=Exception("Health check failed"))
        
        await registry.register_tool(error_tool)
        
        health_results = await registry.health_check_all()
        
        assert "error_tool" in health_results
        assert health_results["error_tool"]["status"] == "error"
        assert "Health check failed" in health_results["error_tool"]["error"]
    
    @pytest.mark.asyncio
    async def test_cleanup_all(self, registry, mock_tool):
        """Test cleaning up all tools."""
        await registry.register_tool(mock_tool)
        
        assert len(registry) == 1
        
        await registry.cleanup_all()
        
        assert len(registry) == 0
        assert not mock_tool.is_initialized
    
    @pytest.mark.asyncio
    async def test_cleanup_all_with_error(self, registry):
        """Test cleanup with tool error."""
        error_tool = MockTool({"enabled": True}, "error_tool")
        error_tool.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        
        await registry.register_tool(error_tool)
        
        # Should not raise exception, just log error
        await registry.cleanup_all()
        
        assert len(registry) == 0
    
    @pytest.mark.asyncio
    async def test_iteration(self, registry, mock_tool):
        """Test iterating over registered tools."""
        await registry.register_tool(mock_tool)
        
        tools = list(registry)
        assert len(tools) == 1
        assert tools[0] == mock_tool
    
    @pytest.mark.asyncio
    async def test_contains(self, registry, mock_tool):
        """Test checking if tool is registered."""
        assert "mock_tool" not in registry
        
        await registry.register_tool(mock_tool)
        
        assert "mock_tool" in registry
        assert "unknown_tool" not in registry
"""Unit tests for MCP server core functionality."""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from chromadb_mcp_server.core.mcp_server import MCPServer, MCPError, ErrorHandler
from chromadb_mcp_server.core.config import ServerConfig, ToolConfig, ChromaDBConfig
from chromadb_mcp_server.core.base_tool import BaseTool


class MockTool(BaseTool):
    """Mock tool for testing MCP server."""
    
    def __init__(self, config: Dict[str, Any], name: str = "mock_tool"):
        super().__init__(config)
        self._name = name
        self._version = "1.0.0"
        self._description = "Mock tool for testing"
        self.initialize_called = False
        self.cleanup_called = False
    
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
        self.initialize_called = True
        self._initialized = True
    
    async def cleanup(self) -> None:
        self.cleanup_called = True
        self._initialized = False
    
    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "name": self.name,
            "version": self.version,
            "initialized": self.is_initialized
        }


class FailingMockTool(MockTool):
    """Mock tool that fails operations."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "failing_tool")
    
    async def initialize(self) -> None:
        raise Exception("Initialization failed")
    
    async def cleanup(self) -> None:
        raise Exception("Cleanup failed")
    
    async def health_check(self) -> Dict[str, Any]:
        raise Exception("Health check failed")


@pytest.fixture
def server_config():
    """Create server configuration for testing."""
    return ServerConfig(
        name="test-mcp-server",
        version="1.0.0",
        log_level="DEBUG"
    )


@pytest.fixture
def tool_config():
    """Create tool configuration for testing."""
    return ToolConfig(
        chromadb=ChromaDBConfig(enabled=False)  # Disabled for unit tests
    )


@pytest.fixture
def mcp_server(server_config, tool_config):
    """Create MCP server for testing."""
    return MCPServer(server_config, tool_config)


@pytest.fixture
def mock_tool():
    """Create mock tool for testing."""
    return MockTool({"enabled": True})


@pytest.fixture
def failing_tool():
    """Create failing mock tool for testing."""
    return FailingMockTool({"enabled": True})


class TestMCPError:
    """Test MCP error handling."""
    
    def test_mcp_error_creation(self):
        """Test creating MCP error."""
        error = MCPError("Test error", "test_error", {"detail": "value"})
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_type == "test_error"
        assert error.details == {"detail": "value"}
    
    def test_mcp_error_defaults(self):
        """Test MCP error with default values."""
        error = MCPError("Test error")
        
        assert error.error_type == "internal_error"
        assert error.details == {}


class TestErrorHandler:
    """Test error handler functionality."""
    
    def test_handle_tool_error_mcp_error(self):
        """Test handling MCP error in tool."""
        mcp_error = MCPError("Tool failed", "tool_failure", {"code": 500})
        
        result = ErrorHandler.handle_tool_error(mcp_error, "test_tool")
        
        assert result["isError"] is True
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        assert "Error in test_tool: Tool failed" in result["content"][0]["text"]
    
    def test_handle_tool_error_generic_error(self):
        """Test handling generic error in tool."""
        generic_error = ValueError("Invalid value")
        
        result = ErrorHandler.handle_tool_error(generic_error, "test_tool")
        
        assert result["isError"] is True
        assert "Error in test_tool: Invalid value" in result["content"][0]["text"]
    
    def test_handle_server_error_mcp_error(self):
        """Test handling MCP error in server."""
        mcp_error = MCPError("Server failed", "server_failure")
        
        result = ErrorHandler.handle_server_error(mcp_error)
        
        assert result["isError"] is True
        assert "Server error: Server failed" in result["content"][0]["text"]
    
    def test_handle_server_error_generic_error(self):
        """Test handling generic server error."""
        generic_error = RuntimeError("Runtime error")
        
        result = ErrorHandler.handle_server_error(generic_error)
        
        assert result["isError"] is True
        assert "Server error: Runtime error" in result["content"][0]["text"]


class TestMCPServer:
    """Test MCP server functionality."""
    
    def test_init(self, mcp_server, server_config, tool_config):
        """Test MCP server initialization."""
        assert mcp_server.server_config == server_config
        assert mcp_server.tool_config == tool_config
        assert not mcp_server.is_initialized
        assert not mcp_server.is_running
        assert mcp_server.registered_tools == []
    
    @pytest.mark.asyncio
    async def test_register_tool_class(self, mcp_server):
        """Test registering a tool class."""
        await mcp_server.register_tool_class(MockTool)
        
        assert "mock_tool" in mcp_server.tool_registry.list_tool_classes()
    
    @pytest.mark.asyncio
    async def test_register_tool_class_failure(self, mcp_server):
        """Test registering invalid tool class."""
        class InvalidTool:
            pass
        
        with pytest.raises(MCPError, match="Tool class registration failed"):
            await mcp_server.register_tool_class(InvalidTool)
    
    @pytest.mark.asyncio
    async def test_register_tool(self, mcp_server, mock_tool):
        """Test registering a tool instance."""
        await mcp_server.register_tool(mock_tool)
        
        assert "mock_tool" in mcp_server.tool_registry
        assert mock_tool.is_initialized
    
    @pytest.mark.asyncio
    async def test_register_tool_failure(self, mcp_server, failing_tool):
        """Test registering tool that fails initialization."""
        with pytest.raises(MCPError, match="Tool registration failed"):
            await mcp_server.register_tool(failing_tool)
    
    @pytest.mark.asyncio
    async def test_create_and_register_tool(self, mcp_server):
        """Test creating and registering tool from class."""
        await mcp_server.register_tool_class(MockTool)
        await mcp_server.create_and_register_tool("mock_tool", {"enabled": True})
        
        assert "mock_tool" in mcp_server.tool_registry
    
    @pytest.mark.asyncio
    async def test_create_and_register_tool_failure(self, mcp_server):
        """Test creating tool from unregistered class."""
        with pytest.raises(MCPError, match="Tool creation failed"):
            await mcp_server.create_and_register_tool("unknown_tool", {})
    
    @pytest.mark.asyncio
    async def test_initialize(self, mcp_server):
        """Test server initialization."""
        await mcp_server.initialize()
        
        assert mcp_server.is_initialized
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, mcp_server):
        """Test initializing already initialized server."""
        await mcp_server.initialize()
        assert mcp_server.is_initialized
        
        # Should not raise error
        await mcp_server.initialize()
        assert mcp_server.is_initialized
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, mcp_server):
        """Test server initialization failure."""
        # Mock the _initialize_tools method to raise an exception
        with patch.object(mcp_server, '_initialize_tools', side_effect=Exception("Init failed")):
            with pytest.raises(MCPError, match="Server initialization failed"):
                await mcp_server.initialize()
        
        assert not mcp_server.is_initialized
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mcp_server, mock_tool):
        """Test server cleanup."""
        await mcp_server.register_tool(mock_tool)
        await mcp_server.initialize()
        
        assert mcp_server.is_initialized
        assert mock_tool.is_initialized
        
        await mcp_server.cleanup()
        
        assert not mcp_server.is_initialized
        assert not mcp_server.is_running
        assert mock_tool.cleanup_called
    
    @pytest.mark.asyncio
    async def test_cleanup_with_error(self, mcp_server, failing_tool):
        """Test cleanup with tool error."""
        # Register a tool that will fail cleanup
        failing_tool._initialized = True  # Bypass initialization
        mcp_server.tool_registry._tools["failing_tool"] = failing_tool
        
        await mcp_server.initialize()
        
        # Should not raise exception, just log error
        await mcp_server.cleanup()
        
        assert not mcp_server.is_initialized
    
    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self, mcp_server):
        """Test server lifespan context manager."""
        assert not mcp_server.is_initialized
        
        async with mcp_server.lifespan() as server:
            assert server is mcp_server
            assert mcp_server.is_initialized
        
        assert not mcp_server.is_initialized
    
    @pytest.mark.asyncio
    async def test_lifespan_context_manager_with_error(self, mcp_server):
        """Test lifespan context manager with initialization error."""
        with patch.object(mcp_server, 'initialize', side_effect=Exception("Init failed")):
            with pytest.raises(Exception, match="Init failed"):
                async with mcp_server.lifespan():
                    pass
        
        # Cleanup should still be called
        assert not mcp_server.is_initialized


class TestMCPServerMCPHandlers:
    """Test MCP protocol handlers."""
    
    @pytest.mark.asyncio
    async def test_list_tools_empty(self, mcp_server):
        """Test listing tools when none are registered."""
        await mcp_server.initialize()
        
        # Get the list_tools handler from FastMCP
        tools_dict = await mcp_server.mcp.get_tools()
        assert "list_tools" in tools_dict
        
        list_tools_handler = tools_dict["list_tools"].fn
        result = await list_tools_handler()
        
        assert "No tools are currently registered" in result
    
    @pytest.mark.asyncio
    async def test_list_tools_with_tools(self, mcp_server, mock_tool):
        """Test listing tools when tools are registered."""
        await mcp_server.register_tool(mock_tool)
        await mcp_server.initialize()
        
        # Get the list_tools handler from FastMCP
        tools_dict = await mcp_server.mcp.get_tools()
        assert "list_tools" in tools_dict
        
        list_tools_handler = tools_dict["list_tools"].fn
        result = await list_tools_handler()
        
        assert "Available tools:" in result
        assert "mock_tool" in result
        assert "Mock tool for testing" in result
        assert "Initialized" in result
    
    @pytest.mark.asyncio
    async def test_server_health(self, mcp_server, mock_tool):
        """Test server health check."""
        await mcp_server.register_tool(mock_tool)
        await mcp_server.initialize()
        
        # Get the server_health handler from FastMCP
        tools_dict = await mcp_server.mcp.get_tools()
        assert "server_health" in tools_dict
        
        health_handler = tools_dict["server_health"].fn
        result = await health_handler()
        
        assert "test-mcp-server" in result
        assert "Registered tools: 1" in result
        assert "mock_tool: healthy" in result
    
    @pytest.mark.asyncio
    async def test_server_health_with_error(self, mcp_server, failing_tool):
        """Test server health check with tool error."""
        # Register failing tool manually
        failing_tool._initialized = True
        mcp_server.tool_registry._tools["failing_tool"] = failing_tool
        
        await mcp_server.initialize()
        
        # Get the server_health handler from FastMCP
        tools_dict = await mcp_server.mcp.get_tools()
        assert "server_health" in tools_dict
        
        health_handler = tools_dict["server_health"].fn
        result = await health_handler()
        
        assert "failing_tool: error" in result
        assert "Health check failed" in result


class TestMCPServerIntegration:
    """Integration tests for MCP server components."""
    
    @pytest.mark.asyncio
    async def test_full_tool_lifecycle(self, mcp_server):
        """Test complete tool lifecycle."""
        # Register tool class
        await mcp_server.register_tool_class(MockTool)
        
        # Create and register tool instance
        await mcp_server.create_and_register_tool("mock_tool", {"enabled": True})
        
        # Initialize server
        await mcp_server.initialize()
        
        # Verify tool is registered and initialized
        assert "mock_tool" in mcp_server.registered_tools
        tool = mcp_server.tool_registry.get_tool("mock_tool")
        assert tool is not None
        assert tool.is_initialized
        
        # Test health check
        health_results = await mcp_server.tool_registry.health_check_all()
        assert "mock_tool" in health_results
        assert health_results["mock_tool"]["status"] == "healthy"
        
        # Cleanup
        await mcp_server.cleanup()
        
        assert not mcp_server.is_initialized
        assert tool.cleanup_called
    
    @pytest.mark.asyncio
    async def test_error_handling_throughout_lifecycle(self, mcp_server):
        """Test error handling throughout tool lifecycle."""
        # Test registration error
        with pytest.raises(MCPError):
            await mcp_server.register_tool_class(str)  # Invalid tool class
        
        # Test creation error
        with pytest.raises(MCPError):
            await mcp_server.create_and_register_tool("nonexistent", {})
        
        # Register a valid tool class
        await mcp_server.register_tool_class(MockTool)
        
        # Test successful operations
        await mcp_server.create_and_register_tool("mock_tool", {"enabled": True})
        await mcp_server.initialize()
        
        # Verify everything works
        assert mcp_server.is_initialized
        assert "mock_tool" in mcp_server.registered_tools
        
        await mcp_server.cleanup()
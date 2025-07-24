"""MCP Server core implementation using FastMCP."""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from pydantic import BaseModel

from chromadb_mcp_server.core.tool_registry import ToolRegistry
from chromadb_mcp_server.core.config import ServerConfig, ToolConfig
from chromadb_mcp_server.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP server errors."""
    
    def __init__(self, message: str, error_type: str = "internal_error", details: Optional[Dict[str, Any]] = None):
        """Initialize MCP error.
        
        Args:
            message: Error message
            error_type: Type of error
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}


class ErrorHandler:
    """Handler for MCP server errors."""
    
    @staticmethod
    def handle_tool_error(error: Exception, tool_name: str) -> Dict[str, Any]:
        """Convert exceptions to MCP tool error format.
        
        Args:
            error: The exception that occurred
            tool_name: Name of the tool where error occurred
            
        Returns:
            MCP-compatible error response
        """
        error_message = f"Error in {tool_name}: {str(error)}"
        
        if isinstance(error, MCPError):
            error_type = error.error_type
            details = error.details
        else:
            error_type = "tool_error"
            details = {"exception_type": type(error).__name__}
        
        logger.error(f"Tool error in {tool_name}: {error_message}", extra={"details": details})
        
        return {
            "isError": True,
            "content": [{
                "type": "text",
                "text": error_message
            }]
        }
    
    @staticmethod
    def handle_server_error(error: Exception) -> Dict[str, Any]:
        """Convert server exceptions to MCP error format.
        
        Args:
            error: The exception that occurred
            
        Returns:
            MCP-compatible error response
        """
        error_message = f"Server error: {str(error)}"
        
        if isinstance(error, MCPError):
            error_type = error.error_type
            details = error.details
        else:
            error_type = "server_error"
            details = {"exception_type": type(error).__name__}
        
        logger.error(f"Server error: {error_message}", extra={"details": details})
        
        return {
            "isError": True,
            "content": [{
                "type": "text",
                "text": error_message
            }]
        }


class MCPServer:
    """MCP Server implementation using FastMCP.
    
    This class manages the MCP server lifecycle, tool registration,
    and request handling.
    """
    
    def __init__(self, server_config: ServerConfig, tool_config: ToolConfig):
        """Initialize MCP server.
        
        Args:
            server_config: Server configuration
            tool_config: Tool configuration
        """
        self.server_config = server_config
        self.tool_config = tool_config
        self.tool_registry = ToolRegistry()
        self.mcp = FastMCP(server_config.name)
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._running = False
        
        # Setup logging
        self._setup_logging()
        
        # Register MCP handlers
        self._register_mcp_handlers()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.server_config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )
        
        self.logger.info(f"Logging configured at {self.server_config.log_level} level")
    
    def _register_mcp_handlers(self) -> None:
        """Register MCP protocol handlers."""
        
        @self.mcp.tool()
        async def list_tools() -> str:
            """List all available tools and their information."""
            try:
                tools_info = await self.tool_registry.get_all_tools_info()
                
                if not tools_info:
                    return "No tools are currently registered."
                
                result = "Available tools:\n\n"
                for tool_info in tools_info:
                    result += f"**{tool_info['name']}** (v{tool_info['version']})\n"
                    result += f"Description: {tool_info['description']}\n"
                    result += f"Status: {'Initialized' if tool_info['initialized'] else 'Not initialized'}\n"
                    
                    if 'health' in tool_info:
                        health_status = tool_info['health'].get('status', 'unknown')
                        result += f"Health: {health_status}\n"
                    
                    result += "\n"
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error listing tools: {e}")
                return f"Error listing tools: {str(e)}"
        
        @self.mcp.tool()
        async def server_health() -> str:
            """Check server and all tools health status."""
            try:
                health_results = await self.tool_registry.health_check_all()
                
                result = f"Server: {self.server_config.name} v{self.server_config.version}\n"
                result += f"Status: {'Running' if self._running else 'Stopped'}\n"
                result += f"Registered tools: {len(self.tool_registry)}\n\n"
                
                if health_results:
                    result += "Tool Health Status:\n"
                    for tool_name, health in health_results.items():
                        status = health.get('status', 'unknown')
                        result += f"- {tool_name}: {status}\n"
                        
                        if status == 'error' and 'error' in health:
                            result += f"  Error: {health['error']}\n"
                else:
                    result += "No tools registered.\n"
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error checking server health: {e}")
                return f"Error checking server health: {str(e)}"
    
    async def register_tool_class(self, tool_class: type[BaseTool]) -> None:
        """Register a tool class.
        
        Args:
            tool_class: The tool class to register
        """
        try:
            self.tool_registry.register_tool_class(tool_class)
            self.logger.info(f"Registered tool class: {tool_class.__name__}")
        except Exception as e:
            self.logger.error(f"Failed to register tool class {tool_class.__name__}: {e}")
            raise MCPError(f"Tool class registration failed: {e}", "registration_error")
    
    async def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance.
        
        Args:
            tool: The tool instance to register
        """
        try:
            await self.tool_registry.register_tool(tool)
            self.logger.info(f"Registered tool: {tool.name}")
        except Exception as e:
            self.logger.error(f"Failed to register tool {tool.name}: {e}")
            raise MCPError(f"Tool registration failed: {e}", "registration_error")
    
    async def create_and_register_tool(self, tool_name: str, config: Dict[str, Any]) -> None:
        """Create and register a tool from registered class.
        
        Args:
            tool_name: Name of the tool to create
            config: Configuration for the tool
        """
        try:
            await self.tool_registry.create_and_register_tool(tool_name, config)
            self.logger.info(f"Created and registered tool: {tool_name}")
        except Exception as e:
            self.logger.error(f"Failed to create and register tool {tool_name}: {e}")
            raise MCPError(f"Tool creation failed: {e}", "creation_error")
    
    async def initialize(self) -> None:
        """Initialize the MCP server.
        
        This method sets up the server and initializes all configured tools.
        """
        if self._initialized:
            self.logger.warning("Server is already initialized")
            return
        
        try:
            self.logger.info(f"Initializing {self.server_config.name} v{self.server_config.version}")
            
            # Initialize tools based on configuration
            await self._initialize_tools()
            
            self._initialized = True
            self.logger.info("MCP server initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP server: {e}")
            raise MCPError(f"Server initialization failed: {e}", "initialization_error")
    
    async def _initialize_tools(self) -> None:
        """Initialize tools based on configuration."""
        # For now, we'll just log that tools would be initialized here
        # The actual tool implementations will be added in subsequent tasks
        
        if self.tool_config.chromadb.enabled:
            self.logger.info("ChromaDB tool is enabled in configuration")
            # TODO: Initialize ChromaDB tool in task 6
        else:
            self.logger.info("ChromaDB tool is disabled in configuration")
    
    async def run_stdio(self) -> None:
        """Run the server in stdio mode.
        
        This is the standard MCP transport mode.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._running = True
            self.logger.info("Starting MCP server in stdio mode")
            
            # Run the FastMCP server
            await self.mcp.run("stdio")
            
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except Exception as e:
            self.logger.error(f"Error running stdio server: {e}")
            raise MCPError(f"Server runtime error: {e}", "runtime_error")
        finally:
            self._running = False
            await self.cleanup()
    
    async def run_sse(self, host: str = "localhost", port: int = 3000) -> None:
        """Run the server in SSE mode.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._running = True
            self.logger.info(f"Starting MCP server in SSE mode on {host}:{port}")
            
            # Run the FastMCP server in SSE mode
            await self.mcp.run("sse", host=host, port=port)
            
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except Exception as e:
            self.logger.error(f"Error running SSE server: {e}")
            raise MCPError(f"Server runtime error: {e}", "runtime_error")
        finally:
            self._running = False
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Clean up server resources.
        
        This method should be called when shutting down the server.
        """
        self.logger.info("Cleaning up MCP server")
        
        try:
            # Clean up all registered tools
            await self.tool_registry.cleanup_all()
            
            self._initialized = False
            self._running = False
            
            self.logger.info("MCP server cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during server cleanup: {e}")
    
    @property
    def is_initialized(self) -> bool:
        """Check if server is initialized."""
        return self._initialized
    
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
    
    @property
    def registered_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return self.tool_registry.list_tools()
    
    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for server lifecycle."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.cleanup()
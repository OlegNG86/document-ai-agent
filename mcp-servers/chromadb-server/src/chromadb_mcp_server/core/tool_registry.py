"""Tool registry for managing MCP server tools."""

import logging
from typing import Dict, List, Optional, Type, Any
from chromadb_mcp_server.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing MCP server tools.
    
    This class provides a centralized way to register, discover, and manage
    tools that can be used by the MCP server.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_tool_class(self, tool_class: Type[BaseTool]) -> None:
        """Register a tool class for later instantiation.
        
        Args:
            tool_class: The tool class to register
            
        Raises:
            ValueError: If tool class is invalid or already registered
        """
        if not issubclass(tool_class, BaseTool):
            raise ValueError(f"Tool class {tool_class.__name__} must inherit from BaseTool")
        
        # Get tool name from class (we'll need to instantiate temporarily)
        try:
            temp_instance = tool_class({})
            tool_name = temp_instance.name
        except Exception as e:
            raise ValueError(f"Cannot get name from tool class {tool_class.__name__}: {e}")
        
        if tool_name in self._tool_classes:
            raise ValueError(f"Tool class with name '{tool_name}' is already registered")
        
        self._tool_classes[tool_name] = tool_class
        self.logger.info(f"Registered tool class: {tool_name}")
    
    async def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance.
        
        Args:
            tool: The tool instance to register
            
        Raises:
            ValueError: If tool is invalid or already registered
        """
        if not isinstance(tool, BaseTool):
            raise ValueError("Tool must be an instance of BaseTool")
        
        tool_name = tool.name
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' is already registered")
        
        # Validate tool configuration
        if not tool.validate_config():
            raise ValueError(f"Tool '{tool_name}' has invalid configuration")
        
        # Initialize tool if not already initialized
        if not tool.is_initialized:
            try:
                await tool.initialize()
            except Exception as e:
                self.logger.error(f"Failed to initialize tool '{tool_name}': {e}")
                raise ValueError(f"Tool '{tool_name}' initialization failed: {e}")
        
        self._tools[tool_name] = tool
        self.logger.info(f"Registered tool: {tool_name} v{tool.version}")
    
    async def create_and_register_tool(self, tool_name: str, config: Dict[str, Any]) -> None:
        """Create and register a tool from registered class.
        
        Args:
            tool_name: Name of the tool to create
            config: Configuration for the tool
            
        Raises:
            ValueError: If tool class is not found or creation fails
        """
        if tool_name not in self._tool_classes:
            raise ValueError(f"Tool class '{tool_name}' is not registered")
        
        tool_class = self._tool_classes[tool_name]
        
        try:
            tool_instance = tool_class(config)
            await self.register_tool(tool_instance)
        except Exception as e:
            self.logger.error(f"Failed to create and register tool '{tool_name}': {e}")
            raise
    
    def unregister_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Unregister a tool.
        
        Args:
            tool_name: Name of the tool to unregister
            
        Returns:
            The unregistered tool instance, or None if not found
        """
        tool = self._tools.pop(tool_name, None)
        if tool:
            self.logger.info(f"Unregistered tool: {tool_name}")
        else:
            self.logger.warning(f"Tool '{tool_name}' not found for unregistration")
        return tool
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a registered tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            The tool instance, or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names.
        
        Returns:
            List of registered tool names
        """
        return list(self._tools.keys())
    
    def list_tool_classes(self) -> List[str]:
        """List all registered tool class names.
        
        Returns:
            List of registered tool class names
        """
        return list(self._tool_classes.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary containing tool information, or None if not found
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "version": tool.version,
            "initialized": tool.is_initialized,
            "config": tool.config
        }
    
    async def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered tools.
        
        Returns:
            List of dictionaries containing tool information
        """
        tools_info = []
        for tool_name in self._tools:
            tool_info = self.get_tool_info(tool_name)
            if tool_info:
                # Add health check information
                try:
                    health = await self._tools[tool_name].health_check()
                    tool_info["health"] = health
                except Exception as e:
                    tool_info["health"] = {"status": "error", "error": str(e)}
                
                tools_info.append(tool_info)
        
        return tools_info
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all registered tools.
        
        Returns:
            Dictionary mapping tool names to their health status
        """
        health_results = {}
        
        for tool_name, tool in self._tools.items():
            try:
                health = await tool.health_check()
                health_results[tool_name] = health
            except Exception as e:
                health_results[tool_name] = {
                    "status": "error",
                    "error": str(e)
                }
                self.logger.error(f"Health check failed for tool '{tool_name}': {e}")
        
        return health_results
    
    async def cleanup_all(self) -> None:
        """Clean up all registered tools.
        
        This method should be called when shutting down the server.
        """
        self.logger.info("Cleaning up all registered tools")
        
        for tool_name, tool in self._tools.items():
            try:
                await tool.cleanup()
                self.logger.info(f"Cleaned up tool: {tool_name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up tool '{tool_name}': {e}")
        
        self._tools.clear()
        self.logger.info("All tools cleaned up")
    
    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools
    
    def __iter__(self):
        """Iterate over registered tools."""
        return iter(self._tools.values())
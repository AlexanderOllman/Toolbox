import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .mcp_container_service import MCPContainer

logger = logging.getLogger(__name__)

class MCPErrorCode(Enum):
    """MCP protocol error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

@dataclass
class MCPTool:
    """Represents an MCP tool/function."""
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass
class MCPResponse:
    """Represents an MCP response."""
    success: bool
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None

class MCPClient:
    """
    Simple, clean MCP protocol client for communicating with containerized MCP servers.
    Implements the core MCP protocol over stdio.
    """
    
    def __init__(self, container: MCPContainer):
        self.container = container
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to the MCP server via stdio."""
        try:
            logger.info(f"Connecting to MCP server in container {self.container.container_id[:12]}")
            
            # Start an interactive session with the container
            cmd = [
                'docker', 'exec', '-i',
                self.container.container_id,
                '/bin/sh', '-c', 'cd /app && exec "$@"', '--'
            ]
            
            # Add the actual MCP server command
            # This should be the command that starts the MCP server
            # For now, let's assume it's the default command in the container
            
            self.process = await asyncio.create_subprocess_exec(
                'docker', 'exec', '-i', self.container.container_id,
                'sh', '-c', 'cd /app && python server.py',  # This should be configurable
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize the MCP connection
            init_response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "mcp-test-client", 
                    "version": "1.0.0"
                }
            })
            
            if not init_response.success:
                logger.error(f"MCP initialization failed: {init_response.error}")
                return False
            
            # Send initialized notification
            await self._send_notification("notifications/initialized")
            
            self.is_connected = True
            logger.info(f"Successfully connected to MCP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None
        
        self.is_connected = False
        logger.info("Disconnected from MCP server")
    
    async def list_tools(self) -> List[MCPTool]:
        """List all available tools from the MCP server."""
        if not self.is_connected:
            raise RuntimeError("Not connected to MCP server")
        
        response = await self._send_request("tools/list")
        
        if not response.success:
            raise RuntimeError(f"Failed to list tools: {response.error}")
        
        tools = []
        for tool_data in response.result.get("tools", []):
            tools.append(MCPTool(
                name=tool_data["name"],
                description=tool_data["description"],
                input_schema=tool_data.get("inputSchema", {})
            ))
        
        logger.info(f"Found {len(tools)} tools: {[t.name for t in tools]}")
        return tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        """Call a specific tool with the given arguments."""
        if not self.is_connected:
            raise RuntimeError("Not connected to MCP server")
        
        logger.info(f"Calling tool '{tool_name}' with args: {arguments}")
        
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if response.success:
            logger.info(f"Tool '{tool_name}' executed successfully")
        else:
            logger.error(f"Tool '{tool_name}' failed: {response.error}")
        
        return response
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Send a JSON-RPC request to the MCP server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("No active connection to MCP server")
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        
        if params is not None:
            request["params"] = params
        
        # Send request
        request_json = json.dumps(request) + "\n"
        logger.debug(f"Sending MCP request: {request_json.strip()}")
        
        try:
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), 
                timeout=30.0
            )
            
            if not response_line:
                return MCPResponse(
                    success=False,
                    error={"code": MCPErrorCode.INTERNAL_ERROR.value, "message": "No response from server"}
                )
            
            response_text = response_line.decode().strip()
            logger.debug(f"Received MCP response: {response_text}")
            
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                return MCPResponse(
                    success=False,
                    error={"code": MCPErrorCode.PARSE_ERROR.value, "message": f"Invalid JSON: {e}"},
                    raw_response=response_text
                )
            
            # Check for error in response
            if "error" in response_data:
                return MCPResponse(
                    success=False,
                    error=response_data["error"],
                    raw_response=response_text
                )
            
            return MCPResponse(
                success=True,
                result=response_data.get("result"),
                raw_response=response_text
            )
            
        except asyncio.TimeoutError:
            return MCPResponse(
                success=False,
                error={"code": MCPErrorCode.INTERNAL_ERROR.value, "message": "Request timeout"}
            )
        except Exception as e:
            return MCPResponse(
                success=False,
                error={"code": MCPErrorCode.INTERNAL_ERROR.value, "message": f"Request failed: {e}"}
            )
    
    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("No active connection to MCP server")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        if params is not None:
            notification["params"] = params
        
        notification_json = json.dumps(notification) + "\n"
        logger.debug(f"Sending MCP notification: {notification_json.strip()}")
        
        self.process.stdin.write(notification_json.encode())
        await self.process.stdin.drain()

class MCPTestSession:
    """
    High-level interface for testing MCP servers.
    Combines container management with MCP protocol communication.
    """
    
    def __init__(self, container: MCPContainer):
        self.container = container
        self.client = MCPClient(container)
        self.tools: List[MCPTool] = []
    
    async def start(self) -> bool:
        """Start the test session by connecting to the MCP server."""
        try:
            success = await self.client.connect()
            if success:
                self.tools = await self.client.list_tools()
                logger.info(f"Test session started with {len(self.tools)} tools")
            return success
        except Exception as e:
            logger.error(f"Failed to start test session: {e}")
            return False
    
    async def stop(self):
        """Stop the test session and clean up."""
        await self.client.disconnect()
        logger.info("Test session stopped")
    
    async def test_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        """Test a specific tool with given arguments."""
        return await self.client.call_tool(tool_name, arguments)
    
    async def test_all_tools_basic(self) -> Dict[str, MCPResponse]:
        """Run basic tests on all available tools."""
        results = {}
        
        for tool in self.tools:
            logger.info(f"Testing tool: {tool.name}")
            
            try:
                # Generate minimal valid arguments based on schema
                test_args = self._generate_test_arguments(tool.input_schema)
                result = await self.test_tool(tool.name, test_args)
                results[tool.name] = result
                
            except Exception as e:
                logger.error(f"Failed to test tool {tool.name}: {e}")
                results[tool.name] = MCPResponse(
                    success=False,
                    error={"code": MCPErrorCode.INTERNAL_ERROR.value, "message": str(e)}
                )
        
        return results
    
    def _generate_test_arguments(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic test arguments from a tool's input schema."""
        args = {}
        
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        for prop_name, prop_schema in properties.items():
            if prop_name in required:
                # Generate a basic value based on type
                prop_type = prop_schema.get("type", "string")
                
                if prop_type == "string":
                    args[prop_name] = prop_schema.get("default", "test")
                elif prop_type == "number" or prop_type == "integer":
                    args[prop_name] = prop_schema.get("default", 1)
                elif prop_type == "boolean":
                    args[prop_name] = prop_schema.get("default", True)
                elif prop_type == "array":
                    args[prop_name] = prop_schema.get("default", [])
                elif prop_type == "object":
                    args[prop_name] = prop_schema.get("default", {})
        
        return args 
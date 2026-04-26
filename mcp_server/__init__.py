"""
SintraPrime MCP Server — Model Context Protocol implementation.

Connects Claude Desktop, Cursor, ChatGPT, and other AI tools to
SintraPrime's legal, financial, and research capabilities.
"""

from .mcp_server import SintraMCPServer
from .mcp_types import MCPTool, MCPResource, MCPPrompt

__all__ = ["SintraMCPServer", "MCPTool", "MCPResource", "MCPPrompt"]
__version__ = "1.0.0"

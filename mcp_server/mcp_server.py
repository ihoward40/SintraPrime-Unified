"""
SintraMCPServer — Full Model Context Protocol server implementation.

Supports the MCP specification:
  - initialize / initialized lifecycle
  - tools/list, tools/call
  - resources/list, resources/read
  - prompts/list, prompts/get
  - JSON-RPC 2.0 error handling
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from typing import Any, Dict, List, Optional

from .mcp_types import (
    MCPErrorCode,
    MCPPrompt,
    MCPRequest,
    MCPResource,
    MCPResponse,
    MCPTool,
)
from .mcp_transport import BaseTransport, StdioTransport

logger = logging.getLogger(__name__)

# MCP Protocol version advertised by this server
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "sintra-prime"
SERVER_VERSION = "1.0.0"


class SintraMCPServer:
    """
    Full MCP server for SintraPrime-Unified.

    Usage (stdio mode, the default for Claude Desktop / Cursor):

        server = SintraMCPServer()
        server.register_tool(some_tool)
        server.register_resource(some_resource)
        server.register_prompt(some_prompt)
        server.start()          # blocks until EOF on stdin

    Usage (async / custom transport):

        server = SintraMCPServer(transport=HTTPTransport(port=8765))
        await server.start_async()
    """

    def __init__(
        self,
        transport: Optional[BaseTransport] = None,
        name: str = SERVER_NAME,
        version: str = SERVER_VERSION,
    ) -> None:
        self.name = name
        self.version = version
        self.transport: BaseTransport = transport or StdioTransport()

        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._prompts: Dict[str, MCPPrompt] = {}
        self._initialized = False

        # Load default SintraPrime capabilities
        self._load_defaults()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool(self, tool: MCPTool) -> None:
        """Register an MCP tool with the server."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def register_resource(self, resource: MCPResource) -> None:
        """Register an MCP resource with the server."""
        self._resources[resource.uri] = resource
        logger.debug("Registered resource: %s", resource.uri)

    def register_prompt(self, prompt: MCPPrompt) -> None:
        """Register an MCP prompt with the server."""
        self._prompts[prompt.name] = prompt
        logger.debug("Registered prompt: %s", prompt.name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the server (blocking — runs the asyncio event loop)."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,
        )
        asyncio.run(self.start_async())

    async def start_async(self) -> None:
        """Start the server asynchronously."""
        logger.info("SintraPrime MCP Server v%s starting", self.version)
        await self.transport.start(self._handle_message)

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------

    def _handle_message(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Dispatch a raw JSON-RPC dict and return a response dict (or None)."""
        try:
            req = MCPRequest.from_dict(raw)
        except (KeyError, TypeError) as exc:
            return MCPResponse.err(
                raw.get("id"), MCPErrorCode.INVALID_REQUEST, f"Invalid request: {exc}"
            ).to_dict()

        handler = self._dispatch_table().get(req.method)
        if handler is None:
            if req.id is None:
                # Notification — no response required
                return None
            return MCPResponse.err(
                req.id, MCPErrorCode.METHOD_NOT_FOUND, f"Method not found: {req.method}"
            ).to_dict()

        try:
            result = handler(req)
            if req.id is None:
                return None  # Notification
            return MCPResponse.ok(req.id, result).to_dict()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error handling %s: %s", req.method, exc)
            return MCPResponse.err(
                req.id, MCPErrorCode.INTERNAL_ERROR, str(exc)
            ).to_dict()

    def _dispatch_table(self) -> Dict[str, Any]:
        return {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "ping": self._handle_ping,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
            # Completion / sampling (optional MCP features)
            "completion/complete": self._handle_completion,
        }

    # ------------------------------------------------------------------
    # MCP handlers
    # ------------------------------------------------------------------

    def _handle_initialize(self, req: MCPRequest) -> Dict[str, Any]:
        client_version = req.params.get("protocolVersion", MCP_PROTOCOL_VERSION)
        logger.info("Client initializing with protocol version %s", client_version)
        self._initialized = True
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False, "subscribe": False},
                "prompts": {"listChanged": False},
                "logging": {},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
        }

    def _handle_initialized(self, req: MCPRequest) -> None:
        logger.info("Client initialization complete")
        return None

    def _handle_ping(self, req: MCPRequest) -> Dict[str, Any]:
        return {}

    # --- Tools ---

    def _handle_tools_list(self, req: MCPRequest) -> Dict[str, Any]:
        return {"tools": [t.to_dict() for t in self._tools.values()]}

    def _handle_tools_call(self, req: MCPRequest) -> Dict[str, Any]:
        name = req.params.get("name")
        arguments = req.params.get("arguments", {})

        if not name:
            raise ValueError("tools/call requires 'name' parameter")

        tool = self._tools.get(name)
        if tool is None:
            return MCPResponse.err(
                req.id, MCPErrorCode.TOOL_NOT_FOUND, f"Tool not found: {name}"
            ).to_dict()

        result = tool.call(arguments)
        return result.to_dict()

    # --- Resources ---

    def _handle_resources_list(self, req: MCPRequest) -> Dict[str, Any]:
        return {"resources": [r.to_dict() for r in self._resources.values()]}

    def _handle_resources_read(self, req: MCPRequest) -> Dict[str, Any]:
        uri = req.params.get("uri")
        if not uri:
            raise ValueError("resources/read requires 'uri' parameter")

        # Exact match first
        resource = self._resources.get(uri)

        # Pattern match (URI templates with {param})
        if resource is None:
            resource, kwargs = self._match_resource_uri(uri)
            if resource:
                content = resource.content_fn(**kwargs)
                return {
                    "contents": [
                        {"uri": uri, "mimeType": resource.mime_type, "text": content}
                    ]
                }

        if resource is None:
            return MCPResponse.err(
                req.id, MCPErrorCode.RESOURCE_NOT_FOUND, f"Resource not found: {uri}"
            ).to_dict()

        content = resource.read()
        return {
            "contents": [
                {"uri": uri, "mimeType": resource.mime_type, "text": content}
            ]
        }

    def _match_resource_uri(self, uri: str):
        """Try to match a URI against registered resource URI templates."""
        for template_uri, resource in self._resources.items():
            # Split on {param} tokens and build regex, escaping literal parts
            parts = re.split(r"\{(\w+)\}", template_uri)
            pattern = ""
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    pattern += re.escape(part)
                else:
                    pattern += f"(?P<{part}>[^/]+)"
            m = re.fullmatch(pattern, uri)
            if m:
                return resource, m.groupdict()
        return None, {}

    # --- Prompts ---

    def _handle_prompts_list(self, req: MCPRequest) -> Dict[str, Any]:
        return {"prompts": [p.to_dict() for p in self._prompts.values()]}

    def _handle_prompts_get(self, req: MCPRequest) -> Dict[str, Any]:
        name = req.params.get("name")
        arguments = req.params.get("arguments", {})

        if not name:
            raise ValueError("prompts/get requires 'name' parameter")

        prompt = self._prompts.get(name)
        if prompt is None:
            return MCPResponse.err(
                req.id, MCPErrorCode.PROMPT_NOT_FOUND, f"Prompt not found: {name}"
            ).to_dict()

        return prompt.render(arguments)

    # --- Completion (optional) ---

    def _handle_completion(self, req: MCPRequest) -> Dict[str, Any]:
        # Minimal implementation — clients may call this for auto-complete
        return {"completion": {"values": [], "total": 0, "hasMore": False}}

    # ------------------------------------------------------------------
    # Default capability loading
    # ------------------------------------------------------------------

    def _load_defaults(self) -> None:
        """Load all built-in SintraPrime tools, resources, and prompts."""
        try:
            from .sintra_tools import register_all_tools
            register_all_tools(self)
        except ImportError as exc:
            logger.warning("Could not load sintra_tools: %s", exc)

        try:
            from .sintra_resources import register_all_resources
            register_all_resources(self)
        except ImportError as exc:
            logger.warning("Could not load sintra_resources: %s", exc)

        try:
            from .sintra_prompts import register_all_prompts
            register_all_prompts(self)
        except ImportError as exc:
            logger.warning("Could not load sintra_prompts: %s", exc)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def tools(self) -> Dict[str, MCPTool]:
        return dict(self._tools)

    @property
    def resources(self) -> Dict[str, MCPResource]:
        return dict(self._resources)

    @property
    def prompts(self) -> Dict[str, MCPPrompt]:
        return dict(self._prompts)

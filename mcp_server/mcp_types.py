"""
MCP Protocol Types — JSON-RPC 2.0 compliant type definitions.

Implements the Model Context Protocol (MCP) specification types for
tools, resources, prompts, and transport messages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Content blocks
# ---------------------------------------------------------------------------

@dataclass
class ContentBlock:
    """A single content block returned by a tool or resource."""
    type: str  # "text" | "image" | "resource"
    text: str = ""
    data: Optional[str] = None       # base64 for images
    mime_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"type": self.type}
        if self.type == "text":
            d["text"] = self.text
        elif self.type == "image":
            d["data"] = self.data
            d["mimeType"] = self.mime_type or "image/png"
        return d


# ---------------------------------------------------------------------------
# Tool result
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Result from a tool invocation."""
    content: List[ContentBlock] = field(default_factory=list)
    is_error: bool = False

    @classmethod
    def text(cls, message: str) -> "ToolResult":
        return cls(content=[ContentBlock(type="text", text=message)])

    @classmethod
    def error(cls, message: str) -> "ToolResult":
        return cls(content=[ContentBlock(type="text", text=message)], is_error=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": [c.to_dict() for c in self.content],
            "isError": self.is_error,
        }


# ---------------------------------------------------------------------------
# MCP Tool
# ---------------------------------------------------------------------------

@dataclass
class MCPTool:
    """Represents an MCP-compatible tool that can be called by AI clients."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler_fn: Callable[..., ToolResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def call(self, params: Dict[str, Any]) -> ToolResult:
        try:
            return self.handler_fn(**params)
        except TypeError as exc:
            return ToolResult.error(f"Invalid parameters for tool '{self.name}': {exc}")
        except Exception as exc:  # noqa: BLE001
            return ToolResult.error(f"Tool '{self.name}' raised an error: {exc}")


# ---------------------------------------------------------------------------
# MCP Resource
# ---------------------------------------------------------------------------

@dataclass
class MCPResource:
    """Represents an MCP resource that can be read by AI clients."""
    uri: str
    name: str
    description: str
    mime_type: str
    content_fn: Callable[..., str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }

    def read(self, **kwargs: Any) -> str:
        try:
            return self.content_fn(**kwargs)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Prompt argument
# ---------------------------------------------------------------------------

@dataclass
class PromptArgument:
    """A single argument accepted by an MCP prompt."""
    name: str
    description: str
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }


# ---------------------------------------------------------------------------
# MCP Prompt
# ---------------------------------------------------------------------------

@dataclass
class MCPPrompt:
    """Represents an MCP prompt template."""
    name: str
    description: str
    arguments: List[PromptArgument]
    template: str  # Jinja-style or plain string template

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [a.to_dict() for a in self.arguments],
        }

    def render(self, args: Dict[str, str]) -> Dict[str, Any]:
        """Render the prompt template with the supplied arguments."""
        rendered = self.template
        for key, value in args.items():
            rendered = rendered.replace(f"{{{key}}}", value)
        return {
            "description": self.description,
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": rendered},
                }
            ],
        }


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 messages
# ---------------------------------------------------------------------------

@dataclass
class MCPRequest:
    """An incoming JSON-RPC 2.0 request."""
    id: Any  # int | str | None
    method: str
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        return cls(
            id=data.get("id"),
            method=data["method"],
            params=data.get("params", {}),
        )


@dataclass
class MCPResponse:
    """An outgoing JSON-RPC 2.0 response."""
    id: Any
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        msg: Dict[str, Any] = {"jsonrpc": "2.0", "id": self.id}
        if self.error is not None:
            msg["error"] = self.error
        else:
            msg["result"] = self.result
        return msg

    @classmethod
    def ok(cls, id: Any, result: Any) -> "MCPResponse":
        return cls(id=id, result=result)

    @classmethod
    def err(cls, id: Any, code: int, message: str, data: Any = None) -> "MCPResponse":
        error: Dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return cls(id=id, error=error)


# ---------------------------------------------------------------------------
# MCP Error codes (per JSON-RPC 2.0 + MCP spec)
# ---------------------------------------------------------------------------

class MCPErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # MCP-specific
    TOOL_NOT_FOUND = -32000
    RESOURCE_NOT_FOUND = -32001
    PROMPT_NOT_FOUND = -32002
    TOOL_EXECUTION_ERROR = -32003

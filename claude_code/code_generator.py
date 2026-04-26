"""
SintraPrime module code generator using Claude.
Generate new SintraPrime modules on demand from natural language descriptions.
"""
import os
import json
from typing import Optional
import anthropic


class CodeGenerator:
    """
    Generate new SintraPrime modules on demand.
    Ask: 'Add a module to track all my UCC filings' and get production code.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-5"

    def _send(self, system: str, user: str, max_tokens: int = 8192) -> str:
        """Send a message to Claude and return the text response."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    async def generate_module(self, description: str) -> dict:
        """
        Generate a complete SintraPrime module from a natural language description.

        Returns:
            {
              'files': {'module.py': '...', 'tests/test_module.py': '...'},
              'description': '...',
              'integration_steps': [...]
            }
        """
        system = (
            "You are a senior Python engineer for SintraPrime, a legal AI platform. "
            "Generate complete, production-ready Python modules with: "
            "type hints, docstrings, error handling, logging, and comprehensive tests. "
            "Follow the SintraPrime pattern: async methods, Pydantic models for data, "
            "and integration with the existing RAG and API layers. "
            "Return your response as valid JSON with keys: 'files', 'description', 'integration_steps'."
        )
        user = (
            f"Generate a complete SintraPrime module for: {description}\n\n"
            "Return JSON with:\n"
            "- 'files': dict mapping filename to file content string\n"
            "- 'description': plain English description of what was built\n"
            "- 'integration_steps': list of steps to integrate into SintraPrime\n\n"
            "Include at minimum: the main module file and a test file."
        )
        result = self._send(system, user)

        # Attempt to parse JSON from response
        try:
            # Find JSON block in response
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                json_str = result[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: return raw response
        return {
            "files": {"generated_module.py": result},
            "description": description,
            "integration_steps": ["Review generated code", "Add to SintraPrime modules", "Run tests"],
        }

    async def generate_integration(self, service: str, task: str) -> str:
        """Generate integration code with any external service."""
        system = (
            "You are an expert integration developer for SintraPrime legal AI platform. "
            "Generate production-ready Python integration code for external services. "
            "Include authentication, error handling, rate limiting, and retry logic. "
            "Follow async patterns consistent with SintraPrime architecture."
        )
        user = (
            f"Generate a Python integration with {service} for this task: {task}\n\n"
            "Include: complete async client class, authentication setup, "
            "error handling, example usage, and environment variable configuration."
        )
        return self._send(system, user)

    async def generate_test_suite(self, module_code: str) -> str:
        """Auto-generate a comprehensive test suite for any module."""
        system = (
            "You are an expert Python test engineer specializing in legal technology systems. "
            "Generate comprehensive pytest test suites with: unit tests, integration tests, "
            "edge cases, error cases, and mocking of external dependencies. "
            "Target 90%+ code coverage. Use pytest-asyncio for async code."
        )
        user = (
            f"Generate a comprehensive pytest test suite for this Python module:\n\n"
            f"```python\n{module_code}\n```\n\n"
            "Include: happy path tests, error case tests, edge cases, "
            "mocked external dependencies, fixtures, and parametrized tests. "
            "Aim for 90%+ coverage."
        )
        return self._send(system, user)

    async def scaffold_fastapi_endpoint(self, resource: str, operations: list) -> str:
        """Generate a FastAPI router for a new SintraPrime resource."""
        ops_str = ", ".join(operations)
        system = (
            "You are a FastAPI expert building legal AI platform endpoints. "
            "Generate production FastAPI routers with: Pydantic models, dependency injection, "
            "proper HTTP status codes, error handling, and OpenAPI documentation."
        )
        user = (
            f"Generate a FastAPI router for the '{resource}' resource with operations: {ops_str}\n\n"
            "Include: Pydantic request/response models, CRUD endpoints, "
            "authentication dependency, error handling, and docstrings."
        )
        return self._send(system, user)

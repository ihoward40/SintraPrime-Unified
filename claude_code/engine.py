"""
Claude Code integration for SintraPrime.
Uses Claude's code analysis capabilities for:
1. Analyzing legal document code/scripts
2. Generating legal automation scripts
3. Code review for legal tech implementations
4. Auto-generating API integrations
5. Debugging SintraPrime modules
"""
import anthropic
import os
from typing import Optional


class ClaudeCodeEngine:
    """
    Claude Code as SintraPrime's programming intelligence.
    Powers: code generation, analysis, debugging, legal automation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-5"

    def _send(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Send a message to Claude and return the text response."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    async def analyze_code(self, code: str, language: str = "python") -> dict:
        """Analyze code for bugs, security issues, and improvements."""
        system = (
            "You are an expert code analyzer specializing in legal technology systems. "
            "Analyze the provided code and return a structured assessment covering: "
            "bugs, security vulnerabilities, performance issues, and improvement suggestions. "
            "Format your response as structured sections."
        )
        user = (
            f"Analyze this {language} code:\n\n```{language}\n{code}\n```\n\n"
            "Provide: 1) Bugs found, 2) Security issues, 3) Performance concerns, "
            "4) Improvement suggestions, 5) Overall quality score (1-10)."
        )
        result = self._send(system, user)
        return {
            "analysis": result,
            "language": language,
            "model": self.model,
        }

    async def generate_legal_script(self, description: str) -> dict:
        """Generate a legal automation script from a natural language description."""
        system = (
            "You are an expert legal technology developer specializing in Python. "
            "Generate production-ready Python scripts for legal automation tasks. "
            "Include error handling, logging, type hints, and docstrings. "
            "Scripts should be secure and compliant with legal data handling requirements."
        )
        user = (
            f"Generate a Python script for this legal automation task:\n\n{description}\n\n"
            "Include: imports, type hints, docstrings, error handling, example usage."
        )
        code = self._send(system, user)
        return {
            "code": code,
            "description": description,
            "language": "python",
            "model": self.model,
        }

    async def debug(self, code: str, error: str) -> dict:
        """Debug code given an error message."""
        system = (
            "You are an expert debugger for legal technology applications. "
            "Analyze the code and error, identify the root cause, and provide a fix."
        )
        user = (
            f"Debug this code:\n\n```python\n{code}\n```\n\n"
            f"Error message:\n{error}\n\n"
            "Provide: 1) Root cause, 2) Fixed code, 3) Explanation of the fix."
        )
        result = self._send(system, user)
        return {
            "debug_result": result,
            "original_error": error,
            "model": self.model,
        }

    async def generate_api_integration(self, api_docs: str, task: str) -> str:
        """Generate integration code for any API given its documentation."""
        system = (
            "You are an expert API integration developer for legal technology platforms. "
            "Generate clean, production-ready Python code to integrate with any API. "
            "Include authentication, error handling, rate limiting awareness, and retry logic."
        )
        user = (
            f"Generate API integration code for this task: {task}\n\n"
            f"API Documentation:\n{api_docs}\n\n"
            "Provide complete, runnable Python code with all necessary imports."
        )
        return self._send(system, user)

    async def review_legal_automation(self, code: str) -> dict:
        """Review legal automation code for correctness and compliance."""
        system = (
            "You are a senior legal technology engineer and compliance expert. "
            "Review legal automation code for correctness, security, data privacy compliance, "
            "and potential legal risks. Consider GDPR, CCPA, attorney-client privilege, and "
            "bar association ethics rules around legal technology."
        )
        user = (
            f"Review this legal automation code for compliance and correctness:\n\n"
            f"```python\n{code}\n```\n\n"
            "Assess: 1) Legal compliance risks, 2) Data privacy issues, "
            "3) Security concerns, 4) Correctness of legal logic, 5) Recommendations."
        )
        result = self._send(system, user)
        return {
            "review": result,
            "model": self.model,
            "review_type": "legal_automation",
        }

    async def explain_code(self, code: str) -> str:
        """Explain code in plain English for non-technical lawyers."""
        system = (
            "You are a technical writer who explains code to non-technical legal professionals. "
            "Use plain English, avoid jargon, and relate technical concepts to legal analogies. "
            "Be concise, clear, and focus on what the code does, not how it works internally."
        )
        user = (
            f"Explain what this code does to a non-technical attorney:\n\n"
            f"```\n{code}\n```\n\n"
            "Use bullet points and simple language. Start with a one-sentence summary."
        )
        return self._send(system, user)

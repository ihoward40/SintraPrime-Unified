"""
Claude Code integration for SintraPrime.
Provides AI-powered code generation, analysis, and legal automation.
"""

from .engine import ClaudeCodeEngine
from .code_generator import CodeGenerator
from .legal_code_assistant import LegalCodeAssistant

__all__ = ["ClaudeCodeEngine", "CodeGenerator", "LegalCodeAssistant"]

__version__ = "1.0.0"
__description__ = "Claude Code integration for SintraPrime legal AI platform"

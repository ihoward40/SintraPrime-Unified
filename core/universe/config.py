"""
SintraPrime UniVerse Configuration
"""

import os
from dataclasses import dataclass
from typing import Optional

# ============================================
# LLM Configuration
# ============================================

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
FALLBACK_MODEL = "claude-3-opus-20240229"

# API Keys (load from environment)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ============================================
# Agent Configuration
# ============================================

DEFAULT_AGENT_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout_seconds": 300,
}

# ============================================
# Swarm Configuration
# ============================================

MAX_AGENTS_PER_SWARM = 50
DEFAULT_SWARM_STRATEGY = "collaborative"  # collaborative, competitive, hierarchical, peer
AGENT_NEGOTIATION_TIMEOUT = 5  # seconds
TASK_QUEUE_MAX_SIZE = 10000

# ============================================
# Memory & Knowledge Configuration
# ============================================

KNOWLEDGE_BASE_VECTOR_DIM = 1536  # OpenAI embedding dimension
MAX_KNOWLEDGE_ENTRIES = 100000
SEMANTIC_SEARCH_TOP_K = 10
KNOWLEDGE_CACHE_SIZE = 1000
SKILL_MIN_CONFIDENCE_THRESHOLD = 0.75

# ============================================
# Execution & Rollback Configuration
# ============================================

EXECUTION_TIMEOUT_SECONDS = 300
MAX_ROLLBACK_ATTEMPTS = 3
TRACE_STORAGE_DAYS = 90  # Keep execution traces for 90 days

# ============================================
# Database Configuration
# ============================================

DATABASE_PATH = os.getenv("UNIVERSE_DB_PATH", "/agent/memory.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================
# Integration Configuration
# ============================================

ENABLED_INTEGRATIONS = {
    "slack": {"enabled": True, "max_retries": 3},
    "discord": {"enabled": True, "max_retries": 3},
    "telegram": {"enabled": True, "max_retries": 3},
    "github": {"enabled": True, "max_retries": 3},
    "email": {"enabled": True, "max_retries": 3},
}

# ============================================
# Dashboard Configuration
# ============================================

DASHBOARD_UPDATE_INTERVAL_MS = 1000  # Update dashboard every 1 second
DASHBOARD_MAX_LOG_ENTRIES = 1000

# ============================================
# Performance Thresholds
# ============================================

AGENT_PERFORMANCE_METRICS = {
    "min_success_rate_for_task": 0.70,
    "max_execution_time_ms": 300000,
    "auto_escalate_on_failures": 2,  # Escalate after 2 failures
}

# ============================================
# Feature Flags
# ============================================

FEATURES = {
    "auto_skill_generation": True,
    "auto_agent_scaling": True,
    "federated_learning": True,
    "rollback_support": True,
    "zero_trust_security": True,
    "explainable_ai": True,
    "vision_support": True,
}


@dataclass
class UniVerseConfig:
    """Complete UniVerse configuration."""

    model: str = DEFAULT_MODEL
    max_agents: int = MAX_AGENTS_PER_SWARM
    max_knowledge_entries: int = MAX_KNOWLEDGE_ENTRIES
    database_path: str = DATABASE_PATH
    log_level: str = LOG_LEVEL
    timeout_seconds: int = EXECUTION_TIMEOUT_SECONDS
    enable_rollback: bool = True
    enable_learning: bool = True
    enable_vision: bool = True

    def to_dict(self):
        """Convert config to dictionary."""
        return {
            "model": self.model,
            "max_agents": self.max_agents,
            "max_knowledge_entries": self.max_knowledge_entries,
            "database_path": self.database_path,
            "log_level": self.log_level,
            "timeout_seconds": self.timeout_seconds,
            "enable_rollback": self.enable_rollback,
            "enable_learning": self.enable_learning,
            "enable_vision": self.enable_vision,
        }

"""
SintraPrime-Unified — local_models package
Local/offline model integration: Ollama, DeepSeek, model routing,
quantization management, and offline mode.
"""

from local_models.ollama_client import OllamaClient
from local_models.deepseek_client import DeepSeekClient
from local_models.model_router import ModelRouter, TaskType, Provider
from local_models.quantization_manager import QuantizationManager
from local_models.offline_manager import OfflineMode

__all__ = [
    "OllamaClient",
    "DeepSeekClient",
    "ModelRouter",
    "TaskType",
    "Provider",
    "QuantizationManager",
    "OfflineMode",
]

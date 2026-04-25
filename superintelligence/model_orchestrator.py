"""
SintraPrime Model Orchestrator

Routes requests to the optimal AI model based on:
- Task complexity and type
- Privacy requirements
- Latency constraints
- Cost optimization
- User preferences

The orchestrator is the brain's routing layer.
"""

import asyncio
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Available model types in the orchestrator"""
    REASONING = "claude-3-5-sonnet"      # Deep thinking, planning, analysis
    SPEED = "gpt-4o-mini"                # Fast responses, real-time
    CODE = "claude-code"                  # Code generation, execution, testing
    VISION = "claude-3-5-vision"          # Image/video analysis
    LOCAL = "hermes-3-70b-local"          # Private reasoning (on-device)
    EMBEDDING = "nomic-embed-text"        # Semantic search, similarity
    VOICE = "whisper-realtime"            # Audio input
    AUDIO = "elevenlabs-tts"              # Audio output


class TaskComplexity(Enum):
    """Task complexity classification"""
    SIMPLE = 1        # FAQ, factual lookup → use SPEED
    MODERATE = 2      # Analysis, planning → route based on type
    COMPLEX = 3       # Research, design, debugging → use REASONING
    CRITICAL = 4      # High-stakes, security → use REASONING + LOCAL validation


class PrivacyLevel(Enum):
    """Privacy sensitivity level"""
    PUBLIC = 1        # Public information, no restrictions
    INTERNAL = 2      # Organization data, cloud OK
    SENSITIVE = 3     # PII, code, secrets → use LOCAL or ask
    CRITICAL = 4      # Medical, financial, legal → LOCAL only


@dataclass
class RoutingContext:
    """Context for routing decisions"""
    task_type: str                       # "research", "coding", "planning", etc.
    complexity: TaskComplexity
    privacy_level: PrivacyLevel
    latency_requirement: float           # seconds (0.5, 5, 60)
    budget_constraint: Optional[float]   # max cost in cents
    user_preference: Optional[ModelType] # override if specified
    requires_tool_use: bool              # needs function calling
    requires_vision: bool                # needs image analysis
    requires_audio: bool                 # needs voice I/O
    context_length: int                  # tokens of context needed
    preferred_languages: List[str]       # ['en', 'es', 'fr']


@dataclass
class RoutingDecision:
    """Decision made by orchestrator"""
    primary_model: ModelType
    fallback_models: List[ModelType]
    reasoning: str                       # Why this model was chosen
    estimated_cost: float                # cents
    estimated_latency: float             # seconds
    confidence: float                    # 0.0-1.0
    temperature: float                   # 0.0-2.0
    max_tokens: int


class ModelOrchestrator:
    """
    Central routing intelligence for SintraPrime.
    
    Makes optimal model selection decisions to maximize:
    - Accuracy for the task type
    - Speed relative to importance
    - Cost efficiency
    - Privacy compliance
    - User satisfaction
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.model_capabilities = self._init_model_capabilities()
        self.performance_history: Dict[str, List[Dict]] = {}
        self.cost_tracking: Dict[ModelType, float] = {}
        self.latency_tracking: Dict[ModelType, List[float]] = {}
        
    def _init_model_capabilities(self) -> Dict[ModelType, Dict[str, Any]]:
        """Initialize known capabilities of each model"""
        return {
            ModelType.REASONING: {
                "context_window": 200_000,
                "tool_use": True,
                "vision": False,
                "latency_p50": 3.0,
                "cost_per_1m_tokens": 3.0,  # $3 per million tokens
                "strengths": ["deep_thinking", "planning", "analysis", "research"],
                "best_for": ["complex_problems", "long_form", "reasoning"],
            },
            ModelType.SPEED: {
                "context_window": 128_000,
                "tool_use": True,
                "vision": False,
                "latency_p50": 0.3,
                "cost_per_1m_tokens": 0.05,
                "strengths": ["speed", "cost_efficient", "real_time"],
                "best_for": ["qa", "routing", "summaries", "real_time"],
            },
            ModelType.CODE: {
                "context_window": 200_000,
                "tool_use": True,
                "vision": False,
                "latency_p50": 2.0,
                "cost_per_1m_tokens": 3.0,
                "strengths": ["code_generation", "execution", "debugging"],
                "best_for": ["coding", "testing", "refactoring", "tooling"],
            },
            ModelType.VISION: {
                "context_window": 128_000,
                "tool_use": True,
                "vision": True,
                "latency_p50": 2.0,
                "cost_per_1m_tokens": 1.5,
                "strengths": ["image_analysis", "video_understanding", "ocr"],
                "best_for": ["vision", "document_analysis", "ui_automation"],
            },
            ModelType.LOCAL: {
                "context_window": 32_000,
                "tool_use": True,
                "vision": False,
                "latency_p50": 5.0,
                "cost_per_1m_tokens": 0.0,
                "strengths": ["privacy", "offline", "speed_offline"],
                "best_for": ["sensitive", "offline", "private_reasoning"],
            },
            ModelType.EMBEDDING: {
                "context_window": 8_000,
                "tool_use": False,
                "vision": False,
                "latency_p50": 0.05,
                "cost_per_1m_tokens": 0.02,
                "strengths": ["semantic_search", "similarity", "clustering"],
                "best_for": ["memory_retrieval", "similarity_search"],
            },
        }
    
    async def route(self, context: RoutingContext) -> RoutingDecision:
        """
        Main routing decision.
        
        Returns optimal model choice + fallbacks + reasoning.
        """
        logger.info(f"Routing task: {context.task_type}, complexity: {context.complexity}")
        
        # Step 1: Apply hard constraints (must rules)
        candidates = await self._apply_constraints(context)
        
        if not candidates:
            logger.warning(f"No models satisfy constraints for {context.task_type}")
            candidates = [ModelType.REASONING]  # Fallback to most capable
        
        # Step 2: Score candidates
        scores = await self._score_candidates(candidates, context)
        
        # Step 3: Select primary and fallbacks
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = ranked[0][0]
        fallbacks = [model for model, score in ranked[1:3]]
        
        # Step 4: Build decision
        decision = RoutingDecision(
            primary_model=primary,
            fallback_models=fallbacks,
            reasoning=await self._explain_routing(primary, context),
            estimated_cost=await self._estimate_cost(primary, context),
            estimated_latency=await self._estimate_latency(primary, context),
            confidence=scores[primary],
            temperature=self._select_temperature(context),
            max_tokens=self._select_max_tokens(context),
        )
        
        logger.info(f"Routing decision: {primary.value}, confidence: {decision.confidence:.2%}")
        return decision
    
    async def _apply_constraints(self, context: RoutingContext) -> List[ModelType]:
        """Filter to models that satisfy hard requirements"""
        candidates = []
        
        for model in ModelType:
            caps = self.model_capabilities[model]
            
            # Check privacy constraint
            if context.privacy_level == PrivacyLevel.CRITICAL:
                if model != ModelType.LOCAL:
                    continue  # Only local for critical data
            
            # Check vision requirement
            if context.requires_vision and not caps["vision"]:
                continue
            
            # Check tool use requirement
            if context.requires_tool_use and not caps["tool_use"]:
                continue
            
            # Check context length
            if context.context_length > caps["context_window"]:
                continue
            
            # Check latency requirement
            if context.latency_requirement < (caps["latency_p50"] * 2):
                # Model too slow for latency requirement
                if model != ModelType.SPEED:
                    continue
            
            candidates.append(model)
        
        return candidates or [ModelType.REASONING]
    
    async def _score_candidates(
        self,
        candidates: List[ModelType],
        context: RoutingContext
    ) -> Dict[ModelType, float]:
        """
        Score each candidate model on:
        - Task fit (strengths match task)
        - Cost efficiency
        - Latency fit
        - Reliability history
        - User preference
        """
        scores = {}
        
        for model in candidates:
            score = 0.5  # Base score
            caps = self.model_capabilities[model]
            
            # Task fit (30% weight)
            if context.task_type in caps["best_for"]:
                score += 0.15
            if any(s in context.task_type for s in caps["strengths"]):
                score += 0.10
            
            # Cost efficiency (20% weight)
            if context.budget_constraint:
                model_cost = caps["cost_per_1m_tokens"]
                if model_cost <= context.budget_constraint * 0.1:
                    score += 0.20
                else:
                    score -= 0.10
            else:
                # No budget constraint, prefer cheaper models
                if model in [ModelType.SPEED, ModelType.EMBEDDING]:
                    score += 0.10
            
            # Latency fit (20% weight)
            if context.latency_requirement > 10:
                if model == ModelType.REASONING:
                    score += 0.10
            elif context.latency_requirement < 1:
                if model == ModelType.SPEED:
                    score += 0.20
            
            # User preference (10% weight)
            if context.user_preference == model:
                score += 0.10
            
            # Reliability (20% weight)
            reliability = await self._get_reliability_score(model)
            score += reliability * 0.20
            
            scores[model] = max(0.0, min(1.0, score))
        
        return scores
    
    async def _get_reliability_score(self, model: ModelType) -> float:
        """Get historical reliability from performance tracking"""
        if model not in self.performance_history:
            return 0.9  # New models start at 0.9
        
        history = self.performance_history[model]
        if not history:
            return 0.9
        
        success_count = sum(1 for h in history[-100:] if h.get("success", False))
        return success_count / min(100, len(history))
    
    async def _estimate_cost(self, model: ModelType, context: RoutingContext) -> float:
        """Estimate API cost in cents"""
        caps = self.model_capabilities[model]
        cost_per_1m = caps["cost_per_1m_tokens"]
        
        # Estimate tokens: rough heuristic
        estimated_tokens = context.context_length + 500  # input + output
        
        cost_cents = (estimated_tokens / 1_000_000) * cost_per_1m * 100
        return round(cost_cents, 2)
    
    async def _estimate_latency(self, model: ModelType, context: RoutingContext) -> float:
        """Estimate response latency in seconds"""
        caps = self.model_capabilities[model]
        p50 = caps["latency_p50"]
        
        # Adjust for context size
        # Larger context = slower response
        context_factor = 1.0 + (context.context_length / caps["context_window"]) * 0.5
        
        return p50 * context_factor
    
    async def _explain_routing(self, model: ModelType, context: RoutingContext) -> str:
        """Generate human-readable explanation of routing decision"""
        caps = self.model_capabilities[model]
        reasons = []
        
        if context.task_type in caps["best_for"]:
            reasons.append(f"Optimized for {context.task_type}")
        
        if context.privacy_level == PrivacyLevel.CRITICAL and model == ModelType.LOCAL:
            reasons.append("Privacy requirement met (local processing)")
        
        if context.latency_requirement < 1 and model == ModelType.SPEED:
            reasons.append("Low latency requirement")
        
        if context.complexity == TaskComplexity.CRITICAL and model == ModelType.REASONING:
            reasons.append("Complex task requires deep reasoning")
        
        return " | ".join(reasons) if reasons else "Best overall fit"
    
    def _select_temperature(self, context: RoutingContext) -> float:
        """Select temperature based on task type"""
        if context.task_type in ["factual", "retrieval", "coding"]:
            return 0.0  # Deterministic
        elif context.complexity == TaskComplexity.CRITICAL:
            return 0.5  # Conservative
        else:
            return 1.0  # Balanced
    
    def _select_max_tokens(self, context: RoutingContext) -> int:
        """Select max output tokens based on task"""
        if context.task_type == "coding":
            return 4_000
        elif context.complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]:
            return 2_000
        else:
            return 1_000
    
    async def record_execution(
        self,
        model: ModelType,
        success: bool,
        latency: float,
        tokens: int,
        quality_score: Optional[float] = None
    ):
        """Record execution for continuous improvement"""
        if model not in self.performance_history:
            self.performance_history[model] = []
        
        self.performance_history[model].append({
            "timestamp": datetime.now(),
            "success": success,
            "latency": latency,
            "tokens": tokens,
            "quality_score": quality_score,
        })
        
        # Track latency
        if model not in self.latency_tracking:
            self.latency_tracking[model] = []
        self.latency_tracking[model].append(latency)
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or defaults"""
        # TODO: Load from config file
        return {}


# Example usage
async def example():
    """Example of using the orchestrator"""
    orchestrator = ModelOrchestrator()
    
    # Simple question: route to fast model
    context = RoutingContext(
        task_type="qa",
        complexity=TaskComplexity.SIMPLE,
        privacy_level=PrivacyLevel.PUBLIC,
        latency_requirement=0.5,
        budget_constraint=1.0,
        user_preference=None,
        requires_tool_use=False,
        requires_vision=False,
        requires_audio=False,
        context_length=500,
        preferred_languages=["en"],
    )
    decision = await orchestrator.route(context)
    print(f"Simple question → {decision.primary_model.value}")
    
    # Complex research: route to reasoning model
    context = RoutingContext(
        task_type="research",
        complexity=TaskComplexity.COMPLEX,
        privacy_level=PrivacyLevel.PUBLIC,
        latency_requirement=60.0,
        budget_constraint=None,
        user_preference=None,
        requires_tool_use=True,
        requires_vision=False,
        requires_audio=False,
        context_length=50_000,
        preferred_languages=["en"],
    )
    decision = await orchestrator.route(context)
    print(f"Complex research → {decision.primary_model.value}")
    
    # Sensitive code: route to local + validation
    context = RoutingContext(
        task_type="coding",
        complexity=TaskComplexity.CRITICAL,
        privacy_level=PrivacyLevel.SENSITIVE,
        latency_requirement=5.0,
        budget_constraint=None,
        user_preference=None,
        requires_tool_use=True,
        requires_vision=False,
        requires_audio=False,
        context_length=10_000,
        preferred_languages=["en"],
    )
    decision = await orchestrator.route(context)
    print(f"Sensitive code → {decision.primary_model.value} + {decision.fallback_models}")


if __name__ == "__main__":
    asyncio.run(example())

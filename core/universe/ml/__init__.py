"""
ML Intelligence Layer for SintraPrime UniVerse
Enables agents to learn from experience and optimize their behavior over time
"""

from .experience_buffer import ExperienceBuffer, Experience, PriorityQueue
from .policy_optimizer import PPOOptimizer, PolicyMetrics, Actor, Critic
from .behavior_model import BehaviorModel, BehaviorPrediction
from .reward_model import RewardModel, RewardFeedback, RewardType
from .ml_trainer import MLTrainer, TrainingConfig, TrainingStatus, TrainingMetrics
from .continuous_optimizer import (
    ContinuousOptimizer,
    AdaptiveExploration,
    OnlineLearner,
    MetaLearner,
    TransferLearning,
    BanditArm,
    ABTestResult
)

__version__ = "1.0.0"

__all__ = [
    # Experience Buffer
    "ExperienceBuffer",
    "Experience",
    "PriorityQueue",
    
    # Policy Optimization
    "PPOOptimizer",
    "PolicyMetrics",
    "Actor",
    "Critic",
    
    # Behavior Prediction
    "BehaviorModel",
    "BehaviorPrediction",
    
    # Reward Learning
    "RewardModel",
    "RewardFeedback",
    "RewardType",
    
    # Training
    "MLTrainer",
    "TrainingConfig",
    "TrainingStatus",
    "TrainingMetrics",
    
    # Continuous Optimization
    "ContinuousOptimizer",
    "AdaptiveExploration",
    "OnlineLearner",
    "MetaLearner",
    "TransferLearning",
    "BanditArm",
    "ABTestResult",
]

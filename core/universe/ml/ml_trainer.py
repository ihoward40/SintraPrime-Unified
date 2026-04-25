"""
ML Trainer - Training orchestrator for self-learning agents
Manages experiments, model versioning, checkpoint management, and distributed training
"""

import logging
import json
import os
import time
import hashlib
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
import pickle
import threading
from enum import Enum

try:
    from .experience_buffer import ExperienceBuffer, Experience
    from .policy_optimizer import PPOOptimizer, PolicyMetrics
    from .behavior_model import BehaviorModel
    from .reward_model import RewardModel
except ImportError:
    from experience_buffer import ExperienceBuffer, Experience
    from policy_optimizer import PPOOptimizer, PolicyMetrics
    from behavior_model import BehaviorModel
    from reward_model import RewardModel

logger = logging.getLogger(__name__)


class TrainingStatus(Enum):
    """Training job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class TrainingConfig:
    """Configuration for training job"""
    agent_id: str
    state_dim: int
    action_dim: int
    max_episodes: int = 1000
    max_steps_per_episode: int = 500
    batch_size: int = 64
    learning_rate: float = 3e-4
    gamma: float = 0.99
    lambda_: float = 0.95
    clip_ratio: float = 0.2
    use_prioritized_replay: bool = True
    use_behavior_model: bool = True
    use_reward_model: bool = True
    checkpoint_interval: int = 100
    eval_interval: int = 50
    distributed: bool = False
    num_workers: int = 1
    seed: int = 42


@dataclass
class TrainingMetrics:
    """Training metrics"""
    episode: int = 0
    step: int = 0
    total_steps: int = 0
    cumulative_reward: float = 0.0
    episode_rewards: List[float] = field(default_factory=list)
    policy_loss: float = 0.0
    value_loss: float = 0.0
    entropy: float = 0.0
    policy_divergence: float = 0.0
    buffer_size: int = 0
    training_time: float = 0.0
    learning_rate: float = 0.0
    wall_clock_time: float = 0.0


@dataclass
class ModelCheckpoint:
    """Model checkpoint metadata"""
    checkpoint_id: str
    agent_id: str
    episode: int
    total_steps: int
    cumulative_reward: float
    policy_loss: float
    timestamp: str
    path: str
    metrics: Dict[str, float] = field(default_factory=dict)


class MLTrainer:
    """
    Training orchestrator managing the entire training pipeline
    """
    
    def __init__(
        self,
        config: TrainingConfig,
        model_dir: str = "./models",
        checkpoint_dir: str = "./checkpoints"
    ):
        self.config = config
        self.model_dir = Path(model_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        
        # Create directories
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Components
        self.experience_buffer = ExperienceBuffer(
            max_size=100000,
            compress=True,
            enable_dedup=True,
            enable_prioritization=config.use_prioritized_replay
        )
        
        self.policy_optimizer = PPOOptimizer(
            state_dim=config.state_dim,
            action_dim=config.action_dim,
            learning_rate=config.learning_rate,
            gamma=config.gamma,
            lambda_=config.lambda_,
            clip_ratio=config.clip_ratio,
            batch_size=config.batch_size
        )
        
        self.behavior_model = BehaviorModel(
            state_dim=config.state_dim,
            action_dim=config.action_dim
        ) if config.use_behavior_model else None
        
        self.reward_model = RewardModel(
            state_dim=config.state_dim,
            action_dim=config.action_dim
        ) if config.use_reward_model else None
        
        # Training state
        self.metrics = TrainingMetrics()
        self.checkpoints: Dict[str, ModelCheckpoint] = {}
        self.training_history = []
        self.training_status = TrainingStatus.PENDING
        self.start_time = None
        self.episode_rewards = []
        
        # Distributed training
        self.distributed = config.distributed
        self.num_workers = config.num_workers
        self.worker_threads = []
        self.training_lock = threading.Lock()
        
        logger.info(f"MLTrainer initialized for agent {config.agent_id}")
    
    def add_experience(self, exp: Experience):
        """Add experience to replay buffer"""
        self.experience_buffer.add(exp)
    
    def collect_batch(self, batch_size: int) -> Tuple[List[Experience], Any, Any]:
        """Collect batch from experience buffer"""
        experiences, indices, weights = self.experience_buffer.sample(batch_size)
        return experiences, indices, weights
    
    def train_on_batch(
        self,
        experiences: List[Experience],
        indices: np.ndarray,
        weights: np.ndarray
    ) -> Dict[str, float]:
        """Train policy on batch"""
        if len(experiences) == 0:
            return {}
        
        states = [exp.state for exp in experiences]
        actions = [exp.action for exp in experiences]
        rewards = [exp.reward for exp in experiences]
        next_states = [exp.next_state for exp in experiences]
        dones = [exp.done for exp in experiences]
        
        # Update policy
        metrics = self.policy_optimizer.update(states, actions, rewards, next_states, dones)
        
        # Compute TD errors for priority update
        td_errors = np.array([
            abs(rewards[i] + self.config.gamma * self.policy_optimizer.critic.forward(next_states[i]) 
                - self.policy_optimizer.critic.forward(states[i]))
            for i in range(len(experiences))
        ])
        
        # Update priorities
        self.experience_buffer.update_priorities(indices, td_errors)
        
        return {
            'policy_loss': metrics.policy_loss,
            'value_loss': metrics.value_loss,
            'entropy': metrics.entropy,
            'policy_divergence': metrics.policy_divergence
        }
    
    def train_episode(
        self,
        env_step_fn: callable,
        max_steps: int = None
    ) -> float:
        """Train for one episode"""
        max_steps = max_steps or self.config.max_steps_per_episode
        
        episode_reward = 0.0
        episode_steps = 0
        
        for step in range(max_steps):
            # Get current state and available actions
            state, available_actions = env_step_fn('get_state')
            
            # Select action
            action, action_prob = self.policy_optimizer.select_action(state)
            
            # Behavior prediction
            if self.behavior_model:
                prediction = self.behavior_model.predict(self.config.agent_id, state)
            
            # Step environment
            next_state, reward, done, info = env_step_fn('step', action)
            
            # Detect reward hacking
            if self.reward_model:
                is_hacking, suspicion = self.reward_model.detect_reward_hacking(
                    state, action, reward
                )
                if is_hacking:
                    logger.warning(f"Potential reward hacking detected: {suspicion}")
                    reward = reward * 0.5  # Penalize
            
            # Add to buffer
            exp = Experience(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
                timestamp=time.time(),
                agent_id=self.config.agent_id
            )
            self.add_experience(exp)
            
            episode_reward += reward
            episode_steps += 1
            self.metrics.step += 1
            self.metrics.total_steps += 1
            
            if done:
                break
        
        self.metrics.episode += 1
        self.episode_rewards.append(episode_reward)
        
        return episode_reward
    
    def train(
        self,
        env_step_fn: callable,
        validate_fn: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Main training loop
        
        Args:
            env_step_fn: Function to interact with environment
            validate_fn: Optional validation function
        """
        self.training_status = TrainingStatus.RUNNING
        self.start_time = time.time()
        
        logger.info(f"Starting training for agent {self.config.agent_id}")
        logger.info(f"Episodes: {self.config.max_episodes}, Steps/episode: {self.config.max_steps_per_episode}")
        
        try:
            for episode in range(self.config.max_episodes):
                # Train episode
                episode_reward = self.train_episode(env_step_fn)
                
                # Update metrics
                self.metrics.episode = episode + 1
                self.metrics.cumulative_reward += episode_reward
                self.metrics.learning_rate = self.config.learning_rate
                self.metrics.wall_clock_time = time.time() - self.start_time
                self.metrics.buffer_size = len(self.experience_buffer)
                
                # Training every batch_size steps
                if len(self.experience_buffer) >= self.config.batch_size:
                    experiences, indices, weights = self.collect_batch(self.config.batch_size)
                    batch_metrics = self.train_on_batch(experiences, indices, weights)
                    
                    self.metrics.policy_loss = batch_metrics.get('policy_loss', 0)
                    self.metrics.value_loss = batch_metrics.get('value_loss', 0)
                    self.metrics.entropy = batch_metrics.get('entropy', 0)
                    self.metrics.policy_divergence = batch_metrics.get('policy_divergence', 0)
                
                # Validation
                if episode % self.config.eval_interval == 0 and validate_fn:
                    val_reward = validate_fn()
                    logger.info(f"Episode {episode}: validation reward = {val_reward:.4f}")
                
                # Checkpoint
                if episode % self.config.checkpoint_interval == 0:
                    self.save_checkpoint(episode)
                
                # Log progress
                if episode % 10 == 0:
                    avg_reward = np.mean(self.episode_rewards[-10:])
                    logger.info(
                        f"Episode {episode}: avg_reward={avg_reward:.4f}, "
                        f"buffer_size={len(self.experience_buffer)}, "
                        f"loss={self.metrics.policy_loss:.6f}"
                    )
                
                # Check convergence
                if self.policy_optimizer.has_converged():
                    logger.info("Policy has converged!")
                    break
            
            self.training_status = TrainingStatus.COMPLETED
            logger.info(f"Training completed in {self.metrics.wall_clock_time:.2f}s")
        
        except Exception as e:
            self.training_status = TrainingStatus.FAILED
            logger.error(f"Training failed: {e}")
            raise
        
        return self.get_training_summary()
    
    def save_checkpoint(self, episode: int):
        """Save model checkpoint"""
        checkpoint_id = f"{self.config.agent_id}_{episode}_{int(time.time())}"
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"
        
        checkpoint = ModelCheckpoint(
            checkpoint_id=checkpoint_id,
            agent_id=self.config.agent_id,
            episode=episode,
            total_steps=self.metrics.total_steps,
            cumulative_reward=self.metrics.cumulative_reward,
            policy_loss=self.metrics.policy_loss,
            timestamp=datetime.now().isoformat(),
            path=str(checkpoint_path),
            metrics=asdict(self.metrics)
        )
        
        # Save state
        state = {
            'config': asdict(self.config),
            'checkpoint': asdict(checkpoint),
            'policy_optimizer': {
                'actor_weights': self.policy_optimizer.actor.weights,
                'critic_weights': self.policy_optimizer.critic.weights
            },
            'behavior_model': self.behavior_model.get_statistics() if self.behavior_model else None,
            'reward_model': self.reward_model.get_statistics() if self.reward_model else None
        }
        
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(state, f)
        
        self.checkpoints[checkpoint_id] = checkpoint
        logger.info(f"Checkpoint saved: {checkpoint_id}")
    
    def load_checkpoint(self, checkpoint_id: str):
        """Load model checkpoint"""
        checkpoint = self.checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        with open(checkpoint.path, 'rb') as f:
            state = pickle.load(f)
        
        # Restore state
        self.policy_optimizer.actor.weights = state['policy_optimizer']['actor_weights']
        self.policy_optimizer.critic.weights = state['policy_optimizer']['critic_weights']
        
        logger.info(f"Checkpoint loaded: {checkpoint_id}")
    
    def get_best_checkpoint(self) -> Optional[ModelCheckpoint]:
        """Get best checkpoint by reward"""
        if not self.checkpoints:
            return None
        
        return max(self.checkpoints.values(), key=lambda x: x.cumulative_reward)
    
    def get_training_summary(self) -> Dict[str, Any]:
        """Get training summary"""
        total_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            'agent_id': self.config.agent_id,
            'status': self.training_status.value,
            'total_episodes': self.metrics.episode,
            'total_steps': self.metrics.total_steps,
            'total_reward': self.metrics.cumulative_reward,
            'avg_episode_reward': self.metrics.cumulative_reward / self.metrics.episode if self.metrics.episode > 0 else 0,
            'final_policy_loss': self.metrics.policy_loss,
            'final_value_loss': self.metrics.value_loss,
            'entropy': self.metrics.entropy,
            'policy_divergence': self.metrics.policy_divergence,
            'buffer_size': len(self.experience_buffer),
            'total_time': total_time,
            'num_checkpoints': len(self.checkpoints),
            'best_checkpoint': self.get_best_checkpoint().checkpoint_id if self.get_best_checkpoint() else None
        }
    
    def export_model(self, export_path: str):
        """Export trained model"""
        model_state = {
            'config': asdict(self.config),
            'actor_weights': self.policy_optimizer.actor.weights,
            'critic_weights': self.policy_optimizer.critic.weights,
            'training_summary': self.get_training_summary()
        }
        
        with open(export_path, 'wb') as f:
            pickle.dump(model_state, f)
        
        logger.info(f"Model exported to {export_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            'agent_id': self.config.agent_id,
            'training_config': asdict(self.config),
            'training_metrics': asdict(self.metrics),
            'experience_buffer': self.experience_buffer.get_statistics(),
            'policy_optimizer': {
                'metrics': asdict(self.policy_optimizer.get_metrics())
            },
            'checkpoints': {
                cid: asdict(cp) for cid, cp in self.checkpoints.items()
            },
            'training_summary': self.get_training_summary()
        }


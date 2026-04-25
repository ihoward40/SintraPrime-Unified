"""
Reward Model for learning reward functions from feedback
Supports custom reward shaping, multi-objective optimization, and inverse reward learning
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import pickle

logger = logging.getLogger(__name__)


class RewardType(Enum):
    """Types of rewards"""
    SPARSE = "sparse"
    DENSE = "dense"
    SHAPED = "shaped"
    INTRINSIC = "intrinsic"
    COMPOSITE = "composite"


@dataclass
class RewardFeedback:
    """Reward feedback from environment or human"""
    agent_id: str
    action: Any
    state: np.ndarray
    next_state: np.ndarray
    reward: float
    feedback_type: str  # 'automatic', 'human', 'inferred'
    confidence: float = 1.0
    metadata: Dict = None


class RewardShaper:
    """Reward shaping for better learning"""
    
    def __init__(self, state_dim: int):
        self.state_dim = state_dim
        self.potential_weights = np.random.randn(state_dim) * 0.01
        self.potential_bias = 0.0
    
    def compute_potential(self, state: np.ndarray) -> float:
        """Compute potential-based shaping"""
        state_flat = state.flatten() if state.ndim > 1 else state
        potential = np.dot(state_flat, self.potential_weights) + self.potential_bias
        return float(potential)
    
    def shape_reward(
        self,
        reward: float,
        state: np.ndarray,
        next_state: np.ndarray,
        gamma: float = 0.99
    ) -> float:
        """Apply potential-based reward shaping"""
        current_potential = self.compute_potential(state)
        next_potential = self.compute_potential(next_state)
        
        shaped_reward = reward + gamma * next_potential - current_potential
        return float(shaped_reward)
    
    def update_potential(self, gradients: np.ndarray, learning_rate: float = 0.01):
        """Update potential function"""
        self.potential_weights += learning_rate * gradients
    
    def save(self, path: str):
        """Save shaper state"""
        state = {
            'potential_weights': self.potential_weights,
            'potential_bias': self.potential_bias
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)


class RewardModel:
    """
    Learn reward function from feedback
    Supports multiple objectives and inverse reward learning
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        num_objectives: int = 1,
        learning_rate: float = 0.01,
        reward_range: Tuple[float, float] = (-1.0, 1.0)
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.num_objectives = num_objectives
        self.learning_rate = learning_rate
        self.reward_range = reward_range
        
        # Reward function weights
        self.reward_weights = np.random.randn(state_dim + action_dim, num_objectives) * 0.01
        self.reward_bias = np.zeros(num_objectives)
        
        # Reward shaper
        self.shaper = RewardShaper(state_dim)
        
        # Objective weights for multi-objective optimization
        self.objective_weights = np.ones(num_objectives) / num_objectives
        
        # Inverse reward learning
        self.inverse_learner_weights = np.random.randn(state_dim + action_dim) * 0.01
        
        # Statistics
        self.feedbacks_received = 0
        self.total_reward = 0.0
        self.reward_history = []
        
        # Calibration
        self.reward_calibration = {'min': 0.0, 'max': 1.0, 'mean': 0.0, 'std': 1.0}
    
    def compute_reward(
        self,
        state: np.ndarray,
        action: Any,
        objective_idx: int = 0
    ) -> float:
        """
        Compute reward for state-action pair
        Uses learned reward function
        """
        state_flat = state.flatten() if state.ndim > 1 else state
        
        # Encode action
        if isinstance(action, (int, np.integer)):
            action_encoding = np.zeros(self.action_dim)
            action_encoding[min(action, self.action_dim - 1)] = 1.0
        else:
            action_encoding = np.array(action).flatten()[:self.action_dim]
            if len(action_encoding) < self.action_dim:
                action_encoding = np.pad(action_encoding, (0, self.action_dim - len(action_encoding)))
        
        # Combine state and action
        features = np.concatenate([state_flat, action_encoding])
        
        # Compute raw reward
        raw_reward = np.dot(features, self.reward_weights[:, objective_idx]) + self.reward_bias[objective_idx]
        
        # Clip to range
        reward = np.clip(raw_reward, self.reward_range[0], self.reward_range[1])
        
        return float(reward)
    
    def compute_composite_reward(
        self,
        state: np.ndarray,
        action: Any
    ) -> float:
        """Compute weighted sum of multi-objective rewards"""
        rewards = []
        for i in range(self.num_objectives):
            reward = self.compute_reward(state, action, i)
            rewards.append(reward * self.objective_weights[i])
        
        return float(np.sum(rewards))
    
    def process_feedback(self, feedback: RewardFeedback) -> Dict[str, float]:
        """
        Process feedback and update reward model
        Returns: metrics dict
        """
        self.feedbacks_received += 1
        
        # Apply reward shaping
        shaped_reward = self.shaper.shape_reward(
            feedback.reward,
            feedback.state,
            feedback.next_state
        )
        
        # Update statistics
        self.total_reward += shaped_reward
        self.reward_history.append(shaped_reward)
        if len(self.reward_history) > 10000:
            self.reward_history = self.reward_history[-10000:]
        
        # Update calibration
        self._update_calibration()
        
        # Compute prediction error
        predicted = self.compute_composite_reward(feedback.state, feedback.action)
        error = float(shaped_reward - predicted)
        
        # Update weights (simple gradient descent)
        if feedback.feedback_type == 'human':
            learning_rate = self.learning_rate * feedback.confidence
        else:
            learning_rate = self.learning_rate
        
        self._update_weights(feedback.state, feedback.action, shaped_reward, learning_rate)
        
        metrics = {
            'predicted_reward': predicted,
            'actual_reward': shaped_reward,
            'error': error,
            'feedback_count': self.feedbacks_received,
            'mean_reward': self.total_reward / self.feedbacks_received
        }
        
        return metrics
    
    def _update_weights(
        self,
        state: np.ndarray,
        action: Any,
        target_reward: float,
        learning_rate: float
    ):
        """Update reward function weights"""
        state_flat = state.flatten() if state.ndim > 1 else state
        
        # Encode action
        if isinstance(action, (int, np.integer)):
            action_encoding = np.zeros(self.action_dim)
            action_encoding[min(action, self.action_dim - 1)] = 1.0
        else:
            action_encoding = np.array(action).flatten()[:self.action_dim]
            if len(action_encoding) < self.action_dim:
                action_encoding = np.pad(action_encoding, (0, self.action_dim - len(action_encoding)))
        
        features = np.concatenate([state_flat, action_encoding])
        
        # Compute current prediction
        for i in range(self.num_objectives):
            current = np.dot(features, self.reward_weights[:, i]) + self.reward_bias[i]
            error = target_reward - current
            
            # Update weights
            gradient = -error * features
            self.reward_weights[:, i] += learning_rate * gradient
            self.reward_bias[i] += learning_rate * error
    
    def _update_calibration(self):
        """Update reward calibration statistics"""
        if len(self.reward_history) > 10:
            rewards = np.array(self.reward_history[-100:])
            self.reward_calibration = {
                'min': float(np.min(rewards)),
                'max': float(np.max(rewards)),
                'mean': float(np.mean(rewards)),
                'std': float(np.std(rewards))
            }
    
    def set_objective_weights(self, weights: np.ndarray):
        """Set weights for multi-objective optimization"""
        weights = np.array(weights)
        self.objective_weights = weights / np.sum(weights)
    
    def inverse_reward_learning(
        self,
        trajectories: List[Tuple[List[np.ndarray], List[int], float]],
        iterations: int = 100
    ) -> float:
        """
        Learn reward function from demonstrations
        trajectories: list of (states, actions, total_reward) tuples
        """
        for iteration in range(iterations):
            total_loss = 0
            
            for states, actions, total_reward in trajectories:
                # Compute trajectory reward
                trajectory_reward = sum(
                    self.compute_reward(state, action)
                    for state, action in zip(states, actions)
                )
                
                # TD target
                target = total_reward
                error = target - trajectory_reward
                
                # Update inverse learner
                state_action_features = []
                for state, action in zip(states, actions):
                    state_flat = state.flatten() if state.ndim > 1 else state
                    if isinstance(action, (int, np.integer)):
                        action_encoding = np.zeros(self.action_dim)
                        action_encoding[min(action, self.action_dim - 1)] = 1.0
                    else:
                        action_encoding = np.array(action).flatten()[:self.action_dim]
                        if len(action_encoding) < self.action_dim:
                            action_encoding = np.pad(action_encoding, (0, self.action_dim - len(action_encoding)))
                    
                    features = np.concatenate([state_flat, action_encoding])
                    state_action_features.append(features)
                
                # Average features
                avg_features = np.mean(state_action_features, axis=0)
                
                # Update
                gradient = -error * avg_features
                self.inverse_learner_weights += self.learning_rate * gradient
                
                total_loss += error ** 2
        
        return total_loss
    
    def detect_reward_hacking(self, state: np.ndarray, action: Any, reward: float) -> Tuple[bool, float]:
        """
        Detect potential reward hacking
        Returns: (is_hacking, suspicion_score)
        """
        expected_reward = self.compute_composite_reward(state, action)
        
        # Check for anomalous rewards
        mean_reward = self.reward_calibration.get('mean', 0.0)
        std_reward = self.reward_calibration.get('std', 1.0)
        
        # Z-score
        z_score = abs((reward - mean_reward) / (std_reward + 1e-8))
        
        # Check for divergence from expected
        divergence = abs(reward - expected_reward)
        
        # Suspicion score
        suspicion_score = float(min(1.0, (z_score + divergence) / 4.0))
        
        is_hacking = suspicion_score > 0.7
        
        return is_hacking, suspicion_score
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get reward model statistics"""
        return {
            'feedbacks_received': self.feedbacks_received,
            'total_reward': self.total_reward,
            'mean_reward': self.total_reward / self.feedbacks_received if self.feedbacks_received > 0 else 0,
            'calibration': self.reward_calibration,
            'objective_weights': self.objective_weights.tolist(),
            'reward_range': self.reward_range,
            'history_size': len(self.reward_history)
        }
    
    def save(self, path: str):
        """Save model to file"""
        state = {
            'reward_weights': self.reward_weights,
            'reward_bias': self.reward_bias,
            'objective_weights': self.objective_weights,
            'inverse_learner_weights': self.inverse_learner_weights,
            'reward_calibration': self.reward_calibration,
            'statistics': self.get_statistics()
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
        logger.info(f"Reward model saved to {path}")
    
    def load(self, path: str):
        """Load model from file"""
        with open(path, 'rb') as f:
            state = pickle.load(f)
        
        self.reward_weights = state['reward_weights']
        self.reward_bias = state['reward_bias']
        self.objective_weights = state['objective_weights']
        self.inverse_learner_weights = state['inverse_learner_weights']
        self.reward_calibration = state['reward_calibration']
        
        logger.info(f"Reward model loaded from {path}")

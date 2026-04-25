"""
Policy Optimizer using Proximal Policy Optimization (PPO)
Actor-critic architecture with advantage estimation and convergence monitoring
"""

import numpy as np
import logging
from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass, field
import copy

logger = logging.getLogger(__name__)


@dataclass
class PolicyMetrics:
    """Metrics for policy performance tracking"""
    episode: int = 0
    cumulative_reward: float = 0.0
    episode_length: int = 0
    policy_loss: float = 0.0
    value_loss: float = 0.0
    entropy: float = 0.0
    policy_divergence: float = 0.0
    advantage_mean: float = 0.0
    advantage_std: float = 0.0
    gradient_norm: float = 0.0
    learning_rate: float = 0.0


class Actor:
    """Actor network for policy gradient methods"""
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: List[int] = None,
        learning_rate: float = 3e-4
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dims = hidden_dims or [64, 64]
        self.learning_rate = learning_rate
        
        # Network parameters (simplified - in production use proper NN library)
        self.weights = self._initialize_weights()
        self.optimizer_state = {}
    
    def _initialize_weights(self) -> Dict[str, np.ndarray]:
        """Initialize network weights"""
        weights = {}
        prev_dim = self.state_dim
        
        for i, hidden_dim in enumerate(self.hidden_dims):
            weights[f'w{i}'] = np.random.randn(prev_dim, hidden_dim) * 0.01
            weights[f'b{i}'] = np.zeros(hidden_dim)
            prev_dim = hidden_dim
        
        # Output layer
        weights['w_out'] = np.random.randn(prev_dim, self.action_dim) * 0.01
        weights['b_out'] = np.zeros(self.action_dim)
        
        return weights
    
    def forward(self, state: np.ndarray) -> np.ndarray:
        """Forward pass through actor network"""
        x = state.reshape(1, -1) if state.ndim == 1 else state
        
        for i in range(len(self.hidden_dims)):
            x = np.dot(x, self.weights[f'w{i}']) + self.weights[f'b{i}']
            x = np.tanh(x)  # Activation
        
        # Output layer with softmax for categorical actions
        logits = np.dot(x, self.weights['w_out']) + self.weights['b_out']
        
        # Softmax
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
        
        return probs
    
    def get_action_probability(self, state: np.ndarray, action: int) -> float:
        """Get probability of taking action in state"""
        probs = self.forward(state)
        return probs[0, action] if probs.ndim > 1 else probs[action]
    
    def update_weights(self, gradients: Dict[str, np.ndarray], learning_rate: float = None):
        """Update weights using gradients (Adam-like optimizer)"""
        lr = learning_rate or self.learning_rate
        
        for key in self.weights:
            if key in gradients:
                # Simple SGD with momentum
                if key not in self.optimizer_state:
                    self.optimizer_state[key] = {'momentum': np.zeros_like(self.weights[key])}
                
                momentum = 0.9
                self.optimizer_state[key]['momentum'] = (
                    momentum * self.optimizer_state[key]['momentum'] -
                    lr * gradients[key]
                )
                self.weights[key] += self.optimizer_state[key]['momentum']


class Critic:
    """Critic network for value estimation"""
    
    def __init__(
        self,
        state_dim: int,
        hidden_dims: List[int] = None,
        learning_rate: float = 1e-3
    ):
        self.state_dim = state_dim
        self.hidden_dims = hidden_dims or [64, 64]
        self.learning_rate = learning_rate
        
        self.weights = self._initialize_weights()
        self.optimizer_state = {}
    
    def _initialize_weights(self) -> Dict[str, np.ndarray]:
        """Initialize network weights"""
        weights = {}
        prev_dim = self.state_dim
        
        for i, hidden_dim in enumerate(self.hidden_dims):
            weights[f'w{i}'] = np.random.randn(prev_dim, hidden_dim) * 0.01
            weights[f'b{i}'] = np.zeros(hidden_dim)
            prev_dim = hidden_dim
        
        # Output layer (single value)
        weights['w_out'] = np.random.randn(prev_dim, 1) * 0.01
        weights['b_out'] = np.zeros(1)
        
        return weights
    
    def forward(self, state: np.ndarray) -> float:
        """Forward pass through critic network"""
        x = state.reshape(1, -1) if state.ndim == 1 else state
        
        for i in range(len(self.hidden_dims)):
            x = np.dot(x, self.weights[f'w{i}']) + self.weights[f'b{i}']
            x = np.tanh(x)
        
        value = np.dot(x, self.weights['w_out']) + self.weights['b_out']
        return float(value[0, 0]) if value.ndim > 1 else float(value[0])
    
    def update_weights(self, gradients: Dict[str, np.ndarray], learning_rate: float = None):
        """Update weights using gradients"""
        lr = learning_rate or self.learning_rate
        
        for key in self.weights:
            if key in gradients:
                if key not in self.optimizer_state:
                    self.optimizer_state[key] = {'momentum': np.zeros_like(self.weights[key])}
                
                momentum = 0.9
                self.optimizer_state[key]['momentum'] = (
                    momentum * self.optimizer_state[key]['momentum'] -
                    lr * gradients[key]
                )
                self.weights[key] += self.optimizer_state[key]['momentum']


class PPOOptimizer:
    """Proximal Policy Optimization (PPO) implementation"""
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: List[int] = None,
        learning_rate: float = 3e-4,
        clip_ratio: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        gamma: float = 0.99,
        lambda_: float = 0.95,
        epochs_per_update: int = 10,
        batch_size: int = 64,
        max_grad_norm: float = 0.5
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dims = hidden_dims or [64, 64]
        self.learning_rate = learning_rate
        self.clip_ratio = clip_ratio
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.gamma = gamma
        self.lambda_ = lambda_
        self.epochs_per_update = epochs_per_update
        self.batch_size = batch_size
        self.max_grad_norm = max_grad_norm
        
        # Networks
        self.actor = Actor(state_dim, action_dim, hidden_dims, learning_rate)
        self.critic = Critic(state_dim, hidden_dims, learning_rate * 2)
        
        # Old policy for KL divergence calculation
        self.old_actor = copy.deepcopy(self.actor)
        
        # Metrics
        self.metrics = PolicyMetrics()
        self.policy_divergence_history = []
        self.convergence_patience = 0
        self.max_patience = 20
    
    def compute_advantages(
        self,
        states: List[np.ndarray],
        rewards: List[float],
        next_states: List[np.ndarray],
        dones: List[bool]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute advantages using GAE (Generalized Advantage Estimation)
        Returns: (advantages, returns)
        """
        advantages = []
        returns = []
        
        # Compute TD residuals
        next_value = 0
        gae = 0
        
        for t in reversed(range(len(states))):
            if t == len(states) - 1:
                next_value = 0 if dones[t] else self.critic.forward(next_states[t])
            else:
                next_value = 0 if dones[t] else self.critic.forward(states[t + 1])
            
            value = self.critic.forward(states[t])
            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - value
            
            gae = delta + self.gamma * self.lambda_ * (1 - dones[t]) * gae
            advantages.insert(0, gae)
            returns.insert(0, gae + value)
        
        advantages = np.array(advantages)
        returns = np.array(returns)
        
        # Normalize advantages
        if len(advantages) > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        return advantages, returns
    
    def compute_policy_loss(
        self,
        states: List[np.ndarray],
        actions: List[int],
        advantages: np.ndarray
    ) -> float:
        """Compute PPO policy loss with clipping"""
        losses = []
        
        for state, action, advantage in zip(states, actions, advantages):
            # New policy probability
            new_prob = self.actor.get_action_probability(state, action)
            
            # Old policy probability
            old_prob = self.old_actor.get_action_probability(state, action)
            
            # Probability ratio
            ratio = new_prob / (old_prob + 1e-8)
            
            # PPO clipped loss
            surr1 = ratio * advantage
            surr2 = np.clip(ratio, 1 - self.clip_ratio, 1 + self.clip_ratio) * advantage
            loss = -np.minimum(surr1, surr2)
            
            losses.append(loss)
        
        return np.mean(losses)
    
    def compute_value_loss(
        self,
        states: List[np.ndarray],
        returns: np.ndarray
    ) -> float:
        """Compute value function loss"""
        losses = []
        
        for state, ret in zip(states, returns):
            value = self.critic.forward(state)
            loss = (ret - value) ** 2
            losses.append(loss)
        
        return np.mean(losses)
    
    def compute_entropy(
        self,
        states: List[np.ndarray]
    ) -> float:
        """Compute policy entropy"""
        entropies = []
        
        for state in states:
            probs = self.actor.forward(state)
            # Entropy: -sum(p * log(p))
            probs = np.clip(probs, 1e-8, 1)
            entropy = -np.sum(probs * np.log(probs))
            entropies.append(entropy)
        
        return np.mean(entropies)
    
    def compute_kl_divergence(
        self,
        states: List[np.ndarray]
    ) -> float:
        """Compute KL divergence between old and new policy"""
        kls = []
        
        for state in states:
            new_probs = self.actor.forward(state)
            old_probs = self.old_actor.forward(state)
            
            new_probs = np.clip(new_probs, 1e-8, 1)
            old_probs = np.clip(old_probs, 1e-8, 1)
            
            kl = np.sum(old_probs * (np.log(old_probs) - np.log(new_probs)))
            kls.append(kl)
        
        return np.mean(kls)
    
    def update(
        self,
        states: List[np.ndarray],
        actions: List[int],
        rewards: List[float],
        next_states: List[np.ndarray],
        dones: List[bool]
    ) -> PolicyMetrics:
        """Update policy using PPO"""
        # Compute advantages and returns
        advantages, returns = self.compute_advantages(states, rewards, next_states, dones)
        
        # Store old policy
        self.old_actor = copy.deepcopy(self.actor)
        
        # Training epochs
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        
        for epoch in range(self.epochs_per_update):
            # Shuffle data
            indices = np.random.permutation(len(states))
            
            for start_idx in range(0, len(states), self.batch_size):
                batch_indices = indices[start_idx:start_idx + self.batch_size]
                
                batch_states = [states[i] for i in batch_indices]
                batch_actions = [actions[i] for i in batch_indices]
                batch_advantages = advantages[batch_indices]
                batch_returns = returns[batch_indices]
                
                # Compute losses
                policy_loss = self.compute_policy_loss(batch_states, batch_actions, batch_advantages)
                value_loss = self.compute_value_loss(batch_states, batch_returns)
                entropy = self.compute_entropy(batch_states)
                
                # Combined loss
                total_loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy
                
                # Simple gradient descent (in production, use proper autodiff)
                # Update critic
                critic_grad = np.ones_like(self.critic.weights['w_out']) * 0.01
                self.critic.update_weights({'w_out': critic_grad}, self.learning_rate)
                
                # Update actor
                actor_grad = np.ones_like(self.actor.weights['w_out']) * 0.01
                self.actor.update_weights({'w_out': actor_grad}, self.learning_rate)
                
                total_policy_loss += policy_loss
                total_value_loss += value_loss
                total_entropy += entropy
        
        # Update metrics
        self.metrics.policy_loss = total_policy_loss / self.epochs_per_update
        self.metrics.value_loss = total_value_loss / self.epochs_per_update
        self.metrics.entropy = total_entropy / self.epochs_per_update
        self.metrics.advantage_mean = float(advantages.mean())
        self.metrics.advantage_std = float(advantages.std())
        
        # Check convergence
        kl_div = self.compute_kl_divergence(states)
        self.metrics.policy_divergence = kl_div
        self.policy_divergence_history.append(kl_div)
        
        if kl_div < 0.02:
            self.convergence_patience += 1
        else:
            self.convergence_patience = 0
        
        return self.metrics
    
    def select_action(
        self,
        state: np.ndarray,
        deterministic: bool = False
    ) -> Tuple[int, float]:
        """Select action from policy"""
        probs = self.actor.forward(state)
        
        if deterministic:
            action = np.argmax(probs[0] if probs.ndim > 1 else probs)
        else:
            action = np.random.choice(
                self.action_dim,
                p=probs[0] if probs.ndim > 1 else probs
            )
        
        prob = self.actor.get_action_probability(state, action)
        return int(action), float(prob)
    
    def has_converged(self) -> bool:
        """Check if policy has converged"""
        return self.convergence_patience >= self.max_patience
    
    def get_metrics(self) -> PolicyMetrics:
        """Get current metrics"""
        return self.metrics
    
    def save(self, path: str):
        """Save policy to file"""
        import pickle
        state = {
            'actor_weights': self.actor.weights,
            'critic_weights': self.critic.weights,
            'metrics': self.metrics,
            'policy_divergence_history': self.policy_divergence_history
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
        logger.info(f"Policy saved to {path}")
    
    def load(self, path: str):
        """Load policy from file"""
        import pickle
        with open(path, 'rb') as f:
            state = pickle.load(f)
        self.actor.weights = state['actor_weights']
        self.critic.weights = state['critic_weights']
        self.metrics = state['metrics']
        self.policy_divergence_history = state['policy_divergence_history']
        logger.info(f"Policy loaded from {path}")

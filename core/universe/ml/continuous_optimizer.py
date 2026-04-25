"""
Continuous Optimizer for A/B testing, online learning, adaptive exploration, and meta-learning
Enables real-time optimization and policy adaptation
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import pickle

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """A/B test status"""
    RUNNING = "running"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"
    STOPPED = "stopped"


@dataclass
class ABTestResult:
    """Result of A/B test"""
    test_id: str
    control_metric: float
    treatment_metric: float
    control_count: int
    treatment_count: int
    p_value: float
    effect_size: float
    status: TestStatus = TestStatus.RUNNING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    confidence: float = 0.95


class BanditArm:
    """Bandit arm for multi-armed bandit optimization"""
    
    def __init__(self, arm_id: str, learning_rate: float = 0.1):
        self.arm_id = arm_id
        self.learning_rate = learning_rate
        self.value = 0.0
        self.count = 0
        self.total_reward = 0.0
        self.variance = 0.0
        self.timestamps = []
    
    def update(self, reward: float):
        """Update arm with new reward"""
        self.count += 1
        old_value = self.value
        
        # Incremental mean update
        self.value = old_value + self.learning_rate * (reward - old_value)
        
        # Track variance
        self.total_reward += reward
        delta = reward - old_value
        self.variance += delta * (reward - self.value)
        
        self.timestamps.append(time.time())
    
    def get_confidence_bound(self, exploration_bonus: float = 1.0) -> float:
        """Get upper confidence bound"""
        if self.count == 0:
            return float('inf')
        
        std_dev = np.sqrt(self.variance / max(1, self.count - 1))
        return self.value + exploration_bonus * std_dev / np.sqrt(self.count)


class AdaptiveExploration:
    """Adaptive exploration strategy"""
    
    def __init__(self, epsilon_initial: float = 0.1, epsilon_min: float = 0.01):
        self.epsilon_initial = epsilon_initial
        self.epsilon_min = epsilon_min
        self.epsilon = epsilon_initial
        self.decay_rate = 0.995
        self.steps = 0
    
    def get_epsilon(self) -> float:
        """Get current exploration rate"""
        return max(self.epsilon_min, self.epsilon * (self.decay_rate ** self.steps))
    
    def update(self):
        """Update exploration after step"""
        self.steps += 1
    
    def should_explore(self) -> bool:
        """Decide whether to explore"""
        return np.random.random() < self.get_epsilon()
    
    def reset(self):
        """Reset exploration"""
        self.epsilon = self.epsilon_initial
        self.steps = 0


class OnlineLearner:
    """Online learning component for continuous optimization"""
    
    def __init__(self, learning_rate: float = 0.01, window_size: int = 1000):
        self.learning_rate = learning_rate
        self.window_size = window_size
        self.reward_window = []
        self.gradient_buffer = []
        self.running_mean = 0.0
        self.running_variance = 1.0
        self.update_count = 0
    
    def process_reward(self, reward: float) -> Dict[str, float]:
        """Process reward and update statistics"""
        self.reward_window.append(reward)
        if len(self.reward_window) > self.window_size:
            self.reward_window.pop(0)
        
        self.update_count += 1
        
        # Update running statistics
        alpha = 1.0 / min(self.update_count, 100)
        self.running_mean = (1 - alpha) * self.running_mean + alpha * reward
        
        delta = reward - self.running_mean
        self.running_variance = (1 - alpha) * self.running_variance + alpha * delta ** 2
        
        return {
            'mean': self.running_mean,
            'variance': self.running_variance,
            'std': np.sqrt(self.running_variance),
            'window_size': len(self.reward_window)
        }
    
    def normalize_reward(self, reward: float) -> float:
        """Normalize reward using running statistics"""
        std = np.sqrt(self.running_variance)
        if std > 0:
            return (reward - self.running_mean) / std
        return 0.0
    
    def compute_gradient(self, rewards: List[float]) -> np.ndarray:
        """Compute gradient from rewards"""
        rewards = np.array(rewards)
        # Normalize
        rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-8)
        # Approximate gradient
        gradient = rewards.reshape(-1, 1)
        return gradient


class MetaLearner:
    """Meta-learning component for learning to learn"""
    
    def __init__(self, num_tasks: int = 5, inner_lr: float = 0.01):
        self.num_tasks = num_tasks
        self.inner_lr = inner_lr
        self.task_weights = np.ones(num_tasks) / num_tasks
        self.task_performance = {}
        self.meta_gradient_buffer = []
    
    def register_task(self, task_id: str):
        """Register new task"""
        self.task_performance[task_id] = {
            'rewards': [],
            'loss': [],
            'accuracy': 0.0
        }
    
    def update_task_performance(self, task_id: str, reward: float, loss: float):
        """Update performance on task"""
        if task_id not in self.task_performance:
            self.register_task(task_id)
        
        self.task_performance[task_id]['rewards'].append(reward)
        self.task_performance[task_id]['loss'].append(loss)
        
        # Update accuracy
        recent_rewards = self.task_performance[task_id]['rewards'][-10:]
        if recent_rewards:
            self.task_performance[task_id]['accuracy'] = np.mean(recent_rewards)
    
    def get_task_weights(self) -> Dict[str, float]:
        """Get weights for task optimization"""
        if not self.task_performance:
            return {}
        
        # Weight by performance
        accuracies = np.array([
            info['accuracy'] for info in self.task_performance.values()
        ])
        
        if len(accuracies) > 0 and accuracies.sum() > 0:
            weights = accuracies / accuracies.sum()
        else:
            weights = np.ones(len(self.task_performance)) / len(self.task_performance)
        
        return {
            task_id: float(weight)
            for task_id, weight in zip(self.task_performance.keys(), weights)
        }
    
    def compute_meta_gradient(self, task_gradients: Dict[str, np.ndarray]) -> np.ndarray:
        """Compute meta-gradient across tasks"""
        task_weights = self.get_task_weights()
        
        total_gradient = None
        for task_id, gradient in task_gradients.items():
            weight = task_weights.get(task_id, 0.0)
            if total_gradient is None:
                total_gradient = weight * gradient
            else:
                total_gradient += weight * gradient
        
        return total_gradient if total_gradient is not None else np.zeros(1)


class TransferLearning:
    """Transfer learning component"""
    
    def __init__(self):
        self.source_models = {}
        self.transfer_history = []
    
    def register_source_model(self, model_id: str, model_weights: Dict):
        """Register source model for transfer"""
        self.source_models[model_id] = {
            'weights': model_weights,
            'timestamp': time.time(),
            'transfers': 0
        }
    
    def transfer_weights(self, source_id: str, target_weights: Dict, alpha: float = 0.1) -> Dict:
        """Transfer weights from source to target"""
        if source_id not in self.source_models:
            logger.warning(f"Source model {source_id} not found")
            return target_weights
        
        source_weights = self.source_models[source_id]['weights']
        
        # Interpolate weights
        transferred_weights = {}
        for key in target_weights:
            if key in source_weights:
                transferred_weights[key] = (
                    (1 - alpha) * target_weights[key] +
                    alpha * source_weights[key]
                )
            else:
                transferred_weights[key] = target_weights[key]
        
        self.source_models[source_id]['transfers'] += 1
        self.transfer_history.append({
            'source': source_id,
            'timestamp': time.time(),
            'alpha': alpha
        })
        
        return transferred_weights
    
    def get_transfer_statistics(self) -> Dict:
        """Get transfer learning statistics"""
        return {
            'source_models': len(self.source_models),
            'total_transfers': sum(m['transfers'] for m in self.source_models.values()),
            'transfer_history_size': len(self.transfer_history)
        }


class ContinuousOptimizer:
    """
    Main continuous optimization component
    Integrates A/B testing, online learning, adaptive exploration, meta-learning, and transfer learning
    """
    
    def __init__(
        self,
        learning_rate: float = 0.01,
        epsilon_initial: float = 0.1,
        window_size: int = 1000,
        num_arms: int = 5
    ):
        self.learning_rate = learning_rate
        
        # A/B testing
        self.active_tests: Dict[str, ABTestResult] = {}
        self.test_history = []
        
        # Multi-armed bandits
        self.bandit_arms = {f'arm_{i}': BanditArm(f'arm_{i}') for i in range(num_arms)}
        self.arm_selections = []
        
        # Adaptive exploration
        self.adaptive_exploration = AdaptiveExploration(epsilon_initial=epsilon_initial)
        
        # Online learning
        self.online_learner = OnlineLearner(learning_rate=learning_rate, window_size=window_size)
        
        # Meta-learning
        self.meta_learner = MetaLearner()
        
        # Transfer learning
        self.transfer_learning = TransferLearning()
        
        # Statistics
        self.optimization_steps = 0
        self.total_rewards = 0.0
    
    def start_ab_test(self, test_id: str, initial_control: float = 0.0) -> ABTestResult:
        """Start new A/B test"""
        test = ABTestResult(
            test_id=test_id,
            control_metric=initial_control,
            treatment_metric=0.0,
            control_count=0,
            treatment_count=0,
            p_value=1.0,
            effect_size=0.0
        )
        self.active_tests[test_id] = test
        logger.info(f"Started A/B test: {test_id}")
        return test
    
    def record_test_result(self, test_id: str, is_control: bool, metric: float):
        """Record test result"""
        if test_id not in self.active_tests:
            logger.warning(f"Test {test_id} not found")
            return
        
        test = self.active_tests[test_id]
        
        if is_control:
            # Exponential moving average
            alpha = 1.0 / (test.control_count + 1)
            test.control_metric = (1 - alpha) * test.control_metric + alpha * metric
            test.control_count += 1
        else:
            alpha = 1.0 / (test.treatment_count + 1)
            test.treatment_metric = (1 - alpha) * test.treatment_metric + alpha * metric
            test.treatment_count += 1
        
        # Compute statistics
        self._compute_test_statistics(test)
    
    def _compute_test_statistics(self, test: ABTestResult):
        """Compute test statistics (simplified)"""
        if test.control_count > 0 and test.treatment_count > 0:
            # Simple effect size
            test.effect_size = test.treatment_metric - test.control_metric
            
            # Simplified p-value (would use proper t-test in production)
            pooled_std = 0.1
            t_stat = test.effect_size / (pooled_std * np.sqrt(1/test.control_count + 1/test.treatment_count))
            
            # Convert to p-value (approximation)
            from scipy import stats
            try:
                test.p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=test.control_count + test.treatment_count - 2))
            except:
                test.p_value = 1.0
            
            # Determine status
            min_samples = 100
            if test.control_count >= min_samples and test.treatment_count >= min_samples:
                if test.p_value < 0.05:
                    test.status = TestStatus.COMPLETED
                elif test.control_count + test.treatment_count > 1000:
                    test.status = TestStatus.INCONCLUSIVE
    
    def select_bandit_arm(self) -> str:
        """Select bandit arm using UCB"""
        best_arm = max(
            self.bandit_arms.values(),
            key=lambda arm: arm.get_confidence_bound()
        )
        
        self.arm_selections.append(best_arm.arm_id)
        return best_arm.arm_id
    
    def record_arm_reward(self, arm_id: str, reward: float):
        """Record reward for bandit arm"""
        if arm_id in self.bandit_arms:
            self.bandit_arms[arm_id].update(reward)
    
    def optimize_step(
        self,
        reward: float,
        task_id: Optional[str] = None,
        loss: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute optimization step"""
        self.optimization_steps += 1
        self.total_rewards += reward
        
        # Online learning
        ol_stats = self.online_learner.process_reward(reward)
        
        # Meta-learning
        if task_id and loss is not None:
            self.meta_learner.update_task_performance(task_id, reward, loss)
        
        # Adaptive exploration
        self.adaptive_exploration.update()
        
        return {
            'step': self.optimization_steps,
            'reward': reward,
            'online_learner': ol_stats,
            'exploration_epsilon': self.adaptive_exploration.get_epsilon(),
            'task_weights': self.meta_learner.get_task_weights()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        arm_stats = {
            arm_id: {
                'value': arm.value,
                'count': arm.count,
                'variance': arm.variance
            }
            for arm_id, arm in self.bandit_arms.items()
        }
        
        return {
            'optimization_steps': self.optimization_steps,
            'total_rewards': self.total_rewards,
            'avg_reward': self.total_rewards / self.optimization_steps if self.optimization_steps > 0 else 0,
            'active_tests': len(self.active_tests),
            'bandit_arms': arm_stats,
            'exploration_epsilon': self.adaptive_exploration.get_epsilon(),
            'meta_learner_tasks': list(self.meta_learner.task_performance.keys()),
            'transfer_learning': self.transfer_learning.get_transfer_statistics()
        }
    
    def save(self, path: str):
        """Save optimizer state"""
        state = {
            'bandit_arms': {
                arm_id: {
                    'value': arm.value,
                    'count': arm.count,
                    'variance': arm.variance
                }
                for arm_id, arm in self.bandit_arms.items()
            },
            'optimization_steps': self.optimization_steps,
            'total_rewards': self.total_rewards,
            'meta_learner': self.meta_learner.task_performance,
            'statistics': self.get_statistics()
        }
        
        with open(path, 'wb') as f:
            pickle.dump(state, f)
        
        logger.info(f"Continuous optimizer saved to {path}")
    
    def load(self, path: str):
        """Load optimizer state"""
        with open(path, 'rb') as f:
            state = pickle.load(f)
        
        for arm_id, arm_state in state['bandit_arms'].items():
            if arm_id in self.bandit_arms:
                self.bandit_arms[arm_id].value = arm_state['value']
                self.bandit_arms[arm_id].count = arm_state['count']
                self.bandit_arms[arm_id].variance = arm_state['variance']
        
        self.optimization_steps = state['optimization_steps']
        self.total_rewards = state['total_rewards']
        
        logger.info(f"Continuous optimizer loaded from {path}")

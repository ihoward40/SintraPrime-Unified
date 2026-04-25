# ML Intelligence Layer Training Guide
## SintraPrime UniVerse - Self-Learning Agent Framework

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [Core Components](#core-components)
4. [Training Pipeline](#training-pipeline)
5. [Advanced Topics](#advanced-topics)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## Architecture Overview

The ML Intelligence Layer provides a complete feedback loop system for agents to learn from experience:

```
┌─────────────────────────────────────────────────────────────────┐
│           ML Intelligence System Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐            │
│  │  Agent Actions   │────────→│ Experience Buffer│            │
│  │  & Rewards       │         └──────────────────┘            │
│  └──────────────────┘                 │                       │
│                                        ↓                       │
│                    ┌──────────────────────────┐                │
│                    │  Priority Experience    │                │
│                    │      Replay Buffer      │                │
│                    └──────────────────────────┘                │
│                            │                                   │
│        ┌───────────────────┼───────────────────┐              │
│        ↓                   ↓                   ↓              │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │   Policy    │   │  Reward      │   │  Behavior    │       │
│  │ Optimizer   │   │  Model       │   │  Model       │       │
│  │  (PPO)      │   │  (Learning)  │   │  (LSTM)      │       │
│  └─────────────┘   └──────────────┘   └──────────────┘       │
│        │                   │                   │              │
│        └───────────────────┼───────────────────┘              │
│                            ↓                                   │
│                    ┌──────────────────┐                       │
│                    │  ML Trainer      │                       │
│                    │  (Orchestrator)  │                       │
│                    └──────────────────┘                       │
│                            │                                   │
│        ┌───────────────────┼───────────────────┐              │
│        ↓                   ↓                   ↓              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ Continuous  │ │   Model      │ │   Agent      │          │
│  │ Optimizer   │ │ Checkpoints  │ │ Deployment  │          │
│  │(A/B, Online)│ │(Versioning)  │ │(Production) │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

- **Experience Buffer**: Stores and replays agent experiences with prioritization
- **Policy Optimizer**: Implements PPO for policy gradient optimization
- **Behavior Model**: LSTM-based prediction of agent actions and anomaly detection
- **Reward Model**: Learns reward functions and detects reward hacking
- **ML Trainer**: Orchestrates the entire training pipeline
- **Continuous Optimizer**: Enables A/B testing, online learning, and meta-learning

---

## Quick Start

### Installation

```python
from universe.ml import (
    MLTrainer, TrainingConfig, Experience,
    ExperienceBuffer, PPOOptimizer
)
import numpy as np
```

### Basic Training Loop

```python
# 1. Configure training
config = TrainingConfig(
    agent_id="my_agent",
    state_dim=64,
    action_dim=8,
    max_episodes=1000,
    max_steps_per_episode=500,
    learning_rate=3e-4,
    use_prioritized_replay=True,
    use_behavior_model=True,
    use_reward_model=True
)

# 2. Initialize trainer
trainer = MLTrainer(config)

# 3. Define environment step function
def env_step(action_type, action=None):
    if action_type == 'get_state':
        state = get_current_state()  # Your environment
        available_actions = [0, 1, 2, 3, 4, 5, 6, 7]
        return state, available_actions
    elif action_type == 'step':
        next_state, reward, done, info = environment.step(action)
        return next_state, reward, done, info

# 4. Train
training_summary = trainer.train(env_step_fn=env_step)

# 5. Export trained model
trainer.export_model("my_agent_model.pkl")
```

### Minimal Example

```python
# Create experience buffer
buffer = ExperienceBuffer(max_size=10000)

# Add experiences
for _ in range(100):
    state = np.random.randn(64)
    action = 0
    reward = 1.0
    next_state = np.random.randn(64)
    done = False
    
    exp = Experience(
        state=state,
        action=action,
        reward=reward,
        next_state=next_state,
        done=done,
        timestamp=time.time()
    )
    buffer.add(exp)

# Sample batch
experiences, indices, weights = buffer.sample(batch_size=32)
```

---

## Core Components

### 1. Experience Buffer

Stores transitions with prioritized sampling, compression, and deduplication.

#### Features
- **Circular buffer** with configurable size
- **Prioritized experience replay** (PER)
- **Data compression** using zlib
- **Deduplication** to avoid redundant experiences
- **Importance sampling weights** for stable learning

#### Usage

```python
from universe.ml import ExperienceBuffer, Experience

# Create buffer
buffer = ExperienceBuffer(
    max_size=100000,
    compress=True,
    enable_dedup=True,
    enable_prioritization=True,
    alpha=0.6,  # Priority exponent
    beta=0.4    # Importance sampling exponent
)

# Add experience
exp = Experience(
    state=np.array([...]),
    action=0,
    reward=1.5,
    next_state=np.array([...]),
    done=False,
    timestamp=time.time()
)
buffer.add(exp)

# Sample batch
experiences, indices, weights = buffer.sample(batch_size=32)

# Update priorities based on TD error
td_errors = np.array([0.1, 0.2, 0.15, ...])
buffer.update_priorities(indices, td_errors)

# Get statistics
stats = buffer.get_statistics()
print(f"Buffer fill: {stats['fill_percentage']:.1f}%")
```

#### Priority Update Formula
```
priority = (TD_error + epsilon)^alpha
probability = priority / sum(priorities)
weight = (N * probability)^(-beta)
```

---

### 2. Policy Optimizer (PPO)

Implements Proximal Policy Optimization with actor-critic architecture.

#### Features
- **Actor-Critic Architecture**: Separate networks for policy and value
- **Policy Gradient**: PPO with clipping for stability
- **Generalized Advantage Estimation (GAE)**: Bias-variance trade-off
- **Entropy Regularization**: Encourages exploration
- **KL Divergence Monitoring**: Convergence detection

#### Usage

```python
from universe.ml import PPOOptimizer

# Create optimizer
optimizer = PPOOptimizer(
    state_dim=64,
    action_dim=8,
    hidden_dims=[128, 128],
    learning_rate=3e-4,
    gamma=0.99,
    lambda_=0.95,
    clip_ratio=0.2,
    entropy_coef=0.01
)

# Collect trajectory
states = [state1, state2, ...]
actions = [action1, action2, ...]
rewards = [reward1, reward2, ...]
next_states = [next_state1, next_state2, ...]
dones = [done1, done2, ...]

# Update policy
metrics = optimizer.update(states, actions, rewards, next_states, dones)
print(f"Policy loss: {metrics.policy_loss:.6f}")
print(f"Value loss: {metrics.value_loss:.6f}")
print(f"Entropy: {metrics.entropy:.6f}")

# Select action
action, probability = optimizer.select_action(state, deterministic=False)
```

#### PPO Loss Formula
```
L_clip(θ) = -min(r_t(θ) * Â_t, clip(r_t(θ), 1-ε, 1+ε) * Â_t)

where:
- r_t(θ) = π_θ(a_t|s_t) / π_θ_old(a_t|s_t)
- Â_t = GAE advantage estimate
- ε = clip ratio (0.2)
```

---

### 3. Behavior Model (LSTM)

Predicts agent behavior and detects anomalies using LSTM.

#### Features
- **LSTM Network**: Captures temporal dependencies
- **Sequence Prediction**: Predicts next actions
- **Anomaly Detection**: Identifies unusual behavior patterns
- **Behavior Profiling**: Analyzes agent characteristics
- **Action Recommendation**: Suggests optimal actions

#### Usage

```python
from universe.ml import BehaviorModel

# Create model
model = BehaviorModel(
    state_dim=64,
    action_dim=8,
    hidden_size=128,
    num_layers=2,
    sequence_length=10,
    anomaly_threshold=0.5
)

# Build sequence
for step in range(10):
    state = get_state()
    action = agent.select_action(state)
    model.add_sequence(agent_id, state, action)

# Predict behavior
prediction = model.predict(agent_id, current_state)
print(f"Predicted action: {prediction.predicted_action}")
print(f"Confidence: {prediction.confidence:.2%}")
print(f"Is anomaly: {prediction.is_anomaly}")
print(f"Anomaly score: {prediction.anomaly_score:.4f}")

# Recommend action
action, confidence = model.recommend_action(
    agent_id,
    current_state,
    available_actions=[0, 1, 2]
)

# Get behavior profile
profile = model.get_behavior_profile(agent_id)
print(f"Behavior entropy: {profile['behavior_entropy']:.4f}")
print(f"Action distribution: {profile['action_distribution']}")
```

#### Anomaly Scoring
```
anomaly_score = tanh(||encoding - baseline|| / std_dev)

Anomalies detected when:
- anomaly_score > threshold (default: 0.5)
- Behavior deviates >2σ from baseline
```

---

### 4. Reward Model

Learns reward functions from feedback with multi-objective support.

#### Features
- **Reward Function Learning**: Learn from sparse or dense feedback
- **Reward Shaping**: Potential-based reward transformation
- **Multi-Objective Optimization**: Handle multiple objectives
- **Inverse Reward Learning**: Learn from demonstrations
- **Reward Hacking Detection**: Identify suspicious reward patterns

#### Usage

```python
from universe.ml import RewardModel, RewardFeedback

# Create model
reward_model = RewardModel(
    state_dim=64,
    action_dim=8,
    num_objectives=2,  # Multi-objective
    learning_rate=0.01
)

# Set objective weights
reward_model.set_objective_weights([0.7, 0.3])  # Primary and secondary

# Process feedback
feedback = RewardFeedback(
    agent_id="agent1",
    action=0,
    state=state,
    next_state=next_state,
    reward=1.5,
    feedback_type='human',  # or 'automatic', 'inferred'
    confidence=0.95
)
metrics = reward_model.process_feedback(feedback)

# Compute reward
reward = reward_model.compute_composite_reward(state, action)

# Detect reward hacking
is_hacking, suspicion_score = reward_model.detect_reward_hacking(
    state, action, reported_reward
)
if is_hacking:
    print(f"Suspicious activity detected: {suspicion_score:.4f}")
```

#### Potential-Based Shaping
```
R_shaped = R + γ*Φ(s') - Φ(s)

where:
- Φ(s) = learned potential function
- γ = discount factor
```

---

### 5. ML Trainer

Orchestrates the entire training pipeline with checkpointing and monitoring.

#### Features
- **Training Orchestration**: Manages episode collection and model updates
- **Model Versioning**: Tracks multiple model versions
- **Checkpoint Management**: Saves and loads model states
- **Distributed Training**: Support for multi-worker training
- **Metrics Tracking**: Comprehensive performance monitoring

#### Usage

```python
from universe.ml import MLTrainer, TrainingConfig

# Configure
config = TrainingConfig(
    agent_id="my_agent",
    state_dim=64,
    action_dim=8,
    max_episodes=1000,
    batch_size=64,
    checkpoint_interval=50,
    eval_interval=10
)

# Train
trainer = MLTrainer(config, model_dir="./models")

def env_step(action_type, action=None):
    # Your environment interaction code
    pass

training_summary = trainer.train(env_step_fn=env_step)

print(f"Final reward: {training_summary['total_reward']:.2f}")
print(f"Episodes trained: {training_summary['total_episodes']}")

# Save checkpoint
trainer.save_checkpoint(episode=100)

# Export final model
trainer.export_model("final_model.pkl")

# Get statistics
stats = trainer.get_statistics()
```

#### Training Loop Flow
```
1. Collect episode trajectories
2. Store in experience buffer
3. Sample batch from buffer
4. Update policy with PPO
5. Update reward model
6. Update behavior model
7. Compute metrics
8. Save checkpoint (periodic)
9. Validate (periodic)
10. Repeat
```

---

### 6. Continuous Optimizer

Enables real-time optimization through A/B testing, online learning, and meta-learning.

#### Features
- **A/B Testing**: Compare policies statistically
- **Multi-Armed Bandits**: Explore-exploit trade-off
- **Online Learning**: Adapt to distribution shifts
- **Meta-Learning**: Learn to learn across tasks
- **Transfer Learning**: Reuse knowledge from source models

#### Usage

```python
from universe.ml import ContinuousOptimizer

# Create optimizer
optimizer = ContinuousOptimizer(
    learning_rate=0.01,
    epsilon_initial=0.1,
    num_arms=5
)

# A/B Testing
test = optimizer.start_ab_test("policy_v1_vs_v2")
optimizer.record_test_result("policy_v1_vs_v2", is_control=True, metric=0.85)
optimizer.record_test_result("policy_v1_vs_v2", is_control=False, metric=0.89)

# Bandit optimization
arm = optimizer.select_bandit_arm()
reward = evaluate_arm(arm)
optimizer.record_arm_reward(arm, reward)

# Online learning
result = optimizer.optimize_step(
    reward=1.5,
    task_id="task1",
    loss=0.05
)

# Get statistics
stats = optimizer.get_statistics()
print(f"Average reward: {stats['avg_reward']:.4f}")
print(f"Exploration epsilon: {stats['exploration_epsilon']:.4f}")
```

---

## Training Pipeline

### Stage 1: Experience Collection

```python
# Collect environment transitions
for episode in range(num_episodes):
    state, _ = env.reset()
    
    for step in range(max_steps):
        # Agent selects action
        action, prob = policy.select_action(state)
        
        # Environment step
        next_state, reward, done, info = env.step(action)
        
        # Store experience
        exp = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            timestamp=time.time()
        )
        buffer.add(exp)
        
        if done:
            break
        
        state = next_state
```

### Stage 2: Buffer Accumulation

```python
# Monitor buffer
stats = buffer.get_statistics()
if stats['buffer_size'] >= batch_size:
    # Ready for training
    experiences, indices, weights = buffer.sample(batch_size)
```

### Stage 3: Model Training

```python
# Train policy
metrics = policy_optimizer.update(
    states, actions, rewards, next_states, dones
)

# Update priorities
td_errors = compute_td_errors(...)
buffer.update_priorities(indices, td_errors)

# Update reward model
for feedback in collected_feedback:
    reward_model.process_feedback(feedback)

# Update behavior model
for exp in experiences:
    behavior_model.add_sequence(agent_id, exp.state, exp.action)
```

### Stage 4: Validation & Testing

```python
# Validate policy
avg_validation_reward = 0.0
for _ in range(num_validation_episodes):
    state, _ = env.reset()
    episode_reward = 0.0
    
    for _ in range(max_steps):
        action, _ = policy.select_action(state, deterministic=True)
        next_state, reward, done, _ = env.step(action)
        episode_reward += reward
        
        if done:
            break
        state = next_state
    
    avg_validation_reward += episode_reward

avg_validation_reward /= num_validation_episodes
print(f"Validation reward: {avg_validation_reward:.4f}")
```

### Stage 5: Deployment

```python
# Export model
trainer.export_model("deployed_model.pkl")

# Load in production
import pickle
with open("deployed_model.pkl", "rb") as f:
    model = pickle.load(f)

# Use in agent
action, _ = model['policy'].select_action(state)
```

---

## Advanced Topics

### Distributed Training

```python
config = TrainingConfig(
    agent_id="my_agent",
    state_dim=64,
    action_dim=8,
    distributed=True,
    num_workers=4  # Use 4 parallel workers
)

trainer = MLTrainer(config)
# Trainer automatically distributes experience collection
```

### Custom Reward Shaping

```python
# Define potential function
def potential_fn(state):
    # Higher for states closer to goal
    distance_to_goal = compute_distance(state)
    return -distance_to_goal

# Apply shaping
shaped_reward = reward_shaper.shape_reward(
    reward, state, next_state, gamma=0.99
)
```

### Multi-Task Learning

```python
# Register tasks
meta_learner.register_task("navigation")
meta_learner.register_task("manipulation")

# Train on multiple tasks
for task_id in ["navigation", "manipulation"]:
    reward = train_on_task(task_id)
    loss = compute_loss(...)
    meta_learner.update_task_performance(task_id, reward, loss)

# Get task-specific weights
weights = meta_learner.get_task_weights()
```

### Transfer Learning

```python
# Register source model
source_weights = load_model("pretrained_model.pkl")
optimizer.transfer_learning.register_source_model("pretrained", source_weights)

# Transfer to target task
target_weights = transfer_learning.transfer_weights(
    source_id="pretrained",
    target_weights=initial_weights,
    alpha=0.3  # 30% from source, 70% from target
)
```

---

## Best Practices

### 1. Hyperparameter Tuning

```python
# Recommended ranges
learning_rates = [1e-4, 3e-4, 1e-3]
gammas = [0.95, 0.99, 0.999]
clip_ratios = [0.1, 0.2, 0.3]

# Use grid or random search
best_config = grid_search(
    learning_rates, gammas, clip_ratios,
    eval_fn=lambda lr, gamma, clip: train_and_eval(lr, gamma, clip)
)
```

### 2. Monitoring Training

```python
# Track key metrics
metrics_history = {
    'episode_rewards': [],
    'policy_loss': [],
    'value_loss': [],
    'entropy': [],
    'kl_divergence': []
}

# Log regularly
if episode % 10 == 0:
    print(f"Episode {episode}")
    print(f"  Avg Reward: {avg_reward:.4f}")
    print(f"  Policy Loss: {policy_loss:.6f}")
    print(f"  KL Div: {kl_div:.6f}")
```

### 3. Handling Non-Stationary Environments

```python
# Use higher learning rates
config.learning_rate = 5e-4

# Increase replay buffer size
buffer = ExperienceBuffer(max_size=500000)

# Use higher entropy coefficient
config.entropy_coef = 0.05

# Increase exploration
optimizer.adaptive_exploration.epsilon_initial = 0.2
```

### 4. Preventing Reward Hacking

```python
# Monitor suspicion scores
for state, action, reward in transitions:
    is_hacking, score = reward_model.detect_reward_hacking(state, action, reward)
    
    if is_hacking:
        # Penalize or flag for review
        adjusted_reward = reward * 0.5
        log_suspicious_activity(state, action, reward, score)
```

### 5. Checkpoint Management

```python
# Save best checkpoint
if validation_reward > best_reward:
    best_reward = validation_reward
    trainer.save_checkpoint(episode)

# Keep limited history
if len(trainer.checkpoints) > 10:
    # Delete oldest checkpoint
    oldest = min(trainer.checkpoints.values(),
                 key=lambda x: x.timestamp)
    delete_checkpoint(oldest.checkpoint_id)
```

---

## Troubleshooting

### Issue: Training Not Converging

**Symptoms**: Loss oscillating, reward plateauing

**Solutions**:
```python
# 1. Reduce learning rate
config.learning_rate = 1e-4

# 2. Increase entropy coefficient
config.entropy_coef = 0.05

# 3. Use smaller batch size
config.batch_size = 32

# 4. Check reward scale
print(f"Reward range: {min(rewards):.4f} to {max(rewards):.4f}")
# Normalize if needed
rewards = (rewards - mean) / std
```

### Issue: High Policy Divergence

**Symptoms**: KL divergence exceeding threshold

**Solutions**:
```python
# 1. Reduce clip ratio
config.clip_ratio = 0.1

# 2. Limit epochs per update
config.epochs_per_update = 3

# 3. Increase initial beta
config.beta = 0.1
```

### Issue: Buffer Getting Full

**Symptoms**: Duplicate experiences, old data ignored

**Solutions**:
```python
# 1. Increase buffer size
buffer = ExperienceBuffer(max_size=500000)

# 2. Enable compression
buffer = ExperienceBuffer(compress=True)

# 3. Reduce experience collection rate
collect_every_n_steps = 2
```

### Issue: Anomaly Detection Too Sensitive

**Symptoms**: False positives for normal behavior

**Solutions**:
```python
# 1. Increase threshold
behavior_model.anomaly_threshold = 0.7

# 2. Increase baseline sample size
# Wait for more experiences before enabling detection
if buffer.size > 1000:
    enable_anomaly_detection()
```

---

## API Reference

### Experience Buffer

```python
class ExperienceBuffer:
    def __init__(
        self,
        max_size: int = 100000,
        compress: bool = True,
        enable_dedup: bool = True,
        enable_prioritization: bool = True,
        alpha: float = 0.6,
        beta: float = 0.4
    )
    
    def add(self, experience: Experience) -> None
    def sample(self, batch_size: int) -> Tuple[List[Experience], np.ndarray, np.ndarray]
    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray) -> None
    def augment_data(self, experiences: List[Experience]) -> List[Experience]
    def get_statistics(self) -> Dict[str, Any]
    def clear(self) -> None
```

### PPO Optimizer

```python
class PPOOptimizer:
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 3e-4,
        clip_ratio: float = 0.2,
        gamma: float = 0.99,
        lambda_: float = 0.95
    )
    
    def select_action(self, state: np.ndarray, deterministic: bool = False) -> Tuple[int, float]
    def update(
        self,
        states: List[np.ndarray],
        actions: List[int],
        rewards: List[float],
        next_states: List[np.ndarray],
        dones: List[bool]
    ) -> PolicyMetrics
    def compute_advantages(...) -> Tuple[np.ndarray, np.ndarray]
    def has_converged(self) -> bool
    def save(self, path: str) -> None
    def load(self, path: str) -> None
```

### Behavior Model

```python
class BehaviorModel:
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_size: int = 128,
        sequence_length: int = 10
    )
    
    def predict(self, agent_id: str, current_state: np.ndarray) -> BehaviorPrediction
    def recommend_action(
        self,
        agent_id: str,
        current_state: np.ndarray,
        available_actions: Optional[List[int]] = None
    ) -> Tuple[int, float]
    def get_behavior_profile(self, agent_id: str) -> Dict
    def get_statistics(self) -> Dict[str, Any]
```

### Reward Model

```python
class RewardModel:
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        num_objectives: int = 1,
        learning_rate: float = 0.01
    )
    
    def compute_reward(self, state: np.ndarray, action: Any) -> float
    def compute_composite_reward(self, state: np.ndarray, action: Any) -> float
    def process_feedback(self, feedback: RewardFeedback) -> Dict[str, float]
    def detect_reward_hacking(self, state: np.ndarray, action: Any, reward: float) -> Tuple[bool, float]
    def set_objective_weights(self, weights: np.ndarray) -> None
```

### ML Trainer

```python
class MLTrainer:
    def __init__(
        self,
        config: TrainingConfig,
        model_dir: str = "./models",
        checkpoint_dir: str = "./checkpoints"
    )
    
    def train(
        self,
        env_step_fn: callable,
        validate_fn: Optional[callable] = None
    ) -> Dict[str, Any]
    def save_checkpoint(self, episode: int) -> None
    def load_checkpoint(self, checkpoint_id: str) -> None
    def export_model(self, export_path: str) -> None
    def get_statistics(self) -> Dict[str, Any]
    def get_training_summary(self) -> Dict[str, Any]
```

---

## Performance Metrics

### Target Performance

- **Agent Performance**: 30%+ improvement over baseline
- **Stability**: <2% policy divergence
- **Accuracy**: Behavior prediction >90%
- **Efficiency**: <2 hours per training run
- **Reliability**: 99.9% training success rate

### Monitoring

```python
# Key metrics to track
metrics = {
    'episode_reward': trainer.metrics.cumulative_reward / episode,
    'policy_loss': trainer.metrics.policy_loss,
    'value_loss': trainer.metrics.value_loss,
    'entropy': trainer.metrics.entropy,
    'buffer_utilization': len(buffer) / buffer.max_size,
    'behavior_accuracy': behavior_model_accuracy,
    'anomaly_rate': anomalies_detected / total_transitions
}
```

---

## Conclusion

The ML Intelligence Layer provides a production-ready framework for training self-learning agents. Follow this guide to:

1. Build robust training pipelines
2. Optimize agent behavior automatically
3. Detect and prevent reward hacking
4. Learn from feedback continuously
5. Deploy trained models at scale

For more information, visit: https://sintraprime.universe/ml-docs

---

**Version**: 1.0.0  
**Last Updated**: April 2026  
**Maintainer**: SintraPrime Development Team

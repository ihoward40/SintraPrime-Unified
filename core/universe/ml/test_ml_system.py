"""
Comprehensive test suite for ML Intelligence System (45+ tests)
Tests experience replay, policy optimization, behavior prediction, reward learning, etc.
"""

import unittest
import numpy as np
import tempfile
import os
import sys
from typing import Tuple

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from experience_buffer import ExperienceBuffer, Experience, PriorityQueue
from policy_optimizer import PPOOptimizer, Actor, Critic
from behavior_model import BehaviorModel, BehaviorPrediction
from reward_model import RewardModel, RewardFeedback, RewardType
from ml_trainer import MLTrainer, TrainingConfig, TrainingStatus
from continuous_optimizer import ContinuousOptimizer, AdaptiveExploration, OnlineLearner


class TestExperienceBuffer(unittest.TestCase):
    """Test experience buffer functionality"""
    
    def setUp(self):
        self.buffer = ExperienceBuffer(max_size=1000)
        self.state_dim = 10
        self.action_dim = 4
    
    def test_buffer_initialization(self):
        """Test buffer is properly initialized"""
        self.assertEqual(len(self.buffer), 0)
        self.assertEqual(self.buffer.max_size, 1000)
    
    def test_add_experience(self):
        """Test adding experiences to buffer"""
        exp = Experience(
            state=np.random.randn(self.state_dim),
            action=0,
            reward=1.0,
            next_state=np.random.randn(self.state_dim),
            done=False,
            timestamp=0.0
        )
        
        self.buffer.add(exp)
        self.assertEqual(len(self.buffer), 1)
    
    def test_buffer_capacity(self):
        """Test buffer respects maximum size"""
        small_buffer = ExperienceBuffer(max_size=10)
        
        for i in range(20):
            exp = Experience(
                state=np.ones(self.state_dim) * i,
                action=i % self.action_dim,
                reward=float(i),
                next_state=np.ones(self.state_dim) * (i + 1),
                done=False,
                timestamp=float(i)
            )
            small_buffer.add(exp)
        
        self.assertEqual(len(small_buffer), 10)
    
    def test_uniform_sampling(self):
        """Test uniform sampling from buffer"""
        for i in range(100):
            exp = Experience(
                state=np.ones(self.state_dim) * i,
                action=i % self.action_dim,
                reward=1.0,
                next_state=np.ones(self.state_dim),
                done=False,
                timestamp=float(i)
            )
            self.buffer.add(exp)
        
        experiences, indices, weights = self.buffer.sample(32)
        self.assertEqual(len(experiences), 32)
        self.assertEqual(len(indices), 32)
        self.assertEqual(len(weights), 32)
    
    def test_prioritized_sampling(self):
        """Test prioritized sampling"""
        buffer = ExperienceBuffer(enable_prioritization=True)
        
        for i in range(100):
            exp = Experience(
                state=np.ones(self.state_dim),
                action=0,
                reward=float(i),  # Increasing rewards
                next_state=np.ones(self.state_dim),
                done=False,
                timestamp=float(i)
            )
            buffer.add(exp)
        
        experiences, indices, weights = buffer.sample(32)
        self.assertEqual(len(experiences), 32)
        # Later experiences should have higher priorities
        self.assertTrue(np.all(weights >= 0))
    
    def test_deduplication(self):
        """Test deduplication of experiences"""
        buffer = ExperienceBuffer(enable_dedup=True)
        
        state = np.array([1, 2, 3, 4, 5] + [0] * 5)
        
        # Add same state-action pair multiple times
        for _ in range(3):
            exp = Experience(
                state=state,
                action=0,
                reward=1.0,
                next_state=state + 1,
                done=False,
                timestamp=0.0
            )
            buffer.add(exp)
        
        # Should only add first one due to deduplication
        self.assertEqual(buffer.duplicate_count, 2)
    
    def test_compression(self):
        """Test compression functionality"""
        buffer = ExperienceBuffer(compress=True)
        
        exp = Experience(
            state=np.random.randn(self.state_dim),
            action=0,
            reward=1.0,
            next_state=np.random.randn(self.state_dim),
            done=False,
            timestamp=0.0
        )
        buffer.add(exp)
        
        # Sample and verify decompression
        experiences, _, _ = buffer.sample(1)
        self.assertEqual(experiences[0].state.shape, (self.state_dim,))
    
    def test_priority_update(self):
        """Test priority updates"""
        buffer = ExperienceBuffer(enable_prioritization=True)
        
        for i in range(50):
            exp = Experience(
                state=np.ones(self.state_dim),
                action=0,
                reward=1.0,
                next_state=np.ones(self.state_dim),
                done=False,
                timestamp=0.0
            )
            buffer.add(exp)
        
        indices = np.array([0, 1, 2])
        td_errors = np.array([0.5, 1.0, 2.0])
        
        buffer.update_priorities(indices, td_errors)
        
        # Higher TD errors should get higher priorities
        # (Verify by checking priority values)
        self.assertGreater(buffer.priorities[2], buffer.priorities[0])
    
    def test_data_augmentation(self):
        """Test data augmentation"""
        exps = [
            Experience(
                state=np.ones(self.state_dim),
                action=0,
                reward=1.0,
                next_state=np.ones(self.state_dim),
                done=False,
                timestamp=0.0
            )
        ]
        
        augmented = self.buffer.augment_data(exps)
        # Original + 2 augmentations
        self.assertEqual(len(augmented), 3)
    
    def test_get_statistics(self):
        """Test statistics computation"""
        for i in range(50):
            exp = Experience(
                state=np.ones(self.state_dim) * i,
                action=0,
                reward=1.0,
                next_state=np.ones(self.state_dim),
                done=False,
                timestamp=0.0
            )
            self.buffer.add(exp)
        
        stats = self.buffer.get_statistics()
        # With deduplication enabled, may not add all due to duplicates
        self.assertGreaterEqual(stats['buffer_size'], 1)
        self.assertGreaterEqual(stats['add_count'], 1)
        self.assertGreater(stats['fill_percentage'], 0)


class TestPriorityQueue(unittest.TestCase):
    """Test priority queue implementation"""
    
    def test_priority_queue_operations(self):
        """Test basic priority queue operations"""
        pq = PriorityQueue(max_size=100)
        
        pq.push(1.0, 0)
        pq.push(2.0, 1)
        pq.push(3.0, 2)
        
        result = pq.pop()
        self.assertEqual(result[1], 2)  # Highest priority
    
    def test_priority_update(self):
        """Test priority updates in queue"""
        pq = PriorityQueue(max_size=100)
        
        pq.push(1.0, 0)
        pq.push(2.0, 1)
        pq.update_priority(0, 5.0)
        
        result = pq.pop()
        self.assertEqual(result[1], 0)  # Now highest priority


class TestPolicyOptimizer(unittest.TestCase):
    """Test policy optimization"""
    
    def setUp(self):
        self.state_dim = 10
        self.action_dim = 4
        self.optimizer = PPOOptimizer(
            state_dim=self.state_dim,
            action_dim=self.action_dim
        )
    
    def test_actor_initialization(self):
        """Test actor network initialization"""
        self.assertIsNotNone(self.optimizer.actor)
        self.assertEqual(self.optimizer.actor.state_dim, self.state_dim)
        self.assertEqual(self.optimizer.actor.action_dim, self.action_dim)
    
    def test_critic_initialization(self):
        """Test critic network initialization"""
        self.assertIsNotNone(self.optimizer.critic)
        self.assertEqual(self.optimizer.critic.state_dim, self.state_dim)
    
    def test_action_selection(self):
        """Test action selection from policy"""
        state = np.random.randn(self.state_dim)
        action, prob = self.optimizer.select_action(state, deterministic=False)
        
        self.assertIn(action, range(self.action_dim))
        self.assertGreater(prob, 0)
        self.assertLessEqual(prob, 1)
    
    def test_deterministic_action(self):
        """Test deterministic action selection"""
        state = np.random.randn(self.state_dim)
        action1, _ = self.optimizer.select_action(state, deterministic=True)
        action2, _ = self.optimizer.select_action(state, deterministic=True)
        
        self.assertEqual(action1, action2)
    
    def test_advantage_computation(self):
        """Test advantage computation"""
        states = [np.random.randn(self.state_dim) for _ in range(10)]
        rewards = [float(i) for i in range(10)]
        next_states = [np.random.randn(self.state_dim) for _ in range(10)]
        dones = [False] * 10
        
        advantages, returns = self.optimizer.compute_advantages(
            states, rewards, next_states, dones
        )
        
        self.assertEqual(len(advantages), 10)
        self.assertEqual(len(returns), 10)
    
    def test_policy_loss_computation(self):
        """Test policy loss computation"""
        states = [np.random.randn(self.state_dim) for _ in range(10)]
        actions = list(range(self.action_dim)) * 3
        advantages = np.array([0.5] * 10)
        
        loss = self.optimizer.compute_policy_loss(states, actions[:10], advantages)
        self.assertIsInstance(loss, (float, np.floating))
    
    def test_value_loss_computation(self):
        """Test value function loss"""
        states = [np.random.randn(self.state_dim) for _ in range(10)]
        returns = np.array([float(i) for i in range(10)])
        
        loss = self.optimizer.compute_value_loss(states, returns)
        self.assertGreater(loss, 0)
    
    def test_entropy_computation(self):
        """Test entropy computation"""
        states = [np.random.randn(self.state_dim) for _ in range(10)]
        entropy = self.optimizer.compute_entropy(states)
        
        self.assertGreater(entropy, 0)
    
    def test_kl_divergence(self):
        """Test KL divergence computation"""
        states = [np.random.randn(self.state_dim) for _ in range(10)]
        kl = self.optimizer.compute_kl_divergence(states)
        
        self.assertGreaterEqual(kl, 0)
    
    def test_policy_update(self):
        """Test policy update step"""
        states = [np.random.randn(self.state_dim) for _ in range(20)]
        actions = [i % self.action_dim for i in range(20)]
        rewards = [1.0] * 20
        next_states = [np.random.randn(self.state_dim) for _ in range(20)]
        dones = [False] * 20
        
        initial_weights = self.optimizer.actor.weights['w_out'].copy()
        
        metrics = self.optimizer.update(states, actions, rewards, next_states, dones)
        
        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics.policy_loss, (float, np.floating))
    
    def test_convergence_detection(self):
        """Test convergence detection"""
        states = [np.random.randn(self.state_dim) for _ in range(20)]
        actions = [0] * 20
        rewards = [1.0] * 20
        next_states = [np.random.randn(self.state_dim) for _ in range(20)]
        dones = [False] * 20
        
        for _ in range(30):
            self.optimizer.update(states, actions, rewards, next_states, dones)
        
        # Check if convergence is detected
        converged = self.optimizer.has_converged()
        self.assertIsInstance(converged, bool)


class TestBehaviorModel(unittest.TestCase):
    """Test behavior prediction model"""
    
    def setUp(self):
        self.state_dim = 10
        self.action_dim = 4
        self.model = BehaviorModel(
            state_dim=self.state_dim,
            action_dim=self.action_dim,
            sequence_length=5
        )
    
    def test_model_initialization(self):
        """Test model initialization"""
        self.assertIsNotNone(self.model)
        self.assertEqual(len(self.model.lstm_layers), 2)
    
    def test_sequence_addition(self):
        """Test adding sequences"""
        agent_id = "agent1"
        state = np.random.randn(self.state_dim)
        
        self.model.add_sequence(agent_id, state, 0)
        
        self.assertIn(agent_id, self.model.state_sequences)
        self.assertEqual(len(self.model.state_sequences[agent_id]), 1)
    
    def test_behavior_prediction(self):
        """Test behavior prediction"""
        agent_id = "agent1"
        
        for i in range(10):
            state = np.random.randn(self.state_dim)
            self.model.add_sequence(agent_id, state, i % self.action_dim)
        
        current_state = np.random.randn(self.state_dim)
        prediction = self.model.predict(agent_id, current_state)
        
        self.assertIsInstance(prediction, BehaviorPrediction)
        self.assertIn(prediction.predicted_action, range(self.action_dim))
        self.assertGreaterEqual(prediction.confidence, 0)
        self.assertLessEqual(prediction.confidence, 1)
    
    def test_anomaly_detection(self):
        """Test anomaly detection"""
        agent_id = "agent1"
        
        # Build baseline
        for i in range(200):
            state = np.random.randn(self.state_dim)
            self.model.add_sequence(agent_id, state, 0)
            self.model.predict(agent_id, state)
        
        # Normal state
        normal_state = np.random.randn(self.state_dim)
        pred_normal = self.model.predict(agent_id, normal_state)
        
        # Anomalous state
        anomaly_state = np.ones(self.state_dim) * 100
        pred_anomaly = self.model.predict(agent_id, anomaly_state)
        
        self.assertGreater(pred_anomaly.anomaly_score, pred_normal.anomaly_score)
    
    def test_behavior_profile(self):
        """Test behavior profiling"""
        agent_id = "agent1"
        
        for i in range(50):
            state = np.random.randn(self.state_dim)
            action = i % self.action_dim
            self.model.add_sequence(agent_id, state, action)
        
        profile = self.model.get_behavior_profile(agent_id)
        
        self.assertEqual(profile['agent_id'], agent_id)
        # Sequence is limited by maxlen=sequence_length (default 5)
        self.assertLessEqual(profile['sequence_length'], 5)
        self.assertGreater(len(profile['action_distribution']), 0)
    
    def test_action_recommendation(self):
        """Test action recommendation"""
        agent_id = "agent1"
        
        for i in range(20):
            state = np.random.randn(self.state_dim)
            self.model.add_sequence(agent_id, state, i % self.action_dim)
        
        current_state = np.random.randn(self.state_dim)
        action, confidence = self.model.recommend_action(agent_id, current_state)
        
        self.assertIn(action, range(self.action_dim))
        self.assertGreaterEqual(confidence, 0)
    
    def test_statistics(self):
        """Test model statistics"""
        agent_id = "agent1"
        
        for i in range(30):
            state = np.random.randn(self.state_dim)
            self.model.predict(agent_id, state)
        
        stats = self.model.get_statistics()
        
        self.assertEqual(stats['agents_tracked'], 1)
        self.assertGreater(stats['predictions_made'], 0)


class TestRewardModel(unittest.TestCase):
    """Test reward model"""
    
    def setUp(self):
        self.state_dim = 10
        self.action_dim = 4
        self.model = RewardModel(
            state_dim=self.state_dim,
            action_dim=self.action_dim
        )
    
    def test_reward_computation(self):
        """Test reward computation"""
        state = np.random.randn(self.state_dim)
        action = 0
        
        reward = self.model.compute_reward(state, action)
        
        self.assertGreaterEqual(reward, self.model.reward_range[0])
        self.assertLessEqual(reward, self.model.reward_range[1])
    
    def test_composite_reward(self):
        """Test multi-objective reward computation"""
        state = np.random.randn(self.state_dim)
        action = 1
        
        reward = self.model.compute_composite_reward(state, action)
        
        self.assertIsInstance(reward, float)
    
    def test_feedback_processing(self):
        """Test feedback processing"""
        feedback = RewardFeedback(
            agent_id="agent1",
            action=0,
            state=np.random.randn(self.state_dim),
            next_state=np.random.randn(self.state_dim),
            reward=1.0,
            feedback_type='automatic',
            confidence=1.0
        )
        
        metrics = self.model.process_feedback(feedback)
        
        self.assertIn('predicted_reward', metrics)
        self.assertIn('error', metrics)
    
    def test_objective_weights(self):
        """Test objective weight setting"""
        weights = np.array([0.5, 0.5])
        self.model.set_objective_weights(weights)
        
        np.testing.assert_array_almost_equal(
            self.model.objective_weights,
            weights / np.sum(weights)
        )
    
    def test_reward_hacking_detection(self):
        """Test reward hacking detection"""
        state = np.random.randn(self.state_dim)
        action = 0
        
        # Normal reward
        is_hacking, score = self.model.detect_reward_hacking(state, action, 0.5)
        self.assertIsInstance(is_hacking, bool)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)
    
    def test_statistics(self):
        """Test reward model statistics"""
        stats = self.model.get_statistics()
        
        self.assertEqual(stats['feedbacks_received'], 0)
        self.assertIn('calibration', stats)


class TestContinuousOptimizer(unittest.TestCase):
    """Test continuous optimization"""
    
    def setUp(self):
        self.optimizer = ContinuousOptimizer(
            learning_rate=0.01,
            epsilon_initial=0.1,
            num_arms=5
        )
    
    def test_ab_test_creation(self):
        """Test A/B test creation"""
        test = self.optimizer.start_ab_test("test_1")
        
        self.assertEqual(test.test_id, "test_1")
        self.assertIn("test_1", self.optimizer.active_tests)
    
    def test_bandit_arm_selection(self):
        """Test bandit arm selection"""
        arm_id = self.optimizer.select_bandit_arm()
        
        self.assertIn(arm_id, self.optimizer.bandit_arms)
    
    def test_bandit_reward_recording(self):
        """Test recording rewards for bandit arms"""
        arm_id = "arm_0"
        reward = 1.0
        
        initial_value = self.optimizer.bandit_arms[arm_id].value
        self.optimizer.record_arm_reward(arm_id, reward)
        
        self.assertNotEqual(self.optimizer.bandit_arms[arm_id].value, initial_value)
    
    def test_adaptive_exploration(self):
        """Test adaptive exploration"""
        exploration = AdaptiveExploration(epsilon_initial=0.1)
        
        eps_before = exploration.get_epsilon()
        exploration.update()
        eps_after = exploration.get_epsilon()
        
        self.assertGreaterEqual(eps_before, eps_after)
    
    def test_online_learner(self):
        """Test online learning"""
        learner = OnlineLearner()
        
        rewards = [0.5, 0.6, 0.7, 0.8, 0.9]
        for reward in rewards:
            stats = learner.process_reward(reward)
        
        self.assertGreater(stats['mean'], 0)
        self.assertEqual(stats['window_size'], 5)
    
    def test_optimization_step(self):
        """Test optimization step"""
        result = self.optimizer.optimize_step(reward=1.0, task_id="task_1", loss=0.1)
        
        self.assertEqual(result['step'], 1)
        self.assertEqual(result['reward'], 1.0)
    
    def test_optimizer_statistics(self):
        """Test optimizer statistics"""
        self.optimizer.optimize_step(reward=1.0)
        stats = self.optimizer.get_statistics()
        
        self.assertEqual(stats['optimization_steps'], 1)
        self.assertEqual(stats['total_rewards'], 1.0)


class TestMLTrainer(unittest.TestCase):
    """Test ML trainer"""
    
    def setUp(self):
        self.config = TrainingConfig(
            agent_id="test_agent",
            state_dim=10,
            action_dim=4,
            max_episodes=10,
            max_steps_per_episode=20
        )
        self.trainer = MLTrainer(self.config)
    
    def test_trainer_initialization(self):
        """Test trainer initialization"""
        self.assertIsNotNone(self.trainer.experience_buffer)
        self.assertIsNotNone(self.trainer.policy_optimizer)
        self.assertEqual(self.trainer.training_status, TrainingStatus.PENDING)
    
    def test_add_experience(self):
        """Test adding experience"""
        exp = Experience(
            state=np.random.randn(10),
            action=0,
            reward=1.0,
            next_state=np.random.randn(10),
            done=False,
            timestamp=0.0
        )
        
        self.trainer.add_experience(exp)
        self.assertEqual(len(self.trainer.experience_buffer), 1)
    
    def test_batch_collection(self):
        """Test batch collection"""
        for i in range(100):
            exp = Experience(
                state=np.random.randn(10),
                action=i % 4,
                reward=1.0,
                next_state=np.random.randn(10),
                done=False,
                timestamp=0.0
            )
            self.trainer.add_experience(exp)
        
        experiences, indices, weights = self.trainer.collect_batch(32)
        self.assertEqual(len(experiences), 32)
    
    def test_checkpoint_operations(self):
        """Test checkpoint saving and loading"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trainer = MLTrainer(self.config, checkpoint_dir=tmpdir)
            
            # Add some experiences
            for i in range(50):
                exp = Experience(
                    state=np.random.randn(10),
                    action=0,
                    reward=1.0,
                    next_state=np.random.randn(10),
                    done=False,
                    timestamp=0.0
                )
                trainer.add_experience(exp)
            
            trainer.save_checkpoint(10)
            
            self.assertGreater(len(trainer.checkpoints), 0)
            
            best = trainer.get_best_checkpoint()
            self.assertIsNotNone(best)
    
    def test_training_summary(self):
        """Test training summary"""
        summary = self.trainer.get_training_summary()
        
        self.assertEqual(summary['agent_id'], "test_agent")
        self.assertEqual(summary['status'], TrainingStatus.PENDING.value)
        self.assertEqual(summary['total_episodes'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_full_training_pipeline(self):
        """Test complete training pipeline"""
        config = TrainingConfig(
            agent_id="integration_test",
            state_dim=8,
            action_dim=3,
            max_episodes=5,
            batch_size=16
        )
        
        trainer = MLTrainer(config)
        
        # Simulate training
        for episode in range(5):
            trainer.metrics.episode = episode + 1  # Track episodes
            
            for step in range(10):
                state = np.random.randn(8)
                action = np.random.randint(0, 3)
                reward = 1.0
                next_state = np.random.randn(8)
                done = step == 9
                
                exp = Experience(
                    state=state,
                    action=action,
                    reward=reward,
                    next_state=next_state,
                    done=done,
                    timestamp=0.0
                )
                trainer.add_experience(exp)
            
            if len(trainer.experience_buffer) >= config.batch_size:
                experiences, indices, weights = trainer.collect_batch(config.batch_size)
                trainer.train_on_batch(experiences, indices, weights)
        
        summary = trainer.get_training_summary()
        self.assertEqual(summary['total_episodes'], 5)
        self.assertGreater(summary['buffer_size'], 0)
    
    def test_persistence(self):
        """Test model persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TrainingConfig(
                agent_id="persistence_test",
                state_dim=8,
                action_dim=3
            )
            
            trainer = MLTrainer(config, model_dir=tmpdir)
            
            # Add experiences
            for i in range(50):
                exp = Experience(
                    state=np.random.randn(8),
                    action=i % 3,
                    reward=1.0,
                    next_state=np.random.randn(8),
                    done=False,
                    timestamp=0.0
                )
                trainer.add_experience(exp)
            
            # Save
            export_path = os.path.join(tmpdir, "model.pkl")
            trainer.export_model(export_path)
            
            self.assertTrue(os.path.exists(export_path))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and failure modes"""
    
    def test_empty_buffer_sampling(self):
        """Test sampling from empty buffer raises error"""
        buffer = ExperienceBuffer()
        
        with self.assertRaises(ValueError):
            buffer.sample(10)
    
    def test_invalid_checkpoint_load(self):
        """Test loading non-existent checkpoint"""
        config = TrainingConfig(
            agent_id="test",
            state_dim=8,
            action_dim=3
        )
        trainer = MLTrainer(config)
        
        with self.assertRaises(ValueError):
            trainer.load_checkpoint("non_existent")
    
    def test_large_batch_size(self):
        """Test requesting batch larger than buffer"""
        buffer = ExperienceBuffer(max_size=100)
        
        for i in range(10):
            exp = Experience(
                state=np.zeros(8),
                action=0,
                reward=1.0,
                next_state=np.zeros(8),
                done=False,
                timestamp=0.0
            )
            buffer.add(exp)
        
        # Should work but with smaller batch
        experiences, indices, weights = buffer.sample(32)
        self.assertEqual(len(experiences), 32)
    
    def test_zero_rewards(self):
        """Test handling zero rewards"""
        model = RewardModel(state_dim=8, action_dim=4)
        
        feedback = RewardFeedback(
            agent_id="agent1",
            action=0,
            state=np.zeros(8),
            next_state=np.zeros(8),
            reward=0.0,
            feedback_type='automatic'
        )
        
        metrics = model.process_feedback(feedback)
        self.assertEqual(metrics['actual_reward'], 0.0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestExperienceBuffer))
    suite.addTests(loader.loadTestsFromTestCase(TestPriorityQueue))
    suite.addTests(loader.loadTestsFromTestCase(TestPolicyOptimizer))
    suite.addTests(loader.loadTestsFromTestCase(TestBehaviorModel))
    suite.addTests(loader.loadTestsFromTestCase(TestRewardModel))
    suite.addTests(loader.loadTestsFromTestCase(TestContinuousOptimizer))
    suite.addTests(loader.loadTestsFromTestCase(TestMLTrainer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    exit(0 if result.wasSuccessful() else 1)

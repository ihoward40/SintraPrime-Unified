"""
Behavior Model using LSTM for sequence prediction
Predicts agent actions and detects anomalies
"""

import numpy as np
import logging
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from collections import deque
import pickle

logger = logging.getLogger(__name__)


@dataclass
class BehaviorPrediction:
    """Output of behavior prediction"""
    predicted_action: int
    confidence: float
    top_k_actions: List[Tuple[int, float]]
    is_anomaly: bool
    anomaly_score: float
    sequence_length: int


class SimpleLSTMCell:
    """Simplified LSTM cell implementation"""
    
    def __init__(self, input_size: int, hidden_size: int):
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        # Initialize weights
        self.Wf = np.random.randn(input_size + hidden_size, hidden_size) * 0.01
        self.bf = np.zeros((1, hidden_size))
        
        self.Wi = np.random.randn(input_size + hidden_size, hidden_size) * 0.01
        self.bi = np.zeros((1, hidden_size))
        
        self.Wc = np.random.randn(input_size + hidden_size, hidden_size) * 0.01
        self.bc = np.zeros((1, hidden_size))
        
        self.Wo = np.random.randn(input_size + hidden_size, hidden_size) * 0.01
        self.bo = np.zeros((1, hidden_size))
    
    def forward(self, x: np.ndarray, h: np.ndarray, c: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Forward pass through LSTM cell"""
        combined = np.concatenate([x, h], axis=1)
        
        # Forget gate
        f = self._sigmoid(np.dot(combined, self.Wf) + self.bf)
        
        # Input gate
        i = self._sigmoid(np.dot(combined, self.Wi) + self.bi)
        
        # Cell candidate
        c_hat = np.tanh(np.dot(combined, self.Wc) + self.bc)
        
        # Output gate
        o = self._sigmoid(np.dot(combined, self.Wo) + self.bo)
        
        # New cell state
        c_new = f * c + i * c_hat
        
        # New hidden state
        h_new = o * np.tanh(c_new)
        
        return h_new, c_new
    
    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        """Sigmoid activation"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))


class BehaviorModel:
    """
    LSTM-based model for predicting agent behavior
    Supports sequence prediction, anomaly detection, and action recommendations
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        sequence_length: int = 10,
        anomaly_threshold: float = 0.5
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.sequence_length = sequence_length
        self.anomaly_threshold = anomaly_threshold
        
        # Build LSTM layers
        self.lstm_layers = []
        input_size = state_dim
        
        for _ in range(num_layers):
            self.lstm_layers.append(SimpleLSTMCell(input_size, hidden_size))
            input_size = hidden_size
        
        # Output layer
        self.W_out = np.random.randn(hidden_size, action_dim) * 0.01
        self.b_out = np.zeros((1, action_dim))
        
        # Sequence buffer for each agent
        self.state_sequences = {}
        self.action_sequences = {}
        self.sequence_encodings = deque(maxlen=1000)
        
        # Baseline for anomaly detection
        self.baseline_encoding = None
        self.encoding_mean = None
        self.encoding_std = None
        
        # Statistics
        self.predictions_made = 0
        self.correct_predictions = 0
        self.anomalies_detected = 0
    
    def add_sequence(self, agent_id: str, state: np.ndarray, action: int):
        """Add state-action pair to sequence buffer"""
        if agent_id not in self.state_sequences:
            self.state_sequences[agent_id] = deque(maxlen=self.sequence_length)
            self.action_sequences[agent_id] = deque(maxlen=self.sequence_length)
        
        self.state_sequences[agent_id].append(state.flatten())
        self.action_sequences[agent_id].append(action)
    
    def _encode_sequence(self, agent_id: str) -> Optional[np.ndarray]:
        """Encode sequence using LSTM"""
        if agent_id not in self.state_sequences:
            return None
        
        states = list(self.state_sequences[agent_id])
        if len(states) == 0:
            return None
        
        # Pad or truncate to sequence length
        if len(states) < self.sequence_length:
            states = [np.zeros(self.state_dim)] * (self.sequence_length - len(states)) + states
        else:
            states = states[-self.sequence_length:]
        
        # Initialize hidden states
        h = [np.zeros((1, self.hidden_size)) for _ in range(self.num_layers)]
        c = [np.zeros((1, self.hidden_size)) for _ in range(self.num_layers)]
        
        # Forward pass through LSTM
        for state in states:
            x = state.reshape(1, -1)
            
            for layer_idx in range(self.num_layers):
                h[layer_idx], c[layer_idx] = self.lstm_layers[layer_idx].forward(
                    x, h[layer_idx], c[layer_idx]
                )
                x = h[layer_idx]
        
        # Return final hidden state
        return h[-1].flatten()
    
    def predict(self, agent_id: str, current_state: np.ndarray) -> BehaviorPrediction:
        """Predict next action for agent"""
        self.predictions_made += 1
        
        # Add current state to sequence
        self.add_sequence(agent_id, current_state, -1)
        
        # Encode sequence
        encoding = self._encode_sequence(agent_id)
        
        if encoding is None:
            # Not enough data, return random prediction
            return BehaviorPrediction(
                predicted_action=0,
                confidence=0.0,
                top_k_actions=[(0, 0.0)],
                is_anomaly=False,
                anomaly_score=0.0,
                sequence_length=0
            )
        
        # Store encoding
        self.sequence_encodings.append(encoding)
        
        # Update baseline statistics
        if len(self.sequence_encodings) > 100:
            self._update_baseline_stats()
        
        # Output layer
        logits = np.dot(encoding.reshape(1, -1), self.W_out) + self.b_out
        probs = self._softmax(logits[0])
        
        # Get top predictions
        top_indices = np.argsort(-probs)[:3]
        top_k = [(int(idx), float(probs[idx])) for idx in top_indices]
        
        predicted_action = int(top_indices[0])
        confidence = float(probs[top_indices[0]])
        
        # Anomaly detection
        is_anomaly, anomaly_score = self._detect_anomaly(encoding)
        
        if is_anomaly:
            self.anomalies_detected += 1
        
        seq_len = len(self.state_sequences.get(agent_id, []))
        
        return BehaviorPrediction(
            predicted_action=predicted_action,
            confidence=confidence,
            top_k_actions=top_k,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            sequence_length=seq_len
        )
    
    def predict_next_state(
        self,
        agent_id: str,
        current_state: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """Predict next state given current state"""
        encoding = self._encode_sequence(agent_id)
        
        if encoding is None:
            return current_state, 0.0
        
        # Use encoding as bias for next state prediction
        noise = np.random.randn(*current_state.shape) * 0.01
        next_state = current_state + (encoding[:current_state.shape[0]] if encoding.shape[0] >= current_state.shape[0] 
                                      else np.pad(encoding, (0, current_state.shape[0] - encoding.shape[0]))) + noise
        
        confidence = float(np.clip(1 - np.mean(np.abs(noise)), 0, 1))
        
        return next_state, confidence
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax activation"""
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)
    
    def _detect_anomaly(self, encoding: np.ndarray) -> Tuple[bool, float]:
        """Detect anomalous behavior"""
        if self.baseline_encoding is None or len(self.sequence_encodings) < 100:
            return False, 0.0
        
        # Compute distance from baseline
        distance = np.linalg.norm(encoding - self.baseline_encoding)
        
        # Normalize by standard deviation
        if self.encoding_std is not None and np.mean(self.encoding_std) > 0:
            normalized_distance = distance / np.mean(self.encoding_std)
        else:
            normalized_distance = distance
        
        anomaly_score = float(np.tanh(normalized_distance))
        is_anomaly = anomaly_score > self.anomaly_threshold
        
        return is_anomaly, anomaly_score
    
    def _update_baseline_stats(self):
        """Update baseline statistics for anomaly detection"""
        encodings = np.array(list(self.sequence_encodings))
        
        # Use median as baseline (robust to outliers)
        self.baseline_encoding = np.median(encodings, axis=0)
        self.encoding_mean = np.mean(encodings, axis=0)
        self.encoding_std = np.std(encodings, axis=0)
    
    def recommend_action(
        self,
        agent_id: str,
        current_state: np.ndarray,
        available_actions: Optional[List[int]] = None
    ) -> Tuple[int, float]:
        """
        Recommend best action based on learned behavior patterns
        """
        prediction = self.predict(agent_id, current_state)
        
        recommended_action = prediction.predicted_action
        confidence = prediction.confidence
        
        # Filter by available actions if provided
        if available_actions is not None:
            for action, action_conf in prediction.top_k_actions:
                if action in available_actions:
                    recommended_action = action
                    confidence = action_conf
                    break
        
        return recommended_action, confidence
    
    def get_behavior_profile(self, agent_id: str) -> Dict:
        """Get behavioral profile of agent"""
        if agent_id not in self.state_sequences:
            return {
                'agent_id': agent_id,
                'sequence_length': 0,
                'action_distribution': {},
                'state_variance': 0.0,
                'behavior_entropy': 0.0
            }
        
        # Action distribution
        actions = list(self.action_sequences[agent_id])
        action_dist = {}
        for action in actions:
            action_dist[action] = action_dist.get(action, 0) + 1
        
        total = len(actions)
        if total > 0:
            action_dist = {k: v / total for k, v in action_dist.items()}
        
        # State variance
        states = np.array(list(self.state_sequences[agent_id]))
        state_variance = float(np.var(states)) if len(states) > 0 else 0.0
        
        # Behavior entropy
        behavior_entropy = -sum(p * np.log(p + 1e-8) for p in action_dist.values())
        
        return {
            'agent_id': agent_id,
            'sequence_length': len(actions),
            'action_distribution': action_dist,
            'state_variance': state_variance,
            'behavior_entropy': float(behavior_entropy)
        }
    
    def get_statistics(self) -> Dict:
        """Get model statistics"""
        accuracy = (self.correct_predictions / self.predictions_made * 100 
                   if self.predictions_made > 0 else 0)
        
        anomaly_rate = (self.anomalies_detected / self.predictions_made * 100
                       if self.predictions_made > 0 else 0)
        
        return {
            'predictions_made': self.predictions_made,
            'correct_predictions': self.correct_predictions,
            'accuracy': accuracy,
            'anomalies_detected': self.anomalies_detected,
            'anomaly_rate': anomaly_rate,
            'sequence_encodings_stored': len(self.sequence_encodings),
            'agents_tracked': len(self.state_sequences)
        }
    
    def update_prediction(self, agent_id: str, action: int, reward: float):
        """Update model with actual action taken"""
        # Update action sequence
        if agent_id in self.action_sequences:
            if len(self.action_sequences[agent_id]) > 0:
                self.action_sequences[agent_id][-1] = action
    
    def save(self, path: str):
        """Save model to file"""
        state = {
            'lstm_weights': [
                {
                    'Wf': layer.Wf,
                    'bf': layer.bf,
                    'Wi': layer.Wi,
                    'bi': layer.bi,
                    'Wc': layer.Wc,
                    'bc': layer.bc,
                    'Wo': layer.Wo,
                    'bo': layer.bo
                }
                for layer in self.lstm_layers
            ],
            'W_out': self.W_out,
            'b_out': self.b_out,
            'baseline_encoding': self.baseline_encoding,
            'encoding_mean': self.encoding_mean,
            'encoding_std': self.encoding_std,
            'statistics': self.get_statistics()
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
        logger.info(f"Behavior model saved to {path}")
    
    def load(self, path: str):
        """Load model from file"""
        with open(path, 'rb') as f:
            state = pickle.load(f)
        
        for i, weights in enumerate(state['lstm_weights']):
            self.lstm_layers[i].Wf = weights['Wf']
            self.lstm_layers[i].bf = weights['bf']
            self.lstm_layers[i].Wi = weights['Wi']
            self.lstm_layers[i].bi = weights['bi']
            self.lstm_layers[i].Wc = weights['Wc']
            self.lstm_layers[i].bc = weights['bc']
            self.lstm_layers[i].Wo = weights['Wo']
            self.lstm_layers[i].bo = weights['bo']
        
        self.W_out = state['W_out']
        self.b_out = state['b_out']
        self.baseline_encoding = state['baseline_encoding']
        self.encoding_mean = state['encoding_mean']
        self.encoding_std = state['encoding_std']
        
        logger.info(f"Behavior model loaded from {path}")

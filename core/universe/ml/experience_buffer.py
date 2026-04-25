"""
Experience Buffer for ML Feedback Loops & Self-Learning Agents
Implements circular buffer with prioritized replay, augmentation, and compression
"""

import numpy as np
import pickle
import zlib
from collections import deque
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Single experience tuple"""
    state: np.ndarray
    action: Any
    reward: float
    next_state: np.ndarray
    done: bool
    timestamp: float
    agent_id: str = ""
    metadata: Dict = None


class PriorityQueue:
    """Max-heap based priority queue for experience prioritization"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.heap = []
        self.position_map = {}
        self.size = 0
    
    def push(self, priority: float, idx: int):
        """Add experience with priority"""
        if self.size >= self.max_size:
            return False
        
        self.heap.append((priority, idx))
        self.position_map[idx] = self.size
        self.size += 1
        self._heapify_up(self.size - 1)
        return True
    
    def update_priority(self, idx: int, new_priority: float):
        """Update priority of existing experience"""
        if idx not in self.position_map:
            return
        
        pos = self.position_map[idx]
        old_priority = self.heap[pos][0]
        self.heap[pos] = (new_priority, idx)
        
        if new_priority > old_priority:
            self._heapify_up(pos)
        else:
            self._heapify_down(pos)
    
    def pop(self) -> Optional[Tuple[float, int]]:
        """Get highest priority experience"""
        if self.size == 0:
            return None
        
        result = self.heap[0]
        last = self.heap[self.size - 1]
        
        self.heap[0] = last
        self.position_map[last[1]] = 0
        self.heap.pop()
        self.size -= 1
        
        if self.size > 0:
            self._heapify_down(0)
        
        del self.position_map[result[1]]
        return result
    
    def _heapify_up(self, idx: int):
        """Maintain heap property upward"""
        while idx > 0:
            parent_idx = (idx - 1) // 2
            if self.heap[idx][0] > self.heap[parent_idx][0]:
                self.heap[idx], self.heap[parent_idx] = self.heap[parent_idx], self.heap[idx]
                self.position_map[self.heap[idx][1]] = idx
                self.position_map[self.heap[parent_idx][1]] = parent_idx
                idx = parent_idx
            else:
                break
    
    def _heapify_down(self, idx: int):
        """Maintain heap property downward"""
        while True:
            smallest = idx
            left_idx = 2 * idx + 1
            right_idx = 2 * idx + 2
            
            if left_idx < self.size and self.heap[left_idx][0] > self.heap[smallest][0]:
                smallest = left_idx
            if right_idx < self.size and self.heap[right_idx][0] > self.heap[smallest][0]:
                smallest = right_idx
            
            if smallest != idx:
                self.heap[idx], self.heap[smallest] = self.heap[smallest], self.heap[idx]
                self.position_map[self.heap[idx][1]] = idx
                self.position_map[self.heap[smallest][1]] = smallest
                idx = smallest
            else:
                break


class ExperienceBuffer:
    """
    Circular buffer for storing and replaying experiences.
    Supports prioritized replay, augmentation, deduplication, and compression.
    """
    
    def __init__(
        self,
        max_size: int = 100000,
        compress: bool = True,
        enable_dedup: bool = True,
        enable_prioritization: bool = True,
        alpha: float = 0.6,
        beta: float = 0.4,
        beta_increment: float = 0.001
    ):
        self.max_size = max_size
        self.compress = compress
        self.enable_dedup = enable_dedup
        self.enable_prioritization = enable_prioritization
        
        self.buffer = deque(maxlen=max_size)
        self.priorities = np.zeros(max_size)
        self.priority_queue = PriorityQueue(max_size) if enable_prioritization else None
        
        # Prioritized experience replay parameters
        self.alpha = alpha  # priority exponent
        self.beta = beta    # importance sampling exponent
        self.beta_increment = beta_increment
        self.max_priority = 1.0
        
        # Deduplication
        self.seen_hashes = set()
        self.hash_to_idx = {}
        
        # Statistics
        self.add_count = 0
        self.sample_count = 0
        self.duplicate_count = 0
    
    def _get_state_hash(self, state: np.ndarray, action: Any) -> str:
        """Generate hash for deduplication"""
        try:
            state_bytes = pickle.dumps(state)
            action_bytes = pickle.dumps(action)
            combined = state_bytes + action_bytes
            return hashlib.md5(combined).hexdigest()
        except:
            return None
    
    def add(self, experience: Experience):
        """Add experience to buffer with optional deduplication"""
        # Check for duplicates
        if self.enable_dedup:
            state_hash = self._get_state_hash(experience.state, experience.action)
            if state_hash and state_hash in self.seen_hashes:
                self.duplicate_count += 1
                return
            if state_hash:
                self.seen_hashes.add(state_hash)
        
        # Store experience (with compression if enabled)
        if self.compress:
            experience = self._compress_experience(experience)
        
        self.buffer.append(experience)
        idx = len(self.buffer) - 1
        
        # Set priority
        if self.enable_prioritization:
            priority = self.max_priority ** self.alpha
            self.priorities[idx] = priority
            self.priority_queue.push(priority, idx)
        
        self.add_count += 1
    
    def _compress_experience(self, exp: Experience) -> Experience:
        """Compress experience data using zlib"""
        compressed_exp = Experience(
            state=zlib.compress(pickle.dumps(exp.state)),
            action=zlib.compress(pickle.dumps(exp.action)),
            reward=exp.reward,
            next_state=zlib.compress(pickle.dumps(exp.next_state)),
            done=exp.done,
            timestamp=exp.timestamp,
            agent_id=exp.agent_id,
            metadata=exp.metadata
        )
        return compressed_exp
    
    def _decompress_experience(self, exp: Experience) -> Experience:
        """Decompress experience data"""
        decompressed_exp = Experience(
            state=pickle.loads(zlib.decompress(exp.state)),
            action=pickle.loads(zlib.decompress(exp.action)),
            reward=exp.reward,
            next_state=pickle.loads(zlib.decompress(exp.next_state)),
            done=exp.done,
            timestamp=exp.timestamp,
            agent_id=exp.agent_id,
            metadata=exp.metadata
        )
        return decompressed_exp
    
    def sample(self, batch_size: int) -> Tuple[List[Experience], np.ndarray, np.ndarray]:
        """
        Sample experiences with importance sampling weights
        Returns: (experiences, indices, weights)
        """
        if len(self.buffer) == 0:
            raise ValueError("Buffer is empty")
        
        self.sample_count += 1
        
        if self.enable_prioritization:
            return self._prioritized_sample(batch_size)
        else:
            return self._uniform_sample(batch_size)
    
    def _uniform_sample(self, batch_size: int) -> Tuple[List[Experience], np.ndarray, np.ndarray]:
        """Uniform random sampling"""
        indices = np.random.choice(len(self.buffer), batch_size, replace=True)
        experiences = [self.buffer[i] for i in indices]
        
        # Uniform weights
        weights = np.ones(batch_size) / batch_size
        
        # Decompress if needed
        experiences = [self._decompress_experience(e) if self.compress else e 
                       for e in experiences]
        
        return experiences, indices, weights
    
    def _prioritized_sample(self, batch_size: int) -> Tuple[List[Experience], np.ndarray, np.ndarray]:
        """Prioritized experience replay with importance sampling"""
        if len(self.buffer) == 0:
            raise ValueError("Buffer is empty")
        
        # Calculate priorities and sample
        priorities = self.priorities[:len(self.buffer)]
        priorities = np.maximum(priorities, 1e-6)  # Ensure positive
        probabilities = priorities / np.sum(priorities)
        
        # Ensure probabilities sum to 1 (fix floating point errors)
        probabilities = probabilities / np.sum(probabilities)
        
        indices = np.random.choice(
            len(self.buffer),
            batch_size,
            p=probabilities,
            replace=True
        )
        
        experiences = [self.buffer[i] for i in indices]
        
        # Importance sampling weights
        self.beta = min(1.0, self.beta + self.beta_increment)
        weights = (len(self.buffer) * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()
        
        # Decompress if needed
        experiences = [self._decompress_experience(e) if self.compress else e 
                       for e in experiences]
        
        return experiences, indices, weights
    
    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray):
        """Update priorities based on TD errors"""
        if not self.enable_prioritization:
            return
        
        for idx, td_error in zip(indices, td_errors):
            priority = (np.abs(td_error) + 1e-6) ** self.alpha
            self.priorities[idx] = priority
            self.max_priority = max(self.max_priority, priority)
            
            if self.priority_queue:
                self.priority_queue.update_priority(idx, priority)
    
    def augment_data(self, experiences: List[Experience]) -> List[Experience]:
        """
        Data augmentation: create variations of experiences
        Useful for improving model generalization
        """
        augmented = []
        
        for exp in experiences:
            # Original
            augmented.append(exp)
            
            # State jitter (add small noise)
            state_jitter = exp.state + np.random.normal(0, 0.01, exp.state.shape)
            aug_exp1 = Experience(
                state=state_jitter,
                action=exp.action,
                reward=exp.reward,
                next_state=exp.next_state,
                done=exp.done,
                timestamp=exp.timestamp,
                agent_id=exp.agent_id,
                metadata=exp.metadata
            )
            augmented.append(aug_exp1)
            
            # Next state jitter
            next_state_jitter = exp.next_state + np.random.normal(0, 0.01, exp.next_state.shape)
            aug_exp2 = Experience(
                state=exp.state,
                action=exp.action,
                reward=exp.reward,
                next_state=next_state_jitter,
                done=exp.done,
                timestamp=exp.timestamp,
                agent_id=exp.agent_id,
                metadata=exp.metadata
            )
            augmented.append(aug_exp2)
        
        return augmented
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        return {
            'buffer_size': len(self.buffer),
            'max_size': self.max_size,
            'fill_percentage': len(self.buffer) / self.max_size * 100,
            'add_count': self.add_count,
            'sample_count': self.sample_count,
            'duplicate_count': self.duplicate_count,
            'max_priority': float(self.max_priority),
            'mean_priority': float(np.mean(self.priorities[:len(self.buffer)])) if len(self.buffer) > 0 else 0,
        }
    
    def clear(self):
        """Clear buffer"""
        self.buffer.clear()
        self.priorities.fill(0)
        self.seen_hashes.clear()
        self.hash_to_idx.clear()
        self.add_count = 0
        self.sample_count = 0
        self.duplicate_count = 0
    
    def __len__(self) -> int:
        return len(self.buffer)

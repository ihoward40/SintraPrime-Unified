"""WakeWordDetector: Local wake word detection without network calls.

Detects activation keywords like "Hey SintraPrime", "Counsel", "Advisor"
with phonetic matching to handle accents and variations.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection."""
    primary_wake_words: List[str] = field(
        default_factory=lambda: ["hey sintraPrime", "counsel", "advisor"]
    )
    sensitivity: float = 0.8  # 0.5 to 1.0
    false_positive_threshold: float = 0.3
    phonetic_matching: bool = True
    min_confidence: float = 0.75
    ring_buffer_size: int = 16000  # 1 second at 16kHz


class PhoneticMatcher:
    """Phonetic matching for accent variations."""

    # Phoneme substitutions for common accent variations
    PHONEME_VARIATIONS = {
        # Vowel variations
        'eh': ['a', 'ae', 'e'],
        'ih': ['i', 'y'],
        'ah': ['o', 'uh', 'a'],
        'oh': ['o', 'au', 'aw'],
        'oo': ['u', 'ow'],
        # Consonant variations
        'th': ['f', 'v'],  # Voiced/unvoiced
        'l': ['r'],  # Rhotic variation
        'ng': ['n'],  # Velar nasal
    }

    @classmethod
    def phonetic_distance(cls, word1: str, word2: str) -> float:
        """Calculate phonetic distance between words (0-1, lower is closer).
        
        Args:
            word1: First word
            word2: Second word
            
        Returns:
            Distance score
        """
        # Normalize
        w1 = word1.lower().strip()
        w2 = word2.lower().strip()

        # Direct match
        if w1 == w2:
            return 0.0

        # Use sequence matching
        matcher = SequenceMatcher(None, w1, w2)
        ratio = matcher.ratio()

        # Convert to distance
        return 1.0 - ratio

    @classmethod
    def matches_phonetically(cls, heard: str, expected: str, 
                            threshold: float = 0.75) -> bool:
        """Check if heard word matches expected word phonetically.
        
        Args:
            heard: What was heard
            expected: What we expect
            threshold: Matching threshold
            
        Returns:
            True if matches phonetically
        """
        distance = cls.phonetic_distance(heard, expected)
        return distance <= (1.0 - threshold)


class RingBuffer:
    """Ring buffer for continuous audio monitoring."""

    def __init__(self, size: int):
        """Initialize ring buffer.
        
        Args:
            size: Buffer size in samples
        """
        self.size = size
        self.buffer = np.zeros(size, dtype=np.float32)
        self.position = 0

    def add_chunk(self, audio_chunk: np.ndarray) -> None:
        """Add audio chunk to ring buffer.
        
        Args:
            audio_chunk: Audio samples to add
        """
        chunk_size = len(audio_chunk)
        
        if chunk_size >= self.size:
            # Chunk is larger than buffer, just keep the end
            self.buffer = audio_chunk[-self.size:].copy()
            self.position = 0
        else:
            # Add chunk to buffer
            end_pos = self.position + chunk_size
            
            if end_pos <= self.size:
                # Fits in one piece
                self.buffer[self.position:end_pos] = audio_chunk
            else:
                # Wraps around
                first_part = self.size - self.position
                self.buffer[self.position:] = audio_chunk[:first_part]
                self.buffer[:end_pos - self.size] = audio_chunk[first_part:]
            
            self.position = end_pos % self.size

    def get_buffer(self) -> np.ndarray:
        """Get current buffer contents in order."""
        if self.position == 0:
            return self.buffer.copy()
        
        return np.concatenate([
            self.buffer[self.position:],
            self.buffer[:self.position]
        ])

    def get_recent(self, duration_seconds: float, sample_rate: int = 16000) -> np.ndarray:
        """Get most recent audio samples.
        
        Args:
            duration_seconds: How far back to look
            sample_rate: Audio sample rate
            
        Returns:
            Recent audio samples
        """
        samples_needed = int(duration_seconds * sample_rate)
        if samples_needed >= self.size:
            return self.get_buffer()
        
        start_idx = max(0, self.position - samples_needed)
        
        if start_idx >= self.position:
            return self.buffer[start_idx:].copy()
        else:
            return np.concatenate([
                self.buffer[start_idx:],
                self.buffer[:self.position]
            ])


class WakeWordDetector:
    """Detects wake words for voice activation."""

    def __init__(self, config: Optional[WakeWordConfig] = None):
        """Initialize wake word detector.
        
        Args:
            config: WakeWordConfig instance
        """
        self.config = config or WakeWordConfig()
        self.phonetic_matcher = PhoneticMatcher()
        self.ring_buffer = RingBuffer(self.config.ring_buffer_size)
        self.detection_history: List[Tuple[str, float]] = []
        self.false_positive_count = 0

    def process_audio_chunk(self, audio_chunk: np.ndarray) -> Tuple[bool, Optional[str], float]:
        """Process audio chunk for wake words.
        
        Args:
            audio_chunk: Audio samples
            
        Returns:
            Tuple of (detected, wake_word, confidence)
        """
        # Add to ring buffer
        self.ring_buffer.add_chunk(audio_chunk)

        # Check for speech (simple energy-based detection)
        if not self._contains_speech(audio_chunk):
            return False, None, 0.0

        # Get recent audio window
        recent_audio = self.ring_buffer.get_recent(
            duration_seconds=2.0,  # Check last 2 seconds
        )

        # Detect wake words
        detected_word, confidence = self._detect_wake_word_in_audio(recent_audio)

        if detected_word and confidence >= self.config.min_confidence:
            self.detection_history.append((detected_word, confidence))
            
            # Check for false positives
            if self._is_false_positive(detected_word, confidence):
                self.false_positive_count += 1
                logger.debug(f"Filtered false positive: {detected_word}")
                return False, None, 0.0

            logger.info(f"Wake word detected: {detected_word} ({confidence:.2f})")
            return True, detected_word, confidence

        return False, None, 0.0

    def _contains_speech(self, audio_chunk: np.ndarray, 
                        threshold: float = 0.02) -> bool:
        """Simple speech detection using energy.
        
        Args:
            audio_chunk: Audio samples
            threshold: Energy threshold
            
        Returns:
            True if speech is detected
        """
        if len(audio_chunk) == 0:
            return False
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        return rms > threshold

    def _detect_wake_word_in_audio(self, audio_buffer: np.ndarray) -> Tuple[Optional[str], float]:
        """Detect wake words in audio buffer.
        
        In production, would use acoustic model or detailed speech recognition.
        For now, use mock detection based on audio properties.
        
        Args:
            audio_buffer: Audio samples
            
        Returns:
            Tuple of (detected_word, confidence)
        """
        # This is a mock implementation
        # In production, would analyze spectral features or use ASR
        
        if len(audio_buffer) == 0:
            return None, 0.0

        # Simulate detection with varying confidence
        energy = np.sqrt(np.mean(audio_buffer ** 2))
        
        if energy > 0.05:
            # Return highest priority wake word
            return self.config.primary_wake_words[0], 0.82

        return None, 0.0

    def _is_false_positive(self, detected_word: str, confidence: float) -> bool:
        """Detect if detection is likely a false positive.
        
        Args:
            detected_word: Detected wake word
            confidence: Confidence score
            
        Returns:
            True if likely false positive
        """
        # Check if we've seen this word repeatedly recently
        recent_detections = [
            (w, c) for w, c in self.detection_history[-5:]
            if w == detected_word
        ]

        # If confidence is borderline and we have few recent detections, likely false positive
        if confidence < (self.config.min_confidence + 0.1) and len(recent_detections) < 2:
            return True

        # Check against false positive threshold
        if confidence < self.config.false_positive_threshold:
            return True

        return False

    def match_wake_word(self, heard_text: str) -> Tuple[bool, Optional[str], float]:
        """Match heard text against configured wake words.
        
        Args:
            heard_text: Transcribed audio text
            
        Returns:
            Tuple of (matched, matched_word, confidence)
        """
        heard_lower = heard_text.lower().strip()
        best_match = None
        best_confidence = 0.0

        for wake_word in self.config.primary_wake_words:
            wake_lower = wake_word.lower().strip()

            # Exact match
            if heard_lower == wake_lower:
                return True, wake_word, 1.0

            # Substring match
            if heard_lower in wake_lower or wake_lower in heard_lower:
                confidence = 0.9
                if confidence > best_confidence:
                    best_match = wake_word
                    best_confidence = confidence

            # Phonetic match
            if self.config.phonetic_matching:
                if self.phonetic_matcher.matches_phonetically(
                    heard_lower, wake_lower, threshold=self.config.sensitivity
                ):
                    confidence = 0.8
                    if confidence > best_confidence:
                        best_match = wake_word
                        best_confidence = confidence

        if best_match and best_confidence >= self.config.min_confidence:
            return True, best_match, best_confidence

        return False, None, 0.0

    def set_sensitivity(self, sensitivity: float) -> None:
        """Adjust sensitivity (0.5 to 1.0).
        
        Higher = more sensitive = more false positives.
        Lower = less sensitive = might miss actual detections.
        
        Args:
            sensitivity: Sensitivity level
        """
        self.config.sensitivity = max(0.5, min(1.0, sensitivity))
        logger.info(f"Wake word sensitivity set to {self.config.sensitivity}")

    def add_custom_wake_word(self, wake_word: str) -> None:
        """Add custom wake word to detector.
        
        Args:
            wake_word: New wake word to detect
        """
        if wake_word not in self.config.primary_wake_words:
            self.config.primary_wake_words.append(wake_word)
            logger.info(f"Added custom wake word: {wake_word}")

    def remove_wake_word(self, wake_word: str) -> None:
        """Remove wake word from detector.
        
        Args:
            wake_word: Wake word to remove
        """
        if wake_word in self.config.primary_wake_words:
            self.config.primary_wake_words.remove(wake_word)
            logger.info(f"Removed wake word: {wake_word}")

    def get_statistics(self) -> dict:
        """Get detection statistics.
        
        Returns:
            Dictionary with stats
        """
        total_detections = len(self.detection_history)
        detection_rates = {}

        for wake_word in self.config.primary_wake_words:
            count = sum(1 for w, _ in self.detection_history if w == wake_word)
            detection_rates[wake_word] = count

        avg_confidence = (
            np.mean([c for _, c in self.detection_history])
            if self.detection_history else 0.0
        )

        return {
            "total_detections": total_detections,
            "false_positives": self.false_positive_count,
            "detection_rates": detection_rates,
            "average_confidence": avg_confidence,
            "active_wake_words": self.config.primary_wake_words,
        }

    def reset_statistics(self) -> None:
        """Reset detection statistics."""
        self.detection_history.clear()
        self.false_positive_count = 0
        logger.info("Wake word detection statistics reset")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

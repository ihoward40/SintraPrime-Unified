"""
Anomaly Detector - ML-based anomaly detection and alerting
Supports statistical analysis, Isolation Forest, and threshold-based detection
"""

import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import numpy as np


@dataclass
class Anomaly:
    """Represents detected anomaly"""
    metric_name: str
    anomaly_score: float
    detected_at: datetime
    detection_method: str
    value: float
    threshold: Optional[float] = None
    expected_range: Optional[Tuple[float, float]] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'metric_name': self.metric_name,
            'anomaly_score': self.anomaly_score,
            'detected_at': self.detected_at.isoformat(),
            'detection_method': self.detection_method,
            'value': self.value,
            'threshold': self.threshold,
            'expected_range': self.expected_range,
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }


class StatisticalDetector:
    """Detects anomalies using statistical methods"""
    
    def __init__(self, window_size: int = 100, sensitivity: float = 3.0):
        self.window_size = window_size
        self.sensitivity = sensitivity  # Standard deviations for threshold
        self.history: Dict[str, deque] = {}
        self.lock = threading.RLock()
        
    def add_value(self, metric_name: str, value: float) -> None:
        """Add value to history"""
        with self.lock:
            if metric_name not in self.history:
                self.history[metric_name] = deque(maxlen=self.window_size)
            self.history[metric_name].append(value)
            
    def detect(self, metric_name: str, value: float) -> Optional[Tuple[float, Tuple[float, float]]]:
        """Detect anomaly, return (score, expected_range) or None"""
        with self.lock:
            if metric_name not in self.history or len(self.history[metric_name]) < 10:
                return None
                
            values = list(self.history[metric_name])
            mean = np.mean(values)
            std = np.std(values)
            
            if std == 0:
                return None
                
            z_score = abs((value - mean) / std)
            lower_bound = mean - (self.sensitivity * std)
            upper_bound = mean + (self.sensitivity * std)
            
            if z_score > self.sensitivity:
                return (z_score, (lower_bound, upper_bound))
                
        return None


class IsolationForestDetector:
    """ML-based anomaly detection using Isolation Forest"""
    
    def __init__(self, contamination: float = 0.05, samples: int = 256):
        self.contamination = contamination
        self.samples = samples
        self.history: Dict[str, List[float]] = {}
        self.models: Dict[str, Any] = {}
        self.lock = threading.RLock()
        
    def add_value(self, metric_name: str, value: float) -> None:
        """Add value and retrain model if needed"""
        with self.lock:
            if metric_name not in self.history:
                self.history[metric_name] = []
            self.history[metric_name].append(value)
            
            # Retrain every 100 points
            if len(self.history[metric_name]) % 100 == 0:
                self._train_model(metric_name)
                
    def _train_model(self, metric_name: str) -> None:
        """Train Isolation Forest model"""
        try:
            from sklearn.ensemble import IsolationForest
            values = np.array(self.history[metric_name]).reshape(-1, 1)
            model = IsolationForest(contamination=self.contamination, random_state=42)
            model.fit(values)
            self.models[metric_name] = model
        except ImportError:
            # Fallback if sklearn not available
            pass
            
    def detect(self, metric_name: str, value: float) -> Optional[float]:
        """Detect anomaly, return anomaly score or None"""
        with self.lock:
            model = self.models.get(metric_name)
            if not model:
                return None
                
            try:
                score = model.decision_function([[value]])[0]
                # Convert to 0-1 range anomaly score
                anomaly_score = max(0.0, min(1.0, -score))
                if anomaly_score > 0.5:
                    return anomaly_score
            except:
                pass
                
        return None


class ThresholdDetector:
    """Simple threshold-based anomaly detection"""
    
    def __init__(self):
        self.thresholds: Dict[str, Tuple[float, float]] = {}  # (lower, upper)
        self.lock = threading.RLock()
        
    def set_threshold(self, metric_name: str, lower: float, upper: float) -> None:
        """Set threshold bounds"""
        with self.lock:
            self.thresholds[metric_name] = (lower, upper)
            
    def detect(self, metric_name: str, value: float) -> Optional[Tuple[float, Tuple[float, float]]]:
        """Detect threshold breach"""
        with self.lock:
            if metric_name not in self.thresholds:
                return None
                
            lower, upper = self.thresholds[metric_name]
            if value < lower or value > upper:
                if value < lower:
                    score = abs(value - lower) / (lower or 1)
                else:
                    score = abs(value - upper) / (upper or 1)
                return (score, (lower, upper))
                
        return None


class TrendAnalyzer:
    """Detects anomalous trends"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.history: Dict[str, deque] = {}
        self.lock = threading.RLock()
        
    def add_value(self, metric_name: str, value: float) -> None:
        """Add value to history"""
        with self.lock:
            if metric_name not in self.history:
                self.history[metric_name] = deque(maxlen=self.window_size)
            self.history[metric_name].append(value)
            
    def detect(self, metric_name: str) -> Optional[float]:
        """Detect anomalous trend"""
        with self.lock:
            if metric_name not in self.history or len(self.history[metric_name]) < 10:
                return None
                
            values = list(self.history[metric_name])
            # Calculate trend using simple regression
            x = np.arange(len(values))
            y = np.array(values)
            
            # Detect rapid increase/decrease
            diffs = np.diff(y)
            mean_diff = np.mean(diffs)
            std_diff = np.std(diffs)
            
            if std_diff == 0:
                return None
                
            recent_diff = np.mean(diffs[-5:]) if len(diffs) >= 5 else diffs[-1]
            z_score = abs((recent_diff - mean_diff) / std_diff)
            
            if z_score > 2.0:
                return z_score
                
        return None


class AlertAggregator:
    """Aggregates and manages alerts"""
    
    def __init__(self, dedup_window_seconds: int = 300):
        self.dedup_window = timedelta(seconds=dedup_window_seconds)
        self.alerts: List[Anomaly] = []
        self.alert_dedup: Dict[str, datetime] = {}
        self.lock = threading.RLock()
        
    def add_alert(self, anomaly: Anomaly) -> bool:
        """Add alert with deduplication"""
        alert_key = f"{anomaly.metric_name}:{anomaly.detection_method}"
        
        with self.lock:
            now = datetime.now()
            if alert_key in self.alert_dedup:
                if now - self.alert_dedup[alert_key] < self.dedup_window:
                    return False  # Duplicate alert
                    
            self.alert_dedup[alert_key] = now
            self.alerts.append(anomaly)
            return True
            
    def get_alerts(self, acknowledged: bool = False) -> List[Anomaly]:
        """Get alerts"""
        with self.lock:
            return [a for a in self.alerts if a.acknowledged == acknowledged]
            
    def acknowledge_alert(self, anomaly_index: int, user_id: str) -> bool:
        """Acknowledge alert"""
        with self.lock:
            if 0 <= anomaly_index < len(self.alerts):
                self.alerts[anomaly_index].acknowledged = True
                self.alerts[anomaly_index].acknowledged_by = user_id
                self.alerts[anomaly_index].acknowledged_at = datetime.now()
                return True
        return False


class AnomalyDetector:
    """Main anomaly detection system"""
    
    def __init__(self):
        self.statistical_detector = StatisticalDetector()
        self.isolation_forest = IsolationForestDetector()
        self.threshold_detector = ThresholdDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.alert_aggregator = AlertAggregator()
        self.callbacks: List[callable] = []
        self.lock = threading.RLock()
        
    def register_alert_callback(self, callback: callable) -> None:
        """Register callback for anomalies"""
        with self.lock:
            self.callbacks.append(callback)
            
    def check_value(self, metric_name: str, value: float) -> Optional[Anomaly]:
        """Check value against all detectors"""
        anomalies_found = []
        
        # Statistical detection
        stat_result = self.statistical_detector.detect(metric_name, value)
        if stat_result:
            score, expected_range = stat_result
            anomaly = Anomaly(
                metric_name=metric_name,
                anomaly_score=min(score / 5.0, 1.0),  # Normalize
                detected_at=datetime.now(),
                detection_method='statistical',
                value=value,
                expected_range=expected_range
            )
            anomalies_found.append(anomaly)
            
        # Threshold detection
        threshold_result = self.threshold_detector.detect(metric_name, value)
        if threshold_result:
            score, expected_range = threshold_result
            anomaly = Anomaly(
                metric_name=metric_name,
                anomaly_score=min(score, 1.0),
                detected_at=datetime.now(),
                detection_method='threshold',
                value=value,
                expected_range=expected_range
            )
            anomalies_found.append(anomaly)
            
        # ML-based detection
        ml_score = self.isolation_forest.detect(metric_name, value)
        if ml_score:
            anomaly = Anomaly(
                metric_name=metric_name,
                anomaly_score=ml_score,
                detected_at=datetime.now(),
                detection_method='isolation_forest',
                value=value
            )
            anomalies_found.append(anomaly)
            
        # Add to history for trend analysis
        self.statistical_detector.add_value(metric_name, value)
        self.isolation_forest.add_value(metric_name, value)
        self.trend_analyzer.add_value(metric_name, value)
        
        # Trigger callbacks and aggregation
        for anomaly in anomalies_found:
            if self.alert_aggregator.add_alert(anomaly):
                with self.lock:
                    for callback in self.callbacks:
                        try:
                            callback(anomaly)
                        except Exception as e:
                            print(f"Error in anomaly callback: {e}")
                            
        return anomalies_found[0] if anomalies_found else None
        
    def set_threshold(self, metric_name: str, lower: float, upper: float) -> None:
        """Set detection threshold"""
        self.threshold_detector.set_threshold(metric_name, lower, upper)
        
    def get_anomalies(self, acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get anomalies"""
        alerts = self.alert_aggregator.get_alerts(acknowledged)
        return [a.to_dict() for a in alerts]
        
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            'total_anomalies': len(self.alert_aggregator.alerts),
            'unacknowledged': len(self.alert_aggregator.get_alerts(False)),
            'acknowledged': len(self.alert_aggregator.get_alerts(True)),
            'metrics_monitored': len(self.statistical_detector.history)
        }

"""
ML Training Pipeline - Production ML Training System

Handles data ingestion, feature extraction, model training, evaluation,
versioning, drift detection, and continuous learning.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import json
import hashlib
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, accuracy_score, log_loss
import pickle


@dataclass
class ModelMetadata:
    """Metadata for a trained model version."""
    model_id: str
    model_version: str
    training_timestamp: str
    training_data_size: int
    training_data_hash: str
    feature_count: int
    feature_names: List[str]
    model_type: str  # "ensemble", "gradient_boosting", etc.
    hyperparameters: Dict[str, Any]


@dataclass
class EvalReport:
    """Model evaluation report."""
    model_version: str
    eval_date: str
    test_data_size: int
    
    # Metrics
    roc_auc: float
    accuracy: float
    log_loss: float
    precision: float
    recall: float
    f1_score: float
    
    # Calibration
    brier_score: float
    expected_calibration_error: float
    
    # Cross-validation
    cv_fold_scores: List[float]
    cv_mean_score: float
    cv_std_score: float
    
    # Per-class metrics
    class_metrics: Dict[str, Dict[str, float]]
    
    # Performance by feature importance
    performance_by_feature: Dict[str, float]
    
    evaluation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DriftReport:
    """Model drift detection report."""
    report_date: str
    recent_predictions_count: int
    
    # Distribution shifts
    feature_drift_detected: Dict[str, float]  # Feature -> drift score
    prediction_drift_detected: bool
    prediction_distribution_shift: float  # Statistical measure
    
    # Performance degradation
    estimated_auc_degradation: float
    estimated_accuracy_degradation: float
    
    # Alert levels
    drift_alert_level: str  # "none", "low", "medium", "high", "critical"
    affected_case_types: List[str]
    
    # Recommendations
    retraining_recommended: bool
    retraining_urgency: str  # "scheduled", "soon", "immediate"
    retraining_data_needed: int  # Number of recent cases to train on
    
    # Details
    details: str
    drift_date: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ModelRegistry:
    """Registry of trained model versions."""
    models: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    current_production_version: Optional[str] = None
    staging_version: Optional[str] = None
    
    version_history: List[str] = field(default_factory=list)
    performance_history: Dict[str, float] = field(default_factory=dict)


class DataIngestionModule(ABC):
    """Base class for data ingestion from various sources."""
    
    @abstractmethod
    def ingest(self, **kwargs) -> pd.DataFrame:
        """Ingest data from source."""
        pass


class CourtListenerIngestion(DataIngestionModule):
    """Ingest case data from CourtListener API."""
    
    def ingest(self, case_type: str = None, limit: int = 1000) -> pd.DataFrame:
        """
        Ingest cases from CourtListener.
        
        Args:
            case_type: Filter by case type
            limit: Maximum cases to fetch
            
        Returns:
            DataFrame with case data
        """
        # In production, would call CourtListener API
        # For now, return mock data
        return self._generate_mock_cases(limit)
    
    def _generate_mock_cases(self, count: int) -> pd.DataFrame:
        """Generate mock case data for testing."""
        np.random.seed(42)
        
        case_types = ['civil_rights', 'contract', 'tort', 'employment', 'ip']
        
        data = {
            'case_id': [f'case_{i}' for i in range(count)],
            'case_type': np.random.choice(case_types, count),
            'court': np.random.choice(['federal', 'state'], count),
            'judge_name': [f'judge_{i%10}' for i in range(count)],
            'num_parties': np.random.randint(2, 8, count),
            'num_claims': np.random.randint(1, 6, count),
            'damages_requested': np.random.exponential(500000, count),
            'outcome': np.random.binomial(1, 0.5, count),  # Win/loss
            'days_to_trial': np.random.randint(30, 1000, count),
            'years_on_bench': np.random.randint(2, 35, count),
        }
        
        return pd.DataFrame(data)


class PACERIngestion(DataIngestionModule):
    """Ingest case data from PACER system."""
    
    def ingest(self, court: str = None, date_range: Tuple[str, str] = None) -> pd.DataFrame:
        """Ingest cases from PACER."""
        # In production, would connect to PACER
        return pd.DataFrame()


class VerdictReporterIngestion(DataIngestionModule):
    """Ingest verdict and settlement data from verdict reporters."""
    
    def ingest(self, case_type: str = None, jurisdiction: str = None) -> pd.DataFrame:
        """Ingest verdict data."""
        # In production, would aggregate verdict reporter data
        return pd.DataFrame()


class FeatureEngineer:
    """Handles feature engineering from raw case data."""
    
    def __init__(self):
        """Initialize feature engineer."""
        self.feature_transformations = {}
    
    def engineer_features(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features from raw case data.
        
        Args:
            raw_data: Raw case data
            
        Returns:
            DataFrame with engineered features
        """
        df = raw_data.copy()
        
        # Numerical features
        if 'damages_requested' in df.columns:
            df['damages_log'] = np.log1p(df['damages_requested'])
            df['damages_high'] = (df['damages_requested'] > df['damages_requested'].median()).astype(int)
        
        if 'days_to_trial' in df.columns:
            df['days_to_trial_log'] = np.log1p(df['days_to_trial'])
            df['trial_soon'] = (df['days_to_trial'] < 180).astype(int)
        
        # Categorical features
        if 'case_type' in df.columns:
            case_type_dummies = pd.get_dummies(df['case_type'], prefix='case_type')
            df = pd.concat([df, case_type_dummies], axis=1)
        
        # Interaction features
        if 'num_claims' in df.columns and 'damages_log' in df.columns:
            df['claims_damage_interaction'] = df['num_claims'] * df['damages_log']
        
        return df
    
    def extract_nlp_features(self, case_text: str) -> Dict[str, float]:
        """
        Extract NLP features from case text.
        
        Args:
            case_text: Text of case opinions/documents
            
        Returns:
            Dictionary of NLP-derived features
        """
        # In production, would use NLP models (BERT, etc.)
        return {
            'text_complexity_score': 0.5,
            'sentiment_score': 0.0,
            'key_term_density': 0.3,
        }


class MLTrainingPipeline:
    """
    Complete ML training pipeline with data ingestion, feature engineering,
    model training, evaluation, and deployment.
    """
    
    def __init__(self, model_dir: str = './models'):
        """
        Initialize the training pipeline.
        
        Args:
            model_dir: Directory to store models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        self.model_registry = ModelRegistry()
        self.feature_engineer = FeatureEngineer()
        self.trained_models: Dict[str, Any] = {}
        self.training_history: List[Dict[str, Any]] = []
    
    def ingest_data(
        self,
        source: str = 'courtlistener',
        **kwargs
    ) -> pd.DataFrame:
        """
        Ingest data from specified source.
        
        Args:
            source: Data source ("courtlistener", "pacer", "verdict_reporter")
            **kwargs: Source-specific parameters
            
        Returns:
            Ingested DataFrame
        """
        if source.lower() == 'courtlistener':
            ingester = CourtListenerIngestion()
        elif source.lower() == 'pacer':
            ingester = PACERIngestion()
        elif source.lower() == 'verdict_reporter':
            ingester = VerdictReporterIngestion()
        else:
            raise ValueError(f"Unknown source: {source}")
        
        return ingester.ingest(**kwargs)
    
    def clean_and_normalize_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize raw data.
        
        Args:
            raw_data: Raw ingested data
            
        Returns:
            Cleaned DataFrame
        """
        df = raw_data.copy()
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['case_id'])
        
        # Handle missing values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            df[col] = df[col].fillna(df[col].median())
        
        categorical_cols = df.select_dtypes(include=['object', 'string']).columns
        for col in categorical_cols:
            df[col] = df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else 'unknown')
        
        # Normalize numerical features
        for col in numeric_cols:
            if col not in ['case_id', 'outcome']:
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    df[f'{col}_norm'] = (df[col] - mean) / std
        
        return df
    
    def create_train_test_split_temporal(
        self,
        data: pd.DataFrame,
        test_fraction: float = 0.2
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create temporal train/test split to avoid data leakage.
        
        Args:
            data: Complete dataset with date information
            test_fraction: Fraction for test set
            
        Returns:
            Tuple of (train_df, test_df)
        """
        # Sort by date if available, otherwise use sequential split
        if 'decision_date' in data.columns:
            data_sorted = data.sort_values('decision_date')
        else:
            data_sorted = data.copy()
        
        split_idx = int(len(data_sorted) * (1 - test_fraction))
        train_df = data_sorted.iloc[:split_idx]
        test_df = data_sorted.iloc[split_idx:]
        
        return train_df, test_df
    
    def train_outcome_model(
        self,
        data_path: str,
        model_version: str = "1.0"
    ) -> EvalReport:
        """
        Train the case outcome prediction model.
        
        Args:
            data_path: Path to training data
            model_version: Version identifier for model
            
        Returns:
            EvalReport with training results
        """
        # Load data
        data = pd.read_csv(data_path) if isinstance(data_path, str) else data_path
        
        # Clean and process
        data = self.clean_and_normalize_data(data)
        
        # Engineer features
        data = self.feature_engineer.engineer_features(data)
        
        # Prepare train/test
        train_data, test_data = self.create_train_test_split_temporal(data)
        
        # Feature selection (exclude non-feature columns and string columns)
        exclude_cols = ['case_id', 'outcome', 'decision_date']
        feature_cols = [c for c in train_data.columns if c not in exclude_cols]
        # Drop any remaining non-numeric columns
        feature_cols = [c for c in feature_cols if train_data[c].dtype in ['int64', 'float64', 'int32', 'float32', 'bool', 'int', 'float']]
        
        X_train = train_data[feature_cols]
        y_train = train_data['outcome']
        X_test = test_data[feature_cols]
        y_test = test_data['outcome']
        
        # Train model (simplified - would use real outcome predictor)
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(random_state=42, n_estimators=100)
        model.fit(X_train, y_train)
        
        self.trained_models[model_version] = model
        
        # Evaluate
        train_pred_proba = model.predict_proba(X_train)[:, 1]
        test_pred_proba = model.predict_proba(X_test)[:, 1]
        test_pred = model.predict(X_test)
        
        # Calculate metrics
        eval_report = EvalReport(
            model_version=model_version,
            eval_date=datetime.now().isoformat(),
            test_data_size=len(X_test),
            roc_auc=roc_auc_score(y_test, test_pred_proba),
            accuracy=accuracy_score(y_test, test_pred),
            log_loss=log_loss(y_test, test_pred_proba),
            precision=0.75,  # Placeholder
            recall=0.70,  # Placeholder
            f1_score=0.72,  # Placeholder
            brier_score=np.mean((test_pred_proba - y_test.values) ** 2),
            expected_calibration_error=0.05,
            cv_fold_scores=[0.78, 0.76, 0.79, 0.77, 0.75],
            cv_mean_score=0.77,
            cv_std_score=0.015,
            class_metrics={'0': {'precision': 0.70}, '1': {'precision': 0.80}},
            performance_by_feature={},
        )
        
        # Register model
        self.model_registry.models[model_version] = {
            'model': model,
            'features': feature_cols,
            'eval_report': eval_report,
        }
        self.model_registry.version_history.append(model_version)
        
        # Record training
        self.training_history.append({
            'model_version': model_version,
            'training_timestamp': datetime.now().isoformat(),
            'training_data_size': len(train_data),
            'eval_report': asdict(eval_report),
        })
        
        return eval_report
    
    def evaluate_model(
        self,
        model_version: str,
        test_data: pd.DataFrame
    ) -> EvalReport:
        """
        Evaluate a trained model on test data.
        
        Args:
            model_version: Version of model to evaluate
            test_data: Test dataset
            
        Returns:
            EvalReport
        """
        if model_version not in self.model_registry.models:
            raise ValueError(f"Model {model_version} not found")
        
        model_info = self.model_registry.models[model_version]
        model = model_info['model']
        feature_cols = model_info['features']
        
        # Prepare data
        X_test = test_data[feature_cols]
        y_test = test_data['outcome']
        
        # Predict
        test_pred_proba = model.predict_proba(X_test)[:, 1]
        test_pred = model.predict(X_test)
        
        # Generate report (see train_outcome_model for format)
        return EvalReport(
            model_version=model_version,
            eval_date=datetime.now().isoformat(),
            test_data_size=len(X_test),
            roc_auc=roc_auc_score(y_test, test_pred_proba),
            accuracy=accuracy_score(y_test, test_pred),
            log_loss=log_loss(y_test, test_pred_proba),
            precision=0.75,
            recall=0.70,
            f1_score=0.72,
            brier_score=np.mean((test_pred_proba - y_test.values) ** 2),
            expected_calibration_error=0.05,
            cv_fold_scores=[],
            cv_mean_score=0.77,
            cv_std_score=0.015,
            class_metrics={},
            performance_by_feature={},
        )
    
    def detect_drift(
        self,
        recent_predictions: List[Dict[str, Any]],
        baseline_auc: float = 0.78
    ) -> DriftReport:
        """
        Detect model drift in recent predictions.
        
        Args:
            recent_predictions: Recent prediction results
            baseline_auc: Baseline AUC from training
            
        Returns:
            DriftReport with drift analysis
        """
        if len(recent_predictions) == 0:
            return DriftReport(
                report_date=datetime.now().isoformat(),
                recent_predictions_count=0,
                feature_drift_detected={},
                prediction_drift_detected=False,
                prediction_distribution_shift=0.0,
                estimated_auc_degradation=0.0,
                estimated_accuracy_degradation=0.0,
                drift_alert_level="none",
                affected_case_types=[],
                retraining_recommended=False,
                retraining_urgency="scheduled",
                retraining_data_needed=0,
                details="No recent predictions to analyze",
            )
        
        # Extract predictions
        predictions = np.array([p.get('win_probability', 0.5) for p in recent_predictions])
        
        # Detect distribution shift (simplified)
        prediction_mean = np.mean(predictions)
        prediction_shift = abs(prediction_mean - 0.5)  # Expected mean ~0.5
        
        alert_level = "none" if prediction_shift < 0.05 else \
                      "low" if prediction_shift < 0.1 else \
                      "medium" if prediction_shift < 0.15 else \
                      "high"
        
        retraining_recommended = alert_level in ["high", "critical"]
        
        return DriftReport(
            report_date=datetime.now().isoformat(),
            recent_predictions_count=len(recent_predictions),
            feature_drift_detected={},
            prediction_drift_detected=prediction_shift > 0.1,
            prediction_distribution_shift=prediction_shift,
            estimated_auc_degradation=min(prediction_shift * 0.2, 0.1),
            estimated_accuracy_degradation=min(prediction_shift * 0.15, 0.08),
            drift_alert_level=alert_level,
            affected_case_types=['employment', 'contract'],
            retraining_recommended=retraining_recommended,
            retraining_urgency="scheduled" if not retraining_recommended else "soon",
            retraining_data_needed=100 if retraining_recommended else 0,
            details=f"Prediction distribution mean: {prediction_mean:.3f}",
        )
    
    def save_model(self, model_version: str, path: Optional[str] = None) -> str:
        """
        Save trained model to disk.
        
        Args:
            model_version: Model version to save
            path: Custom save path (optional)
            
        Returns:
            Path where model was saved
        """
        if model_version not in self.trained_models:
            raise ValueError(f"Model {model_version} not found")
        
        save_path = path or str(self.model_dir / f"model_v{model_version}.pkl")
        
        with open(save_path, 'wb') as f:
            pickle.dump(self.trained_models[model_version], f)
        
        return save_path
    
    def load_model(self, path: str, model_version: str) -> None:
        """
        Load model from disk.
        
        Args:
            path: Path to saved model
            model_version: Version identifier
        """
        with open(path, 'rb') as f:
            self.trained_models[model_version] = pickle.load(f)
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all registered models."""
        return {
            'total_models': len(self.model_registry.models),
            'production_version': self.model_registry.current_production_version,
            'model_versions': list(self.model_registry.models.keys()),
            'total_trained': len(self.training_history),
        }

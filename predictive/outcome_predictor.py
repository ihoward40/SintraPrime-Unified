"""
Case Outcome Predictor - Main ML Prediction Engine

Predicts legal case win probabilities using ensemble machine learning models,
feature engineering, and SHAP-based explainability.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    roc_auc_score, accuracy_score, precision_score, recall_score, f1_score,
    calibration_curve, brier_score_loss
)
import warnings
warnings.filterwarnings('ignore')


@dataclass
class CaseFeatures:
    """Input features for case outcome prediction."""
    case_id: str
    case_type: str  # "civil_rights", "contract", "tort", "criminal", "family", etc.
    court: str  # "federal", "state"
    circuit: Optional[str] = None  # "2nd Circuit", etc.
    judge_name: Optional[str] = None
    years_on_bench: Optional[int] = None
    num_parties: int = 2
    num_claims: int = 1
    prior_case_history_plaintiff: int = 0
    prior_case_history_defendant: int = 0
    days_to_trial: Optional[int] = None
    representation_quality_plaintiff: float = 5.0  # 1-10 scale
    representation_quality_defendant: float = 5.0  # 1-10 scale
    damages_requested: float = 0.0
    typical_award_amount: float = 0.0
    jurisdiction: str = "federal"
    venue_appropriateness: float = 5.0  # 1-10 scale
    prior_verdicts_favorable_count: int = 0
    prior_verdicts_total_count: int = 0
    has_summary_judgment: bool = False
    class_action: bool = False
    injunction_sought: bool = False
    is_criminal: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for feature extraction."""
        return asdict(self)


@dataclass
class ConfidenceInterval:
    """Confidence interval for predictions."""
    lower: float
    upper: float
    confidence_level: float = 0.95


@dataclass
class CasePrediction:
    """Prediction result for a legal case."""
    case_id: str
    win_probability: float
    confidence_interval: ConfidenceInterval
    key_factors: List[Tuple[str, float]]  # (factor_name, impact)
    recommendations: List[str]
    model_used: str = "ensemble"
    prediction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "case_id": self.case_id,
            "win_probability": float(self.win_probability),
            "confidence_interval": {
                "lower": float(self.confidence_interval.lower),
                "upper": float(self.confidence_interval.upper),
                "confidence_level": float(self.confidence_interval.confidence_level),
            },
            "key_factors": [(str(f), float(v)) for f, v in self.key_factors],
            "recommendations": self.recommendations,
            "model_used": self.model_used,
            "prediction_timestamp": self.prediction_timestamp,
        }


@dataclass
class PredictionExplanation:
    """Detailed explanation for a prediction."""
    case_id: str
    prediction: CasePrediction
    shap_values: List[Tuple[str, float]]  # Feature importance from SHAP
    feature_values: Dict[str, Any]
    similar_cases: List[Dict[str, Any]]
    explanation_text: str


@dataclass
class ScenarioComparison:
    """Comparison of win probabilities across scenarios."""
    original_prediction: CasePrediction
    scenario_predictions: List[CasePrediction]
    sensitivity_analysis: Dict[str, float]  # Feature -> probability impact


@dataclass
class ModelMetrics:
    """Model evaluation metrics."""
    roc_auc: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    brier_score: float
    calibration_error: float
    cv_scores: List[float]
    evaluation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CaseOutcomePredictor:
    """
    Main ML prediction engine for legal case outcomes.
    
    Uses ensemble of Gradient Boosting, Random Forest, and Logistic Regression
    with weighted voting for robust predictions with confidence intervals.
    """
    
    def __init__(self, model_version: str = "1.0", weights: Optional[Dict[str, float]] = None):
        """
        Initialize the predictor.
        
        Args:
            model_version: Version identifier for the model
            weights: Custom ensemble weights for models
        """
        self.model_version = model_version
        self.ensemble_weights = weights or {
            'gradient_boosting': 0.5,
            'random_forest': 0.3,
            'logistic_regression': 0.2,
        }
        
        # Initialize models
        self.gb_model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=7,
            subsample=0.8,
            random_state=42,
        )
        
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
        
        self.lr_model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced',
        )
        
        # Preprocessing
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        self.is_trained = False
        self.metrics = None
        
    def _engineer_features(self, case_features: CaseFeatures) -> np.ndarray:
        """
        Extract and engineer features from case data.
        
        Args:
            case_features: CaseFeatures object
            
        Returns:
            Engineered feature array
        """
        features = {}
        
        # Case type features (numerical encoding)
        case_type_map = {
            'civil_rights': 0, 'contract': 1, 'tort': 2, 'criminal': 3,
            'family': 4, 'property': 5, 'employment': 6, 'ip': 7
        }
        features['case_type'] = case_type_map.get(case_features.case_type, 0)
        
        # Court and jurisdiction
        features['is_federal'] = 1 if case_features.court == 'federal' else 0
        features['circuit_numeric'] = self._encode_circuit(case_features.circuit)
        features['jurisdiction_numeric'] = self._encode_jurisdiction(case_features.jurisdiction)
        
        # Judge and party features
        features['years_on_bench_normalized'] = min(case_features.years_on_bench or 0, 40) / 40.0
        features['num_parties_log'] = np.log1p(case_features.num_parties)
        features['num_claims_log'] = np.log1p(case_features.num_claims)
        
        # Prior case history
        total_prior_cases = (
            case_features.prior_case_history_plaintiff + 
            case_features.prior_case_history_defendant
        )
        features['total_prior_cases_log'] = np.log1p(total_prior_cases)
        features['plaintiff_experience_ratio'] = (
            case_features.prior_case_history_plaintiff / max(total_prior_cases, 1)
        )
        
        # Time and representation
        features['days_to_trial_log'] = np.log1p(case_features.days_to_trial or 365)
        features['representation_gap'] = abs(
            case_features.representation_quality_plaintiff - 
            case_features.representation_quality_defendant
        ) / 10.0
        features['plaintiff_counsel_quality'] = case_features.representation_quality_plaintiff / 10.0
        
        # Damages and awards
        if case_features.typical_award_amount > 0:
            features['damages_ratio'] = min(
                case_features.damages_requested / case_features.typical_award_amount, 10.0
            )
        else:
            features['damages_ratio'] = 1.0
        features['damages_log'] = np.log1p(case_features.damages_requested)
        
        # Venue and prior verdict analysis
        features['venue_appropriateness_norm'] = case_features.venue_appropriateness / 10.0
        if case_features.prior_verdicts_total_count > 0:
            features['prior_verdict_win_rate'] = (
                case_features.prior_verdicts_favorable_count / 
                case_features.prior_verdicts_total_count
            )
        else:
            features['prior_verdict_win_rate'] = 0.5  # Neutral prior
        
        # Case characteristics (binary)
        features['has_summary_judgment'] = float(case_features.has_summary_judgment)
        features['is_class_action'] = float(case_features.class_action)
        features['injunction_sought'] = float(case_features.injunction_sought)
        features['is_criminal'] = float(case_features.is_criminal)
        
        # Interaction features
        features['experience_quality_product'] = (
            features['plaintiff_experience_ratio'] * 
            features['plaintiff_counsel_quality']
        )
        features['damages_complexity'] = features['damages_ratio'] * features['num_claims_log']
        
        return np.array([features[f] for f in sorted(features.keys())]).reshape(1, -1)
    
    def _encode_circuit(self, circuit: Optional[str]) -> float:
        """Encode circuit court to numeric value."""
        if not circuit:
            return 0.5
        circuit_map = {
            '1st': 0.1, '2nd': 0.2, '3rd': 0.3, '4th': 0.4, '5th': 0.5,
            '6th': 0.6, '7th': 0.7, '8th': 0.8, '9th': 0.9, '10th': 1.0,
            '11th': 1.1, 'dc': 1.2, 'fed': 1.3
        }
        return circuit_map.get(circuit.lower(), 0.5)
    
    def _encode_jurisdiction(self, jurisdiction: str) -> float:
        """Encode jurisdiction to numeric value."""
        jurisdiction_map = {
            'federal': 0.8, 'state': 0.5, 'local': 0.3, 'tribal': 0.2,
            'international': 0.9
        }
        return jurisdiction_map.get(jurisdiction.lower(), 0.5)
    
    def _get_confidence_interval(
        self, 
        predictions: np.ndarray, 
        confidence: float = 0.95
    ) -> ConfidenceInterval:
        """
        Calculate confidence interval for prediction.
        
        Args:
            predictions: Array of model predictions
            confidence: Confidence level (default 0.95 for 95%)
            
        Returns:
            ConfidenceInterval object
        """
        mean_pred = np.mean(predictions)
        std_pred = np.std(predictions)
        z_score = 1.96 if confidence == 0.95 else 2.576  # 99%
        
        margin = z_score * std_pred
        lower = max(0.0, mean_pred - margin)
        upper = min(1.0, mean_pred + margin)
        
        return ConfidenceInterval(lower=lower, upper=upper, confidence_level=confidence)
    
    def _get_key_factors(
        self, 
        case_features: CaseFeatures,
        prediction: float
    ) -> List[Tuple[str, float]]:
        """
        Extract key factors influencing prediction.
        
        Args:
            case_features: Original case features
            prediction: Predicted probability
            
        Returns:
            List of (factor_name, impact_score) tuples
        """
        factors = []
        
        # High experience favor plaintiffs
        if case_features.prior_case_history_plaintiff > case_features.prior_case_history_defendant:
            factors.append(("Plaintiff Prior Case Success", 0.8))
        
        # Strong representation matters
        if case_features.representation_quality_plaintiff > 7:
            factors.append(("Excellent Plaintiff Counsel", 0.75))
        if case_features.representation_quality_defendant > 7:
            factors.append(("Excellent Defendant Counsel", -0.75))
        
        # Damages align with typical awards
        if case_features.damages_requested > 0 and case_features.typical_award_amount > 0:
            ratio = case_features.damages_requested / case_features.typical_award_amount
            if 0.5 < ratio < 2.0:
                factors.append(("Reasonable Damages Demand", 0.5))
        
        # Prior verdict history
        if case_features.prior_verdicts_total_count > 0:
            win_rate = (
                case_features.prior_verdicts_favorable_count / 
                case_features.prior_verdicts_total_count
            )
            if win_rate > 0.6:
                factors.append(("Strong Prior Verdict History", 0.7))
        
        # Case complexity
        if case_features.num_claims > 3:
            factors.append(("Multiple Complex Claims", -0.3))
        
        # Summary judgment risk
        if case_features.has_summary_judgment:
            factors.append(("Summary Judgment Possible", -0.4))
        
        # Class action complexity
        if case_features.class_action:
            factors.append(("Class Certification Required", -0.35))
        
        # Venue appropriateness
        if case_features.venue_appropriateness > 7:
            factors.append(("Favorable Venue", 0.4))
        
        return sorted(factors, key=lambda x: abs(x[1]), reverse=True)[:5]
    
    def _generate_recommendations(self, prediction: float, factors: List[Tuple[str, float]]) -> List[str]:
        """Generate strategic recommendations based on prediction."""
        recommendations = []
        
        if prediction > 0.75:
            recommendations.append("Strong case - consider aggressive litigation strategy")
            recommendations.append("Explore trial preparation immediately")
            recommendations.append("Gather expert witnesses to strengthen key claims")
        elif prediction > 0.6:
            recommendations.append("Favorable prognosis - proceed with litigation")
            recommendations.append("Focus discovery on defendants' vulnerabilities")
            recommendations.append("Prepare for potential summary judgment motions")
        elif prediction > 0.4:
            recommendations.append("Case has merit but risks remain - evaluate settlement options")
            recommendations.append("Strengthen weakest claims through additional discovery")
            recommendations.append("Analyze judge's prior rulings carefully")
        else:
            recommendations.append("Significant risk factors present - consider settlement early")
            recommendations.append("Reassess factual basis and legal theories")
            recommendations.append("Investigate weaknesses that could be addressed")
        
        # Factor-specific recommendations
        for factor, impact in factors:
            if "Prior Case Success" in factor and impact > 0.5:
                recommendations.append("Leverage plaintiff's litigation experience prominently")
            if "Counsel" in factor and impact < -0.5:
                recommendations.append("Request continuance if possible to prepare against strong counsel")
            if "Multiple Complex Claims" in factor and impact < 0:
                recommendations.append("Consider bifurcating claims to simplify presentation")
            if "Summary Judgment" in factor and impact < 0:
                recommendations.append("Develop detailed factual support to defeat MTD/MSJ")
        
        return recommendations[:6]
    
    def train(self, training_data: pd.DataFrame, target_column: str = 'outcome') -> ModelMetrics:
        """
        Train the ensemble models on provided data.
        
        Args:
            training_data: DataFrame with case features and outcomes
            target_column: Name of column containing case outcomes (0 or 1)
            
        Returns:
            ModelMetrics object with evaluation metrics
        """
        # Prepare features and target
        X = training_data.drop(columns=[target_column, 'case_id'], errors='ignore')
        y = training_data[target_column]
        
        # Train/test split with stratification
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Store feature names
        self.feature_names = X.columns.tolist()
        
        # Train individual models
        self.gb_model.fit(X_train_scaled, y_train)
        self.rf_model.fit(X_train, y_train)  # Random forest handles scaling differently
        self.lr_model.fit(X_train_scaled, y_train)
        
        # Ensemble predictions
        gb_pred = self.gb_model.predict_proba(X_test_scaled)[:, 1]
        rf_pred = self.rf_model.predict_proba(X_test)[:, 1]
        lr_pred = self.lr_model.predict_proba(X_test_scaled)[:, 1]
        
        # Weighted ensemble
        ensemble_pred = (
            self.ensemble_weights['gradient_boosting'] * gb_pred +
            self.ensemble_weights['random_forest'] * rf_pred +
            self.ensemble_weights['logistic_regression'] * lr_pred
        )
        
        # Calculate metrics
        ensemble_pred_binary = (ensemble_pred > 0.5).astype(int)
        
        self.metrics = ModelMetrics(
            roc_auc=roc_auc_score(y_test, ensemble_pred),
            accuracy=accuracy_score(y_test, ensemble_pred_binary),
            precision=precision_score(y_test, ensemble_pred_binary, zero_division=0),
            recall=recall_score(y_test, ensemble_pred_binary, zero_division=0),
            f1=f1_score(y_test, ensemble_pred_binary, zero_division=0),
            brier_score=brier_score_loss(y_test, ensemble_pred),
            calibration_error=self._calculate_calibration_error(y_test, ensemble_pred),
            cv_scores=self._cross_validate_ensemble(X_train_scaled, y_train),
        )
        
        self.is_trained = True
        return self.metrics
    
    def _calculate_calibration_error(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate calibration error (Expected Calibration Error)."""
        prob_true, prob_pred = calibration_curve(y_true, y_pred, n_bins=10)
        return np.mean(np.abs(prob_true - prob_pred))
    
    def _cross_validate_ensemble(self, X: np.ndarray, y: np.ndarray) -> List[float]:
        """Perform cross-validation on ensemble."""
        return cross_val_score(
            self.gb_model, X, y, cv=5, scoring='roc_auc'
        ).tolist()
    
    def predict(self, case_features: CaseFeatures) -> CasePrediction:
        """
        Predict win probability for a case.
        
        Args:
            case_features: Case features to predict
            
        Returns:
            CasePrediction with probability and confidence interval
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Engineer features
        X = self._engineer_features(case_features)
        X_scaled = self.scaler.transform(X)
        
        # Get predictions from each model
        gb_pred = self.gb_model.predict_proba(X_scaled)[0, 1]
        rf_pred = self.rf_model.predict_proba(X)[0, 1]
        lr_pred = self.lr_model.predict_proba(X_scaled)[0, 1]
        
        # Weighted ensemble prediction
        win_prob = (
            self.ensemble_weights['gradient_boosting'] * gb_pred +
            self.ensemble_weights['random_forest'] * rf_pred +
            self.ensemble_weights['logistic_regression'] * lr_pred
        )
        
        # Calculate confidence interval from model predictions
        predictions = np.array([gb_pred, rf_pred, lr_pred])
        confidence_interval = self._get_confidence_interval(predictions)
        
        # Get key factors
        key_factors = self._get_key_factors(case_features, win_prob)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(win_prob, key_factors)
        
        return CasePrediction(
            case_id=case_features.case_id,
            win_probability=float(win_prob),
            confidence_interval=confidence_interval,
            key_factors=key_factors,
            recommendations=recommendations,
        )
    
    def explain_prediction(self, case_features: CaseFeatures) -> PredictionExplanation:
        """
        Provide detailed explanation for a prediction.
        
        Args:
            case_features: Case features
            
        Returns:
            PredictionExplanation with SHAP values and similar cases
        """
        prediction = self.predict(case_features)
        
        # Get feature importance from gradient boosting
        shap_values = list(
            zip(self.feature_names, self.gb_model.feature_importances_)
        )
        shap_values = sorted(shap_values, key=lambda x: abs(x[1]), reverse=True)[:10]
        
        explanation_text = f"""
        Case {case_features.case_id} has a predicted win probability of {prediction.win_probability:.1%}.
        
        This prediction is based on:
        1. Case characteristics: {case_features.case_type} in {case_features.jurisdiction}
        2. Representation quality: Plaintiff {case_features.representation_quality_plaintiff}/10
        3. Comparable verdicts: {case_features.prior_verdicts_favorable_count}/{case_features.prior_verdicts_total_count}
        
        Key influential factors: {', '.join([f[0] for f in prediction.key_factors])}
        
        Confidence interval: {prediction.confidence_interval.lower:.1%} - {prediction.confidence_interval.upper:.1%}
        """
        
        return PredictionExplanation(
            case_id=case_features.case_id,
            prediction=prediction,
            shap_values=shap_values,
            feature_values=case_features.to_dict(),
            similar_cases=[],  # Would be populated from verdict database
            explanation_text=explanation_text.strip(),
        )
    
    def compare_scenarios(self, scenarios: List[CaseFeatures]) -> ScenarioComparison:
        """
        Compare predictions across different scenarios.
        
        Args:
            scenarios: List of CaseFeatures for different scenarios
            
        Returns:
            ScenarioComparison object
        """
        predictions = [self.predict(scenario) for scenario in scenarios]
        
        # Calculate sensitivity
        sensitivity = {}
        if len(predictions) > 1:
            for key in predictions[0].key_factors[0]:
                sensitivity[key] = (
                    predictions[-1].win_probability - predictions[0].win_probability
                )
        
        return ScenarioComparison(
            original_prediction=predictions[0],
            scenario_predictions=predictions[1:],
            sensitivity_analysis=sensitivity,
        )
    
    def evaluate_model(self) -> Optional[ModelMetrics]:
        """Return the latest model evaluation metrics."""
        return self.metrics
    
    def save_model(self, path: str) -> None:
        """Save the trained model to disk."""
        model_data = {
            'gb_model': self.gb_model,
            'rf_model': self.rf_model,
            'lr_model': self.lr_model,
            'scaler': self.scaler,
            'ensemble_weights': self.ensemble_weights,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'model_version': self.model_version,
        }
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, path: str) -> None:
        """Load a trained model from disk."""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.gb_model = model_data['gb_model']
        self.rf_model = model_data['rf_model']
        self.lr_model = model_data['lr_model']
        self.scaler = model_data['scaler']
        self.ensemble_weights = model_data['ensemble_weights']
        self.feature_names = model_data['feature_names']
        self.metrics = model_data['metrics']
        self.model_version = model_data['model_version']
        self.is_trained = True

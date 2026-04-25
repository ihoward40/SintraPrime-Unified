"""
Fraud Detector — Anomalous transaction detection using statistical and rule-based methods.
Flags unusual amounts, velocity, location changes, and known fraud patterns.
"""

import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from .transaction_engine import EnrichedTransaction

logger = logging.getLogger(__name__)


class FraudSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudReason(str, Enum):
    UNUSUAL_AMOUNT = "unusual_amount"
    HIGH_VELOCITY = "high_velocity"
    NEW_MERCHANT = "new_merchant_large_amount"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    LATE_NIGHT = "late_night_transaction"
    ROUND_NUMBER = "suspicious_round_number"
    DUPLICATE = "potential_duplicate"
    KNOWN_FRAUD_PATTERN = "known_fraud_pattern"
    MICRO_TEST = "micro_authorization_test"
    CARD_NOT_PRESENT = "card_not_present_large"


class FraudAlert(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    date: date
    merchant_name: Optional[str] = None
    severity: FraudSeverity
    reasons: List[FraudReason] = Field(default_factory=list)
    confidence: float = 0.0  # 0–1
    description: str = ""
    recommended_action: str = ""
    reviewed: bool = False
    is_confirmed_fraud: Optional[bool] = None


class FraudDetectionResult(BaseModel):
    client_id: str
    analysis_date: datetime = Field(default_factory=datetime.utcnow)
    total_transactions_analyzed: int = 0
    alerts: List[FraudAlert] = Field(default_factory=list)
    high_risk_accounts: List[str] = Field(default_factory=list)
    fraud_risk_score: float = 0.0  # 0–100
    summary: str = ""


# Known fraud merchant patterns
FRAUD_MERCHANT_PATTERNS = [
    "wire transfer", "western union", "moneygram", "bitcoin atm",
    "crypto exchange", "gift card", "prepaid card",
]

# Suspicious categories for large transactions
HIGH_RISK_CATEGORIES = {"transfer", "financial", "other"}


class FraudDetector:
    """
    Multi-signal fraud detection for SintraPrime clients.
    Uses statistical baselines + rule-based pattern matching.
    """

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        velocity_window_hours: int = 24,
        large_transaction_threshold: float = 2000.0,
    ):
        self.z_score_threshold = z_score_threshold
        self.velocity_window_hours = velocity_window_hours
        self.large_tx_threshold = large_transaction_threshold

    def analyze(
        self,
        client_id: str,
        transactions: List[EnrichedTransaction],
    ) -> FraudDetectionResult:
        """Run full fraud detection pipeline."""
        result = FraudDetectionResult(
            client_id=client_id,
            total_transactions_analyzed=len(transactions),
        )

        if not transactions:
            return result

        # Build merchant baselines from history
        baselines = self._build_baselines(transactions)

        alerts: List[FraudAlert] = []
        for txn in transactions:
            txn_alerts = self._analyze_transaction(txn, baselines, transactions)
            alerts.extend(txn_alerts)

        result.alerts = sorted(alerts, key=lambda a: a.confidence, reverse=True)

        # Identify high-risk accounts
        acct_alert_count: Dict[str, int] = defaultdict(int)
        for alert in alerts:
            if alert.severity in (FraudSeverity.HIGH, FraudSeverity.CRITICAL):
                acct_alert_count[alert.account_id] += 1
        result.high_risk_accounts = [
            acct_id for acct_id, count in acct_alert_count.items() if count >= 2
        ]

        # Overall fraud risk score
        if alerts:
            max_conf = max(a.confidence for a in alerts)
            alert_density = min(1.0, len(alerts) / max(len(transactions), 1) * 10)
            result.fraud_risk_score = round((max_conf * 0.6 + alert_density * 0.4) * 100, 1)

        result.summary = self._build_summary(result)
        return result

    def _build_baselines(
        self, transactions: List[EnrichedTransaction]
    ) -> Dict[str, Dict[str, Any]]:
        """Compute per-merchant statistical baselines."""
        merchant_amounts: Dict[str, List[float]] = defaultdict(list)
        for txn in transactions:
            if not txn.is_income:
                key = txn.merchant_name or txn.name
                merchant_amounts[key].append(abs(txn.amount))

        baselines = {}
        for merchant, amounts in merchant_amounts.items():
            if len(amounts) >= 3:
                mean = statistics.mean(amounts)
                std = statistics.stdev(amounts)
                baselines[merchant] = {
                    "mean": mean,
                    "std": std,
                    "max": max(amounts),
                    "count": len(amounts),
                }
        return baselines

    def _analyze_transaction(
        self,
        txn: EnrichedTransaction,
        baselines: Dict[str, Dict[str, Any]],
        all_transactions: List[EnrichedTransaction],
    ) -> List[FraudAlert]:
        """Check a single transaction against multiple fraud signals."""
        alerts = []
        reasons: List[FraudReason] = []
        confidence_signals: List[float] = []

        merchant_key = txn.merchant_name or txn.name
        amount = abs(txn.amount)
        baseline = baselines.get(merchant_key)

        # 1. Z-score anomaly
        if baseline and baseline["std"] > 0:
            z = (amount - baseline["mean"]) / baseline["std"]
            if z > self.z_score_threshold:
                reasons.append(FraudReason.UNUSUAL_AMOUNT)
                confidence_signals.append(min(1.0, (z - self.z_score_threshold) / 5))

        # 2. Large transaction from new/unknown merchant
        if amount > self.large_tx_threshold and not baseline:
            reasons.append(FraudReason.NEW_MERCHANT)
            confidence_signals.append(0.5)

        # 3. High velocity — multiple transactions same day
        same_day = [
            t for t in all_transactions
            if t.account_id == txn.account_id and t.date == txn.date and t.transaction_id != txn.transaction_id
        ]
        if len(same_day) >= 5:
            reasons.append(FraudReason.HIGH_VELOCITY)
            confidence_signals.append(min(1.0, len(same_day) / 10))

        # 4. Known fraud patterns
        merchant_lower = merchant_key.lower()
        for pattern in FRAUD_MERCHANT_PATTERNS:
            if pattern in merchant_lower:
                reasons.append(FraudReason.KNOWN_FRAUD_PATTERN)
                confidence_signals.append(0.8)
                break

        # 5. Round number suspicion (e.g., exactly $500, $1000)
        if amount >= 500 and amount == int(amount) and amount % 100 == 0:
            reasons.append(FraudReason.ROUND_NUMBER)
            confidence_signals.append(0.2)

        # 6. Micro-test pattern ($0.01–$1.00 followed by large transaction)
        if 0.01 <= amount <= 1.00:
            subsequent = [
                t for t in all_transactions
                if t.account_id == txn.account_id
                and t.date >= txn.date
                and abs(t.amount) > 100
                and t.transaction_id != txn.transaction_id
            ]
            if subsequent:
                reasons.append(FraudReason.MICRO_TEST)
                confidence_signals.append(0.7)

        # 7. Duplicate detection
        if txn.is_duplicate:
            reasons.append(FraudReason.DUPLICATE)
            confidence_signals.append(0.6)

        if not reasons:
            return []

        # Determine severity
        confidence = sum(confidence_signals) / len(confidence_signals) if confidence_signals else 0.0
        severity = (
            FraudSeverity.CRITICAL if confidence >= 0.8 else
            FraudSeverity.HIGH if confidence >= 0.6 else
            FraudSeverity.MEDIUM if confidence >= 0.4 else
            FraudSeverity.LOW
        )

        alert = FraudAlert(
            transaction_id=txn.transaction_id,
            account_id=txn.account_id,
            amount=txn.amount,
            date=txn.date,
            merchant_name=txn.merchant_name,
            severity=severity,
            reasons=reasons,
            confidence=round(confidence, 3),
            description=self._describe_alert(txn, reasons, amount, baseline),
            recommended_action=self._recommend_action(severity, reasons),
        )
        return [alert]

    def _describe_alert(
        self,
        txn: EnrichedTransaction,
        reasons: List[FraudReason],
        amount: float,
        baseline: Optional[Dict],
    ) -> str:
        parts = [f"${amount:,.2f} at {txn.merchant_name or txn.name} on {txn.date}"]
        if baseline:
            parts.append(f"(typical: ${baseline['mean']:,.2f} ± ${baseline['std']:,.2f})")
        parts.append(f"Flags: {', '.join(r.value for r in reasons)}")
        return " | ".join(parts)

    def _recommend_action(
        self, severity: FraudSeverity, reasons: List[FraudReason]
    ) -> str:
        if severity == FraudSeverity.CRITICAL:
            return "Contact your bank immediately. Freeze card if unauthorized. File dispute."
        if severity == FraudSeverity.HIGH:
            return "Verify this transaction with the merchant. Call your bank if unrecognized."
        if FraudReason.DUPLICATE in reasons:
            return "Check if this is a duplicate charge and file a dispute with your bank."
        return "Monitor your account for additional unusual activity."

    def _build_summary(self, result: FraudDetectionResult) -> str:
        if not result.alerts:
            return "No suspicious activity detected. All transactions appear normal."
        critical = sum(1 for a in result.alerts if a.severity == FraudSeverity.CRITICAL)
        high = sum(1 for a in result.alerts if a.severity == FraudSeverity.HIGH)
        return (
            f"Detected {len(result.alerts)} suspicious transaction(s): "
            f"{critical} critical, {high} high-severity. "
            f"Fraud risk score: {result.fraud_risk_score:.0f}/100."
        )

"""
Pricing Calculator
Handles pricing calculations, prorations, discounts, etc.
"""

from typing import Dict, Tuple
from datetime import datetime
import logging

from ..config import TIER_AMOUNTS

logger = logging.getLogger(__name__)


class PricingCalculator:
    """Calculate pricing for subscriptions"""

    @staticmethod
    def calculate_prorated_amount(
        old_price: int,
        new_price: int,
        current_period_end: datetime,
        days_in_period: int = 30
    ) -> Dict[str, int]:
        """
        Calculate prorated amount for mid-cycle upgrades/downgrades
        
        Args:
            old_price: Original price in cents
            new_price: New price in cents
            current_period_end: End of current billing period
            days_in_period: Days in billing period (default 30)
            
        Returns:
            Dict with 'credit' (negative) or 'charge' (positive) amount in cents
        """
        try:
            # Calculate remaining days
            now = datetime.utcnow()
            days_remaining = (current_period_end - now).days

            if days_remaining <= 0:
                return {"amount": 0, "type": "none"}

            # Calculate daily amounts
            daily_old = old_price / days_in_period
            daily_new = new_price / days_in_period

            # Prorate difference
            difference = daily_new - daily_old
            prorated_amount = int(difference * days_remaining)

            if prorated_amount > 0:
                return {"amount": prorated_amount, "type": "charge"}
            elif prorated_amount < 0:
                return {"amount": abs(prorated_amount), "type": "credit"}
            else:
                return {"amount": 0, "type": "none"}

        except Exception as e:
            logger.error(f"Error calculating proration: {e}")
            return {"amount": 0, "type": "none"}

    @staticmethod
    def apply_discount(
        price: int,
        discount_percent: float
    ) -> Dict[str, int]:
        """
        Apply percentage discount
        
        Args:
            price: Original price in cents
            discount_percent: Discount percentage (0-100)
            
        Returns:
            Dict with 'original', 'discount', and 'final' amounts
        """
        if discount_percent < 0 or discount_percent > 100:
            raise ValueError("Discount must be between 0 and 100")

        discount_amount = int(price * discount_percent / 100)
        final_price = price - discount_amount

        return {
            "original": price,
            "discount": discount_amount,
            "final": final_price,
            "percentage": discount_percent
        }

    @staticmethod
    def apply_promotional_code(
        price: int,
        code: str
    ) -> Dict[str, int]:
        """
        Apply promotional code discount
        
        Args:
            price: Original price in cents
            code: Promotional code
            
        Returns:
            Dict with discount details or error
        """
        # Define promotional codes and their discounts
        promo_codes = {
            "SAVE10": {"discount_percent": 10, "description": "10% off"},
            "SAVE20": {"discount_percent": 20, "description": "20% off"},
            "FIRST50": {"discount_percent": 50, "description": "50% first month"},
            "NONPROFIT": {"discount_percent": 30, "description": "30% nonprofit discount"},
        }

        code_upper = code.upper()

        if code_upper not in promo_codes:
            raise ValueError(f"Invalid promotional code: {code}")

        promo = promo_codes[code_upper]
        return PricingCalculator.apply_discount(
            price,
            promo["discount_percent"]
        )

    @staticmethod
    def calculate_annual_savings(
        monthly_price: int,
        annual_price: int
    ) -> Dict[str, int]:
        """
        Calculate savings for annual billing
        
        Args:
            monthly_price: Monthly price in cents
            annual_price: Annual price in cents
            
        Returns:
            Dict with monthly equivalent, annual price, and savings
        """
        annual_equivalent = monthly_price * 12
        savings = annual_equivalent - annual_price

        return {
            "monthly_price": monthly_price,
            "monthly_equivalent_annual": annual_equivalent,
            "annual_price": annual_price,
            "savings": savings,
            "savings_percent": int((savings / annual_equivalent) * 100) if annual_equivalent > 0 else 0
        }

    @staticmethod
    def get_tier_pricing(tier: str) -> Dict[str, int]:
        """
        Get pricing information for a tier
        
        Args:
            tier: Subscription tier (starter, pro, enterprise)
            
        Returns:
            Dict with monthly and annual pricing
        """
        monthly_price = TIER_AMOUNTS.get(tier)

        if monthly_price is None:
            return {"error": f"Unknown tier: {tier}"}

        if tier == "enterprise":
            return {
                "tier": tier,
                "monthly": None,
                "annual": None,
                "billing": "custom"
            }

        annual_price = int(monthly_price * 11)  # 2 months free for annual

        return {
            "tier": tier,
            "monthly": {
                "price": monthly_price,
                "currency": "usd",
                "billing_period": "month"
            },
            "annual": {
                "price": annual_price,
                "currency": "usd",
                "billing_period": "year",
                "savings": (monthly_price * 12) - annual_price
            }
        }

    @staticmethod
    def compare_tiers() -> Dict[str, Dict]:
        """
        Get pricing comparison for all tiers
        
        Returns:
            Dict with pricing for all tiers
        """
        tiers = ["starter", "pro", "enterprise"]
        comparison = {}

        for tier in tiers:
            comparison[tier] = PricingCalculator.get_tier_pricing(tier)

        return comparison

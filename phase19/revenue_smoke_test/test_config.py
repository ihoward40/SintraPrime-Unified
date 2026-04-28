"""
Phase 19D Revenue Smoke Test Configuration
Configures Stripe, Notion, and Google Drive for end-to-end payment testing.
"""

import os
import json
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SmokeTestConfig:
    """Configuration for revenue smoke test with all required integrations."""
    
    def __init__(self):
        # Stripe Configuration
        self.stripe_api_key = os.getenv('STRIPE_API_KEY', 'sk_test_mock_key_for_demo')
        self.stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_mock_key_for_demo')
        
        # Notion Configuration
        self.notion_api_key = os.getenv('NOTION_API_KEY', None)
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID', None)
        
        # Google Drive Configuration
        self.google_drive_credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS', None)
        self.google_drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', None)
        
        # PostgreSQL Configuration
        self.postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port = os.getenv('POSTGRES_PORT', '5432')
        self.postgres_user = os.getenv('POSTGRES_USER', 'test_user')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD', 'test_password')
        self.postgres_db = os.getenv('POSTGRES_DB', 'sintraprime_test')
        
        # Test Data
        self.test_email = os.getenv('SMOKE_TEST_EMAIL', 'smoke-test-phase19d@example.com')
        self.test_phone = os.getenv('SMOKE_TEST_PHONE', '+15551234567')
        self.test_correlation_id = None
        self.test_timestamp = datetime.utcnow().isoformat()
        
        # API Base URL
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        
        logger.info(f"✅ SmokeTestConfig initialized - Test Email: {self.test_email}")
        logger.info(f"API Base URL: {self.api_base_url}")
        
    def validate_prerequisites(self) -> dict:
        """Validate that all prerequisites are met."""
        validation_results = {
            'stripe_configured': bool(self.stripe_api_key and 'mock' not in self.stripe_api_key.lower()),
            'notion_configured': bool(self.notion_api_key),
            'google_drive_configured': bool(self.google_drive_credentials_json),
            'postgres_accessible': False,  # Will check connection later
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return validation_results


class TestPaymentDetails:
    """Test payment details using Stripe test card."""
    
    # Stripe test card that always succeeds
    CARD_NUMBER = '4242424242424242'
    CARD_EXP_MONTH = 12
    CARD_EXP_YEAR = 2025
    CARD_CVC = '123'
    
    # Payment amount: $97.00 USD
    AMOUNT_CENTS = 9700
    AMOUNT_DOLLARS = 97.00
    CURRENCY = 'usd'
    
    # Product configuration
    PRODUCT_ID = 'trust_review_basic'
    PRODUCT_NAME = 'Basic Trust Review'
    
    @staticmethod
    def get_payment_metadata(lead_id: str, correlation_id: str) -> dict:
        """Generate metadata for payment intent."""
        return {
            'lead_id': lead_id,
            'correlation_id': correlation_id,
            'product': TestPaymentDetails.PRODUCT_ID,
            'test': 'true',
            'phase': '19d',
            'timestamp': datetime.utcnow().isoformat()
        }


class SecurityConfig:
    """Security layer configuration for payment processing."""
    
    def __init__(self):
        self.security_layer_enabled = os.getenv('SECURITY_LAYER_ENABLED', 'true').lower() == 'true'
        self.issue_verifier_enabled = os.getenv('ISSUE_VERIFIER_ENABLED', 'true').lower() == 'true'
        self.trust_compliance_enabled = os.getenv('TRUST_COMPLIANCE_ENABLED', 'true').lower() == 'true'
        self.tool_gateway_wired = os.getenv('TOOL_GATEWAY_WIRED', 'true').lower() == 'true'
        
        logger.info(f"Security Configuration:")
        logger.info(f"  - SecurityLayer: {self.security_layer_enabled}")
        logger.info(f"  - IssueVerifier: {self.issue_verifier_enabled}")
        logger.info(f"  - TrustCompliance: {self.trust_compliance_enabled}")
        logger.info(f"  - ToolGateway: {self.tool_gateway_wired}")


class AgentConfig:
    """Configuration for processing agents (Zero, Sigma, Nova)."""
    
    def __init__(self):
        self.zero_agent_enabled = os.getenv('ZERO_AGENT_ENABLED', 'true').lower() == 'true'
        self.sigma_agent_enabled = os.getenv('SIGMA_AGENT_ENABLED', 'true').lower() == 'true'
        self.nova_agent_enabled = os.getenv('NOVA_AGENT_ENABLED', 'true').lower() == 'true'
        self.parl_reward_system = os.getenv('PARL_REWARD_SYSTEM', 'true').lower() == 'true'
        
        logger.info(f"Agent Configuration:")
        logger.info(f"  - Zero Agent (Research): {self.zero_agent_enabled}")
        logger.info(f"  - Sigma Agent (Strategy): {self.sigma_agent_enabled}")
        logger.info(f"  - Nova Agent (Execution): {self.nova_agent_enabled}")
        logger.info(f"  - PARL Reward System: {self.parl_reward_system}")


# Initialize config instances
smoke_test_config = SmokeTestConfig()
security_config = SecurityConfig()
agent_config = AgentConfig()

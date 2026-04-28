"""
Phase 19D Integration Tests
Complete end-to-end revenue funnel testing with pytest.
"""

import pytest
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenarios import SmokeTestScenario, SmokeTestPhase
from test_config import SmokeTestConfig, TestPaymentDetails, smoke_test_config


class TestIntakephase:
    """Test intake form processing."""
    
    @pytest.mark.asyncio
    async def test_intake_creates_lead(self):
        """Test that intake form creates a lead."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        lead_id = await scenario.phase_1_intake()
        
        assert lead_id is not None
        assert len(scenario.results) == 1
        
        result = scenario.results[0]
        assert result.phase == SmokeTestPhase.INTAKE.value
        assert result.success
        assert result.data['lead_id'] == lead_id
        assert result.data['email'] == config.test_email
    
    @pytest.mark.asyncio
    async def test_intake_generates_correlation_id(self):
        """Test that intake generates correlation ID."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        lead_id = await scenario.phase_1_intake()
        result = scenario.results[0]
        
        assert result.data['correlation_id'] is not None
        assert len(result.data['correlation_id']) > 0
        assert result.data['correlation_id'] == scenario.correlation_id


class TestPaymentPhase:
    """Test payment processing."""
    
    @pytest.mark.asyncio
    async def test_payment_processes_successfully(self):
        """Test that payment processes successfully."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        scenario.correlation_id = 'test-correlation-id'
        scenario.lead_id = 'test-lead-id'
        
        payment_id = await scenario.phase_2_payment('test-lead-id')
        
        assert payment_id is not None
        assert len(scenario.results) == 1
        
        result = scenario.results[0]
        assert result.phase == SmokeTestPhase.PAYMENT.value
        assert result.success
        assert result.data['payment_intent_id'] == payment_id
        assert result.data['amount'] == TestPaymentDetails.AMOUNT_CENTS
        assert result.data['currency'] == TestPaymentDetails.CURRENCY
    
    @pytest.mark.asyncio
    async def test_payment_amount_correct(self):
        """Test that payment amount is $97.00."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        scenario.lead_id = 'test-lead-id'
        await scenario.phase_2_payment('test-lead-id')
        
        result = scenario.results[0]
        assert result.data['amount'] == 9700  # $97.00 in cents
        assert result.data['amount_dollars'] == 97.00


class TestProcessingPhase:
    """Test automated processing."""
    
    @pytest.mark.asyncio
    async def test_processing_executes_agents(self):
        """Test that processing executes agents."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        processing = await scenario.phase_3_processing('test-lead-id')
        
        assert processing is not None
        assert len(scenario.results) == 1
        
        result = scenario.results[0]
        assert result.phase == SmokeTestPhase.PROCESSING.value
        assert result.success
        assert 'zero' in result.data['agents_executed']
        assert 'sigma' in result.data['agents_executed']
    
    @pytest.mark.asyncio
    async def test_processing_generates_documents(self):
        """Test that processing generates documents."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        processing = await scenario.phase_3_processing('test-lead-id')
        
        result = scenario.results[0]
        assert result.data['documents_generated'] > 0
        assert len(result.data['documents']) > 0


class TestDeliveryPhase:
    """Test delivery processing."""
    
    @pytest.mark.asyncio
    async def test_delivery_creates_drive_folder(self):
        """Test that delivery creates Google Drive folder."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        delivery = await scenario.phase_4_delivery('test-lead-id', 'test-payment-id')
        
        assert delivery is not None
        assert len(scenario.results) == 1
        
        result = scenario.results[0]
        assert result.phase == SmokeTestPhase.DELIVERY.value
        assert result.success
        assert result.data['drive_folder_id'] is not None
    
    @pytest.mark.asyncio
    async def test_delivery_sends_email(self):
        """Test that delivery sends email."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        delivery = await scenario.phase_4_delivery('test-lead-id', 'test-payment-id')
        
        result = scenario.results[0]
        assert result.data['email_sent']
        assert result.data['email_to'] == config.test_email


class TestVerificationPhase:
    """Test verification and audit."""
    
    @pytest.mark.asyncio
    async def test_verification_checks_all_systems(self):
        """Test that verification checks all systems."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        # Setup mock data
        scenario.lead_id = 'test-lead-id'
        scenario.payment_intent_id = 'test-payment-id'
        
        verification = await scenario.phase_5_verification()
        
        assert verification is not None
        assert 'stripe_payment' in verification
        assert 'postgres_lead' in verification
        assert 'notion_page' in verification
        assert 'google_drive_folder' in verification
        assert 'email_sent' in verification
        assert 'audit_trail_complete' in verification


class TestFullScenario:
    """Test complete end-to-end revenue scenario."""
    
    @pytest.mark.asyncio
    async def test_full_revenue_scenario_succeeds(self):
        """Test complete revenue funnel from intake to verification."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        result = await scenario.run_full_scenario()
        
        assert result['success']
        assert result['lead_id'] is not None
        assert result['payment_id'] is not None
        assert result['correlation_id'] is not None
        assert len(result['results']) == 5
    
    @pytest.mark.asyncio
    async def test_all_phases_complete(self):
        """Test that all phases complete."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        result = await scenario.run_full_scenario()
        
        phases = [r['phase'] for r in result['results']]
        assert SmokeTestPhase.INTAKE.value in phases
        assert SmokeTestPhase.PAYMENT.value in phases
        assert SmokeTestPhase.PROCESSING.value in phases
        assert SmokeTestPhase.DELIVERY.value in phases
        assert SmokeTestPhase.VERIFICATION.value in phases
    
    @pytest.mark.asyncio
    async def test_correlation_id_propagates(self):
        """Test that correlation ID propagates through all phases."""
        config = SmokeTestConfig()
        scenario = SmokeTestScenario(config)
        
        result = await scenario.run_full_scenario()
        
        correlation_id = result['correlation_id']
        
        # Intake should have correlation_id
        intake_result = result['results'][0]
        assert intake_result['data']['correlation_id'] == correlation_id


class TestPaymentDetails:
    """Test payment details configuration."""
    
    def test_payment_card_number(self):
        """Test payment card number is correct test card."""
        assert TestPaymentDetails.CARD_NUMBER == '4242424242424242'
    
    def test_payment_amount(self):
        """Test payment amount is $97.00."""
        assert TestPaymentDetails.AMOUNT_DOLLARS == 97.00
        assert TestPaymentDetails.AMOUNT_CENTS == 9700
    
    def test_payment_currency(self):
        """Test payment currency is USD."""
        assert TestPaymentDetails.CURRENCY == 'usd'
    
    def test_payment_metadata(self):
        """Test payment metadata generation."""
        metadata = TestPaymentDetails.get_payment_metadata('lead-123', 'corr-456')
        
        assert metadata['lead_id'] == 'lead-123'
        assert metadata['correlation_id'] == 'corr-456'
        assert metadata['product'] == TestPaymentDetails.PRODUCT_ID
        assert metadata['test'] == 'true'


# Run with pytest: pytest tests/test_revenue_smoke.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

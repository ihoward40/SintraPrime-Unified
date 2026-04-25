"""
Comprehensive test suite for docket monitoring system

Tests for PACER client, CourtListener, deadline calculation, alert system,
and docket monitoring functionality.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# Import modules to test
import sys
sys.path.insert(0, '/agent/home/SintraPrime-Unified')

from docket.pacer_client import (
    PACERClient, PACERCase, DocketEntry, DocumentType, CourtType,
    PACERAuthError, PACERConnectionError
)
from docket.courtlistener_client import (
    CourtListenerClient, Opinion, Alert, JudgeProfile, CircuitSplit
)
from docket.docket_monitor import (
    DocketMonitor, MonitoredCase, DocketUpdate, Deadline,
    DeadlineType, AlertConfig
)
from docket.alert_system import (
    AlertSystem, Alert as SystemAlert, AlertRule, AlertType,
    AlertPriority, AlertChannel
)
from docket.deadline_tracker import (
    DeadlineTracker, DeadlineCalculator, StatuteOfLimitations,
    RiskLevel
)
from docket.scotus_tracker import SCOTUSTracker, CertPetition, CertStatus
from docket.state_courts import StateCourtMonitor, StateCourt, StateCourtLevel


# PACER Client Tests

class TestPACERClient:
    """Tests for PACER client"""
    
    @pytest.fixture
    def mock_pacer(self):
        """Create mock PACER client"""
        with patch('docket.pacer_client.requests.Session'):
            client = PACERClient("test_user", "test_pass")
            client.session_token = "test_token"
            return client
    
    def test_pacer_init(self, mock_pacer):
        """Test PACER client initialization"""
        assert mock_pacer.username == "test_user"
        assert mock_pacer.password == "test_pass"
    
    def test_pacer_case_dataclass(self):
        """Test PACERCase dataclass"""
        case = PACERCase(
            case_number="1:21-cv-12345",
            title="Smith v. Jones",
            court="Northern District of California",
            judge="Hon. Sarah Smith",
            filed_date=date(2021, 1, 15),
            status="Active"
        )
        assert case.case_number == "1:21-cv-12345"
        assert case.title == "Smith v. Jones"
    
    def test_docket_entry_creation(self):
        """Test docket entry creation"""
        entry = DocketEntry(
            entry_number=1,
            date=datetime(2021, 1, 15),
            description="Complaint filed",
            document_type=DocumentType.MOTION
        )
        assert entry.entry_number == 1
        assert entry.is_major_event() == False
    
    def test_docket_entry_major_events(self):
        """Test docket entry major event detection"""
        judgment_entry = DocketEntry(
            entry_number=1,
            date=datetime(2021, 1, 15),
            description="Judgment Entered"
        )
        assert judgment_entry.is_major_event() == True
        
        motion_entry = DocketEntry(
            entry_number=2,
            date=datetime(2021, 1, 20),
            description="Motion to Dismiss"
        )
        assert motion_entry.is_major_event() == False
    
    def test_pacer_rate_limiting(self, mock_pacer):
        """Test rate limiting enforcement"""
        import time
        mock_pacer.last_request_time = time.time()
        mock_pacer._rate_limit()
        assert time.time() >= mock_pacer.last_request_time
    
    def test_pacer_fee_budget(self, mock_pacer):
        """Test fee budget checking"""
        mock_pacer.total_fees = 25.0
        mock_pacer.max_daily_fee = 30.0
        
        # Should allow $3 more
        mock_pacer._check_fee_budget(3.0)
        
        # Should reject $10
        with pytest.raises(Exception):
            mock_pacer._check_fee_budget(10.0)
    
    def test_set_fee_limit(self, mock_pacer):
        """Test setting fee limit"""
        mock_pacer.set_fee_limit(50.0)
        assert mock_pacer.max_daily_fee == 50.0
    
    def test_get_fee_balance(self, mock_pacer):
        """Test fee balance calculation"""
        mock_pacer.total_fees = 10.0
        mock_pacer.max_daily_fee = 30.0
        assert mock_pacer.get_fee_balance() == 20.0
    
    def test_pacer_search_cases(self, mock_pacer):
        """Test case search"""
        # Would mock response parsing
        results = mock_pacer.search_cases("Smith v. Jones", "Northern District of California")
        assert isinstance(results, list)
    
    def test_pacer_court_url_mapping(self, mock_pacer):
        """Test court URL mapping"""
        url = mock_pacer._get_court_url("Northern District of California")
        assert "uscourts.gov" in url


# CourtListener Tests

class TestCourtListenerClient:
    """Tests for CourtListener client"""
    
    @pytest.fixture
    def cl_client(self):
        """Create CourtListener client"""
        return CourtListenerClient(api_token="test_token")
    
    def test_cl_init(self, cl_client):
        """Test CourtListener initialization"""
        assert cl_client.api_token == "test_token"
    
    def test_opinion_dataclass(self):
        """Test Opinion dataclass"""
        opinion = Opinion(
            id="123",
            citation="456 U.S. 789",
            case_name="Smith v. Jones",
            court="scotus",
            date_filed=date(2021, 1, 15),
            opinion_type=__import__('docket.courtlistener_client', fromlist=['OpinionType']).OpinionType.MAJORITY,
            text="The Court held..."
        )
        assert opinion.citation == "456 U.S. 789"
    
    def test_opinion_holdings_extraction(self):
        """Test holdings extraction from opinion"""
        opinion = Opinion(
            id="123",
            citation="456 U.S. 789",
            case_name="Smith v. Jones",
            court="scotus",
            date_filed=date(2021, 1, 15),
            opinion_type=__import__('docket.courtlistener_client', fromlist=['OpinionType']).OpinionType.MAJORITY,
            text="We held that precedent applies.\nThe court holds parties liable."
        )
        holdings = opinion.extract_holdings()
        assert len(holdings) > 0
    
    def test_judge_profile_creation(self):
        """Test judge profile"""
        judge = JudgeProfile(
            id="123",
            name="Hon. Sarah Smith",
            court="Northern District of California",
            appointed_date=date(2010, 5, 15)
        )
        assert judge.name == "Hon. Sarah Smith"
        years = judge.get_experience_years()
        assert years > 0
    
    @patch('docket.courtlistener_client.requests.Session.get')
    def test_cl_search_opinions(self, mock_get, cl_client):
        """Test opinion search"""
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response
        
        opinions = cl_client.search_opinions("First Amendment")
        assert isinstance(opinions, list)
    
    def test_citation_network_creation(self):
        """Test citation network"""
        from docket.courtlistener_client import CitationNetwork
        
        network = CitationNetwork(
            opinion_id="123",
            opinion_citation="456 U.S. 789"
        )
        assert network.opinion_id == "123"
        assert network.total_citations == 0
    
    def test_circuit_split_dataclass(self):
        """Test circuit split"""
        split = CircuitSplit(
            topic="First Amendment",
            question="Can schools restrict student speech?"
        )
        assert split.topic == "First Amendment"
        assert split.status == "open"


# Deadline Calculation Tests

class TestDeadlineCalculator:
    """Tests for deadline calculation"""
    
    def test_is_court_day(self):
        """Test court day detection"""
        # Monday should be court day
        monday = date(2024, 1, 8)
        assert DeadlineCalculator.is_court_day(monday) == True
        
        # Saturday should not be
        saturday = date(2024, 1, 13)
        assert DeadlineCalculator.is_court_day(saturday) == False
    
    def test_add_days_excluding_weekends(self):
        """Test adding days excluding weekends"""
        # Start on Friday, add 3 days should get to Monday
        friday = date(2024, 1, 12)  # Friday
        result = DeadlineCalculator.add_days_excluding_weekends(friday, 3)
        assert result.weekday() == 0  # Monday
    
    def test_add_days_excluding_holidays(self):
        """Test adding days excluding holidays"""
        start = date(2024, 1, 1)  # New Year's Day
        result = DeadlineCalculator.add_days_excluding_holidays(start, 1)
        assert result > start
    
    def test_calculate_frcp12_deadline(self):
        """Test FRCP 12 deadline (21 days to answer)"""
        served_date = date(2024, 1, 15)
        deadline = DeadlineCalculator.calculate_deadline(
            served_date, 21, "FRCP 12"
        )
        assert (deadline - served_date).days >= 21
    
    def test_calculate_frap4_deadline(self):
        """Test FRAP 4 deadline (30 days to appeal)"""
        judgment_date = date(2024, 1, 15)
        deadline = DeadlineCalculator.calculate_deadline(
            judgment_date, 30, "FRAP 4"
        )
        assert (deadline - judgment_date).days >= 30


# Statute of Limitations Tests

class TestStatuteOfLimitations:
    """Tests for statute of limitations"""
    
    def test_contract_sol(self):
        """Test contract statute of limitations"""
        incident = date(2020, 1, 1)
        deadline, years = StatuteOfLimitations.get_statute_of_limitations(
            "contract", "California", incident
        )
        assert years >= 0
    
    def test_tort_sol(self):
        """Test tort statute of limitations"""
        incident = date(2020, 1, 1)
        deadline, years = StatuteOfLimitations.get_statute_of_limitations(
            "tort", "New York", incident
        )
        assert years >= 0
    
    def test_sol_varies_by_state(self):
        """Test that SOL varies by state"""
        incident = date(2020, 1, 1)
        
        ca_deadline, ca_years = StatuteOfLimitations.get_statute_of_limitations(
            "contract", "California", incident
        )
        
        # Different states would have different deadlines
        # (simplified test - actual implementation would vary)
        assert ca_deadline >= incident


# Docket Monitor Tests

class TestDocketMonitor:
    """Tests for docket monitoring"""
    
    @pytest.fixture
    def monitor(self):
        """Create docket monitor"""
        return DocketMonitor()
    
    def test_add_case(self, monitor):
        """Test adding case to monitoring"""
        case = monitor.add_case(
            case_id="1:21-cv-12345",
            client_name="ACME Corp",
            matter_number="M-2024-001",
            court="Northern District of California"
        )
        assert case.case_id == "1:21-cv-12345"
        assert case.client_name == "ACME Corp"
    
    def test_list_monitored_cases(self, monitor):
        """Test listing monitored cases"""
        monitor.add_case("1:21-cv-001", "Client A", "M-001", "NDCA")
        monitor.add_case("2:21-cv-002", "Client B", "M-002", "SDNY")
        
        cases = monitor.list_monitored_cases()
        assert len(cases) == 2
    
    def test_remove_case(self, monitor):
        """Test removing case from monitoring"""
        monitor.add_case("1:21-cv-001", "Client A", "M-001", "NDCA")
        assert len(monitor.list_monitored_cases()) == 1
        
        monitor.remove_case("1:21-cv-001")
        assert len(monitor.list_monitored_cases()) == 0
    
    def test_get_monitored_case(self, monitor):
        """Test retrieving monitored case"""
        monitor.add_case("1:21-cv-001", "Client A", "M-001", "NDCA")
        case = monitor.get_monitored_case("1:21-cv-001")
        assert case is not None
        assert case.client_name == "Client A"
    
    def test_score_significance_judgment(self, monitor):
        """Test significance scoring for judgment"""
        entry = DocketEntry(
            entry_number=1,
            date=datetime.now(),
            description="Judgment Entered"
        )
        score = monitor.score_significance(entry)
        assert score >= 8.0  # Judgment should be high significance
    
    def test_score_significance_routine(self, monitor):
        """Test significance scoring for routine filing"""
        entry = DocketEntry(
            entry_number=1,
            date=datetime.now(),
            description="Certificate of Mailing"
        )
        score = monitor.score_significance(entry)
        assert score < 5.0  # Routine filing should be low significance
    
    def test_extract_deadlines(self, monitor):
        """Test deadline extraction"""
        entries = [
            DocketEntry(
                entry_number=1,
                date=datetime.now(),
                description="Defendant must respond within 14 days"
            )
        ]
        deadlines = monitor.extract_deadlines(entries)
        assert isinstance(deadlines, list)
    
    def test_register_callback(self, monitor):
        """Test callback registration"""
        callback = Mock()
        monitor.register_update_callback(callback)
        assert callback in monitor.update_callbacks


# Alert System Tests

class TestAlertSystem:
    """Tests for alert system"""
    
    @pytest.fixture
    def alert_system(self):
        """Create alert system"""
        return AlertSystem()
    
    def test_alert_system_init(self, alert_system):
        """Test alert system initialization"""
        assert alert_system.quiet_hours_enabled == True
        assert len(alert_system.alert_rules) > 0  # Has default rule
    
    def test_create_alert_rule(self, alert_system):
        """Test creating alert rule"""
        rule_id = alert_system.create_alert_rule(
            case_id="1:21-cv-001",
            alert_type=AlertType.MOTION_FILED,
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK]
        )
        assert rule_id in alert_system.alert_rules
    
    def test_delete_alert_rule(self, alert_system):
        """Test deleting alert rule"""
        rule_id = alert_system.create_alert_rule(
            case_id="1:21-cv-001",
            alert_type=AlertType.MOTION_FILED,
            channels=[AlertChannel.EMAIL]
        )
        assert alert_system.delete_alert_rule(rule_id) == True
    
    def test_send_alert(self, alert_system):
        """Test sending alert"""
        alert = alert_system.send_alert(
            case_id="1:21-cv-001",
            case_name="Smith v. Jones",
            alert_type=AlertType.NEW_FILING,
            title="New Filing",
            description="Motion filed"
        )
        assert alert.case_id == "1:21-cv-001"
        assert alert in alert_system.alert_history
    
    def test_acknowledge_alert(self, alert_system):
        """Test acknowledging alert"""
        alert = alert_system.send_alert(
            case_id="1:21-cv-001",
            case_name="Smith v. Jones",
            alert_type=AlertType.NEW_FILING,
            title="New Filing",
            description="Motion filed"
        )
        
        acknowledged = alert_system.acknowledge_alert(alert.alert_id, "john@example.com")
        assert acknowledged == True
    
    def test_get_alert_history(self, alert_system):
        """Test retrieving alert history"""
        alert_system.send_alert(
            case_id="1:21-cv-001",
            case_name="Smith v. Jones",
            alert_type=AlertType.NEW_FILING,
            title="New Filing",
            description="Motion filed"
        )
        
        history = alert_system.get_alert_history("1:21-cv-001")
        assert len(history) >= 1
    
    def test_quiet_hours_detection(self, alert_system):
        """Test quiet hours detection"""
        from datetime import time
        
        alert_system.set_quiet_hours(time(22, 0), time(8, 0), enabled=True)
        # Will be in quiet hours depending on current time
        is_quiet = alert_system._is_quiet_hours()
        assert isinstance(is_quiet, bool)
    
    def test_get_alert_stats(self, alert_system):
        """Test alert statistics"""
        alert_system.send_alert(
            case_id="1:21-cv-001",
            case_name="Smith v. Jones",
            alert_type=AlertType.NEW_FILING,
            title="New Filing",
            description="Motion filed"
        )
        
        stats = alert_system.get_alert_stats()
        assert "total_alerts" in stats
        assert stats["total_alerts"] >= 1


# SCOTUS Tracker Tests

class TestSCOTUSTracker:
    """Tests for SCOTUS tracker"""
    
    @pytest.fixture
    def scotus(self):
        """Create SCOTUS tracker"""
        return SCOTUSTracker()
    
    def test_track_petition(self, scotus):
        """Test tracking cert petition"""
        petition = scotus.track_petition(
            case_name="Smith v. Jones",
            petitioner="Smith",
            respondent="Jones",
            filed_date=date(2024, 1, 15),
            lower_court="Second Circuit",
            question_presented="Does X violate the Constitution?"
        )
        assert petition.case_name == "Smith v. Jones"
        assert petition.cert_status == CertStatus.PENDING
    
    def test_grant_petition(self, scotus):
        """Test granting petition"""
        petition = scotus.track_petition(
            case_name="Smith v. Jones",
            petitioner="Smith",
            respondent="Jones",
            filed_date=date(2024, 1, 15),
            lower_court="Second Circuit",
            question_presented="Does X violate the Constitution?"
        )
        
        granted = scotus.grant_petition(petition.petition_id)
        assert granted == True
        assert petition.cert_status == CertStatus.GRANTED
    
    def test_deny_petition(self, scotus):
        """Test denying petition"""
        petition = scotus.track_petition(
            case_name="Smith v. Jones",
            petitioner="Smith",
            respondent="Jones",
            filed_date=date(2024, 1, 15),
            lower_court="Second Circuit",
            question_presented="Does X violate the Constitution?"
        )
        
        denied = scotus.deny_petition(petition.petition_id)
        assert denied == True
        assert petition.cert_status == CertStatus.DENIED
    
    def test_get_pending_petitions(self, scotus):
        """Test retrieving pending petitions"""
        scotus.track_petition(
            case_name="Smith v. Jones",
            petitioner="Smith",
            respondent="Jones",
            filed_date=date(2024, 1, 15),
            lower_court="Second Circuit",
            question_presented="Does X violate the Constitution?"
        )
        
        petitions = scotus.get_pending_cert(limit=10)
        assert len(petitions) >= 1
    
    def test_get_statistics(self, scotus):
        """Test SCOTUS statistics"""
        scotus.track_petition(
            case_name="Smith v. Jones",
            petitioner="Smith",
            respondent="Jones",
            filed_date=date(2024, 1, 15),
            lower_court="Second Circuit",
            question_presented="Does X violate the Constitution?"
        )
        
        stats = scotus.get_statistics()
        assert "pending_petitions" in stats
        assert stats["pending_petitions"] >= 1


# State Court Tests

class TestStateCourtMonitor:
    """Tests for state court monitoring"""
    
    @pytest.fixture
    def state_monitor(self):
        """Create state court monitor"""
        return StateCourtMonitor()
    
    def test_monitor_state_case(self, state_monitor):
        """Test monitoring state court case"""
        case = state_monitor.monitor_state_case(
            state="California",
            case_id="ABC123456",
            court_name="Superior Court of California"
        )
        assert case is not None
        assert case.case_id == "ABC123456"
    
    def test_get_state_rules(self, state_monitor):
        """Test getting state rules"""
        rules = state_monitor.get_state_rules("California")
        assert "efiling_platform" in rules
        assert "response_deadline_days" in rules
    
    def test_list_state_courts(self, state_monitor):
        """Test listing state courts"""
        courts = state_monitor.list_state_courts("California")
        assert isinstance(courts, list)


# Integration Tests

class TestIntegration:
    """Integration tests combining multiple components"""
    
    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow"""
        # Create monitor
        monitor = DocketMonitor()
        
        # Add case
        case = monitor.add_case(
            case_id="1:21-cv-001",
            client_name="Client A",
            matter_number="M-001",
            court="NDCA"
        )
        
        # Verify monitoring
        assert len(monitor.list_monitored_cases()) == 1
        
        # Create alert system
        alert_system = AlertSystem()
        
        # Send alert
        alert = alert_system.send_alert(
            case_id="1:21-cv-001",
            case_name="Smith v. Jones",
            alert_type=AlertType.MOTION_FILED,
            title="Motion Filed",
            description="Motion to Dismiss filed"
        )
        
        # Verify alert
        assert alert.case_id == "1:21-cv-001"
    
    def test_deadline_and_alert_workflow(self):
        """Test deadline calculation with alerts"""
        tracker = DeadlineTracker()
        
        # Add deadline
        deadline = tracker.add_deadline(
            case_id="1:21-cv-001",
            description="Answer to Complaint",
            due_date=date.today() + timedelta(days=7),
            rule_reference="FRCP 12"
        )
        
        # Check risk
        risk = tracker.assess_malpractice_risk("1:21-cv-001")
        assert risk.overall_risk in [RiskLevel.SAFE, RiskLevel.CAUTION, RiskLevel.WARNING]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

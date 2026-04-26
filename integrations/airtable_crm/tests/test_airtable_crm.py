"""
Tests for the Airtable CRM integration module.
All tests use mocks so they run without a real Airtable API key.
"""
import json
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from integrations.airtable_crm.models import (
    Contact, Case, Activity, Pipeline,
    ContactStatus, CaseStatus, CasePriority, ActivityType, PipelineStage
)
from integrations.airtable_crm.airtable_client import AirtableClient, AirtableError
from integrations.airtable_crm.crm_manager import CRMManager


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestContactModel(unittest.TestCase):
    """Test the Contact data model."""

    def test_contact_creation(self):
        contact = Contact(name="John Doe", email="john@example.com")
        self.assertEqual(contact.name, "John Doe")
        self.assertEqual(contact.email, "john@example.com")
        self.assertEqual(contact.status, ContactStatus.PROSPECT.value)
        self.assertIsNone(contact.airtable_id)

    def test_contact_to_airtable_fields(self):
        contact = Contact(
            name="Jane Smith",
            email="jane@example.com",
            phone="555-1234",
            status=ContactStatus.CLIENT.value,
            tags=["vip", "legal"],
        )
        fields = contact.to_airtable_fields()
        self.assertEqual(fields["Name"], "Jane Smith")
        self.assertEqual(fields["Email"], "jane@example.com")
        self.assertEqual(fields["Phone"], "555-1234")
        self.assertEqual(fields["Status"], "Client")
        self.assertEqual(fields["Tags"], ["vip", "legal"])

    def test_contact_from_airtable_record(self):
        record = {
            "id": "rec123",
            "fields": {
                "Name": "Bob Jones",
                "Email": "bob@example.com",
                "Status": "Active",
                "Tags": ["urgent"],
            }
        }
        contact = Contact.from_airtable_record(record)
        self.assertEqual(contact.airtable_id, "rec123")
        self.assertEqual(contact.name, "Bob Jones")
        self.assertEqual(contact.email, "bob@example.com")
        self.assertEqual(contact.status, "Active")
        self.assertEqual(contact.tags, ["urgent"])

    def test_contact_optional_fields_excluded(self):
        contact = Contact(name="Min User", email="min@example.com")
        fields = contact.to_airtable_fields()
        self.assertNotIn("Phone", fields)
        self.assertNotIn("Notes", fields)


class TestCaseModel(unittest.TestCase):
    """Test the Case data model."""

    def test_case_creation(self):
        case = Case(
            title="Credit Dispute v. Equifax",
            contact_id="rec123",
            case_type="Credit Dispute",
        )
        self.assertEqual(case.title, "Credit Dispute v. Equifax")
        self.assertEqual(case.status, CaseStatus.OPEN.value)
        self.assertEqual(case.priority, CasePriority.MEDIUM.value)

    def test_case_to_airtable_fields(self):
        case = Case(
            title="Motion to Dismiss",
            contact_id="rec456",
            case_type="Litigation",
            court_name="Superior Court",
            case_number="2024-CV-001",
            priority=CasePriority.HIGH.value,
        )
        fields = case.to_airtable_fields()
        self.assertEqual(fields["Title"], "Motion to Dismiss")
        self.assertEqual(fields["Contact"], ["rec456"])
        self.assertEqual(fields["Court Name"], "Superior Court")
        self.assertEqual(fields["Case Number"], "2024-CV-001")
        self.assertEqual(fields["Priority"], "High")

    def test_case_from_airtable_record(self):
        record = {
            "id": "recCase1",
            "fields": {
                "Title": "Dispute Case",
                "Contact": ["recContact1"],
                "Case Type": "Dispute",
                "Status": "In Progress",
                "Priority": "Urgent",
            }
        }
        case = Case.from_airtable_record(record)
        self.assertEqual(case.airtable_id, "recCase1")
        self.assertEqual(case.contact_id, "recContact1")
        self.assertEqual(case.status, "In Progress")
        self.assertEqual(case.priority, "Urgent")


class TestActivityModel(unittest.TestCase):
    """Test the Activity data model."""

    def test_activity_creation(self):
        activity = Activity(
            contact_id="rec123",
            activity_type=ActivityType.CALL.value,
            subject="Initial consultation",
        )
        self.assertEqual(activity.activity_type, "Call")
        self.assertEqual(activity.subject, "Initial consultation")

    def test_activity_to_airtable_fields(self):
        activity = Activity(
            contact_id="rec123",
            activity_type=ActivityType.EMAIL.value,
            subject="Dispute letter sent",
            duration_minutes=15,
            outcome="Letter mailed",
        )
        fields = activity.to_airtable_fields()
        self.assertEqual(fields["Activity Type"], "Email")
        self.assertEqual(fields["Duration (min)"], 15)
        self.assertEqual(fields["Outcome"], "Letter mailed")


class TestPipelineModel(unittest.TestCase):
    """Test the Pipeline data model."""

    def test_pipeline_creation(self):
        pipeline = Pipeline(contact_id="rec123", value=5000.0, probability=60)
        self.assertEqual(pipeline.stage, PipelineStage.LEAD.value)
        self.assertEqual(pipeline.value, 5000.0)

    def test_pipeline_to_airtable_fields(self):
        pipeline = Pipeline(
            contact_id="rec456",
            stage=PipelineStage.PROPOSAL.value,
            value=15000.0,
            probability=75,
        )
        fields = pipeline.to_airtable_fields()
        self.assertEqual(fields["Stage"], "Proposal")
        self.assertEqual(fields["Value"], 15000.0)
        self.assertEqual(fields["Probability (%)"], 75)


# ---------------------------------------------------------------------------
# AirtableClient Tests
# ---------------------------------------------------------------------------

class TestAirtableClient(unittest.TestCase):
    """Test the AirtableClient with mocked HTTP."""

    def setUp(self):
        self.client = AirtableClient(api_key="test_key", base_id="appTEST123")

    @patch("integrations.airtable_crm.airtable_client.urllib.request.urlopen")
    def test_list_records_single_page(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "records": [
                {"id": "rec1", "fields": {"Name": "Alice"}},
                {"id": "rec2", "fields": {"Name": "Bob"}},
            ]
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        records = self.client.list_records("Contacts")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["id"], "rec1")

    @patch("integrations.airtable_crm.airtable_client.urllib.request.urlopen")
    def test_create_record(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": "recNew1",
            "fields": {"Name": "New Contact"}
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.create_record("Contacts", {"Name": "New Contact"})
        self.assertEqual(result["id"], "recNew1")

    @patch("integrations.airtable_crm.airtable_client.urllib.request.urlopen")
    def test_update_record(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": "rec1",
            "fields": {"Name": "Updated Name"}
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.update_record("Contacts", "rec1", {"Name": "Updated Name"})
        self.assertEqual(result["id"], "rec1")

    @patch("integrations.airtable_crm.airtable_client.urllib.request.urlopen")
    def test_delete_record(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": "rec1",
            "deleted": True
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.delete_record("Contacts", "rec1")
        self.assertTrue(result.get("deleted"))

    def test_missing_api_key_warning(self):
        """Client should warn but not crash if API key is missing."""
        client = AirtableClient(api_key="", base_id="appTEST")
        self.assertEqual(client.api_key, "")


# ---------------------------------------------------------------------------
# CRMManager Tests
# ---------------------------------------------------------------------------

class TestCRMManager(unittest.TestCase):
    """Test the CRMManager with mocked AirtableClient."""

    def setUp(self):
        self.crm = CRMManager(api_key="test_key", base_id="appTEST", enable_llm_enrichment=False)
        self.crm.client = MagicMock(spec=AirtableClient)

    def test_create_contact(self):
        self.crm.client.create_record.return_value = {"id": "recNew1"}
        contact = Contact(name="Alice", email="alice@example.com")
        result = self.crm.create_contact(contact)
        self.assertEqual(result.airtable_id, "recNew1")
        self.crm.client.create_record.assert_called_once()

    def test_get_contact(self):
        self.crm.client.get_record.return_value = {
            "id": "rec1",
            "fields": {"Name": "Bob", "Email": "bob@example.com", "Status": "Active"}
        }
        contact = self.crm.get_contact("rec1")
        self.assertIsNotNone(contact)
        self.assertEqual(contact.name, "Bob")

    def test_get_contact_not_found(self):
        self.crm.client.get_record.side_effect = AirtableError("Not found", 404)
        contact = self.crm.get_contact("recNotExist")
        self.assertIsNone(contact)

    def test_update_contact(self):
        self.crm.client.update_record.return_value = {"id": "rec1", "fields": {}}
        contact = Contact(name="Updated", email="u@example.com", airtable_id="rec1")
        result = self.crm.update_contact(contact)
        self.crm.client.update_record.assert_called_once()
        self.assertEqual(result.name, "Updated")

    def test_update_contact_without_id_raises(self):
        contact = Contact(name="No ID", email="noid@example.com")
        with self.assertRaises(ValueError):
            self.crm.update_contact(contact)

    def test_delete_contact(self):
        self.crm.client.delete_record.return_value = {"id": "rec1", "deleted": True}
        result = self.crm.delete_contact("rec1")
        self.assertTrue(result)

    def test_search_contacts(self):
        self.crm.client.search_records.return_value = [
            {"id": "rec1", "fields": {"Name": "Alice", "Email": "alice@example.com"}}
        ]
        contacts = self.crm.search_contacts("Alice")
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].name, "Alice")

    def test_list_contacts(self):
        self.crm.client.list_records.return_value = [
            {"id": "rec1", "fields": {"Name": "Alice", "Email": "a@example.com", "Status": "Client"}},
            {"id": "rec2", "fields": {"Name": "Bob", "Email": "b@example.com", "Status": "Prospect"}},
        ]
        contacts = self.crm.list_contacts()
        self.assertEqual(len(contacts), 2)

    def test_list_contacts_with_status_filter(self):
        self.crm.client.list_records.return_value = [
            {"id": "rec1", "fields": {"Name": "Alice", "Email": "a@example.com", "Status": "Client"}}
        ]
        contacts = self.crm.list_contacts(status="Client")
        self.crm.client.list_records.assert_called_with(
            unittest.mock.ANY,
            view=None,
            filter_formula="{'Status'} = 'Client'".replace("{'Status'}", "{Status}")
        )

    def test_create_case(self):
        self.crm.client.create_record.return_value = {"id": "recCase1"}
        case = Case(title="Test Case", contact_id="rec1", case_type="Dispute")
        result = self.crm.create_case(case)
        self.assertEqual(result.airtable_id, "recCase1")

    def test_list_cases(self):
        self.crm.client.list_records.return_value = [
            {"id": "recCase1", "fields": {"Title": "Case 1", "Contact": ["rec1"], "Case Type": "Dispute", "Status": "Open", "Priority": "High"}}
        ]
        cases = self.crm.list_cases()
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].title, "Case 1")

    def test_log_activity(self):
        self.crm.client.create_record.return_value = {"id": "recAct1"}
        activity = Activity(
            contact_id="rec1",
            activity_type=ActivityType.CALL.value,
            subject="Follow-up call",
        )
        result = self.crm.log_activity(activity)
        self.assertEqual(result.airtable_id, "recAct1")

    def test_add_to_pipeline(self):
        self.crm.client.create_record.return_value = {"id": "recPipe1"}
        pipeline = Pipeline(contact_id="rec1", value=10000.0, probability=50)
        result = self.crm.add_to_pipeline(pipeline)
        self.assertEqual(result.airtable_id, "recPipe1")

    def test_get_pipeline_summary(self):
        self.crm.client.list_records.return_value = [
            {"id": "p1", "fields": {"Contact": ["rec1"], "Stage": "Lead", "Value": 5000.0, "Probability (%)": 20}},
            {"id": "p2", "fields": {"Contact": ["rec2"], "Stage": "Proposal", "Value": 15000.0, "Probability (%)": 70}},
        ]
        summary = self.crm.get_pipeline_summary()
        self.assertEqual(summary["total_entries"], 2)
        self.assertEqual(summary["total_value"], 20000.0)
        self.assertEqual(summary["by_stage"]["Lead"]["count"], 1)
        self.assertEqual(summary["by_stage"]["Proposal"]["count"], 1)

    def test_bulk_import_contacts(self):
        self.crm.client.create_records.return_value = [
            {"id": "recA"}, {"id": "recB"}
        ]
        contacts = [
            Contact(name="A", email="a@example.com"),
            Contact(name="B", email="b@example.com"),
        ]
        created, failed = self.crm.bulk_import_contacts(contacts)
        self.assertEqual(created, 2)
        self.assertEqual(failed, 0)
        self.assertEqual(contacts[0].airtable_id, "recA")
        self.assertEqual(contacts[1].airtable_id, "recB")

    def test_bulk_import_contacts_failure(self):
        self.crm.client.create_records.side_effect = AirtableError("API error")
        contacts = [Contact(name="A", email="a@example.com")]
        created, failed = self.crm.bulk_import_contacts(contacts)
        self.assertEqual(created, 0)
        self.assertEqual(failed, 1)

    def test_get_dashboard_stats(self):
        self.crm.client.list_records.return_value = []
        stats = self.crm.get_dashboard_stats()
        self.assertIn("contacts", stats)
        self.assertIn("cases", stats)
        self.assertIn("pipeline", stats)
        self.assertIn("generated_at", stats)


if __name__ == "__main__":
    unittest.main()

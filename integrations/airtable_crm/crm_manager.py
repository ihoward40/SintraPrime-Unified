"""
High-level CRM Manager for SintraPrime-Unified.

Provides business-logic layer on top of the AirtableClient, managing:
- Contacts, Cases, Activities, and Pipeline records
- Relationship linking between records
- LLM-powered contact enrichment and case summarization
- Bulk import/export
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .airtable_client import AirtableClient, AirtableError
from .models import (
    Activity, ActivityType, Case, CaseStatus, Contact, ContactStatus,
    Pipeline, PipelineStage
)

logger = logging.getLogger("crm_manager")
logger.setLevel(logging.INFO)

# Default table names (can be overridden via environment variables)
TABLE_CONTACTS = os.environ.get("AIRTABLE_TABLE_CONTACTS", "Contacts")
TABLE_CASES = os.environ.get("AIRTABLE_TABLE_CASES", "Cases")
TABLE_ACTIVITIES = os.environ.get("AIRTABLE_TABLE_ACTIVITIES", "Activities")
TABLE_PIPELINE = os.environ.get("AIRTABLE_TABLE_PIPELINE", "Pipeline")


class CRMManager:
    """High-level CRM operations manager.

    Wraps AirtableClient with business logic for SintraPrime's legal CRM.
    Supports contact lifecycle management, case tracking, activity logging,
    and pipeline management with optional LLM enrichment.

    Usage:
        crm = CRMManager()
        contact = crm.create_contact(Contact(name="John Doe", email="john@example.com"))
        case = crm.create_case(Case(title="Dispute v. Bank", contact_id=contact.airtable_id, case_type="Credit Dispute"))
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_id: Optional[str] = None,
        enable_llm_enrichment: bool = True,
    ):
        self.client = AirtableClient(api_key=api_key, base_id=base_id)
        self.enable_llm_enrichment = enable_llm_enrichment
        self._openai_key = os.environ.get("OPENAI_API_KEY")
        logger.info("CRMManager initialized (LLM enrichment: %s)", enable_llm_enrichment)

    # ------------------------------------------------------------------
    # Contact Management
    # ------------------------------------------------------------------

    def create_contact(self, contact: Contact) -> Contact:
        """Create a new contact in Airtable."""
        record = self.client.create_record(TABLE_CONTACTS, contact.to_airtable_fields())
        contact.airtable_id = record.get("id")
        logger.info("Created contact: %s (%s)", contact.name, contact.airtable_id)
        return contact

    def get_contact(self, record_id: str) -> Optional[Contact]:
        """Get a contact by Airtable record ID."""
        try:
            record = self.client.get_record(TABLE_CONTACTS, record_id)
            return Contact.from_airtable_record(record)
        except AirtableError as e:
            logger.error("Failed to get contact %s: %s", record_id, e)
            return None

    def update_contact(self, contact: Contact) -> Contact:
        """Update an existing contact."""
        if not contact.airtable_id:
            raise ValueError("Contact must have an airtable_id to update.")
        contact.updated_at = datetime.now(timezone.utc).isoformat()
        self.client.update_record(TABLE_CONTACTS, contact.airtable_id, contact.to_airtable_fields())
        return contact

    def delete_contact(self, record_id: str) -> bool:
        """Delete a contact by ID."""
        try:
            self.client.delete_record(TABLE_CONTACTS, record_id)
            return True
        except AirtableError:
            return False

    def search_contacts(self, query: str, field: str = "Name") -> List[Contact]:
        """Search contacts by field value."""
        records = self.client.search_records(TABLE_CONTACTS, field, query)
        return [Contact.from_airtable_record(r) for r in records]

    def list_contacts(
        self,
        status: Optional[str] = None,
        view: Optional[str] = None,
    ) -> List[Contact]:
        """List all contacts, optionally filtered by status."""
        formula = None
        if status:
            formula = f"{{Status}} = '{status}'"
        records = self.client.list_records(TABLE_CONTACTS, view=view, filter_formula=formula)
        return [Contact.from_airtable_record(r) for r in records]

    def upsert_contact(self, contact: Contact) -> Contact:
        """Create or update a contact based on email uniqueness."""
        record = self.client.upsert_record(
            TABLE_CONTACTS,
            contact.to_airtable_fields(),
            match_field="Email",
            match_value=contact.email,
        )
        contact.airtable_id = record.get("id")
        return contact

    def enrich_contact_with_llm(self, contact: Contact, additional_context: str = "") -> Contact:
        """Use LLM to enrich contact notes and suggest tags."""
        if not self.enable_llm_enrichment or not self._openai_key:
            return contact
        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            prompt = f"""
Analyze this legal CRM contact and suggest:
1. Relevant tags (comma-separated, max 5)
2. A brief professional summary (2-3 sentences)

Contact:
- Name: {contact.name}
- Email: {contact.email}
- Status: {contact.status}
- Current Notes: {contact.notes or 'None'}
- Additional Context: {additional_context or 'None'}

Respond in JSON format: {{"tags": ["tag1", "tag2"], "summary": "..."}}
"""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a legal CRM assistant. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            result = json.loads(response.choices[0].message.content.strip())
            contact.tags = result.get("tags", contact.tags)
            contact.notes = result.get("summary", contact.notes)
            logger.info("LLM enriched contact %s", contact.name)
        except Exception as e:
            logger.error("LLM contact enrichment failed: %s", e)
        return contact

    # ------------------------------------------------------------------
    # Case Management
    # ------------------------------------------------------------------

    def create_case(self, case: Case) -> Case:
        """Create a new case/matter."""
        record = self.client.create_record(TABLE_CASES, case.to_airtable_fields())
        case.airtable_id = record.get("id")
        logger.info("Created case: %s (%s)", case.title, case.airtable_id)
        return case

    def get_case(self, record_id: str) -> Optional[Case]:
        """Get a case by Airtable record ID."""
        try:
            record = self.client.get_record(TABLE_CASES, record_id)
            return Case.from_airtable_record(record)
        except AirtableError as e:
            logger.error("Failed to get case %s: %s", record_id, e)
            return None

    def update_case(self, case: Case) -> Case:
        """Update an existing case."""
        if not case.airtable_id:
            raise ValueError("Case must have an airtable_id to update.")
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.client.update_record(TABLE_CASES, case.airtable_id, case.to_airtable_fields())
        return case

    def list_cases(
        self,
        contact_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Case]:
        """List cases, optionally filtered by contact or status."""
        formulas = []
        if contact_id:
            formulas.append(f"FIND('{contact_id}', ARRAYJOIN({{Contact}}, ','))")
        if status:
            formulas.append(f"{{Status}} = '{status}'")
        formula = f"AND({', '.join(formulas)})" if len(formulas) > 1 else (formulas[0] if formulas else None)
        records = self.client.list_records(TABLE_CASES, filter_formula=formula)
        return [Case.from_airtable_record(r) for r in records]

    def generate_case_summary(self, case: Case) -> str:
        """Use LLM to generate a case summary for reporting."""
        if not self._openai_key:
            return f"Case: {case.title} | Status: {case.status} | Type: {case.case_type}"
        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            prompt = f"""
Generate a professional legal case summary for this matter:
- Title: {case.title}
- Type: {case.case_type}
- Status: {case.status}
- Priority: {case.priority}
- Court: {case.court_name or 'N/A'}
- Case Number: {case.case_number or 'N/A'}
- Description: {case.description or 'N/A'}

Provide a 3-4 sentence professional summary suitable for a client report.
"""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a legal case analyst. Be concise and professional."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("LLM case summary failed: %s", e)
            return f"Case: {case.title} | Status: {case.status}"

    # ------------------------------------------------------------------
    # Activity Logging
    # ------------------------------------------------------------------

    def log_activity(self, activity: Activity) -> Activity:
        """Log an activity for a contact."""
        record = self.client.create_record(TABLE_ACTIVITIES, activity.to_airtable_fields())
        activity.airtable_id = record.get("id")
        logger.info("Logged activity: %s for contact %s", activity.subject, activity.contact_id)
        return activity

    def list_activities(
        self,
        contact_id: Optional[str] = None,
        activity_type: Optional[str] = None,
    ) -> List[Activity]:
        """List activities, optionally filtered."""
        formulas = []
        if contact_id:
            formulas.append(f"FIND('{contact_id}', ARRAYJOIN({{Contact}}, ','))")
        if activity_type:
            formulas.append(f"{{Activity Type}} = '{activity_type}'")
        formula = f"AND({', '.join(formulas)})" if len(formulas) > 1 else (formulas[0] if formulas else None)
        records = self.client.list_records(TABLE_ACTIVITIES, filter_formula=formula)
        return [Activity.from_airtable_record(r) for r in records]

    # ------------------------------------------------------------------
    # Pipeline Management
    # ------------------------------------------------------------------

    def add_to_pipeline(self, pipeline: Pipeline) -> Pipeline:
        """Add a contact to the pipeline."""
        record = self.client.create_record(TABLE_PIPELINE, pipeline.to_airtable_fields())
        pipeline.airtable_id = record.get("id")
        logger.info("Added to pipeline: contact %s at stage %s", pipeline.contact_id, pipeline.stage)
        return pipeline

    def advance_pipeline_stage(self, record_id: str, new_stage: str) -> Optional[Pipeline]:
        """Advance a pipeline entry to the next stage."""
        try:
            record = self.client.update_record(
                TABLE_PIPELINE, record_id,
                {"Stage": new_stage, "Updated": datetime.now(timezone.utc).isoformat()[:10]}
            )
            return Pipeline.from_airtable_record(record)
        except AirtableError as e:
            logger.error("Failed to advance pipeline stage: %s", e)
            return None

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get a summary of the current pipeline by stage."""
        records = self.client.list_records(TABLE_PIPELINE)
        pipelines = [Pipeline.from_airtable_record(r) for r in records]

        summary: Dict[str, Any] = {
            "total_entries": len(pipelines),
            "total_value": sum(p.value for p in pipelines),
            "by_stage": {},
        }
        for stage in PipelineStage:
            stage_items = [p for p in pipelines if p.stage == stage.value]
            summary["by_stage"][stage.value] = {
                "count": len(stage_items),
                "value": sum(p.value for p in stage_items),
                "avg_probability": (
                    sum(p.probability for p in stage_items) / len(stage_items)
                    if stage_items else 0
                ),
            }
        return summary

    # ------------------------------------------------------------------
    # Bulk Operations
    # ------------------------------------------------------------------

    def bulk_import_contacts(self, contacts: List[Contact]) -> Tuple[int, int]:
        """Bulk import contacts. Returns (created, failed) counts."""
        created = 0
        failed = 0
        fields_list = [c.to_airtable_fields() for c in contacts]
        try:
            records = self.client.create_records(TABLE_CONTACTS, fields_list)
            for i, record in enumerate(records):
                if i < len(contacts):
                    contacts[i].airtable_id = record.get("id")
            created = len(records)
        except AirtableError as e:
            logger.error("Bulk import failed: %s", e)
            failed = len(contacts)
        return created, failed

    def export_contacts_to_json(self, output_path: str) -> int:
        """Export all contacts to a JSON file."""
        contacts = self.list_contacts()
        data = [
            {
                "id": c.airtable_id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "status": c.status,
                "tags": c.tags,
            }
            for c in contacts
        ]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Exported %d contacts to %s", len(data), output_path)
        return len(data)

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get CRM dashboard statistics."""
        contacts = self.list_contacts()
        cases = self.list_cases()
        pipeline_summary = self.get_pipeline_summary()

        return {
            "contacts": {
                "total": len(contacts),
                "by_status": {
                    status: len([c for c in contacts if c.status == status])
                    for status in [s.value for s in ContactStatus]
                },
            },
            "cases": {
                "total": len(cases),
                "by_status": {
                    status: len([c for c in cases if c.status == status])
                    for status in [s.value for s in CaseStatus]
                },
            },
            "pipeline": pipeline_summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

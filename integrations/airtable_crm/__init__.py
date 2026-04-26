"""
Airtable CRM Integration for SintraPrime-Unified.

Provides a Python-native Airtable CRM client that mirrors the TypeScript
phase-10-4-airtable-crm branch functionality. Supports:
- Contact management (create, read, update, delete)
- Case/matter tracking
- Activity logging
- Pipeline management
- Bulk operations
"""
from .airtable_client import AirtableClient
from .crm_manager import CRMManager
from .models import Contact, Case, Activity, Pipeline

__all__ = ["AirtableClient", "CRMManager", "Contact", "Case", "Activity", "Pipeline"]

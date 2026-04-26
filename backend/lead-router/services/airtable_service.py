"""
Airtable Integration Service.
Writes lead records to Airtable CRM.
"""

import os
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from models.lead import Lead, AgentType

logger = logging.getLogger(__name__)


class AirtableService:
    """Service for managing lead records in Airtable."""
    
    def __init__(self, api_key: Optional[str] = None, base_id: Optional[str] = None):
        """
        Initialize Airtable service.
        
        Args:
            api_key: Airtable API key (defaults to AIRTABLE_API_KEY env var)
            base_id: Airtable base ID (defaults to AIRTABLE_BASE_ID env var)
        """
        self.api_key = api_key or os.getenv("AIRTABLE_API_KEY", "dummy_key_for_testing")
        self.base_id = base_id or os.getenv("AIRTABLE_BASE_ID", "appDummy123")
        self.table_name = "Leads"
        self.base_url = "https://api.airtable.com/v0"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def write_lead(self, lead: Lead) -> Dict[str, Any]:
        """
        Write lead record to Airtable.
        
        Args:
            lead: Lead object to write
            
        Returns:
            Response from Airtable API (including created record ID)
        """
        try:
            # Map lead to Airtable fields
            fields = {
                "LeadID": lead.lead_id,
                "Name": lead.name,
                "Email": lead.email,
                "Phone": lead.phone,
                "LegalSituation": lead.legal_situation,
                "FinancialSnapshot": lead.financial_snapshot,
                "Goals": lead.goals,
                "CompanyName": lead.company_name,
                "Industry": lead.industry,
                "ReferralSource": lead.referral_source,
                "AssignedAgent": lead.assigned_agent.value,
                "LegalScore": lead.legal_score,
                "FinancialScore": lead.financial_score,
                "UrgencyScore": lead.urgency_score,
                "QualificationScore": lead.qualification_score,
                "Status": lead.status.value,
                "SubmittedAt": lead.submitted_at.isoformat(),
            }
            
            # Only include optional datetime fields if set
            if lead.contacted_at:
                fields["ContactedAt"] = lead.contacted_at.isoformat()
            if lead.demo_scheduled_at:
                fields["DemoScheduledAt"] = lead.demo_scheduled_at.isoformat()
            
            url = f"{self.base_url}/{self.base_id}/{self.table_name}"
            
            payload = {"fields": fields}
            
            logger.info(f"Writing lead {lead.lead_id} to Airtable")
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            airtable_id = result.get("id")
            logger.info(f"Lead {lead.lead_id} written to Airtable with ID {airtable_id}")
            
            return {
                "success": True,
                "airtable_id": airtable_id,
                "response": result,
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to write lead to Airtable: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "airtable_id": None,
            }
    
    def update_lead_status(
        self,
        airtable_id: str,
        status: str,
        contacted_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Update lead status in Airtable.
        
        Args:
            airtable_id: Airtable record ID
            status: New status value
            contacted_at: When agent contacted the lead
            
        Returns:
            Update result
        """
        try:
            fields = {"Status": status}
            if contacted_at:
                fields["ContactedAt"] = contacted_at.isoformat()
            
            url = f"{self.base_url}/{self.base_id}/{self.table_name}/{airtable_id}"
            payload = {"fields": fields}
            
            logger.info(f"Updating Airtable record {airtable_id} status to {status}")
            response = requests.patch(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Successfully updated Airtable record {airtable_id}")
            return {
                "success": True,
                "response": response.json(),
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update lead status in Airtable: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def schedule_demo(self, airtable_id: str, demo_time: datetime) -> Dict[str, Any]:
        """
        Update lead record with scheduled demo time.
        
        Args:
            airtable_id: Airtable record ID
            demo_time: When the demo is scheduled
            
        Returns:
            Update result
        """
        return self.update_lead_status(
            airtable_id=airtable_id,
            status="demo-scheduled",
            contacted_at=datetime.utcnow(),
        )
    
    def get_lead_by_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve lead from Airtable by LeadID.
        
        Args:
            lead_id: Lead UUID
            
        Returns:
            Lead record or None if not found
        """
        try:
            url = f"{self.base_url}/{self.base_id}/{self.table_name}"
            params = {
                "filterByFormula": f"{{LeadID}} = '{lead_id}'",
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            records = response.json().get("records", [])
            if records:
                return records[0]
            
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve lead from Airtable: {str(e)}")
            return None


# Singleton instance
_airtable_service: Optional[AirtableService] = None


def get_airtable_service() -> AirtableService:
    """Get or create Airtable service singleton."""
    global _airtable_service
    if _airtable_service is None:
        _airtable_service = AirtableService()
    return _airtable_service

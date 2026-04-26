"""
Configuration and environment variables for lead router service.
"""

import os
from typing import Optional


class Config:
    """Base configuration."""
    
    # API Configuration
    API_TITLE = "SintraPrime Lead Router"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "Backend service for lead submission, routing, and agent assignment"
    
    # Server
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Airtable Configuration
    AIRTABLE_API_KEY = os.getenv(
        "AIRTABLE_API_KEY",
        "pat_dummy_key_for_testing"
    )
    AIRTABLE_BASE_ID = os.getenv(
        "AIRTABLE_BASE_ID",
        "appDummy123ForTesting"
    )
    AIRTABLE_TABLE_NAME = "Leads"
    
    # Email Configuration
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "sendgrid")  # sendgrid or ses
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "SG.dummy_key")
    AWS_SES_REGION = os.getenv("AWS_SES_REGION", "us-east-1")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "leads@sintraprime.ai")
    
    # Calendly Configuration
    CALENDLY_URL = os.getenv(
        "CALENDLY_URL",
        "https://calendly.com/sintraprime/demo"
    )
    
    # Tasklet Configuration (optional)
    TASKLET_API_ENABLED = os.getenv("TASKLET_API_ENABLED", "false").lower() == "true"
    TASKLET_API_KEY = os.getenv("TASKLET_API_KEY", "")
    TASKLET_WORKSPACE_ID = os.getenv("TASKLET_WORKSPACE_ID", "")
    
    # Slack Configuration (optional)
    SLACK_ENABLED = os.getenv("SLACK_ENABLED", "false").lower() == "true"
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
    
    # Follow-up Schedule (days)
    FOLLOWUP_FIRST_REMINDER_DAYS = int(os.getenv("FOLLOWUP_FIRST_REMINDER_DAYS", "3"))
    FOLLOWUP_SECOND_REMINDER_DAYS = int(os.getenv("FOLLOWUP_SECOND_REMINDER_DAYS", "7"))
    
    # Lead Routing Thresholds
    LEGAL_SPECIALIST_THRESHOLD = float(os.getenv("LEGAL_SPECIALIST_THRESHOLD", "70"))
    FINANCIAL_SPECIALIST_THRESHOLD = float(os.getenv("FINANCIAL_SPECIALIST_THRESHOLD", "70"))
    COMBINED_SPECIALIST_THRESHOLD = float(os.getenv("COMBINED_SPECIALIST_THRESHOLD", "50"))
    GENERAL_INQUIRY_THRESHOLD = float(os.getenv("GENERAL_INQUIRY_THRESHOLD", "50"))
    
    # Logging Configuration
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """Get configuration as dictionary."""
        return {
            k: getattr(cls, k)
            for k in dir(cls)
            if not k.startswith("_") and k.isupper()
        }


def load_config() -> Config:
    """Load and validate configuration."""
    config = Config()
    
    # Validate required keys
    if not config.AIRTABLE_API_KEY or "dummy" in config.AIRTABLE_API_KEY:
        import warnings
        warnings.warn(
            "AIRTABLE_API_KEY not configured. Set AIRTABLE_API_KEY environment variable.",
            UserWarning
        )
    
    if not config.SENDGRID_API_KEY or "dummy" in config.SENDGRID_API_KEY:
        import warnings
        warnings.warn(
            "SENDGRID_API_KEY not configured. Email service will use stubs.",
            UserWarning
        )
    
    return config


# Global config instance
config = load_config()

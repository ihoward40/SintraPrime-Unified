"""
Email Service for Lead Confirmation and Follow-up.
Sends automated emails via SendGrid or AWS SES.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from models.lead import Lead, AgentType
from utils.matching import get_agent_display_name

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending confirmation and follow-up emails."""
    
    def __init__(
        self,
        provider: str = "sendgrid",
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        """
        Initialize email service.
        
        Args:
            provider: "sendgrid" or "ses"
            api_key: API key for provider (defaults to env var)
            from_email: From email address (defaults to leads@sintraprime.ai)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv("SENDGRID_API_KEY", "SG.dummy_key")
        self.from_email = from_email or os.getenv(
            "FROM_EMAIL",
            "leads@sintraprime.ai"
        )
        self.calendly_url = os.getenv(
            "CALENDLY_URL",
            "https://calendly.com/sintraprime/demo"
        )
    
    def send_confirmation_email(
        self,
        lead: Lead,
        agent_name: str,
    ) -> Dict[str, Any]:
        """
        Send confirmation email to lead.
        
        Args:
            lead: Lead object
            agent_name: Display name of assigned agent
            
        Returns:
            Email send result
        """
        try:
            subject = f"Welcome to SintraPrime, {lead.name.split()[0]}!"
            
            # Compose email body
            body_html = self._compose_confirmation_html(
                lead_name=lead.name,
                agent_name=agent_name,
                calendly_url=self.calendly_url,
            )
            
            body_text = self._compose_confirmation_text(
                lead_name=lead.name,
                agent_name=agent_name,
                calendly_url=self.calendly_url,
            )
            
            # Send via provider
            if self.provider == "sendgrid":
                result = self._send_via_sendgrid(
                    to_email=lead.email,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                )
            else:
                result = self._send_via_ses(
                    to_email=lead.email,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "email_id": None,
            }
    
    def send_followup_reminder(
        self,
        lead: Lead,
        agent_name: str,
        reminder_number: int = 1,
    ) -> Dict[str, Any]:
        """
        Send follow-up reminder email.
        
        Args:
            lead: Lead object
            agent_name: Assigned agent name
            reminder_number: 1 for first reminder, 2 for second, etc.
            
        Returns:
            Email send result
        """
        try:
            if reminder_number == 1:
                subject = "Let's Get Started - SintraPrime Reminder"
                message = "We haven't heard from you yet! Our specialist is ready to help. Schedule your free 30-minute consultation within the next 24 hours."
            else:
                subject = "Final Reminder: Your Free Consultation Awaits"
                message = "This is your final reminder to schedule your consultation. We're here to help you achieve your goals."
            
            body_html = self._compose_followup_html(
                lead_name=lead.name,
                agent_name=agent_name,
                message=message,
                calendly_url=self.calendly_url,
            )
            
            body_text = self._compose_followup_text(
                lead_name=lead.name,
                agent_name=agent_name,
                message=message,
                calendly_url=self.calendly_url,
            )
            
            if self.provider == "sendgrid":
                result = self._send_via_sendgrid(
                    to_email=lead.email,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                )
            else:
                result = self._send_via_ses(
                    to_email=lead.email,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to send follow-up email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> Dict[str, Any]:
        """Send email via SendGrid API (stub implementation)."""
        try:
            # Stub implementation - would use sendgrid library in production
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            
            logger.info(f"[STUB] Sending email to {to_email} via SendGrid")
            logger.debug(f"Subject: {subject}")
            
            # Simulate API call
            email_id = f"sendgrid_{datetime.utcnow().timestamp()}"
            
            return {
                "success": True,
                "email_id": email_id,
                "provider": "sendgrid",
                "to_email": to_email,
                "subject": subject,
            }
        
        except Exception as e:
            logger.error(f"SendGrid error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "email_id": None,
            }
    
    def _send_via_ses(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> Dict[str, Any]:
        """Send email via AWS SES (stub implementation)."""
        try:
            # Stub implementation - would use boto3 in production
            # import boto3
            # ses_client = boto3.client('ses', region_name='us-east-1')
            
            logger.info(f"[STUB] Sending email to {to_email} via AWS SES")
            logger.debug(f"Subject: {subject}")
            
            # Simulate API call
            email_id = f"ses_{datetime.utcnow().timestamp()}"
            
            return {
                "success": True,
                "email_id": email_id,
                "provider": "ses",
                "to_email": to_email,
                "subject": subject,
            }
        
        except Exception as e:
            logger.error(f"SES error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "email_id": None,
            }
    
    def _compose_confirmation_html(
        self,
        lead_name: str,
        agent_name: str,
        calendly_url: str,
    ) -> str:
        """Compose HTML confirmation email."""
        first_name = lead_name.split()[0]
        return f"""
        <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ color: #1e40af; font-size: 24px; font-weight: bold; margin-bottom: 20px; }}
                    .content {{ color: #333; line-height: 1.6; margin-bottom: 20px; }}
                    .cta {{ background-color: #1e40af; color: white; padding: 12px 24px; border-radius: 4px; text-decoration: none; display: inline-block; }}
                    .footer {{ color: #999; font-size: 12px; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">Welcome to SintraPrime, {first_name}!</div>
                    
                    <div class="content">
                        <p>Thank you for your application. We're excited to help you achieve your goals.</p>
                        
                        <p><strong>{agent_name}</strong> has been assigned to your case and will review your information shortly. 
                        You can expect a call within the next 24 business hours.</p>
                        
                        <p><strong>Can't wait?</strong> Schedule your free 30-minute consultation directly:</p>
                        
                        <p><a href="{calendly_url}" class="cta">Schedule a Consultation</a></p>
                        
                        <p>This is your complimentary, no-obligation consultation to discuss your situation and explore how we can help.</p>
                        
                        <p>If you have any questions in the meantime, feel free to reply to this email.</p>
                        
                        <p>Best regards,<br/>The SintraPrime Team</p>
                    </div>
                    
                    <div class="footer">
                        <p>This email was sent to you because you submitted an inquiry through SintraPrime.ai</p>
                    </div>
                </div>
            </body>
        </html>
        """
    
    def _compose_confirmation_text(
        self,
        lead_name: str,
        agent_name: str,
        calendly_url: str,
    ) -> str:
        """Compose plain text confirmation email."""
        first_name = lead_name.split()[0]
        return f"""
Welcome to SintraPrime, {first_name}!

Thank you for your application. We're excited to help you achieve your goals.

{agent_name} has been assigned to your case and will review your information shortly.
You can expect a call within the next 24 business hours.

Can't wait? Schedule your free 30-minute consultation:
{calendly_url}

This is your complimentary, no-obligation consultation to discuss your situation and explore how we can help.

If you have any questions, feel free to reply to this email.

Best regards,
The SintraPrime Team
        """
    
    def _compose_followup_html(
        self,
        lead_name: str,
        agent_name: str,
        message: str,
        calendly_url: str,
    ) -> str:
        """Compose HTML follow-up email."""
        first_name = lead_name.split()[0]
        return f"""
        <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ color: #1e40af; font-size: 20px; font-weight: bold; margin-bottom: 20px; }}
                    .content {{ color: #333; line-height: 1.6; margin-bottom: 20px; }}
                    .cta {{ background-color: #1e40af; color: white; padding: 12px 24px; border-radius: 4px; text-decoration: none; display: inline-block; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">Don't Miss Out, {first_name}!</div>
                    
                    <div class="content">
                        <p>{message}</p>
                        
                        <p><a href="{calendly_url}" class="cta">Schedule Your Consultation</a></p>
                        
                        <p>Or contact {agent_name} directly to arrange a time that works best for you.</p>
                        
                        <p>We look forward to helping you!</p>
                        <p>The SintraPrime Team</p>
                    </div>
                </div>
            </body>
        </html>
        """
    
    def _compose_followup_text(
        self,
        lead_name: str,
        agent_name: str,
        message: str,
        calendly_url: str,
    ) -> str:
        """Compose plain text follow-up email."""
        first_name = lead_name.split()[0]
        return f"""
Don't Miss Out, {first_name}!

{message}

Schedule your consultation: {calendly_url}

Or contact {agent_name} directly.

We look forward to helping you!
The SintraPrime Team
        """


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service(provider: str = "sendgrid") -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService(provider=provider)
    return _email_service

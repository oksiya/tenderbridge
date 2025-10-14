"""
Email Service for TenderBridge (Phase 3)

Supports multiple email providers:
- SMTP (Gmail, Outlook, etc.)
- SendGrid
- Console (for testing)
"""

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EmailLog
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service supporting multiple providers.
    Provides async email sending with template rendering.
    """
    
    def __init__(self):
        self.enabled = settings.EMAIL_ENABLED
        self.provider = settings.EMAIL_PROVIDER
        self.test_mode = settings.EMAIL_TEST_MODE
        
        # Set up Jinja2 environment for email templates
        self.jinja_env = Environment(
            loader=FileSystemLoader("app/templates/emails"),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        user_id: Optional[uuid.UUID] = None,
        notification_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Send an email using configured provider.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Name of email template (without .html)
            context: Template context variables
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            user_id: User ID for logging (optional)
            notification_id: Related notification ID (optional)
        
        Returns:
            Dict with status and message
        """
        # Create email log entry
        log_id = None
        db = None
        if user_id:
            try:
                db = SessionLocal()
                email_log = EmailLog(
                    id=uuid.uuid4(),
                    notification_id=notification_id,
                    user_id=user_id,
                    email_to=to_email,
                    subject=subject,
                    template_name=template_name,
                    status="queued",
                    provider=self.provider if self.enabled else "disabled"
                )
                db.add(email_log)
                db.commit()
                log_id = email_log.id
                logger.info(f"Created email log {log_id} for {to_email}")
            except Exception as e:
                logger.error(f"Failed to create email log: {str(e)}")
                if db:
                    db.rollback()
            finally:
                if db:
                    db.close()
        
        if not self.enabled:
            logger.info(f"Email disabled. Would send to {to_email}: {subject}")
            self._update_log_status(log_id, "disabled", "Email service is disabled")
            return {"status": "disabled", "message": "Email service is disabled"}
        
        # In test mode, redirect all emails to test recipient
        if self.test_mode and settings.EMAIL_TEST_RECIPIENT:
            original_to = to_email
            to_email = settings.EMAIL_TEST_RECIPIENT
            logger.info(f"TEST MODE: Redirecting email from {original_to} to {to_email}")
        
        try:
            # Render email template
            html_body = self._render_template(template_name, context)
            text_body = self._html_to_text(html_body)
            
            # Send via configured provider
            if self.provider == "smtp":
                result = await self._send_smtp(to_email, subject, html_body, text_body, cc, bcc)
            elif self.provider == "sendgrid":
                result = await self._send_sendgrid(to_email, subject, html_body, text_body, cc, bcc)
            elif self.provider == "console":
                result = self._send_console(to_email, subject, html_body, text_body)
            else:
                raise ValueError(f"Unknown email provider: {self.provider}")
            
            # Update log with success
            self._update_log_status(log_id, "sent", None)
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to send email to {to_email}: {error_msg}")
            self._update_log_status(log_id, "failed", error_msg)
            return {
                "status": "failed",
                "message": error_msg,
                "error": error_msg
            }
    
    def _update_log_status(self, log_id: Optional[uuid.UUID], status: str, error_message: Optional[str] = None):
        """Update email log status."""
        if not log_id:
            return
        
        try:
            db = SessionLocal()
            email_log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
            if email_log:
                email_log.status = status
                if error_message:
                    email_log.error_message = error_message
                if status == "sent":
                    email_log.sent_at = datetime.utcnow()
                db.commit()
                logger.info(f"Updated email log {log_id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update email log: {str(e)}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        try:
            template = self.jinja_env.get_template(f"{template_name}.html")
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            # Fallback to basic template
            return f"<html><body><h1>{context.get('title', 'Notification')}</h1><p>{context.get('message', '')}</p></body></html>"
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple version)."""
        import re
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html)
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    async def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg['To'] = to_email
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
            
            # Attach text and HTML parts
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send via SMTP
            await asyncio.to_thread(self._send_smtp_sync, msg, to_email, cc, bcc)
            
            return {
                "status": "sent",
                "message": "Email sent successfully via SMTP",
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise Exception(f"SMTP error: {str(e)}")
    
    def _send_smtp_sync(
        self,
        msg: MIMEMultipart,
        to_email: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ):
        """Synchronous SMTP sending (for asyncio.to_thread)."""
        recipients = [to_email]
        if cc:
            recipients.extend(cc)
        if bcc:
            recipients.extend(bcc)
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            server.sendmail(settings.EMAIL_FROM, recipients, msg.as_string())
    
    async def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send email via SendGrid API."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            message = Mail(
                from_email=Email(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", text_body),
                html_content=Content("text/html", html_body)
            )
            
            if cc:
                message.cc = [Email(email) for email in cc]
            if bcc:
                message.bcc = [Email(email) for email in bcc]
            
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = await asyncio.to_thread(sg.send, message)
            
            return {
                "status": "sent",
                "message": "Email sent successfully via SendGrid",
                "sent_at": datetime.utcnow().isoformat(),
                "sendgrid_message_id": response.headers.get('X-Message-Id')
            }
        except Exception as e:
            raise Exception(f"SendGrid error: {str(e)}")
    
    def _send_console(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> Dict[str, Any]:
        """'Send' email to console (for development/testing)."""
        print("\n" + "="*80)
        print("📧 EMAIL (Console Mode)")
        print("="*80)
        print(f"To: {to_email}")
        print(f"From: {settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>")
        print(f"Subject: {subject}")
        print("-"*80)
        print("TEXT BODY:")
        print(text_body[:500] + ("..." if len(text_body) > 500 else ""))
        print("-"*80)
        print("HTML BODY (preview):")
        print(html_body[:500] + ("..." if len(html_body) > 500 else ""))
        print("="*80 + "\n")
        
        return {
            "status": "console",
            "message": "Email logged to console",
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def send_notification_email(
        self,
        user_email: str,
        notification_type: str,
        title: str,
        message: str,
        related_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
        notification_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Send email for a notification.
        
        Args:
            user_email: Recipient email
            notification_type: Type of notification (e.g., 'tender_published')
            title: Notification title
            message: Notification message
            related_data: Additional context (tender details, bid details, etc.)
            user_id: User ID for logging (optional)
            notification_id: Related notification ID (optional)
        
        Returns:
            Email send result
        """
        # Map notification type to template
        template_map = {
            "tender_published": "tender_published",
            "tender_closed": "tender_closed",
            "tender_cancelled": "tender_cancelled",
            "tender_awarded": "tender_awarded",
            "tender_status_changed": "tender_status_changed",
            "tender_deadline_reminder": "tender_deadline_reminder",  # Phase 3
            "bid_submitted": "bid_submitted",
            "bid_accepted": "bid_accepted",
            "bid_rejected": "bid_rejected",
            "bid_withdrawn": "bid_withdrawn",
        }
        
        template_name = template_map.get(notification_type, "generic_notification")
        
        # Build template context
        context = {
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "project_name": settings.PROJECT_NAME,
            "year": datetime.utcnow().year,
            **(related_data or {})
        }
        
        # Create subject line
        subject = f"{settings.PROJECT_NAME} - {title}"
        
        return await self.send_email(
            to_email=user_email,
            subject=subject,
            template_name=template_name,
            context=context,
            user_id=user_id,
            notification_id=notification_id
        )


# Singleton instance
email_service = EmailService()

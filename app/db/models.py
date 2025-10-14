from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Numeric, Float, Boolean, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from app.db.session import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    registration_number = Column(String, unique=True, nullable=False)
    bee_level = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(String, default="active")  # active, deactivated, deleted
    deactivated_at = Column(DateTime, nullable=True)
    
    users = relationship("User", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    role = Column(String, default="user")  # admin, company_admin, tender_manager, evaluator, user
    is_verified = Column(String, default="false")  # true, false
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Email preferences (Phase 3)
    email_notifications = Column(String, default="true")  # true, false
    email_frequency = Column(String, default="immediate")  # immediate, daily, weekly, never

    company = relationship("Company", back_populates="users")

class Tender(Base):
    __tablename__ = "tenders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    closing_date = Column(DateTime, nullable=False)
    publish_date = Column(DateTime, nullable=True)  # Phase 3: Scheduled publishing
    budget = Column(Float, nullable=True)  # Phase 3: Estimated budget
    posted_by_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status: draft, published, open, evaluation, closed, awarded, cancelled
    status = Column(String, default="draft")
    status_updated_at = Column(DateTime, default=datetime.utcnow)
    
    document_path = Column(String, nullable=True)
    
    # Cancellation fields
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Award-related fields (only populated when tender is awarded)
    awarded_at = Column(DateTime, nullable=True)
    winning_bid_id = Column(UUID(as_uuid=True), nullable=True)
    award_chain_tx = Column(String, nullable=True)
    award_hash_on_chain = Column(String, nullable=True)
    award_justification = Column(Text, nullable=True)

    posted_by = relationship("Company", backref="tenders")
    bids = relationship("Bid", back_populates="tender", cascade="all, delete", foreign_keys="Bid.tender_id")
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])


class Bid(Base):
    __tablename__ = "bids"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    amount = Column(Numeric, nullable=False)
    document_path = Column(String, nullable=True)
    
    # Status: pending, shortlisted, accepted, rejected, withdrawn
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Withdrawal fields
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawal_reason = Column(Text, nullable=True)
    
    # Revision tracking
    revision_number = Column(Integer, default=1)
    parent_bid_id = Column(UUID(as_uuid=True), nullable=True)  # For tracking revisions

    tender = relationship("Tender", back_populates="bids", foreign_keys=[tender_id])
    company = relationship("Company", backref="bids")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # tender_published, bid_submitted, tender_awarded, etc.
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    related_tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=True)
    related_bid_id = Column(UUID(as_uuid=True), ForeignKey("bids.id"), nullable=True)
    is_read = Column(String, default="false")  # true, false
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    user = relationship("User", backref="notifications")


class EmailLog(Base):
    """Email delivery tracking (Phase 3)"""
    __tablename__ = "email_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    email_to = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    template_name = Column(String, nullable=False)
    status = Column(String, default="queued")  # queued, sent, failed, bounced
    provider = Column(String, nullable=True)  # smtp, sendgrid, console
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="email_logs")
    notification = relationship("Notification", backref="email_logs")


class Question(Base):
    """Questions on tenders (Phase 3)"""
    __tablename__ = "questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)
    asked_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    is_answered = Column(String, default="false")  # true, false
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tender = relationship("Tender", backref="questions")
    asked_by = relationship("User", backref="questions_asked", foreign_keys=[asked_by_id])


class Answer(Base):
    """Answers to questions (Phase 3)"""
    __tablename__ = "answers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    answered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    question = relationship("Question", backref="answers")
    answered_by = relationship("User", backref="answers_given", foreign_keys=[answered_by_id])


class Document(Base):
    """Enhanced document management with versioning and approval workflow (Phase 3)"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Document ownership (either tender or bid, not both)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=True)
    bid_id = Column(UUID(as_uuid=True), ForeignKey("bids.id", ondelete="CASCADE"), nullable=True)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # File information
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String, nullable=False)
    file_hash = Column(String, nullable=True)  # SHA256 for integrity
    
    # Document classification
    category = Column(String, nullable=False, default="general")
    # Categories: technical, financial, compliance, legal, general, addendum
    tags = Column(Text, nullable=True)  # Comma-separated tags
    description = Column(Text, nullable=True)
    
    # Versioning support
    version = Column(Integer, nullable=False, default=1)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    is_current_version = Column(Boolean, default=True)
    
    # Approval workflow
    status = Column(String, nullable=False, default="draft")
    # Status: draft, pending_approval, approved, rejected, archived
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Metadata (extensible JSON field) - renamed to avoid SQLAlchemy conflict
    doc_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tender = relationship("Tender", backref="documents", foreign_keys=[tender_id])
    bid = relationship("Bid", backref="documents", foreign_keys=[bid_id])
    uploaded_by = relationship("User", backref="uploaded_documents", foreign_keys=[uploaded_by_id])
    approved_by = relationship("User", backref="approved_documents", foreign_keys=[approved_by_id])
    parent_document = relationship("Document", remote_side=[id], backref="revisions")


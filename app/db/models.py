from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
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

    company = relationship("Company", back_populates="users")

class Tender(Base):
    __tablename__ = "tenders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    closing_date = Column(DateTime, nullable=False)
    posted_by_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="open")  # open, closed, awarded
    document_path = Column(String, nullable=True)
    
    # Award-related fields (only populated when tender is awarded)
    awarded_at = Column(DateTime, nullable=True)
    winning_bid_id = Column(UUID(as_uuid=True), nullable=True)
    award_chain_tx = Column(String, nullable=True)
    award_hash_on_chain = Column(String, nullable=True)

    posted_by = relationship("Company", backref="tenders")
    bids = relationship("Bid", back_populates="tender", cascade="all, delete", foreign_keys="Bid.tender_id")


class Bid(Base):
    __tablename__ = "bids"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    amount = Column(Numeric, nullable=False)
    document_path = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    tender = relationship("Tender", back_populates="bids", foreign_keys=[tender_id])
    company = relationship("Company", backref="bids")


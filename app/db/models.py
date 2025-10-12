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
    
    users = relationship("User", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
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
    status = Column(String, default="open")

    document_path = Column(String, nullable=True)

    posted_by = relationship("Company", backref="tenders")
    bids = relationship("Bid", back_populates="tender", cascade="all, delete")


class Bid(Base):
    __tablename__ = "bids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"))
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    amount = Column(Numeric, nullable=False)
    document_path = Column(String, nullable=True)
    status = Column(String, default="submitted")
    created_at = Column(DateTime, default=datetime.utcnow)

    tender = relationship("Tender", back_populates="bids")
    company = relationship("Company", backref="bids")


from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DocumentCategory(str, Enum):
    """Valid document categories"""
    technical = "technical"
    financial = "financial"
    compliance = "compliance"
    legal = "legal"
    general = "general"
    addendum = "addendum"


class DocumentStatus(str, Enum):
    """Document approval workflow statuses"""
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    archived = "archived"


# ------------------------
# Document Schemas
# ------------------------

class DocumentBase(BaseModel):
    """Base document schema with common fields"""
    file_name: str
    file_type: str
    category: DocumentCategory = DocumentCategory.general
    description: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated tags
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags format (comma-separated, no leading/trailing spaces)"""
        if v:
            tags = [tag.strip() for tag in v.split(',')]
            return ','.join(tags)
        return v


class DocumentCreate(DocumentBase):
    """Schema for creating/uploading a document"""
    # tender_id or bid_id will be provided in the URL path
    metadata: Optional[dict] = None
    
    class Config:
        schema_extra = {
            "example": {
                "file_name": "technical_specs.pdf",
                "file_type": "application/pdf",
                "category": "technical",
                "description": "Technical specifications for the tender",
                "tags": "specifications,technical,requirements",
                "metadata": {
                    "page_count": 45,
                    "author": "Engineering Team",
                    "version_notes": "Initial version"
                }
            }
        }


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata (not the file itself)"""
    description: Optional[str] = None
    tags: Optional[str] = None
    category: Optional[DocumentCategory] = None
    metadata: Optional[dict] = None
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            tags = [tag.strip() for tag in v.split(',')]
            return ','.join(tags)
        return v


class DocumentOut(DocumentBase):
    """Schema for document output"""
    id: UUID
    tender_id: Optional[UUID] = None
    bid_id: Optional[UUID] = None
    uploaded_by_id: UUID
    file_path: str
    file_size: int
    file_hash: Optional[str] = None
    version: int
    parent_document_id: Optional[UUID] = None
    is_current_version: bool
    status: DocumentStatus
    approved_by_id: Optional[UUID] = None
    approval_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    doc_metadata: Optional[dict] = None  # Direct field name from DB
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class DocumentListOut(BaseModel):
    """Simplified document schema for list views"""
    id: UUID
    file_name: str
    file_type: str
    file_size: int
    category: DocumentCategory
    version: int
    status: DocumentStatus
    uploaded_by_id: UUID
    created_at: datetime
    is_current_version: bool
    
    class Config:
        orm_mode = True


class DocumentVersionInfo(BaseModel):
    """Version history information"""
    id: UUID
    version: int
    file_name: str
    file_size: int
    status: DocumentStatus
    uploaded_by_id: UUID
    created_at: datetime
    parent_document_id: Optional[UUID] = None
    
    class Config:
        orm_mode = True


# ------------------------
# Approval Workflow Schemas
# ------------------------

class DocumentApprovalRequest(BaseModel):
    """Schema for approving a document"""
    metadata: Optional[dict] = None  # Optional notes or approval metadata
    
    class Config:
        schema_extra = {
            "example": {
                "metadata": {
                    "approved_by_name": "John Doe",
                    "approval_notes": "Document meets all requirements"
                }
            }
        }


class DocumentRejectionRequest(BaseModel):
    """Schema for rejecting a document"""
    rejection_reason: str = Field(..., min_length=10, max_length=1000)
    
    class Config:
        schema_extra = {
            "example": {
                "rejection_reason": "Document is missing required technical specifications on pages 10-15"
            }
        }


# ------------------------
# Search & Filter Schemas
# ------------------------

class DocumentSearchQuery(BaseModel):
    """Schema for document search and filtering"""
    category: Optional[DocumentCategory] = None
    status: Optional[DocumentStatus] = None
    tags: Optional[str] = None  # Comma-separated tags to search
    uploaded_by_id: Optional[UUID] = None
    file_type: Optional[str] = None
    current_version_only: bool = True
    min_file_size: Optional[int] = None
    max_file_size: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "category": "technical",
                "status": "approved",
                "tags": "specifications,requirements",
                "current_version_only": True,
                "created_after": "2024-01-01T00:00:00"
            }
        }


# ------------------------
# Statistics Schemas
# ------------------------

class DocumentStats(BaseModel):
    """Document statistics for a tender or bid"""
    total_documents: int
    documents_by_category: dict  # {"technical": 5, "financial": 2, ...}
    documents_by_status: dict  # {"approved": 3, "pending_approval": 2, ...}
    total_file_size: int  # Total size in bytes
    latest_upload: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "total_documents": 7,
                "documents_by_category": {
                    "technical": 3,
                    "financial": 2,
                    "compliance": 1,
                    "general": 1
                },
                "documents_by_status": {
                    "approved": 5,
                    "pending_approval": 2
                },
                "total_file_size": 15728640,
                "latest_upload": "2024-01-15T14:30:00"
            }
        }

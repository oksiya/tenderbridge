from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from uuid import UUID
from datetime import datetime
from typing import Optional, List
import os
import uuid as uuid_lib
import hashlib
import json

from app.db.session import get_db
from app.db.models import Document, Tender, Bid, User
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentOut, DocumentListOut,
    DocumentVersionInfo, DocumentApprovalRequest, DocumentRejectionRequest,
    DocumentSearchQuery, DocumentStats, DocumentCategory, DocumentStatus
)
from app.core.deps import get_current_user
from app.utils.permissions import ROLES, can_create_tender
from app.services import notification_service as ns

router = APIRouter(prefix="/documents", tags=["documents"])
UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# File validation constants
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "xlsx", "xls", "zip", "jpg", "jpeg", "png", "txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ------------------------
# Helper Functions
# ------------------------

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file for integrity verification"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def validate_file(file: UploadFile) -> None:
    """Validate file extension and size"""
    # Check extension
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (if Content-Length header is available)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)} MB"
        )


def can_view_document(user: User, document: Document, db: Session) -> bool:
    """Check if user can view a document"""
    # If document belongs to tender
    if document.tender_id:
        tender = db.query(Tender).filter(Tender.id == document.tender_id).first()
        if not tender:
            return False
        # Tender owner company can view
        if user.company_id == tender.posted_by_id:
            return True
        # Companies that have submitted bids can view
        bid_exists = db.query(Bid).filter(
            and_(Bid.tender_id == tender.id, Bid.company_id == user.company_id)
        ).first()
        return bid_exists is not None
    
    # If document belongs to bid
    if document.bid_id:
        bid = db.query(Bid).filter(Bid.id == document.bid_id).first()
        if not bid:
            return False
        tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
        # Bid owner can view
        if user.company_id == bid.company_id:
            return True
        # Tender owner can view
        if user.company_id == tender.posted_by_id:
            return True
    
    return False


def can_modify_document(user: User, document: Document, db: Session) -> bool:
    """Check if user can modify a document (metadata only)"""
    # Must be uploader or tender manager+ from owning company
    if document.uploaded_by_id == user.id:
        return True
    
    # Tender managers and above from the document owner's company
    if ROLES.get(user.role, 0) >= ROLES["tender_manager"]:
        if document.tender_id:
            tender = db.query(Tender).filter(Tender.id == document.tender_id).first()
            return user.company_id == tender.posted_by_id
        elif document.bid_id:
            bid = db.query(Bid).filter(Bid.id == document.bid_id).first()
            return user.company_id == bid.company_id
    
    return False


def can_approve_document(user: User, document: Document, db: Session) -> bool:
    """Check if user can approve/reject a document"""
    # Must be tender_manager or above
    if ROLES.get(user.role, 0) < ROLES["tender_manager"]:
        return False
    
    # From the owning company
    if document.tender_id:
        tender = db.query(Tender).filter(Tender.id == document.tender_id).first()
        return user.company_id == tender.posted_by_id
    elif document.bid_id:
        bid = db.query(Bid).filter(Bid.id == document.bid_id).first()
        # Tender owner company can approve bid documents
        tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
        return user.company_id == tender.posted_by_id
    
    return False


# ------------------------
# Document Upload Endpoints
# ------------------------

@router.post("/tenders/{tender_id}/upload", response_model=DocumentOut)
async def upload_tender_document(
    tender_id: UUID,
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    metadata_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document for a tender.
    Only tender owner's company (tender_manager+) can upload.
    """
    # Validate tender exists
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Check permissions
    if current_user.company_id != tender.posted_by_id:
        raise HTTPException(
            status_code=403,
            detail="Only tender owner's company can upload documents"
        )
    
    if ROLES.get(current_user.role, 0) < ROLES["tender_manager"]:
        raise HTTPException(
            status_code=403,
            detail="Only tender managers and above can upload documents"
        )
    
    # Validate file
    validate_file(file)
    
    # Save file
    unique_name = f"{uuid_lib.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        file_size = len(content)
    
    # Calculate file hash
    file_hash = calculate_file_hash(file_path)
    
    # Parse metadata
    metadata = None
    if metadata_json:
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Create document record
    document = Document(
        tender_id=tender_id,
        uploaded_by_id=current_user.id,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        file_type=file.content_type or f".{file.filename.split('.')[-1]}",
        file_hash=file_hash,
        category=category,
        description=description,
        tags=tags,
        doc_metadata=metadata,
        status="draft",
        version=1,
        is_current_version=True
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Send notification to tender owner company users
    await ns.notify_document_uploaded(
        db, tender_id, current_user.email, file.filename
    )
    
    return document


@router.post("/bids/{bid_id}/upload", response_model=DocumentOut)
async def upload_bid_document(
    bid_id: UUID,
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    metadata_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document for a bid.
    Only bid owner's company can upload.
    """
    # Validate bid exists
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    # Check permissions
    if current_user.company_id != bid.company_id:
        raise HTTPException(
            status_code=403,
            detail="Only bid owner's company can upload documents"
        )
    
    # Validate file
    validate_file(file)
    
    # Save file
    unique_name = f"{uuid_lib.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        file_size = len(content)
    
    # Calculate file hash
    file_hash = calculate_file_hash(file_path)
    
    # Parse metadata
    metadata = None
    if metadata_json:
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Create document record
    document = Document(
        bid_id=bid_id,
        uploaded_by_id=current_user.id,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        file_type=file.content_type or f".{file.filename.split('.')[-1]}",
        file_hash=file_hash,
        category=category,
        description=description,
        tags=tags,
        doc_metadata=metadata,
        status="draft",
        version=1,
        is_current_version=True
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Send notification to tender owner
    tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
    await ns.notify_bid_document_uploaded(
        db, tender.id, bid.company_id, file.filename
    )
    
    return document


# ------------------------
# Document Retrieval Endpoints
# ------------------------

@router.get("/tenders/{tender_id}", response_model=List[DocumentListOut])
def list_tender_documents(
    tender_id: UUID,
    category: Optional[DocumentCategory] = None,
    status: Optional[DocumentStatus] = None,
    current_version_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all documents for a tender.
    Tender owner and bidders can view.
    """
    # Validate tender exists
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Check permissions
    can_view = (
        current_user.company_id == tender.posted_by_id or
        db.query(Bid).filter(
            and_(Bid.tender_id == tender_id, Bid.company_id == current_user.company_id)
        ).first() is not None
    )
    if not can_view:
        raise HTTPException(status_code=403, detail="Not authorized to view documents")
    
    # Build query
    query = db.query(Document).filter(Document.tender_id == tender_id)
    
    if current_version_only:
        query = query.filter(Document.is_current_version == True)
    if category:
        query = query.filter(Document.category == category.value)
    if status:
        query = query.filter(Document.status == status.value)
    
    documents = query.order_by(Document.created_at.desc()).all()
    return documents


@router.get("/bids/{bid_id}", response_model=List[DocumentListOut])
def list_bid_documents(
    bid_id: UUID,
    category: Optional[DocumentCategory] = None,
    status: Optional[DocumentStatus] = None,
    current_version_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all documents for a bid.
    Bid owner and tender owner can view.
    """
    # Validate bid exists
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
    
    # Check permissions
    can_view = (
        current_user.company_id == bid.company_id or
        current_user.company_id == tender.posted_by_id
    )
    if not can_view:
        raise HTTPException(status_code=403, detail="Not authorized to view documents")
    
    # Build query
    query = db.query(Document).filter(Document.bid_id == bid_id)
    
    if current_version_only:
        query = query.filter(Document.is_current_version == True)
    if category:
        query = query.filter(Document.category == category.value)
    if status:
        query = query.filter(Document.status == status.value)
    
    documents = query.order_by(Document.created_at.desc()).all()
    return documents


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if not can_view_document(current_user, document, db):
        raise HTTPException(status_code=403, detail="Not authorized to view this document")
    
    return document


@router.get("/{document_id}/versions", response_model=List[DocumentVersionInfo])
def get_document_versions(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get version history for a document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if not can_view_document(current_user, document, db):
        raise HTTPException(status_code=403, detail="Not authorized to view this document")
    
    # Find all versions (including this one and all descendants)
    root_id = document.parent_document_id if document.parent_document_id else document.id
    
    versions = db.query(Document).filter(
        or_(
            Document.id == root_id,
            Document.parent_document_id == root_id
        )
    ).order_by(Document.version.desc()).all()
    
    return versions


# ------------------------
# Document Update Endpoints
# ------------------------

@router.put("/{document_id}", response_model=DocumentOut)
def update_document_metadata(
    document_id: UUID,
    data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update document metadata (not the file itself).
    Only uploader or tender_manager+ can update.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if not can_modify_document(current_user, document, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to modify this document"
        )
    
    # Update fields
    if data.description is not None:
        document.description = data.description
    if data.tags is not None:
        document.tags = data.tags
    if data.category is not None:
        document.category = data.category.value
    if data.metadata is not None:
        document.doc_metadata = data.metadata
    
    document.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    
    return document


@router.post("/{document_id}/new-version", response_model=DocumentOut)
async def upload_new_document_version(
    document_id: UUID,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    metadata_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a new version of an existing document.
    Only uploader or tender_manager+ can create new versions.
    """
    original_doc = db.query(Document).filter(Document.id == document_id).first()
    if not original_doc:
        raise HTTPException(status_code=404, detail="Original document not found")
    
    # Check permissions
    if not can_modify_document(current_user, original_doc, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to create new version of this document"
        )
    
    # Validate file
    validate_file(file)
    
    # Save new file
    unique_name = f"{uuid_lib.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        file_size = len(content)
    
    file_hash = calculate_file_hash(file_path)
    
    # Parse metadata
    metadata = original_doc.doc_metadata or {}
    if metadata_json:
        try:
            new_metadata = json.loads(metadata_json)
            metadata.update(new_metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Mark original as not current
    original_doc.is_current_version = False
    
    # Create new version
    new_version = Document(
        tender_id=original_doc.tender_id,
        bid_id=original_doc.bid_id,
        uploaded_by_id=current_user.id,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        file_type=file.content_type or f".{file.filename.split('.')[-1]}",
        file_hash=file_hash,
        category=original_doc.category,
        description=description or original_doc.description,
        tags=original_doc.tags,
        doc_metadata=metadata,
        status="draft",  # New version starts as draft
        version=original_doc.version + 1,
        parent_document_id=document_id,
        is_current_version=True
    )
    
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    
    # Send notification
    if original_doc.tender_id:
        await ns.notify_document_version_uploaded(
            db, original_doc.tender_id, current_user.email, file.filename, new_version.version
        )
    
    return new_version


# ------------------------
# Approval Workflow Endpoints
# ------------------------

@router.post("/{document_id}/approve", response_model=DocumentOut)
async def approve_document(
    document_id: UUID,
    approval_data: DocumentApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a document.
    Only tender_manager+ from owning company can approve.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if not can_approve_document(current_user, document, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to approve this document"
        )
    
    # Update document status
    document.status = "approved"
    document.approved_by_id = current_user.id
    document.approval_date = datetime.utcnow()
    
    # Update metadata if provided
    if approval_data.metadata:
        if document.doc_metadata:
            document.doc_metadata.update(approval_data.metadata)
        else:
            document.doc_metadata = approval_data.metadata
    
    db.commit()
    db.refresh(document)
    
    # Send notification to uploader
    await ns.notify_document_approved(
        db, document.uploaded_by_id, document.file_name, current_user.email
    )
    
    return document


@router.post("/{document_id}/reject", response_model=DocumentOut)
async def reject_document(
    document_id: UUID,
    rejection_data: DocumentRejectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a document with reason.
    Only tender_manager+ from owning company can reject.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if not can_approve_document(current_user, document, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to reject this document"
        )
    
    # Update document status
    document.status = "rejected"
    document.rejection_reason = rejection_data.rejection_reason
    document.approved_by_id = current_user.id
    document.approval_date = datetime.utcnow()
    
    db.commit()
    db.refresh(document)
    
    # Send notification to uploader
    await ns.notify_document_rejected(
        db, document.uploaded_by_id, document.file_name, 
        current_user.email, rejection_data.rejection_reason
    )
    
    return document


# ------------------------
# Statistics Endpoints
# ------------------------

@router.get("/tenders/{tender_id}/stats", response_model=DocumentStats)
def get_tender_document_stats(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document statistics for a tender"""
    # Validate tender exists
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Check permissions
    can_view = (
        current_user.company_id == tender.posted_by_id or
        db.query(Bid).filter(
            and_(Bid.tender_id == tender_id, Bid.company_id == current_user.company_id)
        ).first() is not None
    )
    if not can_view:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get current documents only
    documents = db.query(Document).filter(
        and_(Document.tender_id == tender_id, Document.is_current_version == True)
    ).all()
    
    # Calculate statistics
    total_documents = len(documents)
    total_file_size = sum(doc.file_size for doc in documents)
    
    # Documents by category
    docs_by_category = {}
    for doc in documents:
        docs_by_category[doc.category] = docs_by_category.get(doc.category, 0) + 1
    
    # Documents by status
    docs_by_status = {}
    for doc in documents:
        docs_by_status[doc.status] = docs_by_status.get(doc.status, 0) + 1
    
    # Latest upload
    latest_upload = max((doc.created_at for doc in documents), default=None)
    
    return DocumentStats(
        total_documents=total_documents,
        documents_by_category=docs_by_category,
        documents_by_status=docs_by_status,
        total_file_size=total_file_size,
        latest_upload=latest_upload
    )


@router.get("/bids/{bid_id}/stats", response_model=DocumentStats)
async def get_bid_document_statistics(
    bid_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get document statistics for a bid
    
    Authorization:
    - Bid owner company
    - Tender owner company
    """
    # Check if bid exists
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    # Authorization: bid owner or tender owner
    is_bid_owner = current_user.company_id == bid.company_id
    is_tender_owner = current_user.company_id == bid.tender.posted_by_id
    
    if not (is_bid_owner or is_tender_owner):
        raise HTTPException(status_code=403, detail="Not authorized to view bid document statistics")
    
    # Get all current version documents for this bid
    documents = db.query(Document).filter(
        and_(Document.bid_id == bid_id, Document.is_current_version == True)
    ).all()
    
    # Calculate statistics
    total_documents = len(documents)
    total_file_size = sum(doc.file_size for doc in documents)
    
    # Documents by category
    docs_by_category = {}
    for doc in documents:
        docs_by_category[doc.category] = docs_by_category.get(doc.category, 0) + 1
    
    # Documents by status
    docs_by_status = {}
    for doc in documents:
        docs_by_status[doc.status] = docs_by_status.get(doc.status, 0) + 1
    
    # Latest upload
    latest_upload = max((doc.created_at for doc in documents), default=None)
    
    return DocumentStats(
        total_documents=total_documents,
        documents_by_category=docs_by_category,
        documents_by_status=docs_by_status,
        total_file_size=total_file_size,
        latest_upload=latest_upload
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download a document file
    
    Authorization:
    - Users with view access to the document
    
    Returns the file with proper Content-Disposition header for download
    """
    from fastapi.responses import FileResponse
    
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check view permissions
    if not can_view_document(current_user, document, db):
        raise HTTPException(status_code=403, detail="Not authorized to download this document")
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found on server")
    
    # Return file with proper headers for download
    return FileResponse(
        path=document.file_path,
        filename=document.file_name,
        media_type=document.file_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.file_name}"',
            "X-Document-ID": str(document.id),
            "X-Document-Version": str(document.version),
            "X-File-Hash": document.file_hash or ""
        }
    )

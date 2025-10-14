from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import os, uuid

from app.db.session import get_db
from app.db.models import Tender, Bid
from app.schemas.tender import (
    TenderCreate, TenderOut, TenderUpdate, TenderStatusUpdate,
    AwardTenderRequest, AwardVerification
)
from app.services.blockchain_service import verify_award_by_tender_id
from app.core.deps import get_current_user
from app.services.chain_queue import chain_queue
from app.utils.permissions import can_create_tender, can_award_tender
from app.utils.tender_state import TenderStateMachine, TenderStatus

router = APIRouter(prefix="/tenders", tags=["tenders"])
UPLOAD_DIR = "uploads/tenders"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=TenderOut)
def create_tender(
    data: TenderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Create a new tender in 'draft' status.
    Must be published before it can receive bids.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Check permissions
    if not can_create_tender(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only tender managers and above can create tenders"
        )

    tender = Tender(
        title=data.title,
        description=data.description,
        closing_date=data.closing_date,
        posted_by_id=current_user.company_id,
        status=TenderStatus.DRAFT,  # Start in draft status
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)

    return tender


@router.get("/", response_model=list[TenderOut])
def list_tenders(db: Session = Depends(get_db)):
    return db.query(Tender).order_by(Tender.created_at.desc()).all()


@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: UUID, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.put("/{tender_id}", response_model=TenderOut)
def update_tender(
    tender_id: UUID,
    data: TenderUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update tender details.
    Only allowed in 'draft' or 'published' status.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Authorization
    if not can_award_tender(current_user, tender.posted_by_id):
        raise HTTPException(status_code=403, detail="Not authorized to update this tender")
    
    # Check if tender can be edited
    if not TenderStateMachine.can_edit_tender(tender.status):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit tender in '{tender.status}' status. Only draft/published tenders can be edited."
        )
    
    # Update fields
    if data.title is not None:
        tender.title = data.title
    if data.description is not None:
        tender.description = data.description
    if data.closing_date is not None:
        tender.closing_date = data.closing_date
    
    tender.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tender)
    
    return tender


@router.put("/{tender_id}/status", response_model=TenderOut)
def update_tender_status(
    tender_id: UUID,
    status_update: TenderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update tender status (state machine transitions).
    Validates transitions and handles state-specific logic.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Authorization
    if not can_award_tender(current_user, tender.posted_by_id):
        raise HTTPException(status_code=403, detail="Not authorized to update this tender")
    
    # Validate transition
    is_valid, message = TenderStateMachine.validate_transition(
        tender.status,
        status_update.status,
        status_update.reason
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Handle cancellation
    if status_update.status == TenderStatus.CANCELLED:
        tender.cancelled_at = datetime.utcnow()
        tender.cancellation_reason = status_update.reason
        tender.cancelled_by_id = current_user.id
    
    # Update status
    tender.status = status_update.status
    tender.status_updated_at = datetime.utcnow()
    tender.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tender)
    
    return tender


@router.put("/{tender_id}/close")
def close_tender(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Close tender for bid submissions.
    Transitions from 'open' to 'closed' status.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.posted_by_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to close this tender")
    
    # Validate transition
    if tender.status != TenderStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close tender in '{tender.status}' status. Must be 'open'."
        )

    tender.status = TenderStatus.CLOSED
    tender.status_updated_at = datetime.utcnow()
    tender.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Tender closed successfully", "status": tender.status}


@router.post("/upload")
async def upload_tender(
    title: str = Form(...),
    description: str = Form(...),
    closing_date: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a tender with document attachment (no blockchain stamping)"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Check permissions
    if not can_create_tender(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only tender managers and above can create tenders"
        )

    allowed_ext = {"pdf", "docx", "zip"}
    ext = file.filename.split(".")[-1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, unique_name)
    with open(path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        closing_dt = datetime.fromisoformat(closing_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    tender = Tender(
        title=title,
        description=description,
        closing_date=closing_dt,
        posted_by_id=current_user.company_id,
        document_path=path,
        status=TenderStatus.DRAFT,  # Start in draft status
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)

    return {"message": "Tender uploaded successfully (draft status)", "tender": tender}


@router.post("/{tender_id}/award", response_model=TenderOut)
def award_tender(
    tender_id: UUID,
    award_request: AwardTenderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Award a tender to the winning bid - records on blockchain.
    Requires tender to be in 'evaluation' status.
    Requires justification for the award decision.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Check permissions
    if not can_award_tender(current_user, tender.posted_by_id):
        raise HTTPException(
            status_code=403,
            detail="Only tender managers/admins from the tender-owning company can award tenders"
        )
    
    # Check if tender can be awarded (must be in evaluation status)
    if not TenderStateMachine.can_award(tender.status):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot award tender in '{tender.status}' status. Must be in 'evaluation' status."
        )
    
    if tender.status == TenderStatus.AWARDED:
        raise HTTPException(status_code=400, detail="Tender already awarded")
    
    # Verify the winning bid exists and belongs to this tender
    bid = db.query(Bid).filter(
        Bid.id == award_request.winning_bid_id,
        Bid.tender_id == tender_id
    ).first()
    
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found for this tender")
    
    # Check bid status (should not be withdrawn)
    if bid.status == "withdrawn":
        raise HTTPException(status_code=400, detail="Cannot award to a withdrawn bid")
    
    # Update tender status
    tender.status = TenderStatus.AWARDED
    tender.winning_bid_id = award_request.winning_bid_id
    tender.awarded_at = datetime.utcnow()
    tender.status_updated_at = datetime.utcnow()
    tender.updated_at = datetime.utcnow()
    tender.award_justification = award_request.justification
    
    # Update bid status
    bid.status = "accepted"
    
    # Update all other bids to rejected
    other_bids = db.query(Bid).filter(
        Bid.tender_id == tender_id,
        Bid.id != bid.id,
        Bid.status != "withdrawn"
    ).all()
    for other_bid in other_bids:
        other_bid.status = "rejected"
    
    db.commit()
    db.refresh(tender)
    
    # Queue blockchain job for award recording
    try:
        job = chain_queue.enqueue(
            'app.services.chain_worker.process_award',
            tender_id=str(tender.id),
            winning_bid_id=str(bid.id),
            award_amount=bid.amount
        )
        print(f"✅ Award job queued: {job.id}")
    except Exception as e:
        print(f"⚠️ Blockchain queue failed: {e}")
    
    return tender


@router.get("/{tender_id}/verify", response_model=AwardVerification)
def verify_tender_award(tender_id: UUID, db: Session = Depends(get_db)):
    """
    Verify if a tender award has been recorded on the blockchain.
    Returns award details if found on-chain.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    if tender.status != "awarded":
        return AwardVerification(
            tender_id=str(tender.id),
            verified=False
        )
    
    # Verify award on blockchain
    result = verify_award_by_tender_id(str(tender.id))
    
    if result.get("verified"):
        return AwardVerification(
            tender_id=result.get("tender_id"),
            verified=True,
            winning_bid_id=result.get("winning_bid_id"),
            winning_company_id=result.get("winning_company_id"),
            award_amount=result.get("award_amount"),
            award_date=result.get("award_date"),
            awarded_by=result.get("awarded_by"),
            hash_on_chain=result.get("hash_on_chain"),
            method=result.get("method")
        )
    
    return AwardVerification(
        tender_id=str(tender.id),
        verified=False
    )

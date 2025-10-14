from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
from datetime import datetime
import os, uuid

from app.db.session import get_db
from app.db.models import Bid, Tender
from app.schemas.bid import BidOut, BidStatusUpdate, BidWithdrawal, BidUpdate
from app.core.deps import get_current_user
from app.utils.permissions import can_submit_bid
from app.utils.tender_state import TenderStateMachine

router = APIRouter(prefix="/bids", tags=["bids"])
UPLOAD_DIR = "uploads/bids"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=BidOut)
async def submit_bid_with_file(
    tender_id: UUID = Form(...),
    amount: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit a bid with document attachment - only allowed when tender is 'open'"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Check permissions
    if not can_submit_bid(current_user):
        raise HTTPException(
            status_code=403,
            detail="User must be assigned to a company to submit bids"
        )

    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Check if tender can receive bids
    if not TenderStateMachine.can_receive_bids(tender.status):
        raise HTTPException(
            status_code=400,
            detail=f"Tender is '{tender.status}'. Bids can only be submitted when tender is 'open'."
        )
    
    # Check closing date
    if datetime.utcnow() >= tender.closing_date:
        raise HTTPException(
            status_code=400,
            detail="Tender has passed its closing date and is no longer accepting bids."
        )
    
    # Prevent company from bidding on its own tender
    if tender.posted_by_id == current_user.company_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot bid on your own company's tender"
        )

    allowed = {"pdf", "docx", "zip"}
    ext = file.filename.split(".")[-1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'")

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, unique_name)
    with open(path, "wb") as f:
        f.write(await file.read())

    try:
        amt = Decimal(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount format")

    bid = Bid(
        tender_id=tender_id,
        company_id=current_user.company_id,
        amount=amt,
        document_path=path,
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)

    return bid


@router.get("/company/{company_id}", response_model=list[BidOut])
def list_bids_by_company(
    company_id: UUID, 
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    List all bids by a specific company.
    Authorization: Only company members can view their own bids.
    """
    # Check if user belongs to the company they're trying to view
    if current_user.company_id != company_id:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to view bids for this company"
        )
    
    bids = db.query(Bid).filter(Bid.company_id == company_id).order_by(Bid.created_at.desc()).all()
    return bids


@router.get("/tender/{tender_id}", response_model=list[BidOut])
def list_bids_for_tender(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.posted_by_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to view bids for this tender")

    return db.query(Bid).filter(Bid.tender_id == tender_id).all()


@router.put("/{bid_id}/status")
def update_bid_status(
    bid_id: UUID,
    payload: BidStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
    if tender.posted_by_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to update bids on this tender")

    if payload.status not in {"pending", "accepted", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid status value")

    bid.status = payload.status
    db.commit()
    db.refresh(bid)
    return {"message": "Bid status updated", "bid_id": str(bid.id), "status": bid.status}


@router.get("/{bid_id}")
def get_bid(bid_id: UUID, db: Session = Depends(get_db)):
    """Get bid details by ID"""
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid


@router.post("/{bid_id}/withdraw", response_model=BidOut)
def withdraw_bid(
    bid_id: UUID,
    withdrawal: BidWithdrawal,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Withdraw a bid before tender closes.
    Requires a reason for withdrawal.
    """
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    # Authorization: only bid owner can withdraw
    if bid.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to withdraw this bid")
    
    # Check if bid is already withdrawn
    if bid.status == "withdrawn":
        raise HTTPException(status_code=400, detail="Bid is already withdrawn")
    
    # Check tender status - can only withdraw if tender is open
    tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
    if not TenderStateMachine.can_receive_bids(tender.status):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot withdraw bid when tender is '{tender.status}'. Withdrawals only allowed when tender is 'open'."
        )
    
    # Withdraw the bid
    bid.status = "withdrawn"
    bid.withdrawn_at = datetime.utcnow()
    bid.withdrawal_reason = withdrawal.reason
    bid.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(bid)
    
    return bid


@router.put("/{bid_id}/revise", response_model=BidOut)
async def revise_bid(
    bid_id: UUID,
    amount: str = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Revise a bid before tender closes.
    Creates a new revision with updated amount/document.
    """
    original_bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not original_bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    # Authorization: only bid owner can revise
    if original_bid.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to revise this bid")
    
    # Check if bid is withdrawn
    if original_bid.status == "withdrawn":
        raise HTTPException(status_code=400, detail="Cannot revise a withdrawn bid")
    
    # Check tender status - can only revise if tender is open
    tender = db.query(Tender).filter(Tender.id == original_bid.tender_id).first()
    if not TenderStateMachine.can_receive_bids(tender.status):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot revise bid when tender is '{tender.status}'. Revisions only allowed when tender is 'open'."
        )
    
    # Check closing date
    if datetime.utcnow() >= tender.closing_date:
        raise HTTPException(
            status_code=400,
            detail="Tender has passed its closing date. Cannot revise bid."
        )
    
    # Handle file upload if provided
    document_path = original_bid.document_path
    if file:
        allowed = {"pdf", "docx", "zip"}
        ext = file.filename.split(".")[-1].lower()
        if ext not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'")
        
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        path = os.path.join(UPLOAD_DIR, unique_name)
        with open(path, "wb") as f:
            f.write(await file.read())
        document_path = path
    
    try:
        new_amount = Decimal(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount format")
    
    # Mark original bid as superseded (keep for history)
    original_bid.status = "superseded"
    original_bid.updated_at = datetime.utcnow()
    
    # Create new revision
    revised_bid = Bid(
        tender_id=original_bid.tender_id,
        company_id=original_bid.company_id,
        amount=new_amount,
        document_path=document_path,
        status="pending",
        revision_number=original_bid.revision_number + 1,
        parent_bid_id=bid_id
    )
    
    db.add(revised_bid)
    db.commit()
    db.refresh(revised_bid)
    
    return revised_bid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import os, uuid

from app.db.session import get_db
from app.db.models import Tender, Bid
from app.schemas.tender import TenderCreate, TenderOut, AwardTenderRequest, AwardVerification
from app.services.blockchain_service import verify_award_by_tender_id
from app.core.deps import get_current_user
from app.services.chain_queue import chain_queue

router = APIRouter(prefix="/tenders", tags=["tenders"])
UPLOAD_DIR = "uploads/tenders"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=TenderOut)
def create_tender(
    data: TenderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create a new tender (no blockchain stamping)"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")

    tender = Tender(
        title=data.title,
        description=data.description,
        closing_date=data.closing_date,
        posted_by_id=current_user.company_id,
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


@router.put("/{tender_id}/close")
def close_tender(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.posted_by_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to close this tender")

    tender.status = "closed"
    db.commit()
    return {"message": "Tender closed successfully"}


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
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)

    return {"message": "Tender uploaded successfully", "tender": tender}


@router.post("/{tender_id}/award", response_model=TenderOut)
def award_tender(
    tender_id: UUID,
    award_request: AwardTenderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Award a tender to the winning bid - records on blockchain.
    Only the tender owner can award the tender.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    if tender.posted_by_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Only tender owner can award")
    
    if tender.status == "awarded":
        raise HTTPException(status_code=400, detail="Tender already awarded")
    
    # Verify the winning bid exists and belongs to this tender
    bid = db.query(Bid).filter(
        Bid.id == award_request.winning_bid_id,
        Bid.tender_id == tender_id
    ).first()
    
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found for this tender")
    
    # Update tender status
    tender.status = "awarded"
    tender.winning_bid_id = award_request.winning_bid_id
    tender.awarded_at = datetime.utcnow()
    
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

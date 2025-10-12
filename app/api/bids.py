from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
import os, uuid

from app.db.session import get_db
from app.db.models import Bid, Tender
from app.schemas.bid import BidOut, BidStatusUpdate
from app.core.deps import get_current_user

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
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")

    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender or tender.status != "open":
        raise HTTPException(status_code=400, detail="Tender not open for bids")

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
def list_bids_by_company(company_id: UUID, db: Session = Depends(get_db)):
    bids = db.query(Bid).filter(Bid.company_id == company_id).order_by(Bid.created_at.desc()).all()
    return bids

@router.get("/tender/{tender_id}", response_model=list[BidOut])
def list_bids_for_tender(tender_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.posted_by_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to view bids for this tender")

    return db.query(Bid).filter(Bid.tender_id == tender_id).all()


@router.put("/{bid_id}/status")
def update_bid_status(bid_id: UUID, payload: BidStatusUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
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

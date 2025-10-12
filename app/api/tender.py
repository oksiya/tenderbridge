from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from app.db.session import get_db
from app.db.models import Tender, Bid, Company
from app.schemas.tender import TenderCreate, TenderOut, BidCreate, BidOut
import os, uuid

router = APIRouter(prefix="/tenders", tags=["tenders"])

UPLOAD_DIR = "uploads/tenders"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create a new tender (buyer)
@router.post("/", response_model=TenderOut)
def create_tender(data: TenderCreate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == data.posted_by_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    tender = Tender(**data.dict())
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return tender


# List all tenders
@router.get("/", response_model=list[TenderOut])
def get_tenders(db: Session = Depends(get_db)):
    return db.query(Tender).order_by(Tender.created_at.desc()).all()


# Get single tender
@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: UUID, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


# Close tender
@router.put("/{tender_id}/close")
def close_tender(tender_id: UUID, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    tender.status = "closed"
    db.commit()
    return {"message": "Tender closed successfully"}

# Submit a bid
@router.post("/bids", response_model=BidOut)
def submit_bid(data: BidCreate, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == data.tender_id).first()
    if not tender or tender.status != "open":
        raise HTTPException(status_code=400, detail="Tender not open for bids")

    company = db.query(Company).filter(Company.id == data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    bid = Bid(**data.dict())
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


# Get all bids for a tender
@router.get("/{tender_id}/bids", response_model=list[BidOut])
def get_bids_for_tender(tender_id: UUID, db: Session = Depends(get_db)):
    bids = db.query(Bid).filter(Bid.tender_id == tender_id).all()
    return bids

@router.post("/upload")
async def upload_tender(
    title: str = Form(...),
    description: str = Form(...),
    closing_date: str = Form(...),
    posted_by_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a new tender along with its specification document.
    """
    # Validate file type (optional but safer)
    allowed_extensions = {"pdf", "docx", "zip"}
    file_ext = file.filename.split(".")[-1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save file with unique name
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Convert closing_date string → datetime
    try:
        closing_dt = datetime.fromisoformat(closing_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601 (e.g., 2025-12-10T00:00:00)")

    # Create tender record
    new_tender = Tender(
        title=title,
        description=description,
        closing_date=closing_dt,
        posted_by_id=posted_by_id,
        document_path=file_path,
    )

    db.add(new_tender)
    db.commit()
    db.refresh(new_tender)

    return {
        "message": "Tender uploaded successfully",
        "tender": {
            "id": str(new_tender.id),
            "title": new_tender.title,
            "description": new_tender.description,
            "closing_date": new_tender.closing_date,
            "posted_by_id": str(new_tender.posted_by_id),
            "document_path": new_tender.document_path,
        },
    }


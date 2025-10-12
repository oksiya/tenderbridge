from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
import os, uuid

from app.db.session import get_db
from app.db.models import Tender
from app.schemas.tender import TenderCreate, TenderOut
from app.core.deps import get_current_user

router = APIRouter(prefix="/tenders", tags=["tenders"])
UPLOAD_DIR = "uploads/tenders"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=TenderOut)
def create_tender(data: TenderCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
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
def close_tender(tender_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
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

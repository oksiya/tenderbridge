from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.db.models import Company, User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut

router = APIRouter(prefix="/company", tags=["company"])

# Create company
@router.post("/", response_model=CompanyOut)
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    existing = db.query(Company).filter(Company.registration_number == data.registration_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")
    
    company = Company(**data.dict())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

# Get all companies
@router.get("/", response_model=list[CompanyOut])
def get_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()

# Get single company
@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

# Update company
@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: UUID, data: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    for key, value in data.dict(exclude_unset=True).items():
        setattr(company, key, value)
    
    db.commit()
    db.refresh(company)
    return company

# Delete company
@router.delete("/{company_id}")
def delete_company(company_id: UUID, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    db.delete(company)
    db.commit()
    return {"message": "Company deleted successfully"}

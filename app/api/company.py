from app.core.deps import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from app.db.session import get_db
from app.db.models import Company, User
from app.schemas.company import AssignCompanyRequest, CompanyCreate, CompanyUpdate, CompanyOut

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
    """Get all active companies (excludes deleted/deactivated)"""
    return db.query(Company).filter(Company.is_active == "active").all()

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

# Delete company (soft delete with safety checks)
@router.delete("/{company_id}")
def delete_company(
    company_id: UUID, 
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Deactivate a company (soft delete).
    Prevents deletion if company has active tenders or bids.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for active tenders
    from app.db.models import Tender, Bid
    active_tenders = db.query(Tender).filter(
        Tender.posted_by_id == company_id,
        Tender.status.in_(["open", "evaluation"])
    ).count()
    
    if active_tenders > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete company with {active_tenders} active tender(s). Close or award them first."
        )
    
    # Check for pending bids
    pending_bids = db.query(Bid).filter(
        Bid.company_id == company_id,
        Bid.status == "pending"
    ).count()
    
    if pending_bids > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete company with {pending_bids} pending bid(s). Wait for tender awards."
        )
    
    # Soft delete: deactivate the company
    company.is_active = "deleted"
    company.deactivated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Company deactivated successfully",
        "company_id": str(company_id),
        "deactivated_at": company.deactivated_at
    }

@router.post("/assign")
def assign_user_to_company(
    data: AssignCompanyRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Assign a user to a company.
    Authorization: Only admins or company_admins of the target company can assign users.
    """
    user = db.query(User).filter(User.id == data.user_id).first()
    company = db.query(Company).filter(Company.id == data.company_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Authorization check
    is_admin = current_user.role == "admin"
    is_company_admin = (
        current_user.role == "company_admin" and 
        current_user.company_id == data.company_id
    )
    
    if not (is_admin or is_company_admin):
        raise HTTPException(
            status_code=403,
            detail="Only admins or company administrators can assign users to this company"
        )

    user.company_id = company.id
    db.commit()

    return {
        "message": f"User {user.email} successfully linked to {company.name}",
        "user_id": str(user.id),
        "company_id": str(company.id)
    }

@router.get("/{company_id}/users")
def get_users_by_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Fetch all users under a specific company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    users = db.query(User).filter(User.company_id == company_id).all()

    return [
        {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at
        }
        for user in users
    ]
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .db import get_db
from .models import Organization
from .schemas import OrgCreate, OrgOut

router = APIRouter(prefix="/orgs", tags=["Organizations"])

@router.post("", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
def create_org(payload: OrgCreate, db: Session = Depends(get_db)):
    org = Organization(name=payload.name.strip())
    db.add(org)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Organization name already exists."
        )
    db.refresh(org)
    return org

@router.get("", response_model=list[OrgOut])
def list_orgs(db: Session = Depends(get_db)):
    return db.query(Organization).order_by(Organization.created_at.desc()).all()

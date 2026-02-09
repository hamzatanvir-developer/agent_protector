# app/routes_demo.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import get_db
from .models import AccessRequest, Organization
from .policy_engine import gateway_decide_from_prompt, issue_grant_if_approved

router = APIRouter(prefix="/demo", tags=["Demo Agent"])
templates = Jinja2Templates(directory="app/templates")

DEMO_ORG_NAME = "Judge Demo Org"  # stable for judges


def get_or_create_demo_org(db: Session) -> Organization:
    org = db.query(Organization).filter(Organization.name == DEMO_ORG_NAME).first()
    if org:
        return org
    org = Organization(name=DEMO_ORG_NAME)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _latest_demo_rows(db: Session, org_id: str):
    return (
        db.query(AccessRequest)
        .filter(AccessRequest.org_id == org_id, AccessRequest.agent_id == "demo_agent")
        .order_by(AccessRequest.created_at.desc())
        .limit(15)
        .all()
    )


@router.get("")
def demo_home(request: Request, db: Session = Depends(get_db)):
    org = get_or_create_demo_org(db)
    rows = _latest_demo_rows(db, org.id)
    return templates.TemplateResponse(
        "demo_agent.html",
        {"request": request, "org_id": org.id, "rows": rows, "result": None, "error": None, "created": None},
    )


@router.post("/run")
def demo_run(
    request: Request,
    org_id: str = Form(...),
    prompt: str = Form(...),
    db: Session = Depends(get_db),
):
    # ✅ this MUST be Form(...) to avoid the dict_type 422 error
    prompt = (prompt or "").strip()
    if not prompt:
        rows = _latest_demo_rows(db, org_id)
        return templates.TemplateResponse(
            "demo_agent.html",
            {"request": request, "org_id": org_id, "rows": rows, "result": None, "error": "Prompt cannot be empty.", "created": None},
        )

    # safety: ensure org exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="org_id not found")

    ar = gateway_decide_from_prompt(db=db, org_id=org_id, prompt=prompt)
    rows = _latest_demo_rows(db, org_id)

    return templates.TemplateResponse(
        "demo_agent.html",
        {"request": request, "org_id": org_id, "rows": rows, "result": None, "error": None, "created": ar},
    )


@router.post("/execute")
def demo_execute(
    request: Request,
    org_id: str = Form(...),
    request_id: str = Form(...),
    db: Session = Depends(get_db),
):
    ar = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not ar:
        raise HTTPException(status_code=404, detail="request not found")
    if ar.org_id != org_id:
        raise HTTPException(status_code=403, detail="request does not belong to this org")

    try:
        result = issue_grant_if_approved(db=db, ar=ar)
        error = None
    except Exception as e:
        result = None
        error = str(e)

    rows = _latest_demo_rows(db, org_id)
    return templates.TemplateResponse(
        "demo_agent.html",
        {"request": request, "org_id": org_id, "rows": rows, "result": result, "error": error, "created": None},
    )


@router.post("/reset")
def demo_reset(
    request: Request,
    org_id: str = Form(...),
    db: Session = Depends(get_db),
):
    (
        db.query(AccessRequest)
        .filter(AccessRequest.org_id == org_id, AccessRequest.agent_id == "demo_agent")
        .delete(synchronize_session=False)
    )
    db.commit()

    rows = _latest_demo_rows(db, org_id)
    return templates.TemplateResponse(
        "demo_agent.html",
        {"request": request, "org_id": org_id, "rows": rows, "result": None, "error": None, "created": None, "reset_ok": True},
    )

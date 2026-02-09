# app/routes_demo_agent.py
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Form, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import get_db
from .models import Organization, AccessRequest
from .policy_engine import gateway_decide_from_prompt, issue_grant_if_approved

# ✅ IMPORTANT: change prefix to avoid collision with /demo/*
router = APIRouter(prefix="/demo-agent", tags=["Demo Agent API"])
templates = Jinja2Templates(directory="app/templates")


def _org_exists(db: Session, org_id: str) -> bool:
    return db.query(Organization).filter(Organization.id == org_id).first() is not None


@router.get("/ui", response_class=HTMLResponse)
def demo_agent_ui(org_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Optional UI route (separate from /demo)
    """
    if not _org_exists(db, org_id):
        raise HTTPException(status_code=404, detail="org_id not found")

    return templates.TemplateResponse("demo_agent.html", {"request": request, "org_id": org_id})


@router.post("/run")
async def demo_agent_run(
    # ✅ Accept JSON body (primary)
    payload: Optional[Dict[str, Any]] = Body(default=None),
    # ✅ Also accept Form posts (fallback)
    org_id: Optional[str] = Form(default=None),
    prompt: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    """
    Accepts either:
      - JSON: { "org_id": "...", "prompt": "..." }
      - Form: org_id=...&prompt=...
    Returns: { request_id, decision, risk_score, message, manager_url }
    """
    if payload:
        org_id_val = (payload.get("org_id") or "").strip()
        prompt_val = (payload.get("prompt") or "").strip()
    else:
        org_id_val = (org_id or "").strip()
        prompt_val = (prompt or "").strip()

    if not org_id_val or not prompt_val:
        raise HTTPException(status_code=400, detail="org_id and prompt are required")

    if not _org_exists(db, org_id_val):
        raise HTTPException(status_code=404, detail="org_id not found")

    # Gateway makes decision + creates AccessRequest row
    ar: AccessRequest = gateway_decide_from_prompt(db=db, org_id=org_id_val, prompt=prompt_val)

    return {
        "request_id": ar.id,
        "decision": ar.decision,
        "risk_score": getattr(ar, "risk_score", 0) or 0,
        "message": "Created access request via AgentProtector gateway",
        "manager_url": f"/manager/console?org_id={org_id_val}&tab=pending&refresh=6&from=demo",
        "demo_url": f"/demo?org_id={org_id_val}",
    }


@router.post("/retry")
async def demo_agent_retry(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    org_id: Optional[str] = Form(default=None),
    request_id: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    """
    Accepts either:
      - JSON: { "org_id": "...", "request_id": "..." }
      - Form: org_id=...&request_id=...
    Simulates: agent retries tool after manager decision.
    """
    if payload:
        org_id_val = (payload.get("org_id") or "").strip()
        request_id_val = (payload.get("request_id") or "").strip()
    else:
        org_id_val = (org_id or "").strip()
        request_id_val = (request_id or "").strip()

    if not org_id_val or not request_id_val:
        raise HTTPException(status_code=400, detail="org_id and request_id are required")

    ar = db.query(AccessRequest).filter(AccessRequest.id == request_id_val).first()
    if not ar:
        raise HTTPException(status_code=404, detail="request not found")
    if ar.org_id != org_id_val:
        raise HTTPException(status_code=403, detail="request does not belong to this org")

    grant = issue_grant_if_approved(db=db, ar=ar)

    return {
        "ok": True,
        "tool": grant["tool"],
        "scope": grant["scope"],
        "result": grant["result_preview"],
    }

# app/routes_admin.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import get_db
from .models import Organization, Agent
from .auth import issue_key, hash_key

router = APIRouter(prefix="/admin", tags=["Admin Setup"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    return templates.TemplateResponse(
        "admin_setup.html",
        {"request": request, "created": None},
    )


@router.post("/setup", response_class=HTMLResponse)
def setup_create(
    request: Request,
    org_name: str = Form(...),
    agent_name: str = Form(...),
    db: Session = Depends(get_db),
):
    org_name = (org_name or "").strip()
    agent_name = (agent_name or "").strip()

    if not org_name:
        raise HTTPException(status_code=400, detail="org_name is required")
    if not agent_name:
        raise HTTPException(status_code=400, detail="agent_name is required")

    # Create org
    org = Organization(name=org_name)
    db.add(org)
    db.commit()
    db.refresh(org)

    # Create agent + key
    raw_key = issue_key()
    agent = Agent(org_id=str(org.id), name=agent_name, api_key_hash=hash_key(raw_key))
    db.add(agent)
    db.commit()
    db.refresh(agent)

    created = {
        "org_id": str(org.id),
        "org_name": org.name,
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "api_key": raw_key,  # show ONCE here
    }

    return templates.TemplateResponse(
        "admin_setup.html",
        {"request": request, "created": created},
    )

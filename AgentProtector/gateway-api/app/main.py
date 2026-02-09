# app/main.py
from fastapi import FastAPI

from app.db import init_db
from app import models  # noqa: F401

from app.routes_orgs import router as orgs_router
from app.routes_access import router as access_router
from app.routes_manager import router as manager_router
from app.routes_agents import router as agents_router
from app.routes_admin import router as admin_router
from app.routes_demo_agent import router as demo_agent_router
from app.routes_demo import router as demo_router
from app.routes_judge import router as judge_router

app = FastAPI(title="Agent Access Gateway")


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(orgs_router)
app.include_router(access_router)
app.include_router(manager_router)
app.include_router(agents_router)
app.include_router(admin_router)
app.include_router(demo_agent_router)
app.include_router(demo_router)
app.include_router(judge_router)


@app.get("/")
def root():
    return {"message": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}

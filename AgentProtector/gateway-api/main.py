from fastapi import FastAPI

from app.db import init_db, SessionLocal
from app import models  # noqa: F401  # ensure models are imported/registered

from app.seed import seed_if_empty

from app.routes_orgs import router as orgs_router
from app.routes_access import router as access_router
from app.routes_manager import router as manager_router
from app.routes_agents import router as agents_router
from app.routes_admin import router as admin_router
from app.routes_demo import router as demo_router
from app.routes_judge import router as judge_router

app = FastAPI(title="Agent Access Gateway")


@app.on_event("startup")
def on_startup():
    # ✅ Judge-friendly: auto-create tables (SQLite fallback in db.py)
    init_db()

    # ✅ Judge-friendly: auto seed demo data (so UI works immediately)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


# Routers
app.include_router(orgs_router)
app.include_router(access_router)
app.include_router(manager_router)
app.include_router(agents_router)
app.include_router(admin_router)
app.include_router(demo_router)
app.include_router(judge_router)


@app.get("/")
def root():
    return {"message": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}

"""Procurement Tracker API: FastAPI + SQLAlchemy.
Hierarchy: Project -> Package -> Supplier (real foreign keys, ON DELETE CASCADE).
Run:  uvicorn app:app --reload        (open http://127.0.0.1:8000)
Deploy: Vercel detects `app` in this file; the front end is served from public/.
DB:   DATABASE_URL env var. Default: sqlite:///tracker.db (local dev only).
      Production: your Neon string, e.g. postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require
Auth: set APP_USER and APP_PASSWORD to require a login (always set them online).
"""
import json, os, secrets
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Index, Integer, MetaData, String,
                        Table, Text, create_engine, delete, event, insert, select, update)
from sqlalchemy.engine import Engine

from export_xlsx import package_workbook, project_workbook, to_bytes

DB_URL = os.getenv("DATABASE_URL", "sqlite:///tracker.db")
for prefix in ("postgres://", "postgresql://"):          # hosted DBs hand out these prefixes
    if DB_URL.startswith(prefix):
        DB_URL = "postgresql+psycopg://" + DB_URL[len(prefix):]
# prepare_threshold=None keeps psycopg compatible with Neon's pooled (PgBouncer) endpoint
_args = {"prepare_threshold": None} if DB_URL.startswith("postgresql+psycopg") else {}
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=300, connect_args=_args)

@event.listens_for(Engine, "connect")
def _sqlite_fk(dbapi_conn, _):                            # SQLite ignores FKs unless enabled
    if DB_URL.startswith("sqlite"):
        cur = dbapi_conn.cursor(); cur.execute("PRAGMA foreign_keys=ON"); cur.close()

md = MetaData()
projects = Table("projects", md,
    Column("id", String(64), primary_key=True),
    Column("name", String(200), nullable=False), Column("client", String(200)),
    Column("status", String(20), nullable=False, default="Active"))
packages = Table("packages", md,
    Column("id", String(64), primary_key=True),
    Column("project_id", String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(200), nullable=False), Column("budget", Float), Column("ros", String(10)))
suppliers = Table("suppliers", md,
    Column("id", String(64), primary_key=True),
    Column("package_id", String(64), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(200), nullable=False),
    Column("tech", String(20), nullable=False), Column("stage", String(20), nullable=False),
    Column("total", Float), Column("incoterm", String(100)), Column("payment", String(100)),
    Column("lead_weeks", Float), Column("due", String(10)), Column("next_action", String(300)),
    Column("reason", Text), Column("updated_at", DateTime(timezone=True)))
history = Table("status_history", md,
    Column("id", Integer, primary_key=True),
    Column("supplier_id", String(64), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
    Column("label", String(60), nullable=False), Column("changed_at", DateTime(timezone=True)))
notes = Table("notes", md,
    Column("id", String(64), primary_key=True),
    Column("package_id", String(64), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False),
    Column("supplier_id", String(64), ForeignKey("suppliers.id", ondelete="CASCADE")),
    Column("body", Text, nullable=False), Column("created_at", DateTime(timezone=True)))
Index("ix_notes_package", notes.c.package_id)
Index("ix_packages_project", packages.c.project_id)
Index("ix_suppliers_package", suppliers.c.package_id)
Index("ix_history_supplier", history.c.supplier_id)
md.create_all(engine)

TECH = ["Pending", "In review", "Clarification", "Compliant", "Non-compliant"]
STAGE = ["Invited", "Submitted", "Awarded", "Declined"]
PROJECT_STATUS = ["Active", "Archived"]
TABLES = {"projects": projects, "packages": packages, "suppliers": suppliers, "notes": notes}

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client: Optional[str] = ""
    status: str = "Active"

class PackageIn(BaseModel):
    projectId: str
    name: str = Field(min_length=1, max_length=200)
    budget: Optional[float] = None
    ros: Optional[str] = ""

class SupplierIn(BaseModel):
    packageId: str
    name: str = Field(min_length=1, max_length=200)
    tech: str = "Pending"
    stage: str = "Invited"
    total: Optional[float] = None
    incoterm: Optional[str] = ""
    payment: Optional[str] = ""
    leadWeeks: Optional[float] = None
    due: Optional[str] = ""
    nextAction: Optional[str] = ""
    reason: Optional[str] = ""

class NoteIn(BaseModel):
    packageId: str
    supplierId: Optional[str] = None
    body: str = Field(min_length=1, max_length=5000)
    createdAt: Optional[str] = None

def now(): return datetime.now(timezone.utc)

def check(value, allowed, label):
    if value not in allowed:
        raise HTTPException(422, f"Unknown {label}: {value}")
    return value

def upsert(c, table, id_, **values):
    if c.execute(update(table).where(table.c.id == id_).values(**values)).rowcount == 0:
        c.execute(insert(table).values(id=id_, **values))

def exists(c, table, id_):
    return c.execute(select(table.c.id).where(table.c.id == id_)).first() is not None

def put_project(c, id_, d: ProjectIn):
    upsert(c, projects, id_, name=d.name.strip(), client=d.client or "",
           status=check(d.status, PROJECT_STATUS, "project status"))

def put_package(c, id_, d: PackageIn):
    if not exists(c, projects, d.projectId): raise HTTPException(422, "Unknown project")
    upsert(c, packages, id_, project_id=d.projectId, name=d.name.strip(), budget=d.budget, ros=d.ros or "")

def put_supplier(c, id_, d: SupplierIn):
    check(d.tech, TECH, "technical status"); check(d.stage, STAGE, "stage")
    if not exists(c, packages, d.packageId): raise HTTPException(422, "Unknown package")
    old = c.execute(select(suppliers.c.tech, suppliers.c.stage).where(suppliers.c.id == id_)).first()
    upsert(c, suppliers, id_, package_id=d.packageId, name=d.name.strip(), tech=d.tech, stage=d.stage,
           total=d.total, incoterm=d.incoterm or "", payment=d.payment or "", lead_weeks=d.leadWeeks,
           due=d.due or "", next_action=d.nextAction or "", reason=d.reason or "", updated_at=now())
    if not old or old.tech != d.tech or old.stage != d.stage:
        c.execute(insert(history).values(supplier_id=id_, label=f"{d.tech} / {d.stage}", changed_at=now()))

def put_note(c, id_, d: NoteIn):
    if not exists(c, packages, d.packageId): raise HTTPException(422, "Unknown package")
    if d.supplierId:
        row = c.execute(select(suppliers.c.package_id).where(suppliers.c.id == d.supplierId)).first()
        if not row or row.package_id != d.packageId: raise HTTPException(422, "Supplier is not in this package")
    body = d.body.strip()
    if not body: raise HTTPException(422, "Note is empty")
    if c.execute(update(notes).where(notes.c.id == id_).values(body=body)).rowcount == 0:   # edits keep the original date
        when = now()
        if d.createdAt:
            when = datetime.fromisoformat(d.createdAt.replace("Z", "+00:00"))
            if when.tzinfo is None: when = when.replace(tzinfo=timezone.utc)
        c.execute(insert(notes).values(id=id_, package_id=d.packageId, supplier_id=d.supplierId or None,
                                       body=body, created_at=when))

def snapshot(c):
    hist = {}
    for h in c.execute(select(history).order_by(history.c.changed_at, history.c.id)):
        hist.setdefault(h.supplier_id, []).append({"t": h.changed_at.date().isoformat(), "s": h.label})
    return {
        "projects": [dict(id=r.id, name=r.name, client=r.client or "", status=r.status)
                     for r in c.execute(select(projects).order_by(projects.c.name))],
        "packages": [dict(id=r.id, projectId=r.project_id, name=r.name, budget=r.budget, ros=r.ros or "")
                     for r in c.execute(select(packages).order_by(packages.c.name))],
        "suppliers": [dict(id=r.id, packageId=r.package_id, name=r.name, tech=r.tech, stage=r.stage,
                           total=r.total, incoterm=r.incoterm or "", payment=r.payment or "",
                           leadWeeks=r.lead_weeks, due=r.due or "", nextAction=r.next_action or "",
                           reason=r.reason or "", history=hist.get(r.id, []))
                      for r in c.execute(select(suppliers).order_by(suppliers.c.name))],
        "notes": [dict(id=r.id, packageId=r.package_id, supplierId=r.supplier_id, body=r.body,
                       createdAt=r.created_at.isoformat() if r.created_at else "")
                  for r in c.execute(select(notes).order_by(notes.c.created_at, notes.c.id))],
    }

security = HTTPBasic(auto_error=False)
def auth(creds: Optional[HTTPBasicCredentials] = Depends(security)):
    """HTTP Basic auth, enabled when APP_USER and APP_PASSWORD are set."""
    user, pwd = os.getenv("APP_USER"), os.getenv("APP_PASSWORD")
    if not (user and pwd): return
    ok = creds and secrets.compare_digest(creds.username, user) and secrets.compare_digest(creds.password, pwd)
    if not ok: raise HTTPException(401, "Login required", headers={"WWW-Authenticate": "Basic"})

app = FastAPI(title="Procurement Tracker", dependencies=[Depends(auth)])

@app.get("/api/all")
def get_all():
    with engine.connect() as c:
        return snapshot(c)

@app.put("/api/projects/{id_}")
def api_put_project(id_: str, d: ProjectIn):
    with engine.begin() as c: put_project(c, id_, d)
    return {"ok": True}

@app.put("/api/packages/{id_}")
def api_put_package(id_: str, d: PackageIn):
    with engine.begin() as c: put_package(c, id_, d)
    return {"ok": True}

@app.put("/api/suppliers/{id_}")
def api_put_supplier(id_: str, d: SupplierIn):
    with engine.begin() as c: put_supplier(c, id_, d)
    return {"ok": True}

@app.put("/api/notes/{id_}")
def api_put_note(id_: str, d: NoteIn):
    with engine.begin() as c: put_note(c, id_, d)
    return {"ok": True}

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def xlsx_response(wb, filename):
    return Response(to_bytes(wb), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@app.get("/api/export/package/{pid}.xlsx")
def export_package(pid: str):
    with engine.connect() as c: snap = snapshot(c)
    if not any(k["id"] == pid for k in snap["packages"]): raise HTTPException(404, "Package not found")
    return xlsx_response(*package_workbook(snap, pid))

@app.get("/api/export/project/{pid}.xlsx")
def export_project(pid: str):
    with engine.connect() as c: snap = snapshot(c)
    if not any(p["id"] == pid for p in snap["projects"]): raise HTTPException(404, "Project not found")
    return xlsx_response(*project_workbook(snap, pid))

@app.delete("/api/{coll}/{id_}")
def api_delete(coll: str, id_: str):
    table = TABLES.get(coll)
    if table is None: raise HTTPException(404, "Unknown collection")
    with engine.begin() as c:                     # idempotent; children are removed by ON DELETE CASCADE
        c.execute(delete(table).where(table.c.id == id_))
    return {"ok": True}

@app.get("/api/backup")
def backup():
    with engine.connect() as c:
        data = snapshot(c)
    data = {"app": "procurement-tracker", "version": 1, "exported": now().isoformat(), **data}
    return Response(json.dumps(data, indent=1), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="procurement-backup-{date.today()}.json"'})

class Backup(BaseModel):
    projects: list[dict] = []
    packages: list[dict] = []
    suppliers: list[dict] = []
    notes: list[dict] = []

@app.post("/api/restore")
def restore(b: Backup):
    """Merge a backup file: records with the same id are overwritten, others are kept."""
    try:
        with engine.begin() as c:
            for r in b.projects: put_project(c, str(r["id"]), ProjectIn(**r))
            for r in b.packages: put_package(c, str(r["id"]), PackageIn(**r))
            for r in b.suppliers:
                sid = str(r["id"]); put_supplier(c, sid, SupplierIn(**r))
                if r.get("history"):
                    c.execute(delete(history).where(history.c.supplier_id == sid))
                    for h in r["history"]:
                        when = datetime.fromisoformat(h["t"]).replace(tzinfo=timezone.utc)
                        c.execute(insert(history).values(supplier_id=sid, label=h["s"], changed_at=when))
            for r in b.notes: put_note(c, str(r["id"]), NoteIn(**r))
    except (KeyError, ValueError, ValidationError) as e:
        raise HTTPException(422, f"Invalid backup file: {e}")
    return {"ok": True, "projects": len(b.projects), "packages": len(b.packages), "suppliers": len(b.suppliers), "notes": len(b.notes)}

# Front end lives in public/. Vercel serves public/ from its CDN; locally FastAPI serves it here.
PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
if os.path.isdir(PUBLIC):
    app.mount("/", StaticFiles(directory=PUBLIC, html=True), name="public")

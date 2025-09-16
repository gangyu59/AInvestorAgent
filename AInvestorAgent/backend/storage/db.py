# backend/storage/db.py
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
from ..core.config import get_settings

Base = declarative_base()

def _default_sqlite_url() -> str:
    # 计算项目根目录：backend/storage/db.py → 项目根 = parents[2]
    root = Path(__file__).resolve().parents[2]
    db_dir = root / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(db_dir / 'AInvestorAgent.sqlite').as_posix()}"

def get_engine():
    settings = get_settings()
    db_url = settings.DB_URL or _default_sqlite_url()
    return create_engine(db_url, echo=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import uuid
def save_trace(scene: str, req: dict, result: dict) -> str:
    trace_id = uuid.uuid4().hex
    rec = models.TraceRecord(
        trace_id=trace_id, scene=scene,
        req_json=req, context=result.get("context"), trace=result.get("trace"))
    with session_scope() as s:
        s.add(rec); s.commit()
    return trace_id


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

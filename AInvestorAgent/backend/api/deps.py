# backend/api/deps.py
from typing import Generator
from backend.storage.db import SessionLocal

def get_db() -> Generator:
    """FastAPI 依赖注入：提供 SQLAlchemy Session，并在请求后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

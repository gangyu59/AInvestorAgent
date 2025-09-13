# -*- coding: utf-8 -*-
import os
import sys
import json
import types
import datetime as dt
import pytest

# 确保包可导入：项目根目录应包含 AInvestorAgent/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.basename(ROOT) != "AInvestorAgent":
    ROOT = os.path.join(ROOT, "AInvestorAgent")
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

# 尝试导入你的 app 与依赖
from backend.app import app  # 假设你入口在 backend/app.py
from backend.api.deps import get_db
from backend.storage.db import SessionLocal, engine, Base  # 你在 storage/models.py 里定义 Base/Models
from backend.storage import models

try:
    from backend.api.routers import metrics, fundamentals, qa
    app.include_router(metrics.router)
    app.include_router(fundamentals.router)
    app.include_router(qa.router)
except Exception as e:
    print("[tests] router include failed (ignored):", e)

@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    """
    使用临时 SQLite（文件 or 内存均可）。
    这里使用文件，方便你调试查看；测试结束不清理以便复盘（需要时可切换为内存）。
    """
    os.makedirs(os.path.join(ROOT, "db"), exist_ok=True)
    # 若你在 config.py 里固定了 DB 路径，这里以你的实际配置为准。
    # 假设 SessionLocal/engine 已指向本地 SQLite。
    Base.metadata.create_all(bind=engine)
    yield
    # 可选：如需每次清空测试库，可在此 drop_all

@pytest.fixture(scope="function")
def db_session():
    """每个用例独立的事务，会在测试末回滚。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    """
    用依赖覆盖把 get_db 指到我们的 session。
    """
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()

# ====== 常用测试工具：生成价格数据 ======
def _daterange(n_days: int, end: dt.date | None = None):
    end = end or dt.date.today()
    for i in range(n_days):
        yield end - dt.timedelta(days=(n_days - 1 - i))

@pytest.fixture(scope="function")
def seed_prices(db_session):
    from backend.storage import models
    import datetime as dt

    # 清理旧数据，避免 UNIQUE(symbol,date) 冲突
    db_session.query(models.PriceDaily).filter(models.PriceDaily.symbol == "AAPL").delete()
    db_session.commit()

    rows = []
    start_price = 100.0
    end = dt.date.today()
    for i in range(300):
        d = end - dt.timedelta(days=(299 - i))
        close = start_price * (1.0 + 0.0008 * i)
        rows.append(models.PriceDaily(
            symbol="AAPL",
            date=d,
            open=close * 0.995,
            high=close * 1.01,
            low=close * 0.99,
            close=close,
            volume=1_000_000 + 1000 * i,
        ))
    db_session.add_all(rows)
    db_session.commit()
    return True



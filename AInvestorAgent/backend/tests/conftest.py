# backend/tests/conftest.py
import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app import app as fastapi_app  # ✅ 避免与 fixture app() 同名

DB_PATH = "db/stock.sqlite"

@pytest.fixture(scope="session", autouse=True)
def _env():
    os.makedirs("db", exist_ok=True)
    os.environ.setdefault("AIA_OFFLINE", "1")  # 单测默认离线

@pytest.fixture(scope="session")
def client():
    """大多数用例用这个（ASGI 原生 TestClient）。"""
    return TestClient(fastapi_app)

@pytest.fixture(scope="session")
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS symbols(symbol TEXT PRIMARY KEY, name TEXT);
    CREATE TABLE IF NOT EXISTS prices_daily(symbol TEXT, date TEXT, close REAL,
      PRIMARY KEY(symbol,date));
    CREATE TABLE IF NOT EXISTS fundamentals(
      symbol TEXT PRIMARY KEY, pe REAL, pb REAL, roe REAL, net_margin REAL,
      market_cap INTEGER, sector TEXT, industry TEXT, as_of TEXT
    );
    CREATE TABLE IF NOT EXISTS news_raw(
      id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, title TEXT, summary TEXT,
      url TEXT, source TEXT, published_at TEXT
    );
    CREATE TABLE IF NOT EXISTS news_scores(
      id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, title TEXT, score REAL,
      published_at TEXT
    );
    """)
    yield conn
    conn.close()

@pytest.fixture
def default_candidates():
    return [
        {"symbol":"AAPL","sector":"Technology","score":86},
        {"symbol":"MSFT","sector":"Technology","score":88},
        {"symbol":"NVDA","sector":"Technology","score":92},
        {"symbol":"AMZN","sector":"Consumer Discretionary","score":79},
        {"symbol":"META","sector":"Communication Services","score":83},
        {"symbol":"JPM","sector":"Financials","score":68},
        {"symbol":"XOM","sector":"Energy","score":65},
    ]

@pytest.fixture
def seed_prices(db_conn):
    rows = [
        ("AAPL","2024-01-02",190.0),("AAPL","2024-01-03",191.0),("AAPL","2024-01-04",192.0),
        ("SPY","2024-01-02",470.0), ("SPY","2024-01-03",471.0), ("SPY","2024-01-04",472.0),
    ]
    for r in rows:
        db_conn.execute(
            "INSERT OR REPLACE INTO prices_daily(symbol,date,close) VALUES(?,?,?)", r
        )
    db_conn.commit()
    yield

@pytest.fixture(scope="session")
def app():
    """
    仅给仍使用 httpx.Client(app=app, ...) 的旧式用例。
    返回 WSGI-callable（用 asgiref 把 FastAPI(ASGI) 包装成 WSGI）。
    """
    try:
        from asgiref.wsgi import AsgiToWsgi
    except ModuleNotFoundError as e:
        # 你确实可以把测试改成 ASGITransport，但为了不改测试，这里强制要求 asgiref
        raise RuntimeError(
            "需要安装 asgiref 才能把 FastAPI(ASGI) 包成 WSGI 给 httpx.Client(app=...). "
            "请执行: pip install asgiref>=3.6"
        ) from e
    return AsgiToWsgi(fastapi_app)

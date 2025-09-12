# backend/tests/test_api.py
from fastapi.testclient import TestClient
from backend.app import app  # 以你的入口为准

client = TestClient(app)

def test_fundamentals():
    r = client.get("/fundamentals/AAPL")
    assert r.status_code in (200, 429, 400, 404)  # AV 限流或无数据时允许非200
    if r.status_code == 200:
        j = r.json()
        for k in ["symbol","pe","pb","roe","net_margin","market_cap","sector","industry","as_of"]:
            assert k in j

def test_metrics():
    r = client.get("/metrics/AAPL")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        j = r.json()
        for k in ["one_month_change","three_months_change","twelve_months_change","volatility","as_of"]:
            assert k in j

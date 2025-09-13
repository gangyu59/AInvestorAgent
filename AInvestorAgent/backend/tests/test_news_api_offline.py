from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from backend.app import app

client = TestClient(app)

def test_news_idempotent(monkeypatch):
    from backend.ingestion import news_api_client

    base = datetime.now(timezone.utc)
    fake = [
        {"title":"AAPL beats estimates","summary":"strong growth","url":"http://x/1","source":"Mock","published_at":(base-timedelta(days=1)).isoformat()},
        {"title":"AAPL faces lawsuit","summary":"risk noted","url":"http://x/2","source":"Mock","published_at":(base-timedelta(days=2)).isoformat()},
    ]
    monkeypatch.setattr(news_api_client, "fetch_news", lambda symbol, days=7, limit=50: fake)

    r1 = client.post("/api/news/fetch", params={"symbol":"AAPL","days":7})
    assert r1.status_code == 200
    r2 = client.post("/api/news/fetch", params={"symbol":"AAPL","days":7})
    assert r2.status_code == 200

    # 查询时间轴应≥2天，且不会越拉越“重复”
    rs = client.get("/api/news/series", params={"symbol":"AAPL","days":7})
    assert rs.status_code == 200
    data = rs.json()
    assert data["symbol"] == "AAPL"
    assert len(data["timeline"]) >= 2

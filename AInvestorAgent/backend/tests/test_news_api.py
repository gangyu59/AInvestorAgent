from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from backend.app import app

client = TestClient(app)

def test_news_fetch_and_series(monkeypatch):
    # 伪造外部新闻返回
    from backend.ingestion import news_client
    def fake_fetch_news(symbol: str, days: int = 7, limit: int = 50):
        base = datetime.now(timezone.utc)
        return [
            {"title":"AAPL beats estimates","summary":"strong growth","url":"http://x/1","source":"Mock","published_at":(base-timedelta(days=1)).isoformat()},
            {"title":"AAPL faces lawsuit","summary":"risk noted","url":"http://x/2","source":"Mock","published_at":(base-timedelta(days=2)).isoformat()},
            {"title":"AAPL launches record product","summary":"upgrade","url":"http://x/3","source":"Mock","published_at":(base-timedelta(days=2)).isoformat()},
        ]
    monkeypatch.setattr(news_client, "fetch_news", fake_fetch_news)

    r = client.post("/api/news/fetch", params={"symbol":"AAPL","days":7})
    assert r.status_code == 200
    r2 = client.get("/api/news/series", params={"symbol":"AAPL","days":7})
    assert r2.status_code == 200
    data = r2.json()
    assert data["symbol"] == "AAPL"
    assert len(data["timeline"]) >= 2
    # 情绪统计字段存在
    t0 = data["timeline"][0]
    for k in ["date","sentiment","count_pos","count_neg","count_neu"]:
        assert k in t0

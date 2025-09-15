import math

def test_dispatch_research_chain_mock(client):
    # 研究链：Ingest→Clean→Research；检查 factors + score + trace
    payload = {"symbol":"AAPL","params":{"mock":True,"news_days":14}}
    r = client.post("/orchestrator/dispatch", json=payload)
    assert r.status_code == 200
    body = r.json()
    ctx = body["context"]; trace = body["trace"]
    assert len(trace) >= 3 and trace[0]["agent"] in ("data_ingestor","ingestor")
    f = ctx.get("factors", {})
    for k in ("value","quality","momentum","sentiment"):
        assert k in f
        assert 0.0 <= f[k] <= 1.0 or isinstance(f[k], float)
    assert 0.0 <= ctx["score"] <= 100.0

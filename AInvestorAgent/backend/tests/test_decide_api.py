import httpx, json
def test_decide_api_smoke(app):
    with httpx.Client(app=app, base_url="http://test") as c:
        r = c.post("/orchestrator/decide", json={"topk":10, "min_score":50, "params":{"risk.max_stock":0.3}})
        j = r.json()
        assert j["ok"] is True
        ctx = j["context"]; assert "kept" in ctx and "orders" in ctx
        assert isinstance(ctx["orders"], list)

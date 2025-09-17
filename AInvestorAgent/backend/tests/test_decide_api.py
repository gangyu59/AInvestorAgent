def test_decide_api_smoke(client):
    r = client.post(
        "/orchestrator/decide",
        json={"topk": 10, "min_score": 50, "params": {"risk.max_stock": 0.3}},
    )
    assert r.status_code == 200, r.text
    j = r.json()

    # 兼容不同的返回格式：ok / success / 仅有 context
    ok = j.get("ok", j.get("success", True if "context" in j else None))
    assert ok is True, f"Unexpected response shape: {j}"

    # 兼容 context 在顶层或直接把上下文放在顶层
    ctx = j.get("context", j)
    assert "kept" in ctx and "orders" in ctx, f"Missing keys in context: {ctx}"
    assert isinstance(ctx["orders"], list)

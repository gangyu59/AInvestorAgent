def test_propose_with_risk_constraints(client, default_candidates):
    # 组合建议 + 风控约束（单票≤30%、行业≤50%、持仓数5–15）
    r = client.post("/orchestrator/propose", json={
        "candidates": default_candidates,
        "params": {"risk.max_stock":0.30,"risk.max_sector":0.50,"risk.count_range":[5,15]}
    })
    assert r.status_code == 200
    ctx = r.json()["context"]
    kept = ctx["kept"]; sector = ctx["concentration"]["sector_dist"]; actions = ctx["actions"]
    assert 5 <= len(kept) <= 15
    assert abs(sum(p["weight"] for p in kept) - 1.0) < 1e-6
    assert max(p["weight"] for p in kept) <= 0.30 + 1e-8
    assert max(sector.values()) <= 0.50 + 1e-8
    # 检查存在风控动作日志（可能为空，允许）
    assert isinstance(actions, list)

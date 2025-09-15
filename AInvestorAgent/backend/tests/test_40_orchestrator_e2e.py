def test_propose_and_backtest_e2e(client, default_candidates):
    # 一键链路：Propose → Risk → Backtest → 可视化字段齐全 & trace包含3个agent
    r = client.post("/orchestrator/propose_backtest", json={
        "candidates": default_candidates,
        "params": {"risk.max_stock":0.30,"risk.max_sector":0.50,"risk.count_range":[5,15],"window_days":180,"mock":True}
    })
    assert r.status_code == 200
    body = r.json(); ctx = body["context"]; trace = body["trace"]
    agents = [t["agent"] for t in trace]
    # 应包含 portfolio_manager / risk_manager / backtest_engineer
    assert "portfolio_manager" in agents and "risk_manager" in agents and "backtest_engineer" in agents
    # 可视化字段
    assert "kept" in ctx and "concentration" in ctx
    assert "dates" in ctx and "nav" in ctx and "drawdown" in ctx and "benchmark_nav" in ctx and "metrics" in ctx

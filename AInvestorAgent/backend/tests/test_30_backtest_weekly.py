def test_backtest_weekly_nav_and_metrics(client):
    # 回测：周频再平衡、含交易成本、输出净值/回撤/指标/基准
    payload = {
        "weights":[
            {"symbol":"AAPL","weight":0.25},
            {"symbol":"MSFT","weight":0.25},
            {"symbol":"NVDA","weight":0.25},
            {"symbol":"AMZN","weight":0.25}
        ],
        "window_days":180, "trading_cost":0.001, "benchmark_symbol":"SPY", "mock": True
    }
    r = client.post("/backtest/run", json=payload)
    assert r.status_code == 200
    data = r.json()["data"]
    for k in ("dates","nav","drawdown","benchmark_nav","metrics"):
        assert k in data
    m = data["metrics"]
    for k in ("annualized_return","max_drawdown","sharpe","win_rate","turnover"):
        assert k in m
    # 指标必须是数值且非NaN
    assert m["win_rate"] >= 0.0 and m["win_rate"] <= 1.0

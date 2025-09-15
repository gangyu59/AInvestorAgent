def test_dispatch_no_news_still_scores(client):
    # 无新闻/情绪为空时，系统应平稳返回，占位或默认值
    payload = {"symbol":"NEE","params":{"mock":True,"news_days":0}}
    r = client.post("/orchestrator/dispatch", json=payload)
    assert r.status_code == 200
    f = r.json()["context"]["factors"]
    assert "sentiment" in f  # 允许为0.5或0.0等占位，但不能缺失

def test_backtest_short_window(client):
    # 极短窗口：至少返回一个点的净值，不报错
    payload = {
        "weights":[{"symbol":"AAPL","weight":1.0}],
        "window_days": 10, "mock": True
    }
    r = client.post("/backtest/run", json=payload)
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["dates"]) >= 1 and len(data["nav"]) >= 1

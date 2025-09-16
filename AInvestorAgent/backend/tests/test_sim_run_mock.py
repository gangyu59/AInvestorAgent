def test_sim_run_mock(client):
    days = [
        {"orders":[{"symbol":"AAPL","side":"BUY","weight_delta":0.5}], "rel_returns":{"AAPL":0.01}},
        {"orders":[{"symbol":"AAPL","side":"BUY","weight_delta":0.5}], "rel_returns":{"AAPL":0.02}},
        {"orders":[ ], "rel_returns":{"AAPL":-0.01}},
    ]
    r = client.post("/sim/run", json={"days": days})
    j = r.json()
    assert j["ok"] is True
    nav = j["data"]["nav"]; assert len(nav)==3 and nav[-1]>0.0

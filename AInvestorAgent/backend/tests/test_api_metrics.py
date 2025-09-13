# -*- coding: utf-8 -*-
def test_metrics_ok(client, seed_prices):
    r = client.get("/metrics/AAPL")
    assert r.status_code == 200, r.text
    j = r.json()
    assert set(j.keys()) == {
        "symbol","one_month_change","three_months_change","twelve_months_change","volatility","as_of"
    }
    # 粗检范围
    assert -50 <= j["one_month_change"] <= 200
    assert j["symbol"] == "AAPL"

def test_metrics_404_when_no_data(client):
    r = client.get("/metrics/ZZZZ")
    assert r.status_code == 404

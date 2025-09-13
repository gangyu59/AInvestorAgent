# -*- coding: utf-8 -*-
import json
from backend.tests.utils.mocks import alpha_vantage_overview_resp

def test_fundamentals_ok_mock(client, monkeypatch):
    import backend.api.routers.fundamentals as fundamentals

    def fake_get(url, params):
        class R:
            def json(self_inner): return alpha_vantage_overview_resp(params["symbol"])
            @property
            def ok(self_inner): return True
        return R()

    monkeypatch.setattr(fundamentals.requests, "get", fake_get)

    r = client.get("/fundamentals/AAPL")
    assert r.status_code in (200, 201)
    j = r.json()
    for k in ["symbol","pe","pb","roe","net_margin","market_cap","sector","industry","as_of"]:
        assert k in j

def test_fundamentals_error_from_api(client, monkeypatch):
    import backend.api.routers.fundamentals as fundamentals

    def fake_get(url, params):
        class R:
            def json(self_inner): return {"Error Message": "Limit"}
            @property
            def ok(self_inner): return False
        return R()

    monkeypatch.setattr(fundamentals.requests, "get", fake_get)
    r = client.get("/fundamentals/AAPL")
    assert r.status_code in (400, 429)

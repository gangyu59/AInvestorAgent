from backend.orchestrator.pipeline import run_portfolio_pipeline

def test_pm_rm_pipeline_basic():
    cands = [
        {"symbol":"AAPL","sector":"Technology","score":90},
        {"symbol":"MSFT","sector":"Technology","score":85},
        {"symbol":"AMZN","sector":"Consumer Discretionary","score":75},
        {"symbol":"JPM","sector":"Financials","score":65},
        {"symbol":"XOM","sector":"Energy","score":60},
        {"symbol":"NEE","sector":"Utilities","score":55},
    ]
    res = run_portfolio_pipeline(cands, {"risk.max_stock":0.3, "risk.max_sector":0.5, "risk.count_range":[5,15]})
    ctx = res["context"]
    assert "kept" in ctx and 5 <= len(ctx["kept"]) <= 15
    assert abs(sum(p["weight"] for p in ctx["kept"]) - 1.0) < 1e-6

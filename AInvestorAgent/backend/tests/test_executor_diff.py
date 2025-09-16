def test_executor_plan_orders_basic():
    from backend.agents.executor import ExecutorAgent
    ex = ExecutorAgent()
    cur = {"AAPL":0.2,"MSFT":0.3}
    tgt = {"AAPL":0.3,"NVDA":0.2}
    orders = ex.plan_orders(cur, tgt)
    m = { (o["symbol"], o["side"]): o for o in orders }
    assert m[("AAPL","BUY")]["weight_delta"] == 0.1
    assert m[("MSFT","SELL")]["weight_delta"] == -0.3
    assert m[("NVDA","BUY")]["weight_delta"] == 0.2

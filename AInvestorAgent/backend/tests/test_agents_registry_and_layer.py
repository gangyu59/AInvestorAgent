import importlib

def test_registry_order_and_min_layer_outputs():
    reg = importlib.import_module("backend.agents.registry")
    # 你的文件名是 agent_layer.py（不是 base_layer.py）
    agent_layer = importlib.import_module("backend.agents.agent_layer")
    ba = importlib.import_module("backend.agents.base_agent")

    assert hasattr(reg, "REGISTRY") and hasattr(reg, "ORDER")
    order = reg.ORDER
    assert order == ["news","macro","earnings","technical","value","quant","macro_strategy","chair","execution"]

    ctx = ba.ResearchContext(symbol="AAPL")
    out = agent_layer.run_agent_layer(ctx, params={"mock": True})

    for k in ("value","quality","momentum","sentiment"):
        assert k in out.factors, f"missing factor: {k}"

    agents = [t.get("agent") for t in out.trace]
    for name in ["News/Sentiment","Macro","Earnings","Technical","Value","Quant","Macro Strategy","Chair","Execution"]:
        assert name in agents

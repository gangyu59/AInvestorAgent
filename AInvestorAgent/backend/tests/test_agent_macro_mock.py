import importlib

def test_macro_agent_mock_snapshot():
    ba = importlib.import_module("backend.agents.base_agent")
    macro = importlib.import_module("backend.agents.macro")

    agent = macro.MacroAgent()
    ctx = ba.ResearchContext(symbol="NVDA")
    out = agent.run(ctx, mock=True)

    assert "macro" in out.factors
    assert 0.0 <= out.factors["macro"] <= 1.0
    snap = out.signals.get("macro", {})
    assert isinstance(snap, dict)
    for k in ("cpi_yoy","gdp_yoy","policy_rate"):
        assert k in snap

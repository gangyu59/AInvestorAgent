# -*- coding: utf-8 -*-
import json
from backend.agents import SignalResearcher, PortfolioManager, RiskManager
from backend.agents.base_agent import AgentContext

def test_min_pipeline_ok():
    ctx = AgentContext()
    factors = SignalResearcher(ctx).act(symbol="AAPL")["factors"]
    scores = {
        "AAPL": {"score": 80, **factors},
        "MSFT": {"score": 75, **factors},
        "TSLA": {"score": 60, **factors},
    }
    pm = PortfolioManager(ctx).act(scores=scores, max_positions=2)
    assert pm["ok"] is True
    assert len(pm["weights"]) == 2

    rm = RiskManager(ctx).act(weights=pm["weights"], max_weight=0.3, max_sector=0.5)
    assert rm["ok"] is True
    assert abs(sum(rm["weights"].values()) - 1.0) < 1e-6

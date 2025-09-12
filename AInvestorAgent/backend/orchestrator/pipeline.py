# -*- coding: utf-8 -*-
from typing import Dict, Any
from backend.agents import (
    DataIngestor, DataCleaner, SignalResearcher,
    PortfolioManager, RiskManager, BacktestEngineer,
)
from backend.agents.base_agent import AgentContext

def analyze_one(symbol: str, ctx: AgentContext) -> Dict[str, Any]:
    factors = SignalResearcher(ctx).act(symbol=symbol)["factors"]
    return {"symbol": symbol, "factors": factors}

def propose_portfolio(scores: Dict[str, Dict[str, float]], ctx: AgentContext) -> Dict[str, Any]:
    pm = PortfolioManager(ctx).act(scores=scores)
    rm = RiskManager(ctx).act(weights=pm["weights"])
    return {"weights": rm["weights"], "explain": pm["explain"]}

# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List

from backend.agents.data_ingestor import DataIngestor
from backend.agents.data_cleaner import DataCleaner
from backend.agents.signal_researcher import SignalResearcher
from backend.agents.portfolio_manager import PortfolioManager
from backend.agents.risk_manager import RiskManager
from backend.agents.backtest_engineer import BacktestEngineer

STEPS = [DataIngestor(), DataCleaner(), SignalResearcher()]

def run_pipeline(symbol: str, extras: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Ingest -> Clean -> Research
    返回：{"symbol", "context", "trace"}
    """
    ctx: Dict[str, Any] = {"symbol": symbol}
    if extras: ctx.update(extras)
    trace: List[Dict[str, Any]] = []
    for agent in STEPS:
        res = agent.run(ctx)
        trace.append({"agent": agent.name, **res})
        if not res.get("ok"):
            break
        ctx.update(res.get("data", {}))
    return {"symbol": symbol, "context": ctx, "trace": trace}

def run_portfolio_pipeline(candidates: List[Dict[str, Any]], extras: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    candidates -> PortfolioManager -> RiskManager
    """
    ctx: Dict[str, Any] = {"candidates": candidates}
    if extras: ctx.update(extras)
    trace: List[Dict[str, Any]] = []

    pm = PortfolioManager()
    r1 = pm.run(ctx); trace.append({"agent": pm.name, **r1})
    if not r1.get("ok"): return {"context": ctx, "trace": trace}
    ctx.update(r1.get("data", {}))

    rk = RiskManager()
    r2 = rk.run(ctx); trace.append({"agent": rk.name, **r2})
    if r2.get("ok"):
        ctx.update(r2.get("data", {}))
    return {"context": ctx, "trace": trace}

def run_propose_and_backtest(candidates: List[Dict[str, Any]], extras: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    candidates -> PM -> Risk -> Backtest
    """
    ctx: Dict[str, Any] = {"candidates": candidates}
    if extras: ctx.update(extras)
    trace: List[Dict[str, Any]] = []

    pm = PortfolioManager()
    r1 = pm.run(ctx); trace.append({"agent": pm.name, **r1})
    if not r1.get("ok"): return {"context": ctx, "trace": trace}
    ctx.update(r1.get("data", {}))

    rk = RiskManager()
    r2 = rk.run(ctx); trace.append({"agent": rk.name, **r2})
    if not r2.get("ok"): return {"context": ctx, "trace": trace}
    ctx.update(r2.get("data", {}))

    bk = BacktestEngineer()
    r3 = bk.run(ctx); trace.append({"agent": bk.name, **r3})
    if r3.get("ok"):
        ctx.update(r3.get("data", {}))
    return {"context": ctx, "trace": trace}

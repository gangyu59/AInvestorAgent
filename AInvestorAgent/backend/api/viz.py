# backend/api/viz.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from backend.storage import db, models
from backend.agents.backtest_engineer import BacktestEngineer
from backend.agents.portfolio_manager import PortfolioManager

router = APIRouter(prefix="/viz", tags=["viz"])

@router.get("/weights")
def weights(portfolio_id: int | None = None) -> Dict[str, Any]:
    """组合权重饼图数据：返回 kept 列表"""
    with db.session_scope() as s:
        if portfolio_id is None:
            snap = s.query(models.PortfolioSnapshot).order_by(models.PortfolioSnapshot.snapshot_id.desc()).first()
        else:
            snap = s.query(models.PortfolioSnapshot).get(portfolio_id)
        if not snap:
            raise HTTPException(404, "no portfolio snapshot")
        return {"kept": (snap.holdings or [])}

@router.get("/radar")
def radar(symbol: str, mock: bool = True) -> Dict[str, Any]:
    """因子雷达：value/quality/momentum/sentiment"""
    if mock:
        # 直接复用 orchestrator 中的确定性生成逻辑
        base = sum(ord(c) for c in symbol) % 100
        def norm(v: int) -> float: return max(0.0, min(1.0, (v % 100) / 100.0))
        return {"symbol": symbol.upper(), "factors": {
            "value": norm(base + 13), "quality": norm(base + 37),
            "momentum": norm(base + 59), "sentiment": norm(base + 71),
        }}
    # TODO: 非 mock 时：可从 factors_daily/scores_daily 查询最近一日
    raise HTTPException(501, "non-mock not implemented")

@router.get("/backtest")
def backtest(portfolio_id: int | None = None, window_days: int = 180, benchmark: str = "SPY"):
    """回测曲线（dates/nav/benchmark_nav/drawdown/metrics）"""
    with db.session_scope() as s:
        if portfolio_id is None:
            snap = s.query(models.PortfolioSnapshot).order_by(models.PortfolioSnapshot.snapshot_id.desc()).first()
        else:
            snap = s.query(models.PortfolioSnapshot).get(portfolio_id)
        if not snap: raise HTTPException(404, "no portfolio snapshot")
    kept = snap.holdings or []

    be = BacktestEngineer()
    be_out = be.run({"kept": kept, "window_days": window_days, "mock": True, "benchmark_symbol": benchmark})
    if not be_out.get("ok"): raise HTTPException(500, "backtest failed")
    d = be_out["data"]
    return {"dates": d.get("dates", []), "nav": d.get("nav", []),
            "benchmark_nav": d.get("benchmark_nav", []), "drawdown": d.get("drawdown", []),
            "metrics": d.get("metrics", {})}

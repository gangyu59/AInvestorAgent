from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/backtest", tags=["backtest"])

# 强韧导入：先按标准包名，再退回相对，再退回顶层文件
try:
    from backend.agents.backtest_engineer import BacktestEngineer
except Exception:
    try:
        from backend.agents.backtest_engineer import BacktestEngineer  # 若代码在 backend/ 旁边
    except Exception:
        from backtest_engineer import BacktestEngineer  # 若你把 .py 直接放在项目根


class WeightItem(BaseModel):
    symbol: str
    weight: float

class RunBacktestReq(BaseModel):
    kept: Optional[List[Dict[str, Any]]] = None   # RiskManager 输出
    weights: Optional[List[WeightItem]] = None    # 直接提供权重
    start: Optional[str] = None                   # YYYY-MM-DD
    end: Optional[str] = None
    window_days: Optional[int] = 120
    trading_cost: Optional[float] = 0.001
    benchmark_symbol: Optional[str] = "SPY"
    mock: Optional[bool] = False

@router.post("/run")
def run_backtest(req: RunBacktestReq):
    try:
        agent = BacktestEngineer()
        data = {
            "kept": req.kept,
            "weights": [w.model_dump(exclude_none=False) for w in req.weights] if req.weights else None,
            "start": req.start, "end": req.end,
            "window_days": req.window_days,
            "trading_cost": req.trading_cost,
            "benchmark_symbol": req.benchmark_symbol,
            "mock": req.mock,
        }
        res = agent.run(data)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error", "backtest failed"))

        # -------- 统一输出结构（最小侵入式补齐）--------
        dates = res.get("dates") or res.get("timeline") or []
        nav = res.get("nav") or res.get("portfolio_nav") or []
        benchmark_nav = res.get("benchmark_nav") or res.get("bench") or []

        # 计算回撤与指标（若引擎已给同名字段，将以引擎结果为准，否则补齐）
        from ...backtest.metrics import compute_drawdown, compute_metrics
        drawdown = res.get("drawdown") or compute_drawdown(nav)
        metrics = res.get("metrics") or compute_metrics(nav, dates)

        payload = {
            "dates": dates,
            "nav": nav,
            "benchmark_nav": benchmark_nav,
            "drawdown": drawdown,
            "metrics": {
                "ann_return": float(metrics.get("ann_return", 0.0)),
                "sharpe": float(metrics.get("sharpe", 0.0)),
                "max_dd": float(metrics.get("max_dd", metrics.get("mdd", 0.0))),  # 兼容 mdd
                "win_rate": float(metrics.get("win_rate", 0.0)),
            },
            "params": {
                "window": f"{res.get('window_days') or 252}D",
                "cost": res.get("trading_cost", 0.001),
                "rebalance": res.get("rebalance", "W"),
                "max_trades_per_week": res.get("max_trades_per_week", 3),
            },
            "version_tag": res.get("version_tag", "bt_v1.0.0"),
        }

        return {"success": True, **payload}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

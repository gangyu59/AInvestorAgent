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
            raise HTTPException(status_code=400, detail=res.get("error","backtest failed"))
        return {"success": True, **res}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

router = APIRouter(tags=["metrics"])
logger = logging.getLogger(__name__)

# 依赖与模型：尽量弱依赖，避免你现有项目导入冲突
try:
    from backend.api.deps import get_db  # type: ignore
    from backend.storage.models import PriceDaily  # type: ignore
    from sqlalchemy.orm import Session  # type: ignore
except Exception:  # 允许在空项目里通过
    Session = object  # type: ignore
    def get_db():  # type: ignore
        raise RuntimeError("get_db not wired")
    class PriceDaily:  # type: ignore
        symbol: str; date: date; close: float

class MetricsResp(BaseModel):
    symbol: str
    one_month_change: float
    three_months_change: float
    twelve_months_change: float
    volatility: float
    as_of: date

def _pct(a: float, b: float) -> float:
    return 0.0 if a == 0 else (b - a) / a * 100.0

def _vol(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / n
    return var ** 0.5

@router.get("/metrics/{symbol}", response_model=MetricsResp)
def get_metrics(symbol: str, db: Session = Depends(get_db)) -> MetricsResp:
    # 取过去 400 天，足以覆盖 12M 估算窗口
    end = date.today()
    start = end - timedelta(days=400)
    q = db.query(PriceDaily).filter(PriceDaily.symbol == symbol, PriceDaily.date >= start).order_by(PriceDaily.date.asc())
    rows = q.all()
    if not rows or len(rows) < 40:
        raise HTTPException(status_code=404, detail="not enough data")
    closes = [float(r.close) for r in rows]
    dates = [r.date for r in rows]

    # 近 1/3/12 月：用近 21/63/252 个交易日近似
    def pick(n: int) -> float:
        return _pct(closes[-n], closes[-1]) if len(closes) > n else 0.0
    one_m = pick(21)
    three_m = pick(63)
    twelve_m = pick(252)
    vol60 = _vol(closes[-60:]) if len(closes) >= 60 else _vol(closes)

    return MetricsResp(
        symbol=symbol,
        one_month_change=round(one_m, 4),
        three_months_change=round(three_m, 4),
        twelve_months_change=round(twelve_m, 4),
        volatility=round(vol60, 6),
        as_of=dates[-1],
    )

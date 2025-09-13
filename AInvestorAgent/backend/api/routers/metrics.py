# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from typing import Dict, List                     # ✅ 加 Dict
from sqlalchemy.orm import Session               # ✅ 明确导 Session
from backend.storage import models               # ✅ 明确导 models

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

@router.get("/metrics/{symbol}")
def get_metrics(symbol: str, db: Session = Depends(get_db)) -> Dict:
    # 需要至少 ~252 个交易日
    q = (
        db.query(models.PriceDaily)
        .filter(models.PriceDaily.symbol == symbol)
        .order_by(models.PriceDaily.date.desc())
        .limit(300)
        .all()
    )
    if not q or len(q) < 60:
        raise HTTPException(status_code=404, detail="Not Found")

    prices = list(reversed(q))  # 升序
    closes = [float(p.close) for p in prices]
    def pct(chg_days: int) -> float:
        if len(closes) <= chg_days:
            return 0.0
        return (closes[-1] / closes[-1 - chg_days] - 1.0) * 100.0

    # 简单波动率：近60天标准差*√252（如你有现成函数可替换）
    tail = closes[-60:]
    mean = sum(tail) / len(tail)
    var = sum((x - mean) ** 2 for x in tail) / max(1, len(tail) - 1)
    vol = (var ** 0.5) * (252 ** 0.5)

    return {
        "symbol": symbol,
        "one_month_change": round(pct(21), 4),
        "three_months_change": round(pct(63), 4),
        "twelve_months_change": round(pct(252), 4),
        "volatility": round(vol, 6),
        "as_of": prices[-1].date.isoformat(),
    }
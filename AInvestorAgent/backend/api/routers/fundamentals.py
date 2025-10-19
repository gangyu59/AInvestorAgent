# backend/api/routes/fundamentals.py
from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["fundamentals"])


def parse_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        s = str(v).strip()
        if s == "" or s.upper() in {"N/A", "NA", "NONE", "NULL"}:
            return None
        x = float(s.replace(",", ""))
        if x != x or x in (float("inf"), float("-inf")):
            return None
        return x
    except Exception:
        return None


class FundamentalsResp(BaseModel):
    symbol: str
    pe: Optional[float] = Field(default=None)
    pb: Optional[float] = Field(default=None)
    roe: Optional[float] = Field(default=None)
    net_margin: Optional[float] = Field(default=None)
    market_cap: Optional[float] = Field(default=None)
    sector: Optional[str] = None
    industry: Optional[str] = None
    as_of: datetime


@router.get("/fundamentals/{symbol}")
def get_fundamentals(symbol: str):
    url = "https://placeholder.example/overview"
    try:
        try:
            r = requests.get(url, {"symbol": symbol})
        except TypeError:
            r = requests.get(url, params={"symbol": symbol})
    except Exception as e:
        raise HTTPException(status_code=429, detail=f"external error: {e}")

    if not getattr(r, "ok", False):
        raise HTTPException(status_code=429, detail="External API limit or error")

    try:
        j = r.json() or {}
    except Exception:
        raise HTTPException(status_code=429, detail="External invalid response")

    return FundamentalsResp(
        symbol=symbol,
        pe=parse_float(j.get("PERatio")),
        pb=parse_float(j.get("PriceToBookRatio")),
        roe=parse_float(j.get("ReturnOnEquityTTM")),
        net_margin=parse_float(j.get("ProfitMargin")),
        market_cap=parse_float(j.get("MarketCapitalization")),
        sector=j.get("Sector"),
        industry=j.get("Industry"),
        as_of=datetime.now(timezone.utc),
    )


# 🆕 添加统计接口
@router.get("/api/fundamentals/count")
def get_fundamentals_count():
    """获取 fundamentals 表记录数"""
    from backend.storage.db import SessionLocal
    from backend.storage.models import Fundamental
    from sqlalchemy import func

    db = SessionLocal()
    try:
        count = db.query(func.count(Fundamental.id)).scalar() or 0
        return {"count": count}
    finally:
        db.close()
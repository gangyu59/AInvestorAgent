# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests

from backend.api.deps import get_db

router = APIRouter(tags=["fundamentals"])

class FundamentalsResp(BaseModel):
    symbol: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    net_margin: Optional[float] = None
    market_cap: Optional[int] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    as_of: datetime

@router.get("/fundamentals/{symbol}", response_model=FundamentalsResp)
def get_fundamentals(symbol: str, db: Session = Depends(get_db)) -> FundamentalsResp:
    r = requests.get("https://placeholder.example/overview", params={"symbol": symbol})
    data = r.json()
    if not r.ok:
        raise HTTPException(status_code=400, detail="upstream error")

    f = lambda x: float(x) if x not in (None, "", "None") else None
    i = lambda x: int(x) if x not in (None, "", "None") else None

    return FundamentalsResp(
        symbol=symbol,
        pe=f(data.get("PERatio")),
        pb=f(data.get("PBRatio")),
        roe=f(data.get("ReturnOnEquityTTM")),
        net_margin=f(data.get("NetProfitMargin")),
        market_cap=i(data.get("MarketCapitalization")),
        sector=data.get("Sector"),
        industry=data.get("Industry"),
        as_of=datetime.utcnow(),
    )

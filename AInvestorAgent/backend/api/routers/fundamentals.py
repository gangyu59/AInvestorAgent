# backend/api/routers/fundamentals.py

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
import requests
from pydantic import BaseModel
from datetime import datetime

# AlphaVantage API Key 和基本信息
ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_api_key"
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

router = APIRouter()


# 数据模型
class Fundamentals(BaseModel):
    symbol: str
    pe: float
    pb: float
    roe: float
    net_margin: float
    market_cap: float
    sector: str
    industry: str
    as_of: datetime


@router.get("/fundamentals/{symbol}", response_model=Fundamentals)
def get_fundamentals(symbol: str, db: Session = Depends(get_db)):
    # 查询 AlphaVantage API
    response = requests.get(ALPHA_VANTAGE_URL, params={
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY
    })
    data = response.json()

    if "Error Message" in data or "Note" in data:
        raise HTTPException(status_code=400, detail="Error fetching data from AlphaVantage")

    # 处理并存储数据
    fundamentals = Fundamentals(
        symbol=symbol,
        pe=float(data.get("PERatio", 0)),
        pb=float(data.get("PBRatio", 0)),
        roe=float(data.get("ReturnOnEquityTTM", 0)),
        net_margin=float(data.get("NetProfitMargin", 0)),
        market_cap=float(data.get("MarketCapitalization", 0)),
        sector=data.get("Sector", ""),
        industry=data.get("Industry", ""),
        as_of=datetime.utcnow()
    )

    # 存储到数据库
    db.execute("""
        INSERT INTO fundamentals (symbol, pe, pb, roe, net_margin, market_cap, sector, industry, as_of)
        VALUES (:symbol, :pe, :pb, :roe, :net_margin, :market_cap, :sector, :industry, :as_of)
    """, fundamentals.dict())

    db.commit()

    return fundamentals

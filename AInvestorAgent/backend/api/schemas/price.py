# backend/api/schemas/price.py
from datetime import date
from typing import List, Optional
from pydantic import BaseModel

class PricePoint(BaseModel):
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None

class PriceSeriesResp(BaseModel):
    symbol: str
    range: str
    points: List[PricePoint]


class PriceBar(BaseModel):
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    dividend_amount: float
    split_coefficient: float

class PriceSeriesResponse(BaseModel):
    symbol: str
    items: List[PriceBar]

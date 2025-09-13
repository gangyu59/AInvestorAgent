from pydantic import BaseModel
from typing import List

class NewsItem(BaseModel):
    title: str
    summary: str | None = None
    url: str
    source: str | None = None
    published_at: str

class DayPoint(BaseModel):
    date: str
    sentiment: float
    count_pos: int
    count_neg: int
    count_neu: int

class NewsSeriesResponse(BaseModel):
    symbol: str
    days: int
    timeline: List[DayPoint]
    items: List[NewsItem]

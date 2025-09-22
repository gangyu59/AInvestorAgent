from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel

class PriceBlock(BaseModel):
    series: List[Tuple[str, float]] = []             # [["2025-08-01", 191.2], ...]
    ma: Dict[str, List[Optional[float]]] = {"5": [], "20": [], "60": []}

class FundamentalsBlock(BaseModel):
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    net_margin: Optional[float] = None
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    as_of: Optional[str] = None
    source: Optional[str] = None

class FactorsBlock(BaseModel):
    value: Optional[float] = None
    quality: Optional[float] = None
    momentum: Optional[float] = None
    risk: Optional[float] = None
    sentiment: Optional[float] = None

class ScoreBreakdown(BaseModel):
    value: Optional[float] = None
    quality: Optional[float] = None
    momentum: Optional[float] = None
    sentiment: Optional[float] = None
    score: Optional[float] = None
    version_tag: Optional[str] = None

class SentimentPoint(BaseModel):
    date: str
    score: float
    n: int = 1

class AnalyzeResponse(BaseModel):
    symbol: str
    as_of: Optional[str] = None
    price: PriceBlock = PriceBlock()
    fundamentals: FundamentalsBlock = FundamentalsBlock()
    factors: FactorsBlock = FactorsBlock()
    score: ScoreBreakdown = ScoreBreakdown()
    sentiment_timeline: List[SentimentPoint] = []

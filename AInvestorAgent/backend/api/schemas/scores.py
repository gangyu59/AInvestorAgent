from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
class ScoreRow(BaseModel):
    symbol: str
    f_value: Optional[float] = None
    f_quality: Optional[float] = None
    f_momentum: Optional[float] = None
    f_sentiment: Optional[float] = None
    score: float

class ScoreTableResponse(BaseModel):
    as_of: str
    version_tag: str
    items: List[ScoreRow]


class FactorBreakdown(BaseModel):
    # 与现有命名对齐，保留 f_ 前缀风格，便于直接接 compute_factors 输出
    f_value: Optional[float] = None
    f_quality: Optional[float] = None
    f_momentum: Optional[float] = None
    f_sentiment: Optional[float] = None
    f_risk: Optional[float] = None  # 如暂时没有，可为 None

class ScoreDetail(BaseModel):
    value: int
    quality: int
    momentum: int
    sentiment: int
    score: int
    version_tag: str

class BatchScoreItem(BaseModel):
    symbol: str
    factors: FactorBreakdown
    score: ScoreDetail
    updated_at: datetime

class BatchScoreRequest(BaseModel):
    symbols: List[str]
    mock: Optional[bool] = False  # 默认关闭 mock

class BatchScoreResponse(BaseModel):
    items: List[BatchScoreItem]
    as_of: str
    version_tag: str


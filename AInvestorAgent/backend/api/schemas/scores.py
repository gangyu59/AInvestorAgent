from pydantic import BaseModel
from typing import List, Optional

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

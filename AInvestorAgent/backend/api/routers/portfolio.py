from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from ...storage.db import get_db
from ...scoring.scorer import build_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

class PortfolioItem(BaseModel):
    symbol: str
    score: float
    f_value: Optional[float] = None
    f_quality: Optional[float] = None
    f_momentum: Optional[float] = None
    f_sentiment: Optional[float] = None
    weight: float

class PortfolioResponse(BaseModel):
    as_of: str
    version_tag: str
    items: List[PortfolioItem]
    meta: dict

@router.post("/topn", response_model=PortfolioResponse)
def topn(
    symbols: List[str] = Query(..., description="重复传参: symbols=AAPL&symbols=MSFT"),
    top_n: int = 5,
    scheme: str = "proportional",  # or "equal"
    alpha: float = 1.0,
    min_w: float = 0.0,
    max_w: float = 0.4,
    as_of: str | None = None,
    db: Session = Depends(get_db),
):
    dt = date.fromisoformat(as_of) if as_of else date.today()
    return build_portfolio(
        db, symbols, dt,
        top_n=top_n, scheme=scheme, alpha=alpha,
        min_w=min_w, max_w=max_w
    )

class SnapshotBrief(BaseModel):
    weights: Dict[str, float] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)
    version_tag: Optional[str] = None
    kept: Optional[list[str]] = None

@router.get("/portfolio/snapshot")
def get_portfolio_snapshot(latest: int = 1) -> SnapshotBrief:
    """
    最小可用实现：
    - 若你已落库/有 DAO，可在这里读取“最近一条快照”并返回
    - 若暂无数据，仍返回 200 + 空结构，避免前端 404
    """
    # TODO: 如果你有 DAO，这里替换为实际查询；示例：
    # data = PortfolioDAO.latest()  # 自己的存储层
    # if data: return SnapshotBrief(**data)
    return SnapshotBrief()  # 空结构，前端会优雅降级
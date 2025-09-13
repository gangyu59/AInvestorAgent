from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...storage.db import get_db
from backend.scoring.scorer import compute_factors, upsert_scores, aggregate_score
from ..schemas.scores import ScoreRow, ScoreTableResponse

router = APIRouter(prefix="/api/scores", tags=["scores"])

@router.post("/watchlist", response_model=ScoreTableResponse)
def run_watchlist(
    symbols: list[str] = Query(..., description="多只股票，如 symbols=AAPL&symbols=MSFT"),
    as_of: str | None = None,
    db: Session = Depends(get_db),
):
    dt = date.fromisoformat(as_of) if as_of else date.today()
    rows = compute_factors(db, symbols, dt)
    upsert_scores(db, dt, rows, version_tag="v0.1")
    items = [ScoreRow(symbol=r.symbol,
                      f_value=r.f_value, f_quality=r.f_quality,
                      f_momentum=getattr(r, "f_momentum", None),
                      f_sentiment=r.f_sentiment,
                      score=aggregate_score(r)) for r in rows]
    # 按分数降序
    items.sort(key=lambda x: x.score, reverse=True)
    return {"as_of": dt.isoformat(), "version_tag": "v0.1", "items": items}

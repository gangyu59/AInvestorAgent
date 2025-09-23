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


# === 追加导入 ===
from datetime import datetime
from fastapi import HTTPException
from ...storage.dao import ScoresDAO  # 新增 DAO
from ..schemas.scores import (
    BatchScoreRequest, BatchScoreResponse, BatchScoreItem,
    FactorBreakdown, ScoreDetail
)

@router.post("/batch", response_model=BatchScoreResponse)
def score_batch(payload: BatchScoreRequest, db: Session = Depends(get_db)):
    symbols = [s.strip().upper() for s in (payload.symbols or []) if s.strip()]
    if not symbols:
        raise HTTPException(status_code=400, detail="symbols is empty")

    dt = date.today()
    version_tag = "v1.0.0"
    items: list[BatchScoreItem] = []

    for sym in symbols:
        try:
            # 仅计算，不传 mock；不回退；不入库
            rows = compute_factors(db, [sym], dt)
            if not rows:
                continue
            r = rows[0]

            factors = FactorBreakdown(
                f_value=getattr(r, "f_value", None),
                f_quality=getattr(r, "f_quality", None),
                f_momentum=getattr(r, "f_momentum", None),
                f_sentiment=getattr(r, "f_sentiment", None),
                f_risk=getattr(r, "f_risk", None),
            )

            # 如果你已有 aggregate_score 就用它；没有就按权重兜底
            try:
                total = int(round(aggregate_score(r)))
                v = int(round(getattr(r, "f_value", 0) * 25))
                q = int(round(getattr(r, "f_quality", 0) * 25))
                m = int(round(getattr(r, "f_momentum", 0) * 30))
                s = int(round(getattr(r, "f_sentiment", 0) * 20))
            except Exception:
                v = int(round((getattr(r, "f_value", 0) or 0) * 25))
                q = int(round((getattr(r, "f_quality", 0) or 0) * 25))
                m = int(round((getattr(r, "f_momentum", 0) or 0) * 30))
                s = int(round((getattr(r, "f_sentiment", 0) or 0) * 20))
                total = v + q + m + s

            detail = ScoreDetail(
                value=v, quality=q, momentum=m, sentiment=s,
                score=total, version_tag=version_tag,
            )

            items.append(BatchScoreItem(
                symbol=sym, factors=factors, score=detail, updated_at=datetime.utcnow()
            ))

            # 暂时不写库，不做回退：
            # ScoresDAO.upsert(item.model_dump())
            # cached = ScoresDAO.get_last_success(sym)

        except Exception:
            # 失败先跳过，防止 500 拖垮整个批次
            continue

    return BatchScoreResponse(as_of=dt.isoformat(), version_tag=version_tag, items=items)

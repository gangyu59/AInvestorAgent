# AInvestorAgent/backend/api/routers/scores.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from backend.storage.db import get_db
from backend.storage.dao import ScoresDAO  # 你已有 dao.py 里的封装
from backend.scoring.scorer import compute_factors, aggregate_score  # 你已有
from backend.scoring.weights import WEIGHTS  # 你刚建的 weights.py

router = APIRouter(prefix="/api/scores", tags=["scores"])

class BatchPayload(BaseModel):
    symbols: List[str]
    mock: Optional[bool] = False
    as_of: Optional[str] = None  # 允许前端传 as_of；缺省用今天

@router.post("/batch")
def score_batch(payload: BatchPayload, db: Session = Depends(get_db)):
    symbols = [s.strip().upper() for s in payload.symbols if s.strip()]
    as_of = date.fromisoformat(payload.as_of) if payload.as_of else date.today()
    version_tag = getattr(WEIGHTS, "version_tag", None) or getattr(WEIGHTS, "VERSION", None) or "v1.0.0"

    items = []

    for sym in symbols:
        # --- 计算因子 ---
        rows = []
        try:
            # 注意：不再传 mock=，避免 TypeError
            rows = compute_factors(db, [sym], as_of)
        except TypeError:
            # 兼容没有 as_of 的旧签名：compute_factors(db, [sym])
            rows = compute_factors(db, [sym])

        r = rows[0] if rows else None

        if r is not None:
            # r 很可能是 Pydantic/ORM 对象，用 getattr 安全取值
            f_value     = float(getattr(r, "f_value", 0) or 0)
            f_quality   = float(getattr(r, "f_quality", 0) or 0)
            f_momentum  = float(getattr(r, "f_momentum", 0) or 0)
            f_sentiment = float(getattr(r, "f_sentiment", 0) or 0)
            f_risk      = float(getattr(r, "f_risk", 0) or 0)
            # 综合评分
            try:
                total = float(aggregate_score(r))
            except TypeError:
                # 旧实现可能需要权重：aggregate_score(r, WEIGHTS)
                total = float(aggregate_score(r, WEIGHTS))

            item = {
                "symbol": sym,
                "factors": {
                    "f_value": f_value,
                    "f_quality": f_quality,
                    "f_momentum": f_momentum,
                    "f_sentiment": f_sentiment,
                    "f_risk": f_risk,
                },
                "score": {
                    "value": round(f_value * 100) if f_value <= 1 else round(f_value),
                    "quality": round(f_quality * 100) if f_quality <= 1 else round(f_quality),
                    "momentum": round(f_momentum * 100) if f_momentum <= 1 else round(f_momentum),
                    "sentiment": round(f_sentiment * 100) if f_sentiment <= 1 else round(f_sentiment),
                    "score": round(total, 1),
                    "version_tag": version_tag,
                },
                "updated_at": as_of.isoformat(),
            }
        else:
            # 没算出来 → 兜底最后一次成功快照（避免前端表格为空）
            cached = ScoresDAO.get_last_success(sym)
            if cached:
                item = {
                    "symbol": sym,
                    "factors": {
                        "f_value": float(getattr(cached, "f_value", 0) or 0),
                        "f_quality": float(getattr(cached, "f_quality", 0) or 0),
                        "f_momentum": float(getattr(cached, "f_momentum", 0) or 0),
                        "f_sentiment": float(getattr(cached, "f_sentiment", 0) or 0),
                        "f_risk": float(getattr(cached, "f_risk", 0) or 0),
                    },
                    "score": {
                        "value": int(getattr(cached, "s_value", 0) or 0),
                        "quality": int(getattr(cached, "s_quality", 0) or 0),
                        "momentum": int(getattr(cached, "s_momentum", 0) or 0),
                        "sentiment": int(getattr(cached, "s_sentiment", 0) or 0),
                        "score": float(getattr(cached, "score", 0) or 0),
                        "version_tag": getattr(cached, "version_tag", version_tag) or version_tag,
                    },
                    "updated_at": getattr(cached, "as_of", as_of).isoformat() if getattr(cached, "as_of", None) else as_of.isoformat(),
                }
            else:
                item = {
                    "symbol": sym,
                    "factors": {},
                    "score": {"score": 0, "version_tag": version_tag},
                    "updated_at": as_of.isoformat(),
                }

        # 入库（尽量不出错；错了也不影响响应）
        try:
            ScoresDAO.upsert({
                "symbol": item["symbol"],
                "as_of": as_of,
                "version_tag": item["score"].get("version_tag", version_tag),
                "f_value": item["factors"].get("f_value", 0),
                "f_quality": item["factors"].get("f_quality", 0),
                "f_momentum": item["factors"].get("f_momentum", 0),
                "f_sentiment": item["factors"].get("f_sentiment", 0),
                "f_risk": item["factors"].get("f_risk", 0),
                "s_value": item["score"].get("value", 0),
                "s_quality": item["score"].get("quality", 0),
                "s_momentum": item["score"].get("momentum", 0),
                "s_sentiment": item["score"].get("sentiment", 0),
                "score": item["score"].get("score", 0),
            })
        except Exception:
            pass

        items.append(item)

    return {
        "as_of": as_of.isoformat(),
        "version_tag": version_tag,
        "items": items,
    }

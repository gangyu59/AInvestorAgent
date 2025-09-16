# backend/agents/chair.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import date, UTC, datetime
from sqlalchemy import select, desc
from backend.storage.db import session_scope
from backend.storage.models import ScoreDaily  # as_of, symbol, sector?, score 0..100

@dataclass
class ChairConfig:
    topk: int = 20
    min_score: float = 60.0

class ChairAgent:
    name = "chair"

    def run(self, ctx: Dict[str, Any], **params) -> Dict[str, Any]:
        cfg = ChairConfig(**{k: v for k, v in params.items() if k in {"topk", "min_score"}})
        # 取最近一天
        with session_scope() as s:
            q = (select(ScoreDaily)
                 .order_by(desc(ScoreDaily.as_of), desc(ScoreDaily.score))
                 .limit(200))
            rows = s.execute(q).scalars().all()
        if not rows:
            return {"ok": False, "data": {}, "meta": {"err": "no scores_daily"}}

        as_of = rows[0].as_of
        day_rows = [r for r in rows if r.as_of == as_of and r.score is not None]
        day_rows.sort(key=lambda r: r.score, reverse=True)

        cands = []
        for r in day_rows:
            if r.score < cfg.min_score:  # 过滤低分
                continue
            cands.append({"symbol": r.symbol, "score": round(float(r.score), 2)})
            if len(cands) >= cfg.topk:
                break

        meta = {"as_of": str(as_of), "ts": datetime.now(UTC).isoformat(), "topk": cfg.topk}
        return {"ok": True, "data": {"candidates": cands}, "meta": meta}

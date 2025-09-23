# backend/portfolio/explain.py
from __future__ import annotations
from typing import Dict, Iterable, List, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.storage.models import Symbol, ScoreDaily  # 复用你的 ORM 模型
# ↑ 见 models.py 的 Symbol / ScoreDaily 定义
#    sector 字段来源 symbols 表；评分来自 scores_daily 表
#    （不创建新模型/表）                                  # noqa
# ──────────────────────────────────────────────────────

def load_symbol_sectors(db: Session, symbols: Iterable[str]) -> Dict[str, str]:
    syms = [s.upper() for s in symbols]
    rows = db.execute(
        select(Symbol.symbol, Symbol.sector).where(Symbol.symbol.in_(syms))
    ).all()
    return {sym: (sector or "Unknown") for sym, sector in rows}

def build_reasons_from_scores(score_row: ScoreDaily) -> List[str]:
    tags: List[str] = []
    if getattr(score_row, "f_momentum", None) and score_row.f_momentum >= 0.6:
        tags.append("动量↑")
    if getattr(score_row, "f_quality", None) and score_row.f_quality >= 0.6:
        tags.append("质量↑")
    if getattr(score_row, "f_sentiment", None) and score_row.f_sentiment >= 0.6:
        tags.append("舆情↑")
    if getattr(score_row, "f_value", None) and score_row.f_value >= 0.6:
        tags.append("价值↑")
    return tags or ["综合评分领先"]

def sector_concentration(pairs: Iterable[Tuple[str, float]]) -> List[Tuple[str, float]]:
    agg: Dict[str, float] = {}
    for sector, w in pairs:
        agg[sector] = agg.get(sector, 0.0) + float(w or 0.0)
    total = sum(agg.values()) or 1.0
    # 按降序返回（sector, weight[0..1]）
    return sorted(((k, v / total) for k, v in agg.items()), key=lambda x: x[1], reverse=True)

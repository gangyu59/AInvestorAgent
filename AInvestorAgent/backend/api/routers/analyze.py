# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

# ==== 你的 Pydantic Schemas ====
from backend.api.schemas.analyze import (
    AnalyzeResponse, PriceBlock, FundamentalsBlock,
    FactorsBlock, ScoreBreakdown, SentimentPoint
)

# ==== 你的 Session/ORM ====
from backend.storage.db import get_db
from backend.storage import models

# ==== 你的因子&评分 ====
from backend.scoring.scorer import compute_factors, aggregate_score  # 无 mock 参数

router = APIRouter(prefix="/api", tags=["analyze"])

# ---------------------------
# helpers
# ---------------------------
def _compute_ma(series: List[Tuple[str, float]]) -> Dict[str, List[Optional[float]]]:
    closes = [v for _, v in series]
    if not closes:
        return {"5": [], "20": [], "60": []}

    def ma(n: int):
        out: List[Optional[float]] = []
        acc = 0.0
        for i, v in enumerate(closes):
            acc += v
            if i >= n:
                acc -= closes[i - n]
            out.append(acc / n if i >= n - 1 else None)
        return out

    return {"5": ma(5), "20": ma(20), "60": ma(60)}

# ---------------------------
# providers
# ---------------------------
def _prov_price_series(db: Session, symbol: str, limit_days: int) -> List[Tuple[str, float]]:
    stmt = (
        select(models.PriceDaily.date, models.PriceDaily.close)
        .where(models.PriceDaily.symbol == symbol.upper())
        .order_by(models.PriceDaily.date.desc())
        .limit(limit_days)
    )
    rows = db.execute(stmt).all()
    pairs = [(d.isoformat(), float(c)) for d, c in rows if c is not None]
    pairs.sort(key=lambda x: x[0])
    return pairs

def _prov_fundamentals(db: Session, symbol: str) -> FundamentalsBlock:
    # 若你暂未建表，先返回空占位，前端会安全显示
    # 如有表，可改为真实查询：
    # obj = db.query(models.Fundamentals).filter_by(symbol=symbol.upper()).one_or_none()
    # if obj: return FundamentalsBlock(pe=obj.pe, pb=obj.pb, ...)
    return FundamentalsBlock()

def _prov_factors_and_score(db: Session, symbol: str, asof_iso: Optional[str]) -> Tuple[FactorsBlock, ScoreBreakdown]:
    asof = datetime.strptime(asof_iso, "%Y-%m-%d").date() if asof_iso else date.today()
    frs = compute_factors(db, [symbol.upper()], asof)  # 无 mock 参数
    if not frs:
        return FactorsBlock(), ScoreBreakdown(version_tag="v0.1")
    r = frs[0]

    factors = FactorsBlock(
        value=getattr(r, "f_value", None),
        quality=getattr(r, "f_quality", None),
        momentum=getattr(r, "f_momentum", None),
        risk=None,  # 目前 scorer 未产出 risk，占位
        sentiment=getattr(r, "f_sentiment", None),
    )

    total = float(aggregate_score(r))  # 0..100
    # 简单把分项按权重折算（与前端展示对齐；缺项为 None）
    score = ScoreBreakdown(
        value=None if r.f_value is None else r.f_value * 100 * 0.25,
        quality=None if r.f_quality is None else r.f_quality * 100 * 0.20,
        momentum=None if getattr(r, "f_momentum", None) is None else r.f_momentum * 100 * 0.35,
        sentiment=None if r.f_sentiment is None else r.f_sentiment * 100 * 0.20,
        score=total,
        version_tag="v1.0.0",
    )
    return factors, score

def _prov_sentiment_timeline(db: Session, symbol: str, days: int) -> List[SentimentPoint]:
    since = datetime.utcnow() - timedelta(days=days)
    dt_date = func.date(models.NewsRaw.published_at)
    stmt = (
        select(
            dt_date.label("d"),
            func.avg(models.NewsScore.sentiment).label("avg_sent"),
            func.count(models.NewsScore.id).label("n"),
        )
        .join(models.NewsScore, models.NewsScore.news_id == models.NewsRaw.id)
        .where(models.NewsRaw.symbol == symbol.upper(), models.NewsRaw.published_at >= since)
        .group_by(dt_date)
        .order_by(dt_date.asc())
    )
    out: List[SentimentPoint] = []
    for d, avg_sent, n in db.execute(stmt):
        out.append(SentimentPoint(date=str(d), score=float(avg_sent or 0.0), n=int(n or 0)))
    return out

# ---------------------------
# API
# ---------------------------
@router.get("/analyze/{symbol}", response_model=AnalyzeResponse)
def analyze_symbol(
    symbol: str,
    price_days: int = Query(252, ge=30, le=2000, description="价格序列回看天数"),
    news_days: int = Query(30, ge=7, le=180, description="新闻情绪回看天数"),
    asof: Optional[str] = Query(None, description="评分/因子的 as_of（YYYY-MM-DD）"),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()

    # 价格
    series = _prov_price_series(db, symbol, price_days)
    price = PriceBlock(series=series, ma=_compute_ma(series))

    # 基本面（占位/或真实查询）
    fundamentals = _prov_fundamentals(db, symbol)

    # 因子与评分
    factors, score = _prov_factors_and_score(db, symbol, asof)

    # 情绪时间轴
    sentiment_timeline = _prov_sentiment_timeline(db, symbol, news_days)

    return AnalyzeResponse(
        symbol=symbol,
        as_of=(asof or date.today().isoformat()),
        price=price,
        fundamentals=fundamentals,
        factors=factors,
        score=score,
        sentiment_timeline=sentiment_timeline,
    )

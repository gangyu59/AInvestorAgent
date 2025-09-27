# backend/api/routers/sentiment.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from backend.storage.db import get_db
from backend.storage.models import NewsRaw, NewsScore
from backend.api.schemas.sentiment import SentimentBrief, SentimentPoint, NewsItem

router = APIRouter(prefix="/sentiment", tags=["sentiment"])

@router.get("/brief", response_model=SentimentBrief)
def get_sentiment_brief(
    symbols: str = Query(..., description="逗号分隔，如 AAPL,MSFT"),
    days: int = Query(14, ge=1, le=90, description="回看天数（1~90）"),
    db: Session = Depends(get_db)
):
    # 1) 解析参数与时间窗
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        return SentimentBrief(series=[], latest_news=[])
    # 统一用 UTC（入库时一般是 UTC；若不是也只是日期级别聚合，不影响）
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 2) 按“日”聚合平均情绪分（news_raw × news_scores join）
    #    SQLite 下 func.date(published_at) -> 'YYYY-MM-DD'
    rows = (
        db.query(
            func.date(NewsRaw.published_at).label("d"),
            func.avg(NewsScore.sentiment).label("avg_s")
        )
        .join(NewsScore, NewsScore.news_id == NewsRaw.id)
        .filter(NewsRaw.symbol.in_(syms))
        .filter(NewsRaw.published_at >= since)
        .group_by("d")
        .order_by("d")
        .all()
    )
    day2score = {d: float(avg_s or 0.0) for d, avg_s in rows}

    # 3) 补齐缺失日期（无新闻的日期置 0，便于画“0 轴”效果）
    series: list[SentimentPoint] = []
    for i in range(days - 1, -1, -1):  # 从老到新
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat()
        series.append(SentimentPoint(date=d, score=day2score.get(d, 0.0)))

    # 4) 最新新闻（含情绪分）——按时间倒序取前 100 条
    latest = (
        db.query(NewsRaw.title, NewsRaw.url, NewsScore.sentiment, NewsRaw.published_at)
        .join(NewsScore, NewsScore.news_id == NewsRaw.id)
        .filter(NewsRaw.symbol.in_(syms))
        .filter(NewsRaw.published_at >= since)
        .order_by(NewsRaw.published_at.desc())
        .limit(100)
        .all()
    )
    latest_news = [NewsItem(title=t, url=u, score=float(s or 0.0)) for (t, u, s, _) in latest]

    return SentimentBrief(series=series, latest_news=latest_news)

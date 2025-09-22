from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.api.schemas.analyze import (
    AnalyzeResponse, PriceBlock, FundamentalsBlock,
    FactorsBlock, ScoreBreakdown, SentimentPoint
)

# 直接使用你的 Session & ORM
from backend.storage.db import get_db
from backend.storage import models

# 因子与评分：用你给的 scorer.py
from backend.scoring.scorer import compute_factors, aggregate_score  # :contentReference[oaicite:1]{index=1}

router = APIRouter(prefix="/api", tags=["analyze"])


# ---------------------------
# helpers
# ---------------------------
def _compute_ma(series: List[Tuple[str, float]]) -> Dict[str, List[Optional[float]]]:
    """纯 Python 简单 MA5/20/60；空数据安全"""
    closes = [v for _, v in series]
    if not closes:
        return {"5": [], "20": [], "60": []}

    def ma(window: int):
        out: List[Optional[float]] = []
        acc = 0.0
        for i, v in enumerate(closes):
            acc += v
            if i >= window:
                acc -= closes[i - window]
            out.append(acc / window if i >= window - 1 else None)
        return out

    return {"5": ma(5), "20": ma(20), "60": ma(60)}

# ---------------------------
# providers（只在这里对接你的现有模块/DAO）
# ---------------------------
def _prov_price_series(db: Session, symbol: str, limit_days: int) -> List[Tuple[str, float]]:
    """从 prices_daily 读收盘价，升序返回 (date, close)"""
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
    """
    若你暂未建 fundamentals 表，这里先占位，等你给我模型名和字段我再替换为真实查询。
    """
    # 示例（存在时可改成真实查询）：
    # obj = db.query(models.Fundamentals).filter(models.Fundamentals.symbol == symbol.upper()).one_or_none()
    # if obj:
    #     return FundamentalsBlock(pe=obj.pe, pb=obj.pb, roe=obj.roe, net_margin=obj.net_margin,
    #                              market_cap=obj.market_cap, sector=obj.sector,
    #                              as_of=obj.as_of.isoformat() if obj.as_of else None, source=obj.source)
    return FundamentalsBlock()

def _prov_factors_and_score(db: Session, symbol: str, asof_iso: Optional[str]) -> Tuple[FactorsBlock, ScoreBreakdown]:
    """
    基于你的 scorer.py：
      - compute_factors(db, [symbol], asof)
      - aggregate_score(row)
    """
    # asof：优先用传入，否则取今日
    asof = datetime.strptime(asof_iso, "%Y-%m-%d").date() if asof_iso else date.today()

    frs = compute_factors(db, [symbol.upper()], asof)  # List[FactorRow]  :contentReference[oaicite:2]{index=2}
    if not frs:
        return FactorsBlock(), ScoreBreakdown(version_tag="v0.1")

    r = frs[0]
    factors = FactorsBlock(
        value=r.f_value,
        quality=r.f_quality,
        momentum=getattr(r, "f_momentum", None),
        risk=None,  # 你的 scorer 里目前没产出 risk，保持占位
        sentiment=r.f_sentiment,
    )
    score_val = aggregate_score(r)  # float 0..100          :contentReference[oaicite:3]{index=3}
    score = ScoreBreakdown(
        value=None if r.f_value is None else r.f_value * 100 * 0.25,
        quality=None if r.f_quality is None else r.f_quality * 100 * 0.20,
        momentum=None if getattr(r, "f_momentum", None) is None else r.f_momentum * 100 * 0.35,
        sentiment=None if r.f_sentiment is None else r.f_sentiment * 100 * 0.20,
        score=score_val,
        version_tag="v0.1",
    )
    return factors, score

def _prov_sentiment_timeline(db: Session, symbol: str, days: int) -> List[SentimentPoint]:
    """news_raw + news_scores 按日聚合均值与条数"""
    since = datetime.utcnow() - timedelta(days=days)
    dt_date = func.date(models.NewsRaw.published_at)
    stmt = (
        select(
            dt_date.label("d"),
            func.avg(models.NewsScore.sentiment).label("avg_sent"),
            func.count(models.NewsScore.id).label("n"),
        )
        .join(models.NewsScore, models.NewsScore.news_id == models.NewsRaw.id)
        .where(
            models.NewsRaw.symbol == symbol.upper(),
            models.NewsRaw.published_at >= since
        )
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
    news_days: int = Query(30, ge=7, le=180, description="情绪时间轴回看天数"),
    db: Session = Depends(get_db),
):
    """
    统一分析对象：价格+MA / 基本面 / 因子 / 评分 / 情绪时间轴。
    - 缺数据时返回空占位，不抛 500（前端可继续操作）。
    - 因子&评分直接复用你的 scorer.py（权重与版本保持一致）。 :contentReference[oaicite:4]{index=4}
    """
    # 价格与 MA
    series = _prov_price_series(db, symbol, price_days)
    ma = _compute_ma(series)

    # 基本面（若暂无表则为空占位）；as_of 优先用 fundamentals.as_of -> 价格末日 -> 今天
    fundamentals = _prov_fundamentals(db, symbol)
    if fundamentals.as_of:
        as_of = fundamentals.as_of
    elif series:
        as_of = series[-1][0]
    else:
        as_of = datetime.utcnow().strftime("%Y-%m-%d")

    # 因子与评分（用你的 scorer）
    factors, score = _prov_factors_and_score(db, symbol, as_of)

    # 情绪时间轴
    timeline = _prov_sentiment_timeline(db, symbol, news_days)

    return AnalyzeResponse(
        symbol=symbol.upper(),
        as_of=as_of,
        price=PriceBlock(series=series, ma=ma),
        fundamentals=fundamentals,
        factors=factors,
        score=score,
        sentiment_timeline=timeline,
    )

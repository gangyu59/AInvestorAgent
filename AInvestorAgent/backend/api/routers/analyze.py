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

router = APIRouter(prefix="", tags=["analyze"])

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


# -----------------------------------------------------------------------------------
# 生成 Markdown 报告（最小可用版）
# 路由：POST /api/report/generate
# 行为：
#   - 读取最近一次组合快照（若模型/表不存在则降级为空组合）
#   - 汇总持仓权重与 Top2 理由（若有）
#   - 统计每只持仓近 N 天的新闻情绪均值与数量（如果有 NewsRaw/NewsScore）
# 返回：{ ok, format:"markdown", content, snapshot_id? }
# -----------------------------------------------------------------------------------
from fastapi import HTTPException

@router.post("/report/generate")
def generate_report(days: int = 7, db: Session = Depends(get_db)):
    # 1) 读取最近快照（兼容不同模型字段；模型不存在时优雅降级）
    holdings = []
    snapshot_id = None
    try:
        Snap = getattr(models, "PortfolioSnapshot", None)  # 你项目里的快照模型，如不存在则为 None
        if Snap is not None:
            q = db.query(Snap)
            if hasattr(Snap, "created_at"):
                q = q.order_by(Snap.created_at.desc())
            elif hasattr(Snap, "as_of"):
                q = q.order_by(Snap.as_of.desc())
            elif hasattr(Snap, "id"):
                q = q.order_by(Snap.id.desc())
            snap = q.first()
            if snap:
                snapshot_id = getattr(snap, "snapshot_id", None) or getattr(snap, "id", None)
                payload = getattr(snap, "payload", None)
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}
                if isinstance(payload, dict):
                    holdings = payload.get("holdings", []) or []
    except Exception:
        # 快照表不存在/结构不同 → 降级为空组合
        pass

    symbols = [h.get("symbol") for h in holdings if h.get("symbol")] if holdings else []

    # 2) 情绪摘要（近 N 天）：沿用你文件中使用的 NewsRaw/NewsScore 表（同一 models 命名空间）
    senti_lines = []
    if symbols:
        try:
            since = datetime.utcnow() - timedelta(days=days)
            dt_date = func.date(models.NewsRaw.published_at)  # 你的 analyze.py 里已有同表使用方式
            for s in symbols:
                stmt = (
                    select(
                        func.avg(models.NewsScore.sentiment).label("avg_sent"),
                        func.count(models.NewsScore.id).label("n"),
                    )
                    .join(models.NewsScore, models.NewsScore.news_id == models.NewsRaw.id)
                    .where(models.NewsRaw.symbol == s.upper(), models.NewsRaw.published_at >= since)
                )
                r = db.execute(stmt).first()
                avg_val = float(r[0]) if r and r[0] is not None else None
                n_val = int(r[1]) if r and r[1] is not None else 0
                if avg_val is None:
                    senti_lines.append(f"- {s}: 近{days}天收录 {n_val} 条新闻（无有效情绪分数）")
                else:
                    senti_lines.append(f"- {s}: 近{days}天情绪均值 {avg_val:+.2f}（{n_val} 条）")
        except Exception:
            # 情绪表缺失也不阻塞报告生成
            pass

    # 3) 组装 Markdown
    today = date.today().isoformat()
    md = []
    md.append(f"# Daily Portfolio Report\n")
    md.append(f"- Date: **{today}**")
    if snapshot_id:
        md.append(f"- Snapshot ID: `{snapshot_id}`")
    md.append("")

    if holdings:
        md.append("## Current Portfolio")
        for h in holdings:
            sym = h.get("symbol")
            w = h.get("weight", 0)
            rs = h.get("reasons") or []
            line = f"- **{sym}**  weight: **{w:.2%}**"
            if rs:
                line += f"  — reasons: {', '.join(map(str, rs[:2]))}"
            md.append(line)
    else:
        md.append("_No saved portfolio snapshot. Generate one via **Decide Now**._")

    if senti_lines:
        md.append("")
        md.append(f"## Sentiment (last {days} days)")
        md.extend(senti_lines)

    md_txt = "\n".join(md) + "\n"
    return {"ok": True, "format": "markdown", "content": md_txt, "snapshot_id": snapshot_id}


# 在现有 analyze.py 文件顶部的 imports 中添加
from backend.agents.signal_researcher import EnhancedSignalResearcher
import asyncio


@router.post("/analyze/smart/{symbol}")
async def smart_analyze_symbol(symbol: str):
    """AI增强的股票分析"""
    try:
        # 模拟获取数据（你需要根据实际情况调整）
        context = {
            "symbol": symbol,
            "prices": [100, 101, 102, 103, 104],  # 简化的价格数据
            "fundamentals": {"pe": 25, "roe": 15},  # 简化的基本面数据
            "news_raw": [
                {"title": f"{symbol} Q4 earnings beat expectations", "summary": "Strong performance"},
                {"title": f"{symbol} announces new product", "summary": "Innovation continues"}
            ],
            "mock": True  # 启用mock模式确保稳定运行
        }

        # 使用增强版分析器
        researcher = EnhancedSignalResearcher()
        result = await researcher.run_with_llm(context)

        return {
            "symbol": symbol,
            "analysis": result,
            "timestamp": datetime.now().isoformat(),
            "version": "llm_enhanced_v1"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")
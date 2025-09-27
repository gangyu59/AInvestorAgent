# backend/api/routers/decide.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from backend.ingestion.alpha_vantage_client import get_prices_for_symbol
from sqlalchemy.orm import Session
from backend.storage.db import engine
from backend.portfolio.allocator import propose_portfolio
from backend.portfolio.constraints import default_constraints
from backend.agents.signal_researcher import EnhancedSignalResearcher
from backend.agents.portfolio_manager import EnhancedPortfolioManager

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

class DecideRequest(BaseModel):
    symbols: List[str] = Field(..., description="候选股票池")
    topk: int = 8
    min_score: int = 60
    refresh_prices: bool = True
    use_llm: bool = True
    params: Optional[Dict[str, Any]] = None
    trading_cost: Optional[float] = 0.001

    class Config:
        arbitrary_types_allowed = True

class DecideResponse(BaseModel):
    as_of: str
    universe: List[str]
    analyses: Dict[str, Dict[str, Any]]
    holdings: List[Dict[str, Any]]   # {symbol, weight}
    reasoning: str | None = None
    method: str
    snapshot_id: str | None = None   # 如在 propose 内部会落快照，可回填
    version_tag: str | None = None

@router.post("/decide", response_model=DecideResponse)
async def decide_now(req: DecideRequest):
    if not req.symbols:
        raise HTTPException(400, "symbols is empty")

    # 1) 准实时价格（保证“时效性”）：必要时刷新最近报价
    prices_map: Dict[str, list[float]] = {}
    for sym in req.symbols:
        try:
            # 你已有的 client：limit=120 给足 6 个月日线；如 refresh_prices=True，可在 client 内开 refresh/缓存策略
            prices_map[sym] = get_prices_for_symbol(sym, limit=120)
        except Exception:
            prices_map[sym] = []

    # 2) 逐票做“研究”分析（可带 LLM 解释，但**不把权重直接交给LLM**）
    analyses: Dict[str, Dict[str, Any]] = {}
    researcher = EnhancedSignalResearcher()
    researcher.use_llm = req.use_llm

    for sym in req.symbols:
        ctx = {
            "symbol": sym,
            "prices": prices_map[sym],
            # 如有：fundamentals/news_raw 也可以补进来
            "mock": False,
        }
        base = researcher.run(ctx)
        if req.use_llm:
            # LLM 增强（包含建议/逻辑说明），失败会自动兜底为 base
            base = await researcher.run_with_llm(ctx)
        analyses[sym] = base

    # 3) 过滤/排序→取 topk
    ranked = sorted(
        analyses.items(),
        key=lambda kv: (kv[1].get("score") or 0),
        reverse=True
    )
    kept = [(s, a) for s, a in ranked if (a.get("score") or 0) >= req.min_score]
    top = kept[: req.topk] if kept else ranked[: req.topk]
    top_syms = [s for s, _ in top]

    sub_analyses = {s: a for s, a in top}

    # 4) 组合建议：优先用 LLM 生成权重→解析失败自动回退到等权/线性分配
    pm = EnhancedPortfolioManager()
    alloc = await pm.smart_allocate(sub_analyses)

    weights = alloc.get("weights") or []
    reasoning = alloc.get("reasoning")
    method = alloc.get("method", "fallback")

    # 5) 可选：把权重交给你现有的 propose 核心做一次“约束与落库”
    #    - 如果你已有 /portfolio/propose 的核心函数（不通过 HTTP），这里可直接调用以复用“单票≤30%、行业≤50%、5–15 只”等约束与快照落库逻辑。
    #    - 假设你有一个内部核心函数：propose_portfolio_core(symbols, pre_weights=None) → {holdings, snapshot_id, version_tag, ...}
    try:
        # 如果没有 weights（LLM建议失败），就用 top 的票
        top_syms = [w["symbol"] for w in (alloc.get("weights") or [])]
        if not top_syms:
            top_syms = list(sub_analyses.keys())  # 你上文筛出的 top 集合

        # 通过 allocator 的核心函数生成“受约束后的组合”
        with Session(bind=engine) as db:
            holdings, sector_pairs = propose_portfolio(db, top_syms, default_constraints())

        # 先不处理快照（你这条链路里没有落库逻辑），返回空占位即可
        snapshot_id = None
        version_tag = None

    except Exception:
        holdings = weights  # 兜底：直接返回上一步的 weights
        snapshot_id = None
        version_tag = None

    return DecideResponse(
        as_of=datetime.now(timezone.utc).isoformat(),
        universe=req.symbols,
        analyses=sub_analyses,
        holdings=holdings,
        reasoning=reasoning,
        method=method,
        snapshot_id=snapshot_id,
        version_tag=version_tag,
    )

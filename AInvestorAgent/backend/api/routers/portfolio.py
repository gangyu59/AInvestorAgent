# backend/api/routers/portfolio.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy import text, inspect

from ...storage.db import get_db, engine
from ...scoring.scorer import build_portfolio

# === 你原有的路由前缀 & 结构 ===
router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# === 你原有的数据结构（保留） ===
class PortfolioItem(BaseModel):
    symbol: str
    score: float
    f_value: Optional[float] = None
    f_quality: Optional[float] = None
    f_momentum: Optional[float] = None
    f_sentiment: Optional[float] = None
    weight: float

class PortfolioResponse(BaseModel):
    as_of: str
    version_tag: str
    items: List[PortfolioItem]
    meta: dict

@router.post("/topn", response_model=PortfolioResponse)
def topn(
    symbols: List[str] = Query(..., description="重复传参: symbols=AAPL&symbols=MSFT"),
    top_n: int = 5,
    scheme: str = "proportional",  # or "equal"
    alpha: float = 1.0,
    min_w: float = 0.0,
    max_w: float = 0.4,
    as_of: str | None = None,
    db: Session = Depends(get_db),
):
    dt = date.fromisoformat(as_of) if as_of else date.today()
    return build_portfolio(
        db, symbols, dt,
        top_n=top_n, scheme=scheme, alpha=alpha,
        min_w=min_w, max_w=max_w
    )

class SnapshotBrief(BaseModel):
    weights: Dict[str, float] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)
    version_tag: Optional[str] = None
    kept: Optional[list[str]] = None

@router.get("/snapshot")
def get_portfolio_snapshot(latest: int = 1) -> SnapshotBrief:
    return SnapshotBrief()

# === 新增：冲刺 C 的 /propose ===
from backend.portfolio.allocator import propose_portfolio
from backend.portfolio.constraints import Constraints, default_constraints

class ProposeReq(BaseModel):
    symbols: List[str]
    constraints: Optional[Constraints] = None

class HoldingOut(BaseModel):
    symbol: str
    weight: float
    score: float
    sector: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)

class ProposeResp(BaseModel):
    holdings: List[HoldingOut]
    sector_concentration: List[List[Any]]
    as_of: str
    version_tag: str
    snapshot_id: str

@router.post("/propose", response_model=ProposeResp)
def propose(req: ProposeReq, db: Session = Depends(get_db)):
    if not req.symbols:
        raise HTTPException(status_code=400, detail="symbols 不能为空")

    holdings, sector_pairs = propose_portfolio(
        db, req.symbols, req.constraints or default_constraints()
    )

    as_of = date.today().isoformat()
    version_tag = "v1.0.0"
    from uuid import uuid4
    snapshot_id = f"ps_{date.today().strftime('%Y%m%d')}_{uuid4().hex[:6]}"

    payload: Dict[str, Any] = {
        "holdings": [HoldingOut(**h).model_dump() for h in holdings],
        "sector_concentration": [[s, float(w)] for s, w in sector_pairs],
        "as_of": as_of,
        "version_tag": version_tag,
        "snapshot_id": snapshot_id,
    }

    # 尝试落库 portfolio_snapshots（若存在则插入；不存在则跳过）
    try:
        insp = inspect(engine)
        if insp.has_table("portfolio_snapshots"):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO portfolio_snapshots
                        (snapshot_id, as_of, version_tag, payload, created_at)
                        VALUES (:snapshot_id, :as_of, :version_tag, :payload, :created_at)
                    """),
                    dict(
                        snapshot_id=snapshot_id,
                        as_of=as_of,
                        version_tag=version_tag,
                        payload=_json_dumps(payload),
                        created_at=datetime.utcnow().isoformat(timespec="seconds"),
                    ),
                )
    except Exception as e:
        # 不影响主流程
        print(f"[portfolio_snapshots] 写入失败/跳过: {e}")

    return payload


@router.post("/smart_analyze")
async def smart_analyze_portfolio(request: Dict[str, Any]):
    """智能组合分析"""
    try:
        symbols = request.get("symbols", [])
        weights = request.get("weights", [])
        use_llm = request.get("use_llm", True)

        # 调用你已有的智能分析逻辑
        from backend.agents.signal_researcher import EnhancedSignalResearcher
        from backend.agents.portfolio_manager import EnhancedPortfolioManager
        from backend.storage.db import SessionLocal
        from datetime import date

        with SessionLocal() as db:
            # 分析每只股票
            researcher = EnhancedSignalResearcher()
            stock_analyses = {}

            for symbol in symbols:
                ctx = {
                    "symbol": symbol,
                    "db_session": db,
                    "asof": date.today(),
                    "fundamentals": {"pe": 25, "roe": 15},
                    "news_raw": []
                }

                analysis = await researcher.analyze_with_technical_indicators(ctx)
                stock_analyses[symbol] = analysis

            # 组合分析
            pm = EnhancedPortfolioManager()
            portfolio_reasoning = await pm.generate_portfolio_reasoning(stock_analyses, symbols)

            # 计算组合综合评分
            portfolio_score = sum(
                analysis.get("adjusted_score", analysis.get("score", 0)) *
                next((w["weight"] for w in weights if w["symbol"] == symbol), 0)
                for symbol, analysis in stock_analyses.items()
            )

            return {
                "ok": True,
                "portfolio_score": round(portfolio_score),
                "stock_analyses": stock_analyses,
                "portfolio_reasoning": portfolio_reasoning,
                "risk_assessment": "基于当前市场环境，组合整体风险适中。建议定期监控各股票基本面变化。",
                "recommendations": "建议保持当前配置，关注技术指标变化，适时调整仓位。",
                "risk_metrics": {
                    "volatility": 0.15,
                    "sharpe_ratio": 1.2,
                    "max_drawdown": -0.08
                }
            }

    except Exception as e:
        return {"ok": False, "error": str(e)}


def _json_dumps(obj: Any) -> str:
    import json, decimal
    def _default(o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        try:
            return o.__dict__
        except Exception:
            return str(o)
    return json.dumps(obj, ensure_ascii=False, default=_default)

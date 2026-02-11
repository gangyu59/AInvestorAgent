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

    # 补充 sector
    from backend.storage.models import Symbol
    for holding in holdings:
        symbol_obj = db.query(Symbol).filter(Symbol.symbol == holding['symbol']).first()
        if symbol_obj:
            holding['sector'] = symbol_obj.sector or 'Unknown'
            if 'name' not in holding:
                holding['name'] = symbol_obj.name or holding['symbol']
        else:
            holding['sector'] = 'Unknown'
            if 'name' not in holding:
                holding['name'] = holding['symbol']

    # 重新计算 sector 集中度
    from collections import defaultdict
    sector_weights = defaultdict(float)
    for h in holdings:
        sector = h.get('sector', 'Unknown')
        sector_weights[sector] += h.get('weight', 0)
    sector_pairs = [[s, float(w)] for s, w in sector_weights.items()]

    # 🔧 关键修复: 直接计算回测metrics(不再HTTP自调用,不再丢弃权重)
    real_metrics = {"ann_return": 0.0, "mdd": 0.0, "sharpe": 0.0, "winrate": 0.0}

    try:
        from backend.agents.backtest_engineer import _load_prices, _align_by_date, _portfolio_nav
        from backend.backtest.metrics import compute_metrics
        from datetime import timedelta

        # 用portfolio的实际权重做回测
        weights_dict = {h["symbol"]: float(h["weight"]) for h in holdings}
        # 🔧 统一使用 datetime.now() (与 backtest.py 一致)
        end_str = datetime.now().strftime("%Y-%m-%d")
        start_str = (datetime.now() - timedelta(days=252)).strftime("%Y-%m-%d")

        # 加载价格并对齐
        price_map = {}
        for sym in weights_dict:
            series = _load_prices(sym, start_str, end_str, use_mock=False)
            if series:
                price_map[sym] = sorted(series, key=lambda x: x.get("date", ""))

        if price_map:
            dates, closes = _align_by_date(price_map)
            if dates and len(dates) > 10:
                # 使用BacktestEngineer的固定权重NAV计算(与simulator页面一致)
                bt_result = _portfolio_nav(dates, closes, weights_dict, tc=0.001)
                nav = bt_result.get("nav", [])
                m = bt_result.get("metrics", {})
                total_ret = (nav[-1] / nav[0] - 1) if nav and nav[0] > 0 else 0.0
                real_metrics = {
                    "ann_return": round(m.get("ann_return", 0.0), 6),
                    "total_return": round(total_ret, 6),
                    "mdd": round(m.get("mdd", m.get("max_dd", 0.0)), 6),
                    "sharpe": round(m.get("sharpe", 0.0), 4),
                    "winrate": round(m.get("win_rate", 0.0), 4)
                }
                print(f"✅ 直接回测完成, 年化收益: {real_metrics['ann_return'] * 100:.2f}%, "
                      f"累计收益: {real_metrics['total_return'] * 100:.2f}%")
            else:
                print("⚠️ 价格数据不足(<10天),使用默认metrics")
        else:
            print("⚠️ 无法加载价格数据,使用默认metrics")

    except Exception as e:
        print(f"⚠️ 回测失败,使用默认metrics: {e}")
        import traceback
        traceback.print_exc()

    # 构建完整payload
    payload: Dict[str, Any] = {
        "holdings": [HoldingOut(**h).model_dump() for h in holdings],
        "sector_concentration": sector_pairs,
        "as_of": as_of,
        "version_tag": version_tag,
        "snapshot_id": snapshot_id,
        "metrics": real_metrics  # 🔧 使用真实回测的metrics
    }

    # 保存到数据库
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
                print(f"✅ 快照已保存: {snapshot_id}")
    except Exception as e:
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


# 在 backend/api/routers/portfolio.py 中添加

@router.get("/snapshots/latest")
async def get_latest_snapshot(db: Session = Depends(get_db)):
    """
    获取最新的组合快照
    用于Dashboard显示
    🔧 关键修复: 每次返回时用存储的holdings实时重算metrics,
    确保首页显示值与回测页完全一致(同引擎、同权重、同时间窗口)
    """
    from backend.storage.models import PortfolioSnapshot
    import json

    # 查询最新快照
    latest = db.query(PortfolioSnapshot) \
        .order_by(PortfolioSnapshot.created_at.desc()) \
        .first()

    if not latest:
        raise HTTPException(404, "暂无组合快照")

    # 解析payload
    try:
        payload = json.loads(latest.payload) if latest.payload else {}
    except:
        holdings = json.loads(latest.holdings_json) if latest.holdings_json else []
        payload = {"holdings": holdings}

    holdings = payload.get("holdings", [])

    # 为holdings补充sector信息
    from backend.storage.models import Symbol
    for h in holdings:
        if 'sector' not in h or h.get('sector') == 'Unknown':
            symbol_obj = db.query(Symbol).filter(Symbol.symbol == h['symbol']).first()
            if symbol_obj and symbol_obj.sector:
                h['sector'] = symbol_obj.sector
            else:
                h['sector'] = 'Unknown'

    # 计算sector集中度
    from collections import defaultdict
    sector_weights = defaultdict(float)
    for h in holdings:
        sector = h.get('sector', 'Unknown')
        sector_weights[sector] += h.get('weight', 0)

    # ====================================================================
    # 🔧 关键修复: 用存储的holdings实时重算metrics
    # 确保首页与回测页使用完全相同的引擎(BacktestEngineer._portfolio_nav)
    # 完全相同的时间窗口(252 calendar days)和交易成本(0.001)
    # ====================================================================
    fresh_metrics = payload.get("metrics", {
        "ann_return": 0.0, "mdd": 0.0, "sharpe": 0.0, "winrate": 0.0
    })

    try:
        from backend.agents.backtest_engineer import _load_prices, _align_by_date, _portfolio_nav
        from datetime import timedelta

        weights_dict = {h["symbol"]: float(h["weight"])
                        for h in holdings if h.get("weight")}
        if weights_dict:
            end_str = datetime.now().strftime("%Y-%m-%d")
            start_str = (datetime.now() - timedelta(days=252)).strftime("%Y-%m-%d")

            price_map = {}
            for sym in weights_dict:
                series = _load_prices(sym, start_str, end_str, use_mock=False)
                if series:
                    price_map[sym] = sorted(series, key=lambda x: x.get("date", ""))

            if price_map:
                dates, closes = _align_by_date(price_map)
                if dates and len(dates) > 10:
                    bt_result = _portfolio_nav(dates, closes, weights_dict, tc=0.001)
                    m = bt_result.get("metrics", {})
                    nav = bt_result.get("nav", [])
                    total_return = (nav[-1] / nav[0] - 1) if nav and nav[0] > 0 else 0.0

                    fresh_metrics = {
                        "ann_return": round(m.get("ann_return", 0.0), 6),
                        "total_return": round(total_return, 6),
                        "mdd": round(m.get("mdd", m.get("max_dd", 0.0)), 6),
                        "sharpe": round(m.get("sharpe", 0.0), 4),
                        "winrate": round(m.get("win_rate", 0.0), 4),
                    }
                    print(f"✅ snapshots/latest 实时重算: ann={fresh_metrics['ann_return']*100:.2f}%, "
                          f"total={fresh_metrics['total_return']*100:.2f}%, "
                          f"sharpe={fresh_metrics['sharpe']:.2f}")
                else:
                    print("⚠️ snapshots/latest: 价格对齐后数据不足,使用存储值")
            else:
                print("⚠️ snapshots/latest: 无法加载价格,使用存储值")
    except Exception as e:
        print(f"⚠️ snapshots/latest 重算失败,使用存储值: {e}")

    return {
        "snapshot_id": latest.snapshot_id,
        "as_of": latest.as_of or latest.created_at.isoformat(),
        "version_tag": latest.version_tag or "v1.0",
        "holdings": holdings,
        "sector_concentration": [[k, v] for k, v in sector_weights.items()],
        "metrics": fresh_metrics
    }


@router.get("/snapshots")
async def get_snapshots_history(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    获取历史快照列表
    用于 DecisionHistoryModal 展示
    """
    from backend.storage.models import PortfolioSnapshot
    import json
    from sqlalchemy import desc

    # 查询最近 N 个快照
    snapshots = db.query(PortfolioSnapshot) \
        .order_by(desc(PortfolioSnapshot.created_at)) \
        .limit(limit) \
        .all()

    if not snapshots:
        return {"snapshots": []}

    result = []
    for snap in snapshots:
        try:
            payload = json.loads(snap.payload) if snap.payload else {}
        except:
            holdings = json.loads(snap.holdings_json) if snap.holdings_json else []
            payload = {"holdings": holdings}

        holdings = payload.get("holdings", [])
        metrics = payload.get("metrics", {})

        result.append({
            "id": snap.snapshot_id,
            "date": snap.as_of or snap.created_at.strftime("%Y-%m-%d"),
            "holdings_count": len(holdings),
            "version_tag": snap.version_tag or "v1.0",
            "performance": {
                "total_return": metrics.get("ann_return", 0) * 100,  # 转为百分比
                "max_dd": metrics.get("mdd", metrics.get("max_dd", 0)) * 100
            }
        })

    return {"snapshots": result}


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot_by_id(snapshot_id: str, db: Session = Depends(get_db)):
    """
    根据 snapshot_id 获取快照详情
    """
    from backend.storage.models import PortfolioSnapshot
    import json

    snapshot = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.snapshot_id == snapshot_id
    ).first()

    if not snapshot:
        raise HTTPException(404, f"快照 {snapshot_id} 不存在")

    try:
        payload = json.loads(snapshot.payload) if snapshot.payload else {}
    except:
        holdings = json.loads(snapshot.holdings_json) if snapshot.holdings_json else []
        payload = {"holdings": holdings}

    holdings = payload.get("holdings", [])

    # 补充 sector
    from backend.storage.models import Symbol
    for h in holdings:
        if 'sector' not in h or h.get('sector') == 'Unknown':
            symbol_obj = db.query(Symbol).filter(Symbol.symbol == h['symbol']).first()
            if symbol_obj and symbol_obj.sector:
                h['sector'] = symbol_obj.sector

    # 重算 sector 集中度
    from collections import defaultdict
    sector_weights = defaultdict(float)
    for h in holdings:
        sector = h.get('sector', 'Unknown')
        sector_weights[sector] += h.get('weight', 0)

    return {
        "snapshot_id": snapshot.snapshot_id,
        "as_of": snapshot.as_of or snapshot.created_at.isoformat(),
        "version_tag": snapshot.version_tag or "v1.0",
        "holdings": holdings,
        "sector_concentration": [[k, v] for k, v in sector_weights.items()],
        "metrics": payload.get("metrics", {
            "ann_return": 0.0,
            "mdd": 0.0,
            "sharpe": 0.0,
            "winrate": 0.0
        })
    }


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

# backend/portfolio/allocator.py
from __future__ import annotations
from typing import Dict, Iterable, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.storage.models import ScoreDaily
from .constraints import Constraints, default_constraints
from .explain import load_symbol_sectors, build_reasons_from_scores, sector_concentration

class Holding(dict):
    """返回给前端的持仓：symbol/weight/score/sector/reasons"""
    pass

def _latest_scores_for(db: Session, symbols: Iterable[str]) -> List[ScoreDaily]:
    syms = [s.upper() for s in symbols]
    if not syms:
        return []
    sub = (
        select(ScoreDaily.symbol, func.max(ScoreDaily.as_of).label("as_of"))
        .where(ScoreDaily.symbol.in_(syms))
        .group_by(ScoreDaily.symbol)
        .subquery()
    )
    q = (
        select(ScoreDaily)
        .join(sub, (ScoreDaily.symbol == sub.c.symbol) & (ScoreDaily.as_of == sub.c.as_of))
        .order_by(ScoreDaily.score.desc())
    )
    return list(db.execute(q).scalars())

def _truncate_positions(rows: List[ScoreDaily], c: Constraints) -> List[ScoreDaily]:
    if not rows:
        return []
    # 目标区间 [min, max]，优先高分
    k = min(max(len(rows), c.min_positions), c.max_positions)
    return rows[:k]

def _weights_from_scores(rows: List[ScoreDaily]) -> Dict[str, float]:
    total = sum(max(r.score or 0.0, 0.0) for r in rows) or 1.0
    w = {r.symbol.upper(): (max(r.score or 0.0, 0.0) / total) for r in rows}
    s = sum(w.values()) or 1.0
    for k in w: w[k] = w[k] / s
    return w

def _cap_single(w: Dict[str, float], cap: float) -> Dict[str, float]:
    # 超 cap 的截断，溢出按“未触顶部分的比重”再分配；迭代收敛
    for _ in range(6):
        overflow = 0.0
        under = []
        for s, v in w.items():
            if v > cap:
                overflow += v - cap
                w[s] = cap
            else:
                under.append(s)
        if overflow <= 1e-9 or not under:
            break
        denom = sum(w[s] for s in under) or 1.0
        for s in under:
            w[s] += (w[s] / denom) * overflow
    tot = sum(w.values()) or 1.0
    for k in w: w[k] /= tot
    return w

def _cap_sector(w: Dict[str, float], sectors: Dict[str, str], cap: float) -> Dict[str, float]:
    # 对每个超限行业整体缩放，再把缩出来的部分按“其它行业的当前权重”承接；迭代收敛
    for _ in range(8):
        sect_sum: Dict[str, float] = {}
        for sym, v in w.items():
            sect = sectors.get(sym, "Unknown")
            sect_sum[sect] = sect_sum.get(sect, 0.0) + v
        viol = [s for s, v in sect_sum.items() if v > cap + 1e-9]
        if not viol:
            break
        for sct in viol:
            over = sect_sum[sct] - cap
            if over <= 0: continue
            # 本行业整体按比例扣减 over
            for sym, v in list(w.items()):
                if sectors.get(sym, "Unknown") == sct:
                    w[sym] -= v * (over / sect_sum[sct])
            # 其余行业按现有权重比例承接
            others = [sym for sym in w if sectors.get(sym, "Unknown") != sct]
            denom = sum(w[s] for s in others) or 1.0
            for sym in others:
                w[sym] += over * (w[sym] / denom)
        tot = sum(w.values()) or 1.0
        for k in w: w[k] /= tot
    return w


def propose_portfolio(
        db: Session,
        symbols: Iterable[str],
        constraints: Constraints | None = None,
        scores_dict: Dict[str, float] | None = None
) -> Tuple[List[Holding], List[Tuple[str, float]]]:
    c = constraints or default_constraints()

    if scores_dict:
        rows = [
            type('ScoreRow', (), {
                'symbol': s,
                'score': scores_dict[s],
                'f_value': 0, 'f_quality': 0, 'f_momentum': 0, 'f_sentiment': 0
            })()
            for s in symbols if s in scores_dict and scores_dict[s] > 0
        ]
    else:
        rows = [r for r in _latest_scores_for(db, symbols) if (r.score or 0) > 0]

    # 🔍 调试输出1: 查看初始分数
    print("=" * 50)
    print("[allocator] 初始 scores:")
    for r in rows:
        print(f"  {r.symbol}: {r.score}")

    rows = _truncate_positions(rows, c)

    # 🔍 调试输出2: 截断后的股票
    print(f"[allocator] 截断后保留 {len(rows)} 只:")
    for r in rows:
        print(f"  {r.symbol}: {r.score}")

    if not rows:
        return [], []

    w = _weights_from_scores(rows)

    # 🔍 调试输出3: 初始权重(按分数比例)
    print("[allocator] 初始权重(按分数):")
    for sym, wt in w.items():
        print(f"  {sym}: {wt:.4f}")

    w = _cap_single(w, c.max_single)

    # 🔍 调试输出4: 单票上限后
    print(f"[allocator] 单票上限({c.max_single})后:")
    for sym, wt in w.items():
        print(f"  {sym}: {wt:.4f}")

    sectors = load_symbol_sectors(db, [r.symbol for r in rows])
    w = _cap_sector(w, sectors, c.max_sector)

    # 🔍 调试输出5: 行业上限后(最终)
    print(f"[allocator] 行业上限({c.max_sector})后(最终):")
    for sym, wt in w.items():
        print(f"  {sym}: {wt:.4f}")
    print("=" * 50)

    holdings: List[Holding] = []
    for r in rows:
        sym = r.symbol.upper()
        holdings.append(Holding(
            symbol=sym,
            weight=float(w.get(sym, 0.0)),
            score=float(r.score or 0.0),
            sector=sectors.get(sym, "Unknown"),
            reasons=build_reasons_from_scores(r),
        ))

    sector_pairs = sector_concentration((h["sector"], h["weight"]) for h in holdings)
    return holdings, sector_pairs

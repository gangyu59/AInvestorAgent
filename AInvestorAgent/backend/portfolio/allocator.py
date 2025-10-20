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
    """
    🔧 核心修复：持仓截断逻辑

    原代码bug: k = min(max(len(rows), c.min_positions), c.max_positions)
    问题：当rows=3, min=6时，会变成 min(max(3,6),10) = min(6,10) = 6
          然后 rows[:6] 会出错（只有3个元素）

    修复逻辑：
    1. 如果可用数量 <= max_positions: 全部使用
    2. 如果可用数量 > max_positions: 截断到max_positions
    3. 如果最终数量 < min_positions: 仅警告，不强制
    """
    if not rows:
        return []

    available = len(rows)

    # 实际使用数量：不超过max，能用多少用多少
    k = min(available, c.max_positions)

    # 如果少于min，仅记录警告
    if k < c.min_positions:
        print(f"⚠️  警告: 仅有 {k} 只符合条件的股票，少于最小要求 {c.min_positions} 只")

    print(f"[allocator] 从 {available} 只候选中选择 {k} 只")
    return rows[:k]


def _weights_from_scores(rows: List[ScoreDaily]) -> Dict[str, float]:
    total = sum(max(r.score or 0.0, 0.0) for r in rows) or 1.0
    w = {r.symbol.upper(): (max(r.score or 0.0, 0.0) / total) for r in rows}
    s = sum(w.values()) or 1.0
    for k in w: w[k] = w[k] / s
    return w


def _cap_single(w: Dict[str, float], cap: float) -> Dict[str, float]:
    """单票上限约束，迭代收敛"""
    for iteration in range(10):  # 增加迭代次数
        overflow = 0.0
        capped = []
        under = []

        for s, v in w.items():
            if v > cap + 1e-9:  # 加容差
                overflow += v - cap
                w[s] = cap
                capped.append(s)
            else:
                under.append(s)

        if not capped or not under:  # 没有需要调整的，或没有承接方
            break

        # 溢出部分按未触顶股票的权重比例重新分配
        denom = sum(w[s] for s in under)
        if denom > 1e-9:
            for s in under:
                w[s] += overflow * (w[s] / denom)

    # 最终归一化
    total = sum(w.values())
    if total > 1e-9:
        w = {k: v / total for k, v in w.items()}

    # 🔍 调试输出
    print(f"[_cap_single] 迭代{iteration + 1}次后，最大权重: {max(w.values()):.4f}")

    return w


def _cap_sector(w: Dict[str, float], sectors: Dict[str, str], cap: float, single_cap: float) -> Dict[str, float]:
    """行业上限约束，同时遵守单票上限"""
    if cap >= 1.0:
        return w

    for iteration in range(20):
        sector_weight: Dict[str, float] = {}
        for sym, weight in w.items():
            sect = sectors.get(sym, "Unknown")
            sector_weight[sect] = sector_weight.get(sect, 0.0) + weight

        violating = [s for s, wt in sector_weight.items() if wt > cap + 1e-9]
        if not violating:
            break

        for sect in violating:
            overflow = sector_weight[sect] - cap
            if overflow <= 1e-9:
                continue

            # 该行业内股票按比例缩减
            sect_stocks = [sym for sym in w if sectors.get(sym, "Unknown") == sect]
            sect_total = sum(w[s] for s in sect_stocks)

            if sect_total > 1e-9:
                for sym in sect_stocks:
                    reduction = w[sym] * (overflow / sect_total)
                    w[sym] -= reduction

            # 尝试分配溢出，但不能让接收方超过single_cap
            other_stocks = [sym for sym in w if sectors.get(sym, "Unknown") != sect]

            # 计算每只股票还能接收多少
            capacity = {}
            total_capacity = 0.0
            for sym in other_stocks:
                available = max(0, single_cap - w[sym] - 1e-9)
                capacity[sym] = available
                total_capacity += available

            if total_capacity > 1e-9:
                # 按剩余容量比例分配
                for sym in other_stocks:
                    if capacity[sym] > 0:
                        share = min(overflow * (capacity[sym] / total_capacity), capacity[sym])
                        w[sym] += share
            else:
                # 🔥 关键：如果无法分配溢出，说明单票约束和行业约束冲突
                # 此时优先满足单票约束，放弃行业约束
                print(f"    ⚠️  {sect}行业溢出{overflow:.4f}无法分配（单票限制冲突）")
                print(f"    → 保持当前分配，放弃行业{cap:.0%}约束")
                break  # 退出内层循环
        else:
            # 如果所有违规行业都处理完了，继续下一轮
            continue

        # 如果遇到冲突，退出外层循环
        break

    # 归一化
    total = sum(w.values())
    if total > 1e-9:
        w = {k: v / total for k, v in w.items()}

    # 最终验证
    final_sector = {}
    for sym, weight in w.items():
        sect = sectors.get(sym, "Unknown")
        final_sector[sect] = final_sector.get(sect, 0.0) + weight

    print(f"[_cap_sector] 最终行业分布: {final_sector}")

    # 检查单票是否超限（这是最重要的）
    max_single = max(w.values()) if w else 0
    if max_single > single_cap + 1e-6:
        print(f"❌ 错误: 单票权重{max_single:.4f} > 上限{single_cap}")
    else:
        print(f"✅ 单票约束满足: 最大权重{max_single:.4f}")

    return w


def propose_portfolio(
        db: Session,
        symbols: Iterable[str],
        constraints: Constraints | None = None,
        scores_dict: Dict[str, float] | None = None
) -> Tuple[List[Holding], List[Tuple[str, float]]]:
    """
    生成投资组合建议

    Args:
        db: 数据库会话
        symbols: 候选股票列表
        constraints: 约束条件（可选，默认使用 default_constraints）
        scores_dict: 直接提供评分字典（可选，用于测试）

    Returns:
        (holdings, sector_concentration)
        holdings: 持仓列表，每项包含 symbol/weight/score/sector/reasons
        sector_concentration: 行业集中度 [(sector_name, weight), ...]
    """
    c = constraints or default_constraints()

    # 1. 获取候选股票及评分
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

    print("=" * 50)
    print(f"[allocator] 候选股票: {len(rows)} 只")
    for r in rows[:5]:  # 只打印前5只
        print(f"  {r.symbol}: {r.score:.1f}")

    # 2. 根据约束截断持仓数量
    rows = _truncate_positions(rows, c)

    if not rows:
        print("[allocator] 无可用股票，返回空组合")
        return [], []

    # 3. 加载行业信息
    sectors = load_symbol_sectors(db, [r.symbol for r in rows])

    # 4. 计算初始权重（按评分比例）
    w = _weights_from_scores(rows)
    print(f"[allocator] 初始权重(按分数):")
    for sym in sorted(w.keys(), key=lambda s: w[s], reverse=True)[:3]:
        print(f"  {sym}: {w[sym]:.4f}")

    # 5. 应用单票上限约束
    w = _cap_single(w, c.max_single)
    print(f"[allocator] 单票上限({c.max_single})后:")
    max_weight = max(w.values())
    print(f"  最大权重: {max_weight:.4f}")

    # 6. 应用行业上限约束
    w = _cap_sector(w, sectors, c.max_sector, c.max_single)
    print(f"[allocator] 行业上限({c.max_sector})后(最终):")
    for sym in sorted(w.keys(), key=lambda s: w[s], reverse=True)[:3]:
        print(f"  {sym}: {w[sym]:.4f}")
    print("=" * 50)

    # 7. 构建返回结果
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

    # 8. 计算行业集中度
    sector_pairs = sector_concentration((h["sector"], h["weight"]) for h in holdings)

    return holdings, sector_pairs
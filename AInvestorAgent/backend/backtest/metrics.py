# backend/backtest/metrics.py
from __future__ import annotations
from typing import List, Dict
import math


def compute_drawdown(nav: List[float]) -> List[float]:
    """逐日回撤序列(负数向下)"""
    dd, peak = [], float("-inf")
    for v in nav or []:
        if v is None or not (v == v):  # NaN
            dd.append(0.0)
            continue
        peak = max(peak, v)
        dd.append((v / peak - 1.0) if peak > 0 else 0.0)
    return dd


def compute_metrics(nav: List[float], dates: List[str]) -> Dict[str, float]:
    """
    返回四项指标:
    ann_return, sharpe(252日频), max_dd(最小回撤), win_rate(日收益>0 比例)
    兼容你现有前端的 'mdd' 字段:同步给出 mdd=max_dd 的别名。

    🔧 修复: 正确计算年化收益率
    """
    if not nav or len(nav) < 2:
        return {
            "ann_return": 0.0,
            "sharpe": 0.0,
            "max_dd": 0.0,
            "win_rate": 0.0,
            "mdd": 0.0
        }

    # 日收益序列
    rets: List[float] = []
    for i in range(1, len(nav)):
        a, b = nav[i - 1], nav[i]
        if a and b and a > 0:
            rets.append(b / a - 1.0)

    if not rets:
        mdd = min(compute_drawdown(nav) or [0.0])
        return {
            "ann_return": 0.0,
            "sharpe": 0.0,
            "max_dd": float(mdd),
            "win_rate": 0.0,
            "mdd": float(mdd)
        }

    # 🔧 修复: 正确计算年化收益率
    total_return = nav[-1] / nav[0] if nav[0] > 0 else 1.0
    actual_days = len(rets)  # 实际交易天数
    years = actual_days / 252.0  # 实际年数

    # 复合年化收益率 = (总收益率) ^ (1/年数) - 1
    if years > 0 and total_return > 0:
        ann = (total_return ** (1.0 / years)) - 1.0
    else:
        ann = 0.0

    # Sharpe(日频年化)
    avg = sum(rets) / len(rets)
    var = sum((r - avg) ** 2 for r in rets) / max(len(rets) - 1, 1)
    std = math.sqrt(var)
    sharpe = (avg / std) * math.sqrt(252) if std > 0 else 0.0

    # 最大回撤 & 胜率
    max_dd = float(min(compute_drawdown(nav) or [0.0]))
    win = float(sum(1 for r in rets if r > 0) / len(rets)) if rets else 0.0

    return {
        "ann_return": float(ann),
        "sharpe": float(sharpe),
        "max_dd": max_dd,
        "win_rate": win,
        "mdd": max_dd,  # 兼容你当前前端使用的字段名
    }
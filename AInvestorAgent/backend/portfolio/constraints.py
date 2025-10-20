# backend/portfolio/constraints.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Constraints:
    max_single: float = 0.30      # 单票≤30%
    max_sector: float = 1.00      # 行业不限制！
    min_positions: int = 6
    max_positions: int = 10


def default_constraints() -> Constraints:
    """返回默认约束"""
    return Constraints()
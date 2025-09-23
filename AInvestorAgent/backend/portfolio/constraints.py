# backend/portfolio/constraints.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Constraints:
    max_single: float = 0.30      # 单票≤30%
    max_sector: float = 0.50      # 行业≤50%
    min_positions: int = 6        # 最少 6
    max_positions: int = 10       # 最多 10

def default_constraints() -> Constraints:
    return Constraints()

# backend/sim/paper.py
from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class SimState:
    cash: float = 1.0
    positions: Dict[str, float] = field(default_factory=dict)  # 权重视角（最小化）
    nav: float = 1.0

@dataclass
class SimConfig:
    tcost: float = 0.001

class PaperSim:
    def __init__(self, cfg: SimConfig | None = None):
        self.cfg = cfg or SimConfig()
        self.state = SimState()

    def step(self, orders: List[Dict[str, Any]], rel_returns: Dict[str, float]) -> Dict[str, Any]:
        # T+1 近似：先成交（按 weight_delta 即时到位），再按次日相对收益更新 NAV
        # 1) 交易成本
        turnover = sum(abs(o["weight_delta"]) for o in orders)
        self.state.cash -= turnover * self.cfg.tcost

        # 2) 调整权重
        for o in orders:
            sym = o["symbol"]; delta = float(o["weight_delta"])
            self.state.positions[sym] = round(float(self.state.positions.get(sym, 0.0)) + delta, 10)
            if abs(self.state.positions[sym]) < 1e-10:
                self.state.positions.pop(sym, None)

        # 3) 收益更新（权重 * 次日相对涨跌）
        ret = 0.0
        for sym, w in self.state.positions.items():
            r = float(rel_returns.get(sym, 0.0))
            ret += w * r
        self.state.nav *= (1.0 + ret)
        return {"nav": self.state.nav, "turnover": turnover, "positions": self.state.positions.copy()}

# backend/agents/portfolio_manager.py
from __future__ import annotations
from typing import Dict, Any, List
from .base_agent import BaseAgent

class PortfolioManager(BaseAgent):
    name = "portfolio_manager"

    def __init__(self, ctx: dict | None = None):
        super().__init__(ctx or {})

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        # 输入：candidates=[{symbol,sector,score}]
        cands: List[Dict[str, Any]] = ctx.get("candidates", [])
        if not cands:
            return {"ok": False, "error": "no candidates"}

        # 简单：按 score 归一得到初始权重
        scores = [max(0.0, float(c.get("score", 0.0))) for c in cands]
        s = sum(scores) or 1.0
        weights = [{"symbol": c["symbol"], "weight": (scores[i]/s)} for i, c in enumerate(cands)]
        explain = [{"symbol": c["symbol"], "reason": f"score={scores[i]:.1f}"} for i, c in enumerate(cands)]
        return {"ok": True, "data": {"proposal": weights, "explain": explain}}

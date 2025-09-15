# backend/agents/portfolio_manager.py
from __future__ import annotations
from typing import Dict, Any

class PortfolioManager:
    name = "portfolio_manager"

    def __init__(self, ctx: Any | None = None):
        if ctx is None:
            self._ctx = {}
        elif isinstance(ctx, dict):
            self._ctx = ctx
        else:
            # 兼容 AgentContext 或其他对象，直接存引用
            self._ctx = {"ctx": ctx}

    def act(self, scores: Dict[str, Dict[str, Any]], max_positions: int = 5) -> Dict[str, Any]:
        """
        从 scores 中挑选 topN 股票并分配等权重。
        """
        if not scores:
            return {"ok": False, "weights": []}

        # 按 score 排序
        ranked = sorted(scores.items(), key=lambda kv: kv[1].get("score", 0), reverse=True)
        top = ranked[:max_positions]

        n = len(top)
        if n == 0:
            return {"ok": False, "weights": []}

        w = 1.0 / n
        weights = [{"symbol": sym, "weight": w} for sym, _ in top]

        return {"ok": True, "weights": weights}

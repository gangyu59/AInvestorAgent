# -*- coding: utf-8 -*-
from typing import Any, Dict, List
from .base_agent import BaseAgent
import logging
logger = logging.getLogger(__name__)

class PortfolioManager(BaseAgent):
    """
    组合构建：按综合分数分配初始权重→约束修正→给出入选理由（TOP2 因子）。
    """
    name = "portfolio_manager"

    def act(self, scores: Dict[str, Dict[str, float]],  # {symbol: {score:..., value:..., quality:..., momentum:..., sentiment:...}}
            max_positions: int = 10, **_) -> Dict[str, Any]:
        logger.info("[portfolio] candidates=%d max_positions=%d", len(scores), max_positions)
        # 1) 取分数TopN
        ranked = sorted(scores.items(), key=lambda kv: kv[1].get("score", 0.0), reverse=True)[:max_positions]
        if not ranked:
            return {"ok": False, "reason": "no candidates"}
        # 2) 线性权重（按分数/合计）
        total = sum(s["score"] for _, s in ranked) or 1.0
        weights = {sym: s["score"]/total for sym, s in ranked}
        # 3) 入选理由（TOP2 因子）
        explains = {}
        for sym, s in ranked:
            parts = [(k, v) for k, v in s.items() if k in ("value","quality","momentum","sentiment")]
            top2 = sorted(parts, key=lambda kv: kv[1], reverse=True)[:2]
            explains[sym] = [k for k, _ in top2]
        return {"ok": True, "weights": weights, "explain": explains}

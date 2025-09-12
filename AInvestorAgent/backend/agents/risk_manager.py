# -*- coding: utf-8 -*-
from typing import Any, Dict
from .base_agent import BaseAgent
import logging
logger = logging.getLogger(__name__)

class RiskManager(BaseAgent):
    """风险控制：单票/行业/仓位上限校验及调整建议。"""
    name = "risk_manager"

    def act(self, weights: Dict[str, float], sector_map: Dict[str, str] | None = None,
            max_weight: float = 0.30, max_sector: float = 0.50, **_) -> Dict[str, Any]:
        # 最小启发式占位：截断超限并归一
        logger.info("[risk] max_weight=%.2f max_sector=%.2f", max_weight, max_sector)
        w = dict(weights)
        # TODO: 按行业集中度校正（需要 sector_map）
        total = sum(min(v, max_weight) for v in w.values()) or 1.0
        w_adj = {k: min(v, max_weight) / total for k, v in w.items()}
        return {"ok": True, "weights": w_adj, "notes": ["capped_single=%.0f%%" % (max_weight*100)]}

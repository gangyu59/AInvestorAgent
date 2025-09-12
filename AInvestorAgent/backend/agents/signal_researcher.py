# -*- coding: utf-8 -*-
from typing import Any, Dict
from .base_agent import BaseAgent
import logging
logger = logging.getLogger(__name__)

class SignalResearcher(BaseAgent):
    """
    信号研究：计算并评估候选信号（因子），输出标准化因子与简要评估。
    """
    name = "signal_researcher"

    def act(self, symbol: str, lookback: str = "1Y", **_) -> Dict[str, Any]:
        # TODO: 调用 factors/momentum.py / fundamentals.py / aggregator.py
        logger.info("[signal] symbol=%s lookback=%s", symbol, lookback)
        factors = {"value": 0.5, "quality": 0.6, "momentum": 0.55, "sentiment": 0.4}
        return {"ok": True, "symbol": symbol, "factors": factors, "lookback": lookback}

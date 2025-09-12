# -*- coding: utf-8 -*-
from typing import Any, Dict
from .base_agent import BaseAgent
import logging
logger = logging.getLogger(__name__)

class BacktestEngineer(BaseAgent):
    """轻量回测：周频≤3次调仓，输出净值/回撤/Sharpe 等。"""
    name = "backtest_engineer"

    def act(self, portfolio: Dict[str, float], window: str = "1Y", fee_bps: float = 10.0, **_) -> Dict[str, Any]:
        # TODO: 调用 backtest/engine.py 计算曲线与指标
        logger.info("[backtest] window=%s fee_bps=%s positions=%d", window, fee_bps, len(portfolio))
        return {
            "ok": True,
            "window": window,
            "metrics": {"annual": None, "sharpe": None, "maxdd": None, "winrate": None, "turnover": None},
            "equity": [],
        }

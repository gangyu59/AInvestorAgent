# backend/agents/signal_researcher.py
from __future__ import annotations
from typing import Dict, Any, List
import math
from .base_agent import BaseAgent

class SignalResearcher(BaseAgent):
    name = "signal_researcher"

    def __init__(self, ctx: AgentContext | Dict[str, Any] | None = None):
        self._ctx = dict(ctx or {})

    def act(self, **kwargs) -> Dict[str, Any]:
        # 允许最小化用法：SignalResearcher(ctx).act(symbol="AAPL")
        base = self.__dict__.get("_ctx", {})
        if not isinstance(base, dict):
            base = {}
        ctx = {**base, **kwargs}
        return self.run(ctx)

    def _ensure_prices(self, prices: Any | None) -> List[float]:
        if isinstance(prices, list) and prices:
            if isinstance(prices[0], dict) and "close" in prices[0]:
                return [float(p["close"]) for p in prices if "close" in p]
            if isinstance(prices[0], (int, float)):
                return [float(x) for x in prices]
        # 兜底：生成60根缓慢上行的 mock
        start, n = 100.0, 60
        out = [start]
        for i in range(1, n):
            out.append(out[-1] * (1.0 + 0.0005 * (1 + math.sin(i / 9.0))))
        return out

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        import math
        symbol = ctx.get("symbol", "AAPL")
        prices = ctx.get("prices")

        # 缺数据兜底：造一段轻微上行的 mock 序列
        if not prices:
            start, n = 100.0, 60
            prices = [start]
            for i in range(1, n):
                prices.append(prices[-1] * (1.0 + 0.0005 * (1 + math.sin(i / 9.0))))

        # 简单动量：近10期收益之和比例缩放后截断到 [0,1]
        rets = [0.0] + [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices))]
        momentum = max(0.0, min(1.0, 0.5 + 20.0 * sum(rets[-10:])))

        # 其它因子用上下文传入或给默认 0.5
        value = ctx.get("value", 0.5)
        quality = ctx.get("quality", 0.5)
        sentiment = ctx.get("sentiment", 0.5)

        factors = {
            "value": float(value) if value is not None else None,
            "quality": float(quality) if quality is not None else None,
            "momentum": float(momentum) if momentum is not None else None,
            "sentiment": float(sentiment) if sentiment is not None else None,
        }
        nums = [v for v in factors.values() if isinstance(v, (int, float))]
        score = round(sum(nums) / len(nums), 4) if nums else 0.0

        return {"ok": True, "data": {"symbol": symbol, "factors": factors, "score": score}}
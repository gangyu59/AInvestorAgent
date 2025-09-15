# backend/agents/signal_researcher.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import math

class SignalResearcher:
    name = "signal_researcher"

    def __init__(self, ctx: Any | None = None):
        # 兼容 AgentContext / dict / None
        if ctx is None:
            self._ctx = {}
        elif isinstance(ctx, dict):
            self._ctx = ctx
        else:
            self._ctx = {"ctx": ctx}

    # 便捷接口：与测试里的用法对齐：SignalResearcher(ctx).act(symbol="AAPL")
    def act(self, **kwargs) -> Dict[str, Any]:
        # 将 kwargs 合并进上下文再运行
        run_ctx = dict(self._ctx)
        run_ctx.update(kwargs or {})
        return self.run(run_ctx)

    def _extract_price_series(self, prices_any: Any) -> List[float]:
        """
        兼容两种价格格式：
        1) [100.0, 100.2, ...]  纯浮点序列
        2) [{"date":"YYYY-mm-dd","close":101.0}, ...] 字典序列（pipeline mock 就是这种）
        """
        if not prices_any:
            return []

        if isinstance(prices_any, list):
            if not prices_any:
                return []
            first = prices_any[0]
            # dict 序列
            if isinstance(first, dict):
                out = []
                for d in prices_any:
                    c = d.get("close")
                    try:
                        out.append(float(c))
                    except Exception:
                        # 跳过非法
                        continue
                return out
            # 纯数字序列
            else:
                out = []
                for v in prices_any:
                    try:
                        out.append(float(v))
                    except Exception:
                        continue
                return out
        # 其他类型，不支持
        return []

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        symbol = ctx.get("symbol", "AAPL")

        # --- 价格动量 ---
        prices_in = ctx.get("prices")
        prices = self._extract_price_series(prices_in)

        # 缺数据兜底：造一段轻微上行的 mock 序列（长度 60）
        if not prices:
            start, n = 100.0, 60
            prices = [start]
            for i in range(1, n):
                prices.append(prices[-1] * (1.0 + 0.0005 * (1 + math.sin(i / 9.0))))

        # 动量：近10期收益和，缩放+截断到 [0,1]
        if len(prices) < 2:
            momentum = 0.5
        else:
            rets = [0.0] + [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices))]
            k = 10
            tail = rets[-k:] if len(rets) >= k else rets
            raw = sum(tail)  # 典型量级 ~几 %
            # 缩放：假设 ±10% → 映射到 0..1
            momentum = 0.5 + raw / 0.20
            momentum = max(0.0, min(1.0, momentum))

        # --- 情绪（新闻） ---
        sent = 0.5
        news = ctx.get("news_raw") or []
        if isinstance(news, list):
            # 如果有“mock”参数，就给一个正向的稳定偏移；没有新闻也保持 0.5
            if ctx.get("mock"):
                # 有新闻越多略微提高，但有上限
                n = len(news)
                sent = max(0.0, min(1.0, 0.6 + min(n, 50) / 500.0))
            else:
                # 非 mock：保守使用 0.5
                sent = 0.5

        # --- 价值 & 质量（如无基本面，给中性 0.5） ---
        fundamentals = ctx.get("fundamentals") or {}
        pe = fundamentals.get("pe")
        roe = fundamentals.get("roe")

        if pe is None or pe <= 0:
            value = 0.5
        else:
            # PE 越低越“便宜”：简单反比缩放到 0..1
            value = 1.0 / (1.0 + min(float(pe), 100.0) / 20.0)
            value = max(0.0, min(1.0, value))

        if roe is None:
            quality = 0.5
        else:
            # ROE 越高越好：线性缩放并截断
            quality = max(0.0, min(1.0, float(roe) / 20.0))

        factors = {
            "value": float(value),
            "quality": float(quality),
            "momentum": float(momentum),
            "sentiment": float(sent),
        }

        # 综合分数（0..100）
        score = 100.0 * (0.25 * value + 0.25 * quality + 0.30 * momentum + 0.20 * sent)

        return {
            "ok": True,
            "symbol": symbol,
            "factors": factors,
            "score": round(score),
        }

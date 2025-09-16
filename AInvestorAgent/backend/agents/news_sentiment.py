# backend/agents/news_sentiment.py
from .base import BaseAgent, AgentContext, trace_push
import random

class NewsSentimentAgent(BaseAgent):
    NAME = "News/Sentiment"

    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        mock = kwargs.get("mock", False)
        try:
            if mock:
                # 稳健的中性偏正，避免把整体评分拉崩
                s = round(0.2 + random.random() * 0.6, 2)  # 0.20~0.80
                headlines = [f"{ctx.symbol} mock headline {i}" for i in range(1, 4)]
            else:
                feats = (ctx.meta or {}).get("news_features")
                if feats and "sentiment" in feats:
                    s = float(feats["sentiment"])
                    headlines = feats.get("top_headlines", [])[:3]
                else:
                    s, headlines = 0.50, []  # 缺数据→温和中性
            ctx.factors["sentiment"] = float(s)
            ctx.signals.setdefault("news", {})["top"] = headlines
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

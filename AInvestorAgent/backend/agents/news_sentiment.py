# backend/agents/news_sentiment.py
from backend.agents.base_agent import ResearchContext, trace_push  # 修正：从 base_agent 引入
import random

class NewsSentimentAgent:
    NAME = "News/Sentiment"
    def run(self, ctx: ResearchContext, **kwargs) -> ResearchContext:
        try:
            mock = bool(kwargs.get("mock", False))
            if mock:
                s = round(0.2 + random.random()*0.6, 2)  # 0.20~0.80
                headlines = [f"{ctx.symbol} mock headline {i}" for i in range(1,4)]
            else:
                feats = ctx.meta.get("news_features", {})
                s = float(feats.get("sentiment", 0.50))
                headlines = feats.get("top_headlines", [])[:3]
            ctx.factors["sentiment"] = float(s)
            ctx.signals.setdefault("news", {})["top"] = headlines
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

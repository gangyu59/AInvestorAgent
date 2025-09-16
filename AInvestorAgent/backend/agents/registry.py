# backend/agents/registry.py
from backend.agents.news_sentiment import NewsSentimentAgent
from backend.agents.macro import MacroAgent
from backend.agents.base_agent import trace_push  # 修正

class _Stub:
    def __init__(self, name, key=None, factor=None):
        self.NAME = name; self.key = key; self.factor = factor
    def run(self, ctx, **kwargs):
        # 仅在缺失时兜底，不覆盖已有因子
        if self.factor: ctx.factors.setdefault(self.factor, 0.50)
        trace_push(ctx, self.NAME, ok=True)
        return ctx

REGISTRY = {
    "news": NewsSentimentAgent(),
    "macro": MacroAgent(),
    "earnings": _Stub("Earnings", factor="quality"),
    "technical": _Stub("Technical", factor="momentum"),
    "value": _Stub("Value", factor="value"),
    "quant": _Stub("Quant"),
    "macro_strategy": _Stub("Macro Strategy"),
    "chair": _Stub("Chair"),
    "execution": _Stub("Execution")
}
ORDER = ["news","macro","earnings","technical","value","quant","macro_strategy","chair","execution"]

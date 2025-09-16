# backend/agents/macro.py
from backend.agents.base_agent import ResearchContext, trace_push

class MacroAgent:
    NAME = "Macro"
    def run(self, ctx: ResearchContext, **kwargs) -> ResearchContext:
        try:
            mock = bool(kwargs.get("mock", False))
            if mock:
                score, snap = 0.50, {"cpi_yoy":0.02,"gdp_yoy":0.025,"policy_rate":0.05}
            else:
                feats = ctx.meta.get("macro_features", {})
                score = float(feats.get("score", 0.50))
                snap = feats.get("snapshot", {})
            ctx.factors["macro"] = score
            ctx.signals["macro"] = snap
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

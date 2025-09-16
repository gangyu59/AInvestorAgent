# backend/agents/macro.py
from .base import BaseAgent, AgentContext, trace_push

class MacroAgent(BaseAgent):
    NAME = "Macro"

    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        mock = kwargs.get("mock", False)
        try:
            if mock:
                score, snap = 0.50, {"cpi_yoy": 0.02, "gdp_yoy": 0.025, "policy_rate": 0.05}
            else:
                feats = (ctx.meta or {}).get("macro_features")
                if feats and "score" in feats:
                    score = float(feats["score"])
                    snap = feats.get("snapshot", {})
                else:
                    score, snap = 0.50, {}
            ctx.factors["macro"] = score
            ctx.signals["macro"] = snap
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

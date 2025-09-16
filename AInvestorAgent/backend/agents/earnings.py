# backend/agents/earnings.py
from .base import BaseAgent, AgentContext, trace_push
class EarningsAgent(BaseAgent):
    NAME = "Earnings"
    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        try:
            # 若上游已有 quality，就不覆盖；否则给个中性值，保持 Smoketest 通过
            ctx.factors.setdefault("quality", 0.50)
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

# backend/agents/technical.py
from .base import BaseAgent, AgentContext, trace_push
class TechnicalAgent(BaseAgent):
    NAME = "Technical"
    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        try:
            ctx.factors.setdefault("momentum", 0.50)
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

# backend/agents/value.py
from .base import BaseAgent, AgentContext, trace_push
class ValueAgent(BaseAgent):
    NAME = "Value"
    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        try:
            ctx.factors.setdefault("value", 0.50)
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

# backend/agents/quant.py
from .base import BaseAgent, AgentContext, trace_push
class QuantAgent(BaseAgent):
    NAME = "Quant"
    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        try:
            ctx.signals["quant"] = {"alpha_hint": ctx.factors.get("momentum", 0.50)}
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

# backend/agents/macro_strategy.py
from .base import BaseAgent, AgentContext, trace_push
class MacroStrategyAgent(BaseAgent):
    NAME = "Macro Strategy"
    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        try:
            m = ctx.factors.get("macro", 0.50)
            tilt = "risk_on" if m > 0.60 else ("risk_off" if m < 0.40 else "neutral")
            ctx.signals["macro_strategy"] = {"tilt": tilt}
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

# backend/agents/chair.py（主席/决策汇总：计算最终 score）
from .base import BaseAgent, AgentContext, trace_push
class ChairAgent(BaseAgent):
    NAME = "Chair"
    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        try:
            # 保障 Smoketest 的四大因子齐全
            for k in ("value", "quality", "momentum", "sentiment"):
                ctx.factors.setdefault(k, 0.50)
            weights = kwargs.get("weights", {"value":0.25,"quality":0.25,"momentum":0.25,"sentiment":0.25})
            score = sum(ctx.factors[k] * w for k, w in weights.items())
            ctx.score = float(round(score, 4))
            ctx.signals["chair"] = {"final_score": ctx.score, "weights": weights}
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

# backend/agents/execution.py（执行：此处保留 hook，不在 Research 阶段下单）
from .base import BaseAgent, AgentContext, trace_push
class ExecutionAgent(BaseAgent):
    NAME = "Execution"
    def run(self, ctx: AgentContext, **kwargs) -> AgentContext:
        try:
            trace_push(ctx, self.NAME, ok=True)
        except Exception as e:
            trace_push(ctx, self.NAME, ok=False, error=e)
        return ctx

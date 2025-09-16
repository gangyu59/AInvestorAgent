# backend/agents/agent_layer.py
from backend.agents.registry import REGISTRY, ORDER
from backend.agents.base_agent import AgentContext

def run_agent_layer(ctx: AgentContext, params: dict | None = None) -> AgentContext:
    params = params or {}
    for key in ORDER:
        agent = REGISTRY.get(key)
        if agent:
            ctx = agent.run(ctx, **params)
    return ctx

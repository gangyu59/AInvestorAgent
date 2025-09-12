# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging
logger = logging.getLogger(__name__)

@dataclass
class AgentContext:
    """为各个智能体传递的最小上下文。后续可扩展（如版本号、限频信息等）。"""
    db_session: Any = None
    config: Dict[str, Any] = field(default_factory=dict)

class BaseAgent:
    """
    所有智能体的基类：约定统一的接口，便于 orchestrator 编排。
    """

    name: str = "base_agent"

    def __init__(self, context: Optional[AgentContext] = None):
        self.context = context or AgentContext()

    def plan(self, **kwargs) -> Dict[str, Any]:
        """规划阶段：读取需求、给出步骤或任务切分。"""
        logger.debug("[%s] plan kwargs=%s", self.name, kwargs)
        return {"ok": True, "plan": "noop"}

    def act(self, **kwargs) -> Dict[str, Any]:
        """执行阶段：完成具体动作，返回结构化结果。"""
        logger.debug("[%s] act kwargs=%s", self.name, kwargs)
        return {"ok": True, "result": None}

    def report(self, **kwargs) -> Dict[str, Any]:
        """汇报阶段：把结果转为可视化/可读摘要（Markdown/JSON）。"""
        logger.debug("[%s] report kwargs=%s", self.name, kwargs)
        return {"ok": True, "summary": "noop"}

    # 可选的统一入口：便于路由或 orchestrator 直接调用
    def run(self, **kwargs) -> Dict[str, Any]:
        p = self.plan(**kwargs)
        a = self.act(**(kwargs | {"plan": p}))
        r = self.report(**(kwargs | {"plan": p, "result": a}))
        return {"plan": p, "result": a, "report": r}

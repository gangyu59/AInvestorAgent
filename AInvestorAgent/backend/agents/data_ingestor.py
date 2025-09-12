# -*- coding: utf-8 -*-
from typing import Any, Dict
from .base_agent import BaseAgent, AgentContext
import logging
logger = logging.getLogger(__name__)

class DataIngestor(BaseAgent):
    """数据拉取与入库（prices、fundamentals、news 原始数据）。"""
    name = "data_ingestor"

    def act(self, symbols: list[str] | None = None, refresh: bool = False, **_) -> Dict[str, Any]:
        # TODO: 调用 backend/ingestion 下的具体 client & loaders
        logger.info("[ingestor] symbols=%s refresh=%s", symbols, refresh)
        return {"ok": True, "ingested": symbols or [], "refresh": refresh}

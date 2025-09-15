from __future__ import annotations
from typing import Any, Dict, List
from .base_agent import Agent, ok

class DataCleaner(Agent):
    name = "data_cleaner"
    desc = "基础清洗/对齐/去重"

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        prices = list(sorted(
            [p for p in ctx.get("prices", []) if p.get("close") is not None],
            key=lambda x: x.get("date","")
        ))
        news_raw = ctx.get("news_raw", [])
        seen = set(); news_dedup: List[Dict[str, Any]] = []
        for n in news_raw:
            k = (n.get("title",""), n.get("published_at",""))
            if k not in seen:
                seen.add(k); news_dedup.append(n)

        return ok(self.name, {"prices": prices, "news_raw": news_dedup,
                              "stats": {"price_points": len(prices), "news_count": len(news_dedup)}})

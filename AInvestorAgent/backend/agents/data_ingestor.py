from __future__ import annotations
from typing import Any, Dict, List
from .base_agent import Agent, ok, fail

class DataIngestor(Agent):
    name = "data_ingestor"
    desc = "拉取价格与新闻原始数据（可降级Mock）"

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        symbol: str = ctx["symbol"]
        days: int = int(ctx.get("news_days", 14))
        use_mock: bool = bool(ctx.get("mock", False))

        prices: List[Dict[str, Any]] = []
        news_items: List[Dict[str, Any]] = []

        if not use_mock:
            try:
                from ingestion.alpha_vantage_client import get_prices_for_symbol
                prices = get_prices_for_symbol(symbol, limit=240)
            except Exception as e:
                return fail(self.name, f"prices fetch failed: {e}", {"provider": "alpha_vantage"})
            try:
                from ingestion.news_api_client import fetch_latest_news
                news_items = fetch_latest_news(symbol, days=days)
            except Exception:
                news_items = []
        else:
            # —— Mock：保证“看得见”
            prices = [{"date": f"2025-01-{i+1:02d}", "close": 100 + i * 0.2} for i in range(120)]
            news_items = [
                {"title": f"{symbol} mock news {i}", "summary": "positive outlook",
                 "source": "mock", "published_at": f"2025-01-{(i%10)+1:02d}"} for i in range(20)
            ]

        return ok(self.name, {"symbol": symbol, "prices": prices, "news_raw": news_items},
                  {"provider": "alpha_vantage/newsapi" if not use_mock else "mock"})

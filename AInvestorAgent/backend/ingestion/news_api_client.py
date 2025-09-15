# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

class NewsApiClient:
    def fetch_news(self, symbol: str, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        # 简单桩实现（被测试替换）；默认生成若干 Mock 新闻
        now = datetime.now(timezone.utc)
        out: List[Dict[str, Any]] = []
        for i in range(min(limit, max(1, days))):
            dt = now - timedelta(days=i % max(1, days))
            out.append({
                "title": f"{symbol} mock #{i}",
                "summary": "mock",
                "url": f"http://mock/{symbol}/{i}",
                "source": "Mock",
                "published_at": dt.isoformat(),
            })
        return out

def fetch_news(symbol: str, days: int = 7, limit: int = 50) -> List[Dict]:
    """
    最小实现：返回空列表，测试会用 monkeypatch 注入假的返回。
    你后续再接入真实 API 即可。
    """
    return []

news_api_client = NewsApiClient()

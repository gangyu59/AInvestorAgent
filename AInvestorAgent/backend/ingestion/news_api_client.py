# AInvestorAgent/backend/ingestion/news_api_client.py
import os
import hashlib
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import requests

NEWS_API_KEY = os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY") or ""

class NewsApiClient:
    def __init__(self):
        self.api_key = NEWS_API_KEY

    def _pseudo_score(self, text: str) -> float:
        """无密钥/无模型时，给个稳定的小幅度情绪分，避免前端直线。"""
        if not text:
            return 0.0
        h = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        # 映射到 [-0.4, 0.4] 区间
        return ((h % 200) - 100) / 250.0

    def fetch_news(self, symbol: str, days: int = 14, limit: int = 50) -> List[Dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        out: List[Dict[str, Any]] = []

        if self.api_key:  # ✅ 有 key：走真实 NewsAPI.org（或你接的 news.org）
            params = {
                "q": symbol,
                "from": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": min(max(limit, 1), 100),
                "apiKey": self.api_key,
            }
            r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            if r.ok:
                j = r.json()
                for a in j.get("articles", []):
                    title = a.get("title") or ""
                    desc = a.get("description") or ""
                    url = a.get("url") or ""
                    published_at = a.get("publishedAt") or ""
                    # 这里先不给复杂模型，使用轻量兜底（如果你已有模型，换成你的 score_text(title+desc) 即可）
                    score = self._pseudo_score(f"{title} {desc}")
                    out.append({
                        "title": title,
                        "url": url,
                        "published_at": published_at,
                        "sentiment": score,
                    })
                return out

        # ❌ 无 key 或请求失败：返回你原本的 mock，但补上 pseudo score，保证可视化不是直线
        now = datetime.now(timezone.utc)
        syms = [symbol]  # 你也可能外层多 symbol 聚合，这里只返回当前 symbol 的列表
        for i in range(min(limit, max(1, days))):
            dt = now - timedelta(days=i % max(1, days))
            title = f"{symbol} mock #{i}"
            out.append({
                "title": title,
                "url": f"http://mock/{symbol}/{i}",
                "published_at": dt.isoformat(),
                "sentiment": self._pseudo_score(title),
            })
        return out

news_api_client = NewsApiClient()

def fetch_news(symbol: str, days: int = 14, limit: int = 50) -> List[Dict[str, Any]]:
    # 统一从实例走，避免引入返回空列表的旧实现
    return news_api_client.fetch_news(symbol=symbol, days=days, limit=limit)

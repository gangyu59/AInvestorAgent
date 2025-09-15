# backend/ingestion/__init__.py

from .news_api_client import fetch_news  # 供 tests 直接导函数
from . import news_api_client as news_client  # 供 tests monkeypatch: news_client.fetch_news

__all__ = ["fetch_news", "news_client", "news_api_client"]


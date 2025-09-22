# backend/api/schemas/sentiment.py
from __future__ import annotations
from pydantic import BaseModel
from typing import List

class SentimentPoint(BaseModel):
    date: str     # YYYY-MM-DD
    score: float  # 当日平均情绪（-1..1）

class NewsItem(BaseModel):
    title: str
    url: str
    score: float  # 该条新闻的情绪分（-1..1）

class SentimentBrief(BaseModel):
    series: List[SentimentPoint] = []
    latest_news: List[NewsItem] = []

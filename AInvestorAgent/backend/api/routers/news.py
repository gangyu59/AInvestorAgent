# AInvestorAgent/backend/api/routers/news.py
from fastapi import APIRouter, HTTPException, Query
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Any, List
from backend.ingestion.news_api_client import fetch_news as fetch_news_items

# 如已有模型，优先用你的；没有就用个轻量兜底
try:
    from backend.news_sentiment import score_text as _score_text
except Exception:
    def _score_text(text: str) -> float:
        return 0.0

router = APIRouter(prefix="/api/news", tags=["news"])

@router.post("/fetch")
def fetch(symbol: str = Query(..., min_length=1), days: int = 14, limit: int = 20) -> Dict[str, Any]:
    try:
        items = fetch_news_items(symbol=symbol, days=days, limit=limit) or []
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    out: List[Dict[str, Any]] = []
    for it in items[:limit]:
        title = it.get("title") or ""
        url = it.get("url") or it.get("link") or "#"
        published_at = it.get("published_at") or it.get("publishedAt") or it.get("date") or ""
        score = it.get("sentiment")
        if score is None:
            score = _score_text(title)  # 兜底
        out.append({"title": title, "url": url, "published_at": published_at, "score": float(score or 0.0)})
    return {"data": out}

@router.get("/series")
def series(symbol: str = Query(..., min_length=1), days: int = 14) -> Dict[str, Any]:
    try:
        items = fetch_news_items(symbol=symbol, days=days, limit=200) or []
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    bucket = defaultdict(list)
    for it in items:
        ts = it.get("published_at") or it.get("publishedAt") or it.get("date")
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
        day = dt.date().isoformat()

        s = it.get("sentiment")
        if s is None:
            s = _score_text((it.get("title") or "") + " " + (it.get("description") or ""))
        try:
            s = float(s)
        except Exception:
            s = 0.0
        bucket[day].append(s)

    timeline: List[Dict[str, Any]] = []
    for day, arr in sorted(bucket.items()):
        avg = sum(arr) / len(arr) if arr else 0.0
        timeline.append({
            "date": day,
            "sentiment": float(avg),
            "count_pos": int(sum(1 for x in arr if x >  0.05)),
            "count_neg": int(sum(1 for x in arr if x < -0.05)),
            "count_neu": int(sum(1 for x in arr if -0.05 <= x <= 0.05)),
            "count": len(arr),
        })
    if len(timeline) == 1:
        day = timeline[0]["date"]
        timeline.insert(0, {"date": day, "sentiment": 0.0, "count_pos":0, "count_neg":0, "count_neu":0, "count":0})

    return {"data": {"timeline": timeline}}

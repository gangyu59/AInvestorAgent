# 顶部导入建议（保持你原来的 import，不冲突即可）
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, List
from backend.ingestion import news_api_client as news_client  # 若你原来是 news_client 也可继续用

router = APIRouter(prefix="/api/news", tags=["news"])

@router.post("/fetch")
def fetch(
    symbol: str = Query(..., min_length=1),
    days: int = 14,
    limit: int = 30
) -> Dict[str, Any]:
    """
    返回最新新闻列表给前端渲染：
    { data: [ {title, url, published_at, score?}, ... ] }
    """
    try:
        items: List[Dict[str, Any]] = news_client.fetch_news(symbol, days=days, limit=limit) or []
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    out: List[Dict[str, Any]] = []
    for it in items[:limit]:
        title = it.get("title") or ""
        url = it.get("url") or it.get("link") or "#"
        published_at = it.get("published_at") or it.get("publishedAt") or it.get("date") or ""
        # 若上游没打情绪分，这里允许为 None；前端会容错
        score = it.get("sentiment")
        out.append({"title": title, "url": url, "published_at": published_at, "score": score})
    return {"data": out}


@router.get("/series")
def series(
    symbol: str = Query(..., min_length=1),
    days: int = 14
) -> Dict[str, Any]:
    """
    返回情绪时间轴给前端折线图：
    { data: { timeline: [{date, sentiment, count_pos, count_neg, count_neu, count}], } }
    """
    try:
        items: List[Dict[str, Any]] = news_client.fetch_news(symbol, days=days, limit=200) or []
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    bucket = defaultdict(list)
    for it in items:
        ts = it.get("published_at") or it.get("publishedAt") or it.get("date")
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        day = dt.date().isoformat()

        s = it.get("sentiment")
        try:
            score = float(s) if s is not None else 0.0
        except Exception:
            score = 0.0
        bucket[day].append(score)

    timeline: List[Dict[str, Any]] = []
    for day, arr in sorted(bucket.items()):
        if not arr:
            arr = [0.0]
        avg = sum(arr) / len(arr)
        timeline.append({
            "date": day,
            "sentiment": float(avg),
            "count_pos": int(sum(1 for x in arr if x >  0.05)),
            "count_neg": int(sum(1 for x in arr if x < -0.05)),
            "count_neu": int(sum(1 for x in arr if -0.05 <= x <= 0.05)),
            "count": len(arr),
        })

    # 仅一天数据时补一个占位点，保证图表轴好看
    if len(timeline) == 1:
        day = timeline[0]["date"]
        timeline.insert(0, {"date": day, "sentiment": 0.0, "count_pos":0, "count_neg":0, "count_neu":0, "count":0})

    return {"data": {"timeline": timeline}}

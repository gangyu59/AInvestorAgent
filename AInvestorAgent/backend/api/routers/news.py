# backend/api/routers/news.py
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

# ↓↓↓ 按你的项目实际路径修改导入 ↓↓↓
from backend.storage.db import get_db
from backend.ingestion.news_api_client import fetch_news as fetch_news_from_api

router = APIRouter(prefix="/api/news", tags=["news"])


def _score_text(text: str) -> float:
    """极简情绪分（仅用于本地 raw 回退时打一个稳定分）。"""
    text = (text or "").lower()
    pos = sum(w in text for w in ["beat", "surge", "gain", "strong", "upgrade", "buy"])
    neg = sum(w in text for w in ["miss", "drop", "loss", "weak", "downgrade", "sell"])
    return float(pos - neg)


def _fetch_local_news(db: Session, symbol: str, since: datetime, limit: int) -> List[Dict[str, Any]]:
    """只读本地数据：优先 news_scores，其次 news_raw（现场打分）"""
    rows = db.execute(
        """
        SELECT title, url, published_at, score
        FROM news_scores
        WHERE symbol = :symbol AND published_at >= :since
        ORDER BY published_at DESC
        LIMIT :limit
        """,
        {"symbol": symbol, "since": since.isoformat(), "limit": limit},
    ).fetchall()

    if rows:
        return [
            {
                "title": r.title,
                "url": r.url,
                "published_at": r.published_at,
                "score": float(r.score) if r.score is not None else 0.0,
            }
            for r in rows
        ]

    rows2 = db.execute(
        """
        SELECT title, url, published_at
        FROM news_raw
        WHERE symbol = :symbol AND published_at >= :since
        ORDER BY published_at DESC
        LIMIT :limit
        """,
        {"symbol": symbol, "since": since.isoformat(), "limit": limit},
    ).fetchall()

    return [
        {
            "title": r.title,
            "url": r.url,
            "published_at": r.published_at,
            "score": float(_score_text((r.title or "")[:200])),
        }
        for r in rows2
    ]


@router.post("/fetch")
def fetch(
    symbol: str = Query(..., min_length=1),
    days: int = Query(14, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    # 兼容你前端传参：auto=先外部失败回退本地；remote=只外部；local=只本地
    source: str = Query("auto"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    总是 200 返回：
    {
      "data": [ {title, url, published_at, score}, ... ],
      "source": "remote" | "local",
      "warning": "fallback_local: ... / no_local_news: ... / db_error: ..." (可选)
    }
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 只本地（不访问外网）
    if source == "local":
        try:
            items = _fetch_local_news(db, symbol, since, limit)
            resp: Dict[str, Any] = {"data": items, "source": "local"}
            if not items:
                resp["warning"] = f"no_local_news: {symbol} since {since.date()}"
            return resp
        except Exception as e:
            return {"data": [], "source": "local", "warning": f"db_error: {e}"}

    # remote/auto：优先外部，再回退本地
    try:
        remote_items = fetch_news_from_api(symbol=symbol, days=days, limit=limit) or []
        if remote_items:
            data: List[Dict[str, Any]] = []
            for it in remote_items[:limit]:
                title = it.get("title") or ""
                url = it.get("url") or it.get("link") or ""
                published_at = it.get("published_at") or it.get("publishedAt") or it.get("date") or ""
                score = it.get("sentiment") or it.get("score")
                if score is None:
                    score = _score_text(title)
                data.append(
                    {
                        "title": title,
                        "url": url,
                        "published_at": published_at,
                        "score": float(score or 0.0),
                    }
                )
            return {"data": data, "source": "remote"}
        # 外部返回空 → 视为失败，转回退流程
        raise RuntimeError("empty_remote")
    except Exception as e:
        try:
            local_items = _fetch_local_news(db, symbol, since, limit)
            resp: Dict[str, Any] = {"data": local_items, "source": "local"}
            warn = f"fallback_local: {type(e).__name__}"
            if not local_items:
                warn += f", no_local_news: {symbol} since {since.date()}"
            resp["warning"] = warn
            return resp
        except Exception as e2:
            return {"data": [], "source": "local", "warning": f"db_error: {e2}"}

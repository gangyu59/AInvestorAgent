from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from ...storage.db import get_db
from ...storage import models
from ...ingestion.news_api_client import fetch_news, sentiment_score
from ..schemas.news import NewsItem, DayPoint, NewsSeriesResponse

router = APIRouter(prefix="/api/news", tags=["news"])

@router.post("/fetch")
def fetch_and_store(symbol: str, days: int = 7, db: Session = Depends(get_db)):
    try:
        items = fetch_news(symbol, days=days, limit=50)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    upserted = 0
    for it in items:
        dt = datetime.fromisoformat(it["published_at"].replace("Z","+00:00"))
        obj = (db.query(models.NewsRaw)
                 .filter(models.NewsRaw.symbol==symbol, models.NewsRaw.url==it["url"])
                 .one_or_none())
        if obj:
            obj.title = it["title"] or obj.title
            obj.summary = it["summary"] or obj.summary
            obj.source = it["source"] or obj.source
            obj.published_at = dt or obj.published_at
            news = obj
        else:
            news = models.NewsRaw(symbol=symbol, title=it["title"], summary=it["summary"],
                                  url=it["url"], source=it["source"], published_at=dt)
            db.add(news); db.flush()
            
        exists_score = (db.query(models.NewsScore)
                        .filter(models.NewsScore.news_id == news.id)
                        .first())
        if not exists_score:
            s = sentiment_score(news.title or "", news.summary or "")
            db.add(models.NewsScore(news_id=news.id, sentiment=s))
        upserted += 1
    db.commit()
    return {"success": True, "symbol": symbol, "upserted": upserted}

@router.get("/series", response_model=NewsSeriesResponse)
def series(symbol: str, days: int = 7, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (db.query(models.NewsRaw, models.NewsScore)
              .join(models.NewsScore, models.NewsScore.news_id==models.NewsRaw.id)
              .filter(models.NewsRaw.symbol==symbol, models.NewsRaw.published_at>=since)
              .order_by(models.NewsRaw.published_at.asc())
              .all())

    items = [NewsItem(title=n.title, summary=n.summary, url=n.url, source=n.source,
                      published_at=n.published_at.astimezone(timezone.utc).isoformat())
             for (n, _) in rows]

    by_day = defaultdict(lambda: {"sum":0.0,"w":0.0,"pos":0,"neg":0,"neu":0})
    for n, s in rows:
        d = n.published_at.date().isoformat()
        w = 1.0
        by_day[d]["sum"] += s.sentiment*w
        by_day[d]["w"] += w
        if s.sentiment > 0.05: by_day[d]["pos"] += 1
        elif s.sentiment < -0.05: by_day[d]["neg"] += 1
        else: by_day[d]["neu"] += 1

    timeline = []
    for d in sorted(by_day.keys()):
        v = by_day[d]
        avg = (v["sum"]/v["w"]) if v["w"]>0 else 0.0
        timeline.append(DayPoint(date=d, sentiment=round(avg,3),
                                 count_pos=v["pos"], count_neg=v["neg"], count_neu=v["neu"]))
    return NewsSeriesResponse(symbol=symbol, days=days, timeline=timeline, items=items)

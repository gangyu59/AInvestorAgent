from datetime import date, timedelta
from sqlalchemy.orm import Session
from backend.storage import models

def avg_sentiment_7d(db: Session, symbol: str, asof: date, days: int = 7):
    since = asof - timedelta(days=days)
    q = (db.query(models.NewsRaw, models.NewsScore)
           .join(models.NewsScore, models.NewsScore.news_id == models.NewsRaw.id)
           .filter(models.NewsRaw.symbol == symbol,
                   models.NewsRaw.published_at >= since)
           .all())
    if not q:
        return None
    vals = [s.sentiment for (_, s) in q]
    # 映射 [-1,1] -> [0,1]
    mean = sum(vals)/len(vals)
    return 0.5 * (mean + 1.0)

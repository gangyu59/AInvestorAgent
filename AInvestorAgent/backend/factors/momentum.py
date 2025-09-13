from datetime import date, timedelta
from sqlalchemy.orm import Session
from backend.storage import models

def _last_close(db: Session, symbol: str, asof: date):
    q = (db.query(models.PriceDaily)
           .filter(models.PriceDaily.symbol == symbol,
                   models.PriceDaily.date <= asof)
           .order_by(models.PriceDaily.date.desc())
           .limit(1).all())
    return q[0].close if q else None

def momentum_return(db: Session, symbol: str, asof: date, lookback_days: int = 60):
    c_t = _last_close(db, symbol, asof)
    c_0 = _last_close(db, symbol, asof - timedelta(days=lookback_days))
    if c_t and c_0 and c_0 > 0:
        return (c_t / c_0) - 1.0
    return None

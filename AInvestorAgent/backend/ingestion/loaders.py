# backend/ingestion/loaders.py
from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from ..ingestion.alpha_vantage_client import AlphaVantageClient
from ..storage.models import PriceDaily, Symbol
from sqlalchemy.orm import Session
from .alpha_vantage_client import av_daily_raw, normalize_daily
from ..storage.dao import upsert_prices_daily



def load_daily_from_alpha(db: Session, symbol: str, adjusted: bool = True, outputsize: str = "compact") -> int:
    raw = av_daily_raw(symbol, adjusted=adjusted, outputsize=outputsize)
    rows = normalize_daily(raw, symbol)
    return upsert_prices_daily(db, rows)

def _parse_float(s: str | None) -> float | None:
    try:
        return float(s) if s not in (None, "", "None") else None
    except Exception:
        return None

def sync_prices_daily(symbol: str, session: Session) -> int:
    """从 AlphaVantage 同步日线到 SQLite。返回新增/更新的记录数。"""
    cli = AlphaVantageClient()
    raw = cli.daily_adjusted(symbol)
    series = raw.get("Time Series (Daily)") or raw.get("Time Series (Digital Currency Daily)")
    if not series:
        # 可能触发限流或symbol错误
        return 0

    # 确保 symbol 存在于 symbols 表
    if not session.scalars(select(Symbol).where(Symbol.symbol == symbol)).first():
        session.add(Symbol(symbol=symbol))

    upsert_count = 0
    for ds, row in series.items():
        d = datetime.strptime(ds, "%Y-%m-%d").date()
        stmt = insert(PriceDaily).values(
            symbol=symbol,
            date=d,
            open=_parse_float(row.get("1. open")),
            high=_parse_float(row.get("2. high")),
            low=_parse_float(row.get("3. low")),
            close=_parse_float(row.get("4. close")),
            volume=int(float(row.get("6. volume"))) if row.get("6. volume") else None
        )
        # SQLite UPSERT
        stmt = stmt.on_conflict_do_update(
            index_elements=[PriceDaily.symbol, PriceDaily.date],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            }
        )
        session.execute(stmt)
        upsert_count += 1

    session.commit()
    return upsert_count

def get_prices_range(symbol: str, range_key: str, session: Session) -> list[dict]:
    """返回指定区间的价格序列(按日期升序)。"""
    from sqlalchemy import text
    # 仅根据 range_key 做简单窗口
    days_map = {"1M": 22, "3M": 66, "1Y": 252}
    n = days_map.get(range_key.upper(), 66)

    # 取最近 n*1.5 天以保证足够数据
    q = text("""
        SELECT date, open, high, low, close, volume
        FROM prices_daily
        WHERE symbol = :symbol
        ORDER BY date DESC
        LIMIT :limit
    """)
    rows = session.execute(q, {"symbol": symbol, "limit": int(n * 1.5)}).all()
    rows = list(reversed(rows))  # 升序

    return [
        {
            "date": r[0].isoformat(),
            "open": r[1], "high": r[2], "low": r[3],
            "close": r[4], "volume": r[6]
        } for r in rows
    ]

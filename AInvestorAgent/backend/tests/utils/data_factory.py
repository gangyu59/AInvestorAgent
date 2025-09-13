# -*- coding: utf-8 -*-
import datetime as dt
from typing import Iterable, List
from backend.storage import models

def make_price_rows(symbol: str, dates: Iterable[dt.date], base: float = 100.0) -> List[models.PriceDaily]:
    rows = []
    i = 0
    for d in dates:
        close = base * (1.0 + 0.001 * i)
        rows.append(models.PriceDaily(
            symbol=symbol, date=d,
            open=close * 0.99, high=close * 1.01, low=close * 0.98, close=close,
            volume=1_000_000 + 500*i
        ))
        i += 1
    return rows

# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import date

class MetricsResp(BaseModel):
    symbol: str
    one_month_change: float
    three_months_change: float
    twelve_months_change: float
    volatility: float
    as_of: date

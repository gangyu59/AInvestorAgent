#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.db import SessionLocal
from backend.factors.sentiment import avg_sentiment_7d
from datetime import date

with SessionLocal() as db:
    for symbol in ['AAPL', 'MSFT', 'TSLA']:
        result = avg_sentiment_7d(db, symbol, date.today(), days=30)
        print(f"{symbol}: {result}")
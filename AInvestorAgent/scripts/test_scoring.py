# scripts/test_scoring.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.db import SessionLocal
from backend.scoring.scorer import compute_factors, aggregate_score
from datetime import date

with SessionLocal() as db:
    rows = compute_factors(db, ['AAPL'], date.today())
    if rows:
        r = rows[0]
        print(f"AAPL 因子:")
        print(f"  f_value: {r.f_value}")
        print(f"  f_quality: {r.f_quality}")
        print(f"  f_momentum: {r.f_momentum}")
        print(f"  f_sentiment: {r.f_sentiment}")

        score = aggregate_score(r)
        print(f"\n综合评分: {score}")
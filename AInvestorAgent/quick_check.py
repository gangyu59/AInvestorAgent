# quick_check.py
import sys
from pathlib import Path
from datetime import date

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.storage.db import SessionLocal
from backend.storage.models import ScoreDaily

db = SessionLocal()

# 检查今天的因子数据
today = date(2025, 10, 18)
symbols = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL']

print("\n" + "=" * 60)
print(f"📊 检查 {today} 的因子数据")
print("=" * 60)

for symbol in symbols:
    score = db.query(ScoreDaily).filter(
        ScoreDaily.symbol == symbol,
        ScoreDaily.as_of == today
    ).first()

    if score:
        print(f"✅ {symbol}: score={score.score:.1f}, "
              f"momentum={score.f_momentum:.3f}, "
              f"sentiment={score.f_sentiment:.3f}")
    else:
        print(f"❌ {symbol}: 数据库中无因子数据")

db.close()
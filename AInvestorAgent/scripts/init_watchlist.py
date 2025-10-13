#!/usr/bin/env python3
"""初始化watchlist表和默认数据"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.db import engine, SessionLocal
from backend.storage.models import Base, Watchlist


def init_watchlist():
    print("🔧 初始化Watchlist...")

    # 创建表
    Base.metadata.create_all(bind=engine, tables=[Watchlist.__table__])
    print("✅ 表已创建")

    # 添加默认股票
    db = SessionLocal()
    try:
        if db.query(Watchlist).count() == 0:
            defaults = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META", "SPY"]
            for symbol in defaults:
                db.add(Watchlist(symbol=symbol))
            db.commit()
            print(f"✅ 已添加 {len(defaults)} 支默认股票")
            print(f"   {', '.join(defaults)}")
        else:
            count = db.query(Watchlist).count()
            print(f"ℹ️  已有 {count} 支股票")
    finally:
        db.close()

    print("\n✅ 完成! 访问 http://localhost:8000/api/watchlist")


if __name__ == "__main__":
    init_watchlist()
#!/usr/bin/env python3
"""
填充symbols表的sector信息
从symbols.py的COMMON_STOCKS导入
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.db import SessionLocal
from backend.storage.models import Symbol

# 从symbols.py导入股票信息
STOCK_INFO = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology", "exchange": "NASDAQ"},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer", "exchange": "NASDAQ"},
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology", "exchange": "NASDAQ"},
    "META": {"name": "Meta Platforms Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Automotive", "exchange": "NASDAQ"},
    "AVGO": {"name": "Broadcom Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    "ORCL": {"name": "Oracle Corporation", "sector": "Technology", "exchange": "NYSE"},
    "AMD": {"name": "Advanced Micro Devices Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    "COST": {"name": "Costco Wholesale Corp.", "sector": "Consumer", "exchange": "NASDAQ"},
    "LLY": {"name": "Eli Lilly and Company", "sector": "Healthcare", "exchange": "NYSE"},
    "INTC": {"name": "Intel Corporation", "sector": "Technology", "exchange": "NASDAQ"},
    "NFLX": {"name": "Netflix Inc.", "sector": "Media", "exchange": "NASDAQ"},
    "DIS": {"name": "The Walt Disney Company", "sector": "Media", "exchange": "NYSE"},
    "APP": {"name": "AppLovin Corporation", "sector": "Technology", "exchange": "NASDAQ"},
}


def populate_symbols():
    """填充或更新symbols表"""
    print("🔧 开始填充symbols表...")

    db = SessionLocal()
    try:
        updated = 0
        created = 0

        for symbol, info in STOCK_INFO.items():
            # 查找或创建
            obj = db.query(Symbol).filter(Symbol.symbol == symbol).first()

            if obj:
                # 更新
                obj.name = info.get('name')
                obj.sector = info.get('sector')
                obj.exchange = info.get('exchange')
                updated += 1
            else:
                # 创建
                obj = Symbol(
                    symbol=symbol,
                    name=info.get('name'),
                    sector=info.get('sector'),
                    exchange=info.get('exchange')
                )
                db.add(obj)
                created += 1

        db.commit()

        print(f"✅ 完成! 创建 {created} 个, 更新 {updated} 个")

        # 显示当前所有symbol
        all_symbols = db.query(Symbol).all()
        print(f"\n📊 当前symbols表共有 {len(all_symbols)} 条记录:")
        for s in all_symbols[:10]:  # 只显示前10个
            print(f"  • {s.symbol}: {s.name} ({s.sector or '未知'})")

        if len(all_symbols) > 10:
            print(f"  ... 还有 {len(all_symbols) - 10} 个")

    finally:
        db.close()


if __name__ == "__main__":
    populate_symbols()
#!/usr/bin/env python3
"""快速检查数据库内容"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text


def get_db_url():
    """获取数据库URL"""
    try:
        from backend.core.config import get_settings
        settings = get_settings()
        db_url = settings.DB_URL

        # 如果没有设置，使用默认值
        if not db_url:
            db_url = "sqlite:///./db/stock.sqlite"
            print(f"⚠️ DB_URL未设置，使用默认: {db_url}")

        return db_url
    except Exception as e:
        print(f"❌ 无法加载配置: {e}")
        # 使用硬编码默认值
        return "sqlite:///./db/stock.sqlite"


def check_data():
    print("=" * 60)
    print("📊 数据库内容检查")
    print("=" * 60)

    db_url = get_db_url()
    print(f"\n🔗 数据库: {db_url}\n")

    try:
        engine = create_engine(db_url)
    except Exception as e:
        print(f"❌ 无法连接数据库: {e}")
        return

    # 1. 检查价格数据
    print("\n1️⃣ 价格数据 (prices_daily):")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, COUNT(*) as days, MIN(date) as first_date, MAX(date) as last_date 
                FROM prices_daily 
                GROUP BY symbol
                ORDER BY symbol
            """))
            rows = result.fetchall()

            if len(rows) == 0:
                print("  ❌ 没有价格数据！")
                print("  💡 需要运行: python scripts/fetch_prices.py --symbols AAPL,MSFT,TSLA,NVDA,GOOGL --range 1Y")
            else:
                print(f"  ✅ 找到 {len(rows)} 支股票的价格数据:")
                for row in rows:
                    print(f"    {row[0]}: {row[1]} 天 ({row[2]} 到 {row[3]})")
    except Exception as e:
        print(f"  ⚠️ 表可能不存在或查询失败: {e}")

    # 2. 检查新闻数据
    print("\n2️⃣ 新闻数据 (news_raw):")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, COUNT(*) as count 
                FROM news_raw 
                GROUP BY symbol
                ORDER BY symbol
            """))
            rows = result.fetchall()

            if len(rows) == 0:
                print("  ⚠️ 没有新闻数据")
                print("  💡 需要运行: python scripts/fetch_news.py --symbols AAPL,MSFT,TSLA --days 14 --noproxy")
            else:
                print(f"  ✅ 找到 {len(rows)} 支股票的新闻:")
                for row in rows:
                    print(f"    {row[0]}: {row[1]} 条新闻")
    except Exception as e:
        print(f"  ⚠️ 表可能不存在: {e}")

    # 3. 检查基本面数据
    print("\n3️⃣ 基本面数据 (fundamentals):")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, pe, pb, roe, market_cap 
                FROM fundamentals 
                ORDER BY symbol
            """))
            rows = result.fetchall()

            if len(rows) == 0:
                print("  ⚠️ 没有基本面数据")
                print("  💡 需要运行: python scripts/fetch_fundamentals.py --symbols AAPL,MSFT")
            else:
                print(f"  ✅ 找到 {len(rows)} 支股票的基本面:")
                for row in rows:
                    print(f"    {row[0]}: PE={row[1]}, PB={row[2]}, ROE={row[3]}, 市值={row[4]}")
    except Exception as e:
        print(f"  ⚠️ 表可能不存在: {e}")

    # 4. 检查因子数据
    print("\n4️⃣ 因子数据 (factors_daily):")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, COUNT(*) as count, MAX(date) as last_date
                FROM factors_daily 
                GROUP BY symbol
                ORDER BY symbol
            """))
            rows = result.fetchall()

            if len(rows) == 0:
                print("  ℹ️ 没有因子数据（会在生成组合时自动计算）")
            else:
                print(f"  ✅ 找到 {len(rows)} 支股票的因子:")
                for row in rows:
                    print(f"    {row[0]}: {row[1]} 条 (最新: {row[2]})")
    except Exception as e:
        print(f"  ℹ️ 表可能不存在（正常）: {e}")

    # 5. 检查评分数据
    print("\n5️⃣ 评分数据 (scores_daily):")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, score, date, version_tag
                FROM scores_daily 
                ORDER BY date DESC, symbol
                LIMIT 10
            """))
            rows = result.fetchall()

            if len(rows) == 0:
                print("  ℹ️ 没有评分数据（会在生成组合时自动计算）")
            else:
                print(f"  ✅ 最新评分（前10条）:")
                for row in rows:
                    print(f"    {row[0]}: {row[1]:.2f} ({row[2]}, {row[3]})")
    except Exception as e:
        print(f"  ℹ️ 表可能不存在: {e}")

    # 6. 检查组合快照
    print("\n6️⃣ 组合快照 (portfolio_snapshots):")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT snapshot_id, date, holdings
                FROM portfolio_snapshots 
                ORDER BY date DESC
                LIMIT 3
            """))
            rows = result.fetchall()

            if len(rows) == 0:
                print("  ℹ️ 还没有组合快照（这就是为什么holdings是空的）")
            else:
                print(f"  ✅ 最新快照（前3个）:")
                import json
                for row in rows:
                    holdings = json.loads(row[2]) if row[2] else []
                    print(f"    {row[0]} ({row[1]}): {len(holdings)} 只持仓")
                    if holdings:
                        for h in holdings[:3]:
                            print(f"      - {h.get('symbol')}: {h.get('weight', 0):.2%}")
    except Exception as e:
        print(f"  ℹ️ 表可能不存在: {e}")

    # 7. 列出所有表
    print("\n7️⃣ 数据库中的所有表:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """))
            tables = [row[0] for row in result.fetchall()]

            if tables:
                print(f"  ✅ 找到 {len(tables)} 个表:")
                for table in tables:
                    print(f"    - {table}")
            else:
                print("  ⚠️ 数据库是空的！")
    except Exception as e:
        print(f"  ❌ 无法列出表: {e}")

    print("\n" + "=" * 60)
    print("检查完成！")
    print("=" * 60)


if __name__ == "__main__":
    check_data()
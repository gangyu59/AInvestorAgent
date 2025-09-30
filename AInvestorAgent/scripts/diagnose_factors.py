#!/usr/bin/env python3
"""
诊断因子数据质量
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.db import SessionLocal
from backend.factors.momentum import momentum_return, get_price_series
from backend.factors.sentiment import avg_sentiment_7d
from datetime import date, timedelta


def diagnose_data_quality():
    print("\n=== 数据质量诊断 ===\n")

    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    asof = date.today()

    with SessionLocal() as db:
        for symbol in test_symbols:
            print(f"\n{symbol}:")

            # 1. 检查价格数据
            df = get_price_series(db, symbol, asof, 252)
            print(f"  价格数据点数: {len(df)}")

            if len(df) > 0:
                date_range = (df['date'].min(), df['date'].max())
                print(f"  数据范围: {date_range[0]} 到 {date_range[1]}")

                # 2. 检查动量因子
                mom_1m = momentum_return(db, symbol, asof, 20)
                mom_3m = momentum_return(db, symbol, asof, 60)
                print(f"  动量1M: {mom_1m:.4f}" if mom_1m else "  动量1M: None")
                print(f"  动量3M: {mom_3m:.4f}" if mom_3m else "  动量3M: None")

                # 3. 检查情绪数据
                sentiment = avg_sentiment_7d(db, symbol, asof, 7)
                print(f"  情绪得分: {sentiment:.4f}" if sentiment is not None else "  情绪得分: None (无新闻数据)")

                # 4. 检查数据连续性
                dates = df['date'].tolist()
                if len(dates) >= 2:
                    gaps = []
                    for i in range(1, len(dates)):
                        delta = (dates[i] - dates[i - 1]).days
                        if delta > 5:  # 超过5天的空档
                            gaps.append((dates[i - 1], dates[i], delta))

                    if gaps:
                        print(f"  ⚠️ 发现 {len(gaps)} 个数据空档")
                        for gap in gaps[:3]:  # 只显示前3个
                            print(f"    {gap[0]} -> {gap[1]} ({gap[2]}天)")
                    else:
                        print(f"  ✓ 数据连续性良好")
            else:
                print("  ❌ 无价格数据！")

        # 检查新闻数据总量
        from backend.storage.models import NewsRaw
        news_count = db.query(NewsRaw).count()
        print(f"\n总新闻数量: {news_count}")

        if news_count > 0:
            # 按股票统计
            print("\n各股票新闻数量:")
            for symbol in test_symbols:
                count = db.query(NewsRaw).filter(NewsRaw.symbol == symbol).count()
                print(f"  {symbol}: {count} 条")


def check_ic_calculation():
    print("\n\n=== IC计算诊断 ===\n")

    test_symbols = ['AAPL', 'MSFT']
    asof = date.today()

    with SessionLocal() as db:
        print("检查未来收益计算...")
        for symbol in test_symbols:
            current_date = asof - timedelta(days=60)
            future_date = asof - timedelta(days=30)

            # 获取价格
            df_current = get_price_series(db, symbol, current_date, 1)
            df_future = get_price_series(db, symbol, future_date, 1)

            if len(df_current) > 0 and len(df_future) > 0:
                current_price = df_current.iloc[-1]['close']
                future_price = df_future.iloc[-1]['close']
                future_return = (future_price / current_price) - 1.0

                print(f"\n{symbol}:")
                print(f"  {current_date}: ${current_price:.2f}")
                print(f"  {future_date}: ${future_price:.2f}")
                print(f"  未来收益: {future_return:.2%}")
            else:
                print(f"\n{symbol}: 数据不足")


def suggest_fixes():
    print("\n\n=== 修复建议 ===\n")

    print("如果IC为0，可能需要：")
    print("\n1. 增加历史数据")
    print("   python scripts/fetch_prices.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA --range 3Y")
    print("\n2. 增加新闻数据")
    print("   python scripts/fetch_news.py --symbols AAPL,MSFT,GOOGL,TSLA --days 90 --noproxy")
    print("\n3. 等待数据积累")
    print("   - IC分析需要至少3-6个月的滚动数据")
    print("   - 每月更新后IC值才会逐步显现")
    print("\n4. 当前可以开始测试")
    print("   - 即使IC为0，基础功能（组合构建、回测、风险管理）都已就绪")
    print("   - IC验证是长期监控工具，不影响立即使用系统")


if __name__ == "__main__":
    diagnose_data_quality()
    check_ic_calculation()
    suggest_fixes()
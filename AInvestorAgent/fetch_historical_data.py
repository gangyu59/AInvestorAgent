#!/usr/bin/env python3
"""
拉取历史数据 - 用于回测
这是一个独立脚本，不影响现有的 fetch_prices.py

用法:
  python fetch_historical_data.py
  python fetch_historical_data.py --symbols GOOGL,AVGO,META
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import argparse
from backend.storage.db import SessionLocal, engine
from backend.storage.models import Base
from backend.ingestion.loaders import load_daily_from_alpha
from backend.ingestion.alpha_vantage_client import AlphaVantageError


def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def check_existing_data(db, symbol: str) -> int:
    """检查已有数据点数量"""
    from backend.storage.models import PriceDaily
    count = db.query(PriceDaily).filter(
        PriceDaily.symbol == symbol
    ).count()
    return count


def fetch_full_history(symbols: list):
    """拉取完整历史数据 (outputsize=full)"""

    print_header("拉取历史数据 (完整模式)")

    print(f"股票列表: {', '.join(symbols)}")
    print(f"拉取模式: FULL (最大数据量)")
    print(f"预计时间: {len(symbols) * 15} 秒 (每只股票约15秒)")
    print("=" * 80)

    # 确保表存在
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    results = {
        "success": [],
        "failed": [],
        "stats": {}
    }

    try:
        for i, sym in enumerate(symbols, 1):
            sym = sym.strip().upper()

            print(f"\n[{i}/{len(symbols)}] 处理 {sym}")
            print("-" * 40)

            # 检查现有数据
            existing = check_existing_data(db, sym)
            print(f"  现有数据: {existing} 条")

            try:
                # 先尝试 ADJUSTED (outputsize=full)
                print(f"  尝试: TIME_SERIES_DAILY_ADJUSTED (FULL)")
                n = load_daily_from_alpha(
                    db,
                    sym,
                    adjusted=True,
                    outputsize="full"  # 关键：使用 full 模式
                )
                print(f"  ✅ 成功: {n} 条记录 (adjusted)")

                results["success"].append(sym)
                results["stats"][sym] = {
                    "before": existing,
                    "inserted": n,
                    "after": check_existing_data(db, sym),
                    "mode": "adjusted"
                }

            except AlphaVantageError as e:
                error_msg = str(e)

                # 如果 ADJUSTED 不可用，降级到 DAILY
                if "TIME_SERIES_DAILY_ADJUSTED" in error_msg or "Invalid API call" in error_msg:
                    print(f"  ⚠️  ADJUSTED 不可用，降级到 DAILY")
                    try:
                        n = load_daily_from_alpha(
                            db,
                            sym,
                            adjusted=False,
                            outputsize="full"
                        )
                        print(f"  ✅ 成功: {n} 条记录 (daily)")

                        results["success"].append(sym)
                        results["stats"][sym] = {
                            "before": existing,
                            "inserted": n,
                            "after": check_existing_data(db, sym),
                            "mode": "daily"
                        }
                    except Exception as e2:
                        print(f"  ❌ DAILY 也失败: {e2}")
                        results["failed"].append((sym, str(e2)))
                else:
                    print(f"  ❌ 错误: {e}")
                    results["failed"].append((sym, error_msg))

            except Exception as e:
                print(f"  ❌ 意外错误: {e}")
                results["failed"].append((sym, str(e)))

            # 提交当前股票的数据
            db.commit()

            # 限速：避免触发 API 限制 (5 calls/min)
            if i < len(symbols):
                print(f"  等待 15 秒...")
                time.sleep(15)

    except Exception as e:
        db.rollback()
        print(f"\n❌ 全局错误: {e}")
        raise
    finally:
        db.close()

    # 打印总结
    print_header("拉取总结")

    print(f"成功: {len(results['success'])}/{len(symbols)}")
    print(f"失败: {len(results['failed'])}/{len(symbols)}")

    if results["success"]:
        print(f"\n✅ 成功的股票:")
        for sym in results["success"]:
            stats = results["stats"][sym]
            print(
                f"  {sym:6s}  前: {stats['before']:4d}  新增: {stats['inserted']:4d}  后: {stats['after']:4d}  模式: {stats['mode']}")

    if results["failed"]:
        print(f"\n❌ 失败的股票:")
        for sym, error in results["failed"]:
            print(f"  {sym:6s}  {error}")

    print("\n" + "=" * 80 + "\n")

    return results


def verify_data_coverage():
    """验证数据覆盖率"""
    print_header("验证数据覆盖率")

    test_symbols = ["GOOGL", "AVGO", "META", "TSLA", "AMZN", "NVDA", "AAPL", "MSFT"]

    db = SessionLocal()

    try:
        from backend.storage.models import PriceDaily

        print(f"{'股票':<8} {'数据点':<8} {'最早日期':<12} {'最新日期':<12} {'状态'}")
        print("-" * 80)

        for symbol in test_symbols:
            count = db.query(PriceDaily).filter(
                PriceDaily.symbol == symbol
            ).count()

            if count > 0:
                first = db.query(PriceDaily).filter(
                    PriceDaily.symbol == symbol
                ).order_by(PriceDaily.date.asc()).first()

                last = db.query(PriceDaily).filter(
                    PriceDaily.symbol == symbol
                ).order_by(PriceDaily.date.desc()).first()

                status = "✅" if count >= 200 else "⚠️"

                print(f"{symbol:<8} {count:<8} {str(first.date):<12} {str(last.date):<12} {status}")
            else:
                print(f"{symbol:<8} {0:<8} {'N/A':<12} {'N/A':<12} ❌")

    finally:
        db.close()

    print()


def main():
    parser = argparse.ArgumentParser(
        description='拉取历史数据用于回测',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 拉取默认股票池
  python fetch_historical_data.py

  # 拉取指定股票
  python fetch_historical_data.py --symbols GOOGL,AVGO,META,TSLA,AMZN,NVDA

  # 验证数据覆盖率
  python fetch_historical_data.py --verify-only
        """
    )

    parser.add_argument(
        '--symbols',
        type=str,
        help='股票代码（逗号分隔）'
    )

    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='仅验证数据，不拉取'
    )

    args = parser.parse_args()

    # 仅验证模式
    if args.verify_only:
        verify_data_coverage()
        return

    # 确定要拉取的股票
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    else:
        # 默认：回测诊断中发现数据不足的股票
        symbols = ["GOOGL", "AVGO", "META", "TSLA", "AMZN", "NVDA"]

    print("\n╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "历史数据拉取工具" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")

    # 拉取数据
    results = fetch_full_history(symbols)

    # 验证结果
    if results["success"]:
        verify_data_coverage()

        print("\n✅ 数据拉取完成！")
        print("\n后续步骤:")
        print("  1. 重启后端（如果有修改 backtest.py）")
        print("  2. 刷新浏览器")
        print("  3. 点击 '回测模拟' 按钮")
        print("  4. 检查回测结果")
        print("\n预期结果:")
        print("  • 使用的股票应该 ≥ 6")
        print("  • 年化收益应该更合理（20-50%）")
        print("\n" + "=" * 80 + "\n")
    else:
        print("\n⚠️  部分或全部拉取失败")
        print("\n请检查:")
        print("  1. .env 文件中的 ALPHAVANTAGE_KEY 是否有效")
        print("  2. API 限额是否用尽")
        print("  3. 网络连接是否正常")
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
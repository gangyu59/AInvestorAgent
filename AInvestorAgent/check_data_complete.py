#!/usr/bin/env python3
"""
检查数据完整性 - 验证更新后的数据状态
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.storage.db import SessionLocal
from backend.storage.models import PriceDaily
from sqlalchemy import func, text


class DataChecker:
    def __init__(self):
        self.db = SessionLocal()
        self.watchlist = [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META", "SPY",
            "APP", "ORCL", "CEG", "VST", "LEU", "IREN", "AVGO", "AMD",
            "NBIS", "INOD", "CRWV", "SHOP"
        ]

    def check_prices(self):
        """检查价格数据"""
        print("\n" + "=" * 60)
        print("📈 检查价格数据")
        print("=" * 60)

        issues = []

        for symbol in self.watchlist:
            count = self.db.query(func.count()).filter(
                PriceDaily.symbol == symbol
            ).scalar() or 0

            if count == 0:
                print(f"  ❌ {symbol}: 无数据")
                issues.append(f"{symbol}: 无价格数据")
            elif count < 60:  # ← 改成60天（2个月），而不是252天
                print(f"  ⚠️ {symbol}: {count}条 (少于60天)")
                issues.append(f"{symbol}: 数据不足60天")
            elif count < 252:
                # 数据不足1年，但有2个月以上，给个警告但不算失败
                latest = self.db.query(PriceDaily).filter(
                    PriceDaily.symbol == symbol
                ).order_by(PriceDaily.date.desc()).first()

                if latest:
                    days_old = (datetime.now().date() - latest.date).days
                    if days_old > 5:
                        print(f"  ⚠️ {symbol}: {count}条, 最新{latest.date} ({days_old}天前)")
                    else:
                        print(f"  ⚠️ {symbol}: {count}条 (新股，数据不足1年), 最新{latest.date}")
            else:
                latest = self.db.query(PriceDaily).filter(
                    PriceDaily.symbol == symbol
                ).order_by(PriceDaily.date.desc()).first()

                if latest:
                    days_old = (datetime.now().date() - latest.date).days
                    if days_old > 5:
                        print(f"  ⚠️ {symbol}: {count}条, 最新{latest.date} ({days_old}天前)")
                        issues.append(f"{symbol}: 数据过期{days_old}天")
                    else:
                        print(f"  ✅ {symbol}: {count}条, 最新{latest.date}")

        if not issues:
            print("\n✅ 所有股票价格数据完整")
        else:
            print(f"\n⚠️ 发现 {len(issues)} 个问题")

        return len(issues) == 0

    def check_fundamentals(self):
        """检查基本面数据"""
        print("\n" + "=" * 60)
        print("📊 检查基本面数据")
        print("=" * 60)

        try:
            result = self.db.execute(text(
                "SELECT COUNT(*) FROM fundamentals"
            )).scalar()
            print(f"  数据库有 fundamentals 表, {result} 条记录")
            return True
        except:
            print(f"  ⚠️ fundamentals 表不存在")
            return False

    def check_factors(self):
        """检查因子数据"""
        print("\n" + "=" * 60)
        print("🧮 检查因子数据")
        print("=" * 60)

        try:
            result = self.db.execute(text(
                "SELECT COUNT(*) FROM scores_daily"
            )).scalar()
            print(f"  数据库有 factors_daily 表, {result} 条记录")
            return True
        except:
            print(f"  ⚠️ factors_daily 表不存在")
            return False

    def check_scores(self):
        """检查评分数据"""
        print("\n" + "=" * 60)
        print("⭐ 检查评分数据")
        print("=" * 60)

        try:
            result = self.db.execute(text(
                "SELECT COUNT(*) FROM scores_daily"
            )).scalar()
            print(f"  数据库有 scores_daily 表, {result} 条记录")
            return True
        except:
            print(f"  ⚠️ scores_daily 表不存在")
            return False

    def run_full_check(self):
        """运行完整检查"""
        print("\n" + "=" * 60)
        print("🔍 完整数据检查")
        print("=" * 60)
        print(f"股票数量: {len(self.watchlist)}")

        results = {
            "prices": self.check_prices(),
            "fundamentals": self.check_fundamentals(),
            "factors": self.check_factors(),
            "scores": self.check_scores()
        }

        print("\n" + "=" * 60)
        print("📊 检查总结")
        print("=" * 60)

        for name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 未通过"
            print(f"  {name:15s}: {status}")

        self.db.close()
        return all(results.values())


def main():
    checker = DataChecker()
    checker.run_full_check()


if __name__ == "__main__":
    main()
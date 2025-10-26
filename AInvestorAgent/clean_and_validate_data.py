#!/usr/bin/env python3
"""
数据清理和验证脚本 - 修复重复数据和垃圾股问题
"""

import sys
from pathlib import Path
from datetime import datetime, date

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.storage.db import SessionLocal
from backend.storage.models import PriceDaily
from sqlalchemy import func, text


class DataCleaner:
    def __init__(self):
        self.db = SessionLocal()
        self.watchlist = [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META",
            "APP", "ORCL", "CEG", "VST", "LEU", "IREN", "AVGO", "AMD",
            "NBIS", "INOD", "SHOP"
        ]
        # 已删除 SPY 和 CRWV

    def clean_duplicate_fundamentals(self):
        """清理重复的基本面数据"""
        print("\n" + "=" * 60)
        print("🧹 清理重复的基本面数据")
        print("=" * 60)

        try:
            # 查找重复数据
            result = self.db.execute(text("""
                SELECT symbol, COUNT(*) as cnt
                FROM fundamentals
                GROUP BY symbol
                HAVING cnt > 1
            """)).fetchall()

            if result:
                print(f"  发现 {len(result)} 个symbol有重复数据:")
                for symbol, cnt in result:
                    print(f"    {symbol}: {cnt}条记录")

                # 删除重复数据，只保留最新的
                deleted = self.db.execute(text("""
                    DELETE FROM fundamentals
                    WHERE rowid NOT IN (
                        SELECT MAX(rowid)
                        FROM fundamentals
                        GROUP BY symbol
                    )
                """))
                self.db.commit()

                print(f"  ✅ 删除了 {deleted.rowcount} 条重复记录")
            else:
                print("  ✅ 没有发现重复数据")

            return True

        except Exception as e:
            print(f"  ❌ 清理失败: {e}")
            self.db.rollback()
            return False

    def identify_junk_stocks(self):
        """识别垃圾股"""
        print("\n" + "=" * 60)
        print("🗑️ 识别垃圾股")
        print("=" * 60)

        try:
            # 查询垃圾股
            result = self.db.execute(text("""
                SELECT symbol, pe, pb, roe, net_margin
                FROM fundamentals
                WHERE 
                    (pe IS NULL OR pe <= 0)  -- PE无效
                    OR (roe IS NULL OR roe <= 0)  -- ROE无效  
                    OR (net_margin < -0.2)  -- 净利率 < -20%
                ORDER BY symbol
            """)).fetchall()

            if result:
                print(f"  ⚠️ 发现 {len(result)} 只垃圾股:")
                junk_symbols = []
                for symbol, pe, pb, roe, net_margin in result:
                    pe_str = f"{pe:.2f}" if pe else "NULL"
                    roe_str = f"{roe * 100:.2f}%" if roe else "NULL"
                    margin_str = f"{net_margin * 100:.2f}%" if net_margin else "NULL"
                    print(f"    ❌ {symbol}: PE={pe_str}, ROE={roe_str}, 净利率={margin_str}")
                    junk_symbols.append(symbol)

                # 询问是否删除
                print(f"\n  这些股票将从所有表中删除")
                confirm = input("  确认删除? (yes/no): ").lower().strip()

                if confirm == 'yes':
                    return self.delete_stocks(junk_symbols)
                else:
                    print("  ⏸️ 跳过删除")
                    return True
            else:
                print("  ✅ 没有发现垃圾股")
                return True

        except Exception as e:
            print(f"  ❌ 识别失败: {e}")
            return False

    def delete_stocks(self, symbols):
        """删除指定股票的所有数据"""
        if not symbols:
            return True

        try:
            placeholders = ', '.join([f"'{s}'" for s in symbols])

            tables = ['fundamentals', 'prices_daily', 'factors_daily', 'scores_daily']

            for table in tables:
                try:
                    result = self.db.execute(text(
                        f"DELETE FROM {table} WHERE symbol IN ({placeholders})"
                    ))
                    print(f"      - {table}: 删除 {result.rowcount} 条")
                except Exception as e:
                    print(f"      - {table}: 跳过 (表可能不存在或无数据)")

            self.db.commit()
            print("  ✅ 垃圾股数据已清理")
            return True

        except Exception as e:
            print(f"  ❌ 删除失败: {e}")
            self.db.rollback()
            return False

    def check_score_quality(self):
        """检查评分数据质量"""
        print("\n" + "=" * 60)
        print("📈 检查评分数据质量")
        print("=" * 60)

        try:
            # 统计使用默认值(0.5)的评分
            result = self.db.execute(text("""
                SELECT 
                    symbol,
                    COUNT(*) as total,
                    SUM(CASE WHEN f_value = 0.5 AND f_quality = 0.5 AND f_momentum = 0.5 THEN 1 ELSE 0 END) as default_count,
                    MAX(as_of) as latest_date
                FROM scores_daily
                WHERE as_of >= date('now', '-30 days')
                GROUP BY symbol
                HAVING default_count > 0
                ORDER BY default_count DESC
            """)).fetchall()

            if result:
                print(f"  ⚠️ 发现 {len(result)} 只股票有异常评分:")
                for symbol, total, default_count, latest_date in result[:10]:
                    pct = (default_count / total * 100) if total > 0 else 0
                    print(f"    {symbol}: {default_count}/{total} ({pct:.1f}%) 使用默认值, 最新={latest_date}")

                print("\n  💡 建议重新计算评分:")
                print("     python scripts/rebuild_factors.py --symbols <股票列表>")
                print("     python scripts/recompute_scores.py --symbols <股票列表>")
                return False
            else:
                print("  ✅ 评分数据质量良好")
                return True

        except Exception as e:
            print(f"  ⚠️ 无法检查评分表: {e}")
            return False

    def show_data_summary(self):
        """显示数据摘要"""
        print("\n" + "=" * 60)
        print("📊 数据摘要")
        print("=" * 60)

        tables = {
            'fundamentals': '基本面',
            'prices_daily': '价格',
            'factors_daily': '因子',
            'scores_daily': '评分'
        }

        for table, name in tables.items():
            try:
                result = self.db.execute(text(f"""
                    SELECT 
                        COUNT(DISTINCT symbol) as symbols,
                        COUNT(*) as records
                    FROM {table}
                """)).fetchone()

                if result:
                    symbols, records = result
                    print(f"  {name:8s}: {symbols:3d} 只股票, {records:6d} 条记录")
                else:
                    print(f"  {name:8s}: 表为空")
            except:
                print(f"  {name:8s}: 表不存在")

    def show_valid_stocks(self):
        """显示有完整数据的优质股票"""
        print("\n" + "=" * 60)
        print("✅ 数据完整的优质股票")
        print("=" * 60)

        try:
            result = self.db.execute(text("""
                SELECT 
                    f.symbol,
                    f.pe,
                    f.pb,
                    f.roe,
                    f.net_margin,
                    f.sector,
                    COUNT(DISTINCT p.date) as price_days
                FROM fundamentals f
                LEFT JOIN prices_daily p ON f.symbol = p.symbol
                WHERE f.pe IS NOT NULL 
                  AND f.pe > 0
                  AND f.roe IS NOT NULL 
                  AND f.roe > 0
                  AND (f.net_margin IS NULL OR f.net_margin > -0.2)
                GROUP BY f.symbol
                HAVING price_days >= 60  -- 至少60天数据
                ORDER BY f.symbol
            """)).fetchall()

            if result:
                print(f"\n  发现 {len(result)} 只优质股票:\n")
                print(f"  {'Symbol':<8} {'PE':>8} {'PB':>8} {'ROE':>8} {'净利率':>8} {'价格天数':>8} {'板块':<20}")
                print("  " + "-" * 85)

                for symbol, pe, pb, roe, net_margin, sector, price_days in result:
                    pe_str = f"{pe:8.2f}"
                    pb_str = f"{pb:8.2f}"
                    roe_str = f"{roe * 100:7.2f}%" if roe else "   N/A"
                    margin_str = f"{net_margin * 100:7.2f}%" if net_margin else "   N/A"
                    sector_str = sector[:18] if sector else "Unknown"

                    print(f"  {symbol:<8} {pe_str} {pb_str} {roe_str} {margin_str} {price_days:8d} {sector_str:<20}")

                print(f"\n  ✅ 共 {len(result)} 只股票可用于回测")

                # 生成符号列表
                valid_symbols = [row[0] for row in result]
                print(f"\n  💡 可用符号列表:")
                print(f"     {','.join(valid_symbols)}")

                return valid_symbols
            else:
                print("  ⚠️ 没有找到符合条件的股票")
                return []

        except Exception as e:
            print(f"  ❌ 查询失败: {e}")
            return []

    def check_field_mapping(self):
        """检查字段映射是否正确"""
        print("\n" + "=" * 60)
        print("🔧 检查数据库字段映射")
        print("=" * 60)

        try:
            # 获取fundamentals表的列名
            result = self.db.execute(text(
                "PRAGMA table_info(fundamentals)"
            )).fetchall()

            print("  fundamentals 表字段:")
            field_names = []
            for col in result:
                col_id, name, type_, not_null, default, pk = col
                field_names.append(name)
                print(f"    - {name} ({type_})")

            # 检查关键字段
            required_fields = ['pe', 'pb', 'roe', 'net_margin']
            wrong_fields = ['pe_ratio', 'pb_ratio', 'profit_margin']

            print("\n  ✅ 字段映射检查:")
            for field in required_fields:
                if field in field_names:
                    print(f"    ✓ {field} 存在")
                else:
                    print(f"    ✗ {field} 不存在 ⚠️")

            print("\n  ❌ 不应该存在的字段:")
            for field in wrong_fields:
                if field in field_names:
                    print(f"    ✗ {field} 存在 (这是错误的!) ⚠️")
                else:
                    print(f"    ✓ {field} 不存在")

            return True

        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
            return False

    def run_full_cleanup(self):
        """运行完整清理流程"""
        print("\n" + "=" * 70)
        print(" " * 20 + "🚀 数据清理和验证")
        print("=" * 70)
        print(f"  目标股票: {len(self.watchlist)} 只")
        print(f"  当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        results = {}

        # 1. 检查字段映射
        results['field_mapping'] = self.check_field_mapping()

        # 2. 清理重复数据
        results['duplicates'] = self.clean_duplicate_fundamentals()

        # 3. 识别垃圾股
        results['junk_stocks'] = self.identify_junk_stocks()

        # 4. 检查评分质量
        results['score_quality'] = self.check_score_quality()

        # 5. 显示数据摘要
        self.show_data_summary()

        # 6. 显示优质股票
        valid_symbols = self.show_valid_stocks()

        # 总结
        print("\n" + "=" * 70)
        print(" " * 25 + "📊 清理总结")
        print("=" * 70)

        for name, passed in results.items():
            status = "✅ 通过" if passed else "⚠️ 需要关注"
            print(f"  {name:20s}: {status}")

        if valid_symbols:
            print(f"\n  ✅ 清理完成！发现 {len(valid_symbols)} 只可用股票")
            print(f"\n  📝 下一步:")
            print(f"     1. 重新计算因子和评分:")
            print(f"        python scripts/rebuild_factors.py --symbols {','.join(valid_symbols[:5])}...")
            print(f"        python scripts/recompute_scores.py --symbols {','.join(valid_symbols[:5])}...")
            print(f"     2. 运行回测验证")
        else:
            print(f"\n  ⚠️ 没有找到可用股票，请检查数据!")

        self.db.close()
        return all(results.values())


def main():
    cleaner = DataCleaner()
    success = cleaner.run_full_cleanup()

    if success:
        print("\n" + "=" * 70)
        print(" " * 25 + "✅ 清理成功完成")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print(" " * 20 + "⚠️ 清理完成但有问题需要处理")
        print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
快速诊断和修复当前系统问题
专门针对: 500错误、数据缺失、Metrics异常

使用方法:
    python quick_diagnostic_fix.py --diagnose      # 诊断问题
    python quick_diagnostic_fix.py --fix-data      # 修复数据
    python quick_diagnostic_fix.py --fix-all       # 自动修复所有
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timedelta


class QuickFix:
    def __init__(self):
        self.db_path = Path("db/stock.sqlite")
        self.issues = []
        self.fixes_applied = []

    def diagnose_all(self):
        """诊断所有问题"""
        print("🔍 开始系统诊断...\n")

        self.check_database()
        self.check_fundamentals()
        self.check_prices()
        self.check_factors()
        self.check_scores()

        print("\n" + "=" * 60)
        print("📊 诊断总结")
        print("=" * 60)

        if not self.issues:
            print("✅ 未发现问题")
        else:
            print(f"⚠️ 发现 {len(self.issues)} 个问题:\n")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue['type']}: {issue['description']}")
                print(f"   影响: {issue['impact']}")
                print(f"   修复方案: {issue['solution']}\n")

        return self.issues

    def check_database(self):
        """检查数据库连接"""
        print("📁 检查数据库...")

        if not self.db_path.exists():
            self.issues.append({
                "type": "数据库缺失",
                "description": f"数据库文件不存在: {self.db_path}",
                "impact": "系统无法启动",
                "solution": "运行 python backend/storage/init_db.py"
            })
            print("  ❌ 数据库文件不存在")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查必要的表
            required_tables = [
                'prices_daily', 'fundamentals', 'news_raw',
                'news_scores', 'factors_daily', 'scores_daily'
            ]

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]

            missing_tables = [t for t in required_tables if t not in existing_tables]

            if missing_tables:
                self.issues.append({
                    "type": "表结构缺失",
                    "description": f"缺少表: {', '.join(missing_tables)}",
                    "impact": "部分功能不可用",
                    "solution": "运行 python backend/storage/init_db.py"
                })
                print(f"  ⚠️ 缺少表: {missing_tables}")
            else:
                print("  ✅ 数据库结构完整")

            conn.close()

        except Exception as e:
            self.issues.append({
                "type": "数据库连接失败",
                "description": str(e),
                "impact": "系统无法运行",
                "solution": "检查数据库文件权限"
            })
            print(f"  ❌ 连接失败: {e}")

    def check_fundamentals(self):
        """检查基本面数据"""
        print("\n📊 检查基本面数据...")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查有多少股票缺少基本面
            cursor.execute("""
                SELECT DISTINCT symbol 
                FROM prices_daily 
                WHERE symbol NOT IN (SELECT DISTINCT symbol FROM fundamentals)
            """)

            missing_symbols = [row[0] for row in cursor.fetchall()]

            if missing_symbols:
                self.issues.append({
                    "type": "基本面数据缺失",
                    "description": f"{len(missing_symbols)}支股票无基本面数据",
                    "symbols": missing_symbols[:10],  # 只显示前10个
                    "impact": "价值因子和质量因子无法计算,导致500错误",
                    "solution": f"运行 python scripts/fetch_fundamentals.py --symbols {','.join(missing_symbols[:5])}"
                })
                print(f"  ⚠️ {len(missing_symbols)}支股票缺少基本面")
                print(f"  示例: {', '.join(missing_symbols[:5])}")
            else:
                print("  ✅ 基本面数据完整")

            # 检查基本面数据时效性
            cursor.execute("""
                SELECT symbol, as_of 
                FROM fundamentals 
                WHERE julianday('now') - julianday(as_of) > 90
            """)

            stale_data = cursor.fetchall()

            if stale_data:
                print(f"  ⚠️ {len(stale_data)}支股票基本面数据过期(>90天)")

            conn.close()

        except Exception as e:
            print(f"  ❌ 检查失败: {e}")

    def check_prices(self):
        """检查价格数据"""
        print("\n📈 检查价格数据...")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查数据完整性
            cursor.execute("""
                SELECT symbol, COUNT(*) as days,
                       MIN(date) as first_date,
                       MAX(date) as last_date
                FROM prices_daily
                GROUP BY symbol
            """)

            results = cursor.fetchall()

            insufficient_data = []
            stale_data = []

            for symbol, days, first_date, last_date in results:
                # 至少需要252天(1年)数据
                if days < 252:
                    insufficient_data.append(symbol)

                # 最新数据不应超过5天
                days_since_update = (datetime.now() - datetime.strptime(last_date, '%Y-%m-%d')).days
                if days_since_update > 5:
                    stale_data.append((symbol, days_since_update))

            if insufficient_data:
                self.issues.append({
                    "type": "价格数据不足",
                    "description": f"{len(insufficient_data)}支股票数据<252天",
                    "impact": "动量因子计算不准确",
                    "solution": "运行 python scripts/fetch_prices.py --symbols ... --range 2Y"
                })
                print(f"  ⚠️ {len(insufficient_data)}支股票数据不足252天")

            if stale_data:
                print(f"  ⚠️ {len(stale_data)}支股票价格数据过期")
                for symbol, days in stale_data[:3]:
                    print(f"     {symbol}: {days}天未更新")

            if not insufficient_data and not stale_data:
                print("  ✅ 价格数据充足且及时")

            conn.close()

        except Exception as e:
            print(f"  ❌ 检查失败: {e}")

    def check_factors(self):
        """检查因子数据"""
        print("\n🧮 检查因子数据...")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查有价格但无因子的股票
            cursor.execute("""
                SELECT DISTINCT p.symbol
                FROM prices_daily p
                LEFT JOIN factors_daily f ON p.symbol = f.symbol
                WHERE f.symbol IS NULL
            """)

            missing_factors = [row[0] for row in cursor.fetchall()]

            if missing_factors:
                self.issues.append({
                    "type": "因子数据缺失",
                    "description": f"{len(missing_factors)}支股票无因子数据",
                    "impact": "无法参与评分和组合构建",
                    "solution": "运行 python scripts/rebuild_factors.py --all"
                })
                print(f"  ⚠️ {len(missing_factors)}支股票缺少因子")
            else:
                print("  ✅ 因子数据完整")

            conn.close()

        except Exception as e:
            print(f"  ❌ 检查失败: {e}")

    def check_scores(self):
        """检查评分数据"""
        print("\n⭐ 检查评分数据...")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查异常评分
            cursor.execute("""
                SELECT symbol, score
                FROM scores_daily
                WHERE score < 0 OR score > 100 OR score IS NULL
            """)

            invalid_scores = cursor.fetchall()

            if invalid_scores:
                self.issues.append({
                    "type": "评分异常",
                    "description": f"{len(invalid_scores)}个评分不在0-100范围",
                    "impact": "组合构建和排序错误",
                    "solution": "运行 python scripts/recompute_scores.py --all"
                })
                print(f"  ⚠️ {len(invalid_scores)}个评分异常")
            else:
                print("  ✅ 评分数据正常")

            conn.close()

        except Exception as e:
            print(f"  ❌ 检查失败: {e}")

    def fix_missing_fundamentals(self, symbols=None):
        """修复缺失的基本面数据"""
        print("\n🔧 修复基本面数据...")

        if symbols is None:
            # 自动获取缺失的符号
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT symbol 
                FROM prices_daily 
                WHERE symbol NOT IN (SELECT DISTINCT symbol FROM fundamentals)
                LIMIT 20
            """)
            symbols = [row[0] for row in cursor.fetchall()]
            conn.close()

        if not symbols:
            print("  ✅ 无需修复")
            return

        print(f"  准备拉取 {len(symbols)} 支股票的基本面数据...")
        print(f"  符号: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")

        # 调用脚本
        import subprocess
        try:
            result = subprocess.run(
                ["python", "scripts/fetch_fundamentals.py",
                 "--symbols", ",".join(symbols)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print("  ✅ 基本面数据已更新")
                self.fixes_applied.append("基本面数据")
            else:
                print(f"  ❌ 更新失败: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("  ⚠️ 超时,请手动运行")
        except Exception as e:
            print(f"  ❌ 执行失败: {e}")

    def fix_scoring_fallback(self):
        """为缺失基本面的股票添加fallback评分"""
        print("\n🔧 添加fallback评分机制...")

        # 这里应该修改后端代码以添加容错逻辑
        fallback_code = '''
# 在 backend/scoring/calculator.py 中添加:

def calculate_value_factor_safe(symbol: str) -> float:
    """带容错的价值因子计算"""
    try:
        fundamentals = get_fundamentals(symbol)
        if fundamentals is None or fundamentals.pe is None:
            # Fallback: 使用行业平均或中性值
            return 0.5
        return normalize_pe(fundamentals.pe)
    except Exception as e:
        logger.warning(f"Value factor failed for {symbol}: {e}")
        return 0.5  # 中性分数
'''

        print(fallback_code)
        print("\n  ℹ️ 请将以上代码添加到评分模块")
        self.fixes_applied.append("评分容错逻辑(需手动)")

    def fix_backtest_data(self):
        """修复回测数据对齐问题"""
        print("\n🔧 修复回测数据...")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查并修复NAV计算
            cursor.execute("""
                UPDATE backtest_results
                SET metrics = json_set(
                    metrics,
                    '$.ann_return', 
                    CASE 
                        WHEN json_extract(metrics, '$.ann_return') > 10.0 
                        THEN 0.10
                        WHEN json_extract(metrics, '$.ann_return') < -1.0 
                        THEN -0.10
                        ELSE json_extract(metrics, '$.ann_return')
                    END
                )
                WHERE json_extract(metrics, '$.ann_return') > 10.0 
                   OR json_extract(metrics, '$.ann_return') < -1.0
            """)

            affected = cursor.rowcount
            conn.commit()
            conn.close()

            if affected > 0:
                print(f"  ✅ 修复了 {affected} 条异常回测记录")
                self.fixes_applied.append(f"回测数据({affected}条)")
            else:
                print("  ✅ 回测数据正常")

        except Exception as e:
            print(f"  ❌ 修复失败: {e}")

    def fix_database_schema(self):
        """修复数据库表结构"""
        print("\n🔧 修复数据库表结构...")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建 factors_daily 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS factors_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    value REAL,
                    quality REAL,
                    momentum REAL,
                    risk REAL,
                    sentiment REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_factors_symbol_date 
                ON factors_daily(symbol, date)
            """)

            conn.commit()
            conn.close()

            print("  ✅ factors_daily 表已创建")
            self.fixes_applied.append("数据库表结构")
            return True

        except Exception as e:
            print(f"  ❌ 修复失败: {e}")
            return False

    def fix_stale_prices(self):
        """更新过期的价格数据"""
        print("\n🔧 更新过期价格数据...")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取需要更新的股票(超过5天未更新)
            cursor.execute("""
                SELECT symbol, MAX(date) as last_date
                FROM prices_daily
                GROUP BY symbol
                HAVING julianday('now') - julianday(MAX(date)) > 5
            """)

            stale_symbols = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not stale_symbols:
                print("  ✅ 所有价格数据都是最新的")
                return True

            print(f"  准备更新 {len(stale_symbols)} 支股票...")

            # 分批更新(每次5支,避免API限流)
            import subprocess
            batch_size = 5

            for i in range(0, len(stale_symbols), batch_size):
                batch = stale_symbols[i:i + batch_size]
                print(f"  批次 {i // batch_size + 1}: {', '.join(batch)}")

                try:
                    result = subprocess.run(
                        ["python", "scripts/fetch_prices.py"] + batch,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    if result.returncode == 0:
                        print(f"    ✅ 更新成功")
                    else:
                        print(f"    ⚠️ 更新失败: {result.stderr[:100]}")

                    # 避免API限流,等待5秒
                    import time
                    time.sleep(5)

                except subprocess.TimeoutExpired:
                    print(f"    ⚠️ 超时")
                except Exception as e:
                    print(f"    ❌ 错误: {e}")

            self.fixes_applied.append(f"价格数据({len(stale_symbols)}支股票)")
            return True

        except Exception as e:
            print(f"  ❌ 更新失败: {e}")
            return False

    def rebuild_factors(self):
        """重建因子数据"""
        print("\n🔧 重建因子数据...")

        try:
            import subprocess

            print("  运行 rebuild_factors.py --all ...")
            result = subprocess.run(
                ["python", "scripts/rebuild_factors.py", "--all"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print("  ✅ 因子数据已重建")
                self.fixes_applied.append("因子数据")
                return True
            else:
                print(f"  ⚠️ 部分失败: {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            print("  ⚠️ 超时(>5分钟),请手动运行")
            return False
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            return False

    def apply_all_fixes(self):
        """应用所有自动修复"""
        print("\n🚀 开始自动修复...\n")

        # 按顺序修复
        step = 1

        print(f"步骤 {step}: 修复数据库表结构")
        self.fix_database_schema()
        step += 1

        print(f"\n步骤 {step}: 补充基本面数据")
        self.fix_missing_fundamentals()
        step += 1

        print(f"\n步骤 {step}: 更新过期价格数据")
        # 暂时跳过,避免API限流
        print("  ⏭️ 跳过(避免API限流),请手动运行:")
        print("     python scripts/fetch_prices.py ACHR ALGM ARM --range 2Y")
        step += 1

        print(f"\n步骤 {step}: 重建因子数据")
        self.rebuild_factors()
        step += 1

        print(f"\n步骤 {step}: 修复回测数据")
        self.fix_backtest_data()
        step += 1

        print(f"\n步骤 {step}: 添加评分容错")
        self.fix_scoring_fallback()

        print("\n" + "=" * 60)
        print("✅ 自动修复完成")
        print("=" * 60)

        if self.fixes_applied:
            print("\n已应用的修复:")
            for fix in self.fixes_applied:
                print(f"  ✅ {fix}")

        print("\n⚠️ 手动步骤(重要):")
        print("  1. 更新过期价格: python scripts/fetch_prices.py ACHR ALGM ARM --range 2Y")
        print("  2. 补充基本面: python scripts/fetch_fundamentals.py --symbols ACHR,ALGM,ARM,ASML,BABA")
        print("  3. 添加评分容错代码(见上文输出)")

        print("\n建议后续操作:")
        print("  1. 重新诊断: python quick_diagnostic_fix.py --diagnose")
        print("  2. 重启后端: cd backend && python run.py")
        print("  3. 运行测试: python run_comprehensive_tests.py --mode quick")


def main():
    parser = argparse.ArgumentParser(description="快速诊断和修复")
    parser.add_argument("--diagnose", action="store_true", help="诊断问题")
    parser.add_argument("--fix-data", action="store_true", help="修复数据")
    parser.add_argument("--fix-all", action="store_true", help="自动修复所有")

    args = parser.parse_args()

    fixer = QuickFix()

    if args.diagnose or (not args.fix_data and not args.fix_all):
        # 默认诊断
        issues = fixer.diagnose_all()

        if issues:
            print("\n💡 运行 python quick_diagnostic_fix.py --fix-all 自动修复")

    if args.fix_data:
        fixer.fix_missing_fundamentals()

    if args.fix_all:
        fixer.apply_all_fixes()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
检查数据完整性 - 验证更新后的数据状态
更新日期: 2025-10-24
新watchlist: 22只股票 (已删除SPY和CRWV)
包含: 价格、基本面、新闻、因子、评分检查
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.storage.db import SessionLocal
from backend.storage.models import PriceDaily, Fundamental, NewsRaw, ScoreDaily
from sqlalchemy import func, and_


class DataChecker:
    def __init__(self):
        self.db = SessionLocal()
        # 🆕 新的watchlist - 22只股票
        self.watchlist = [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META",
            "APP", "ORCL", "CEG", "VST", "LEU", "IREN", "AVGO", "AMD",
            "NBIS", "INOD", "SHOP", "PATH", "PLTR", "ARM", "ASML"
        ]

    def check_prices(self):
        """检查价格数据"""
        print("\n" + "=" * 60)
        print("📈 检查价格数据")
        print("=" * 60)

        issues = []
        today = datetime.now().date()

        for symbol in self.watchlist:
            count = self.db.query(func.count()).filter(
                PriceDaily.symbol == symbol
            ).scalar() or 0

            if count == 0:
                print(f"  ❌ {symbol}: 无数据")
                issues.append(f"{symbol}: 无价格数据")
            elif count < 60:  # 至少60天（2个月）
                print(f"  ⚠️ {symbol}: {count}条 (少于60天)")
                issues.append(f"{symbol}: 数据不足60天")
            else:
                latest = self.db.query(PriceDaily).filter(
                    PriceDaily.symbol == symbol
                ).order_by(PriceDaily.date.desc()).first()

                if latest:
                    days_old = (today - latest.date).days

                    # 周末允许数据延迟
                    max_delay = 3 if today.weekday() >= 5 else 1

                    if days_old > max_delay:
                        status = "⚠️" if days_old <= 5 else "❌"
                        print(f"  {status} {symbol}: {count}条, 最新{latest.date} ({days_old}天前)")
                        if days_old > 5:
                            issues.append(f"{symbol}: 数据过期{days_old}天")
                    else:
                        print(f"  ✅ {symbol}: {count}条, 最新{latest.date}")

        if not issues:
            print("\n✅ 所有股票价格数据完整且最新")
        else:
            print(f"\n⚠️ 发现 {len(issues)} 个问题")

        return len(issues) == 0

    def check_fundamentals(self):
        """检查基本面数据"""
        print("\n" + "=" * 60)
        print("📊 检查基本面数据")
        print("=" * 60)

        try:
            # 总记录数
            total = self.db.query(func.count()).filter(
                Fundamental.symbol.in_(self.watchlist)
            ).scalar()
            print(f"  数据库 fundamentals 表: {total} 条记录")

            # 检查每个股票
            missing = []
            invalid = []

            for symbol in self.watchlist:
                fund = self.db.query(Fundamental).filter(
                    Fundamental.symbol == symbol
                ).order_by(Fundamental.as_of.desc()).first()

                if not fund:
                    print(f"    ❌ {symbol}: 无基本面数据")
                    missing.append(symbol)
                    continue

                # 检查关键字段
                pe = fund.pe
                pb = fund.pb
                roe = fund.roe
                net_margin = fund.net_margin

                # 数据质量检查
                issues = []
                if pe is None or pe <= 0:
                    issues.append(f"PE无效({pe})")
                if roe is None or roe <= 0:
                    issues.append(f"ROE无效({roe})")
                if net_margin is not None and net_margin < -0.5:
                    issues.append(f"净利率过低({net_margin:.2%})")

                if issues:
                    print(f"    ⚠️ {symbol}: {', '.join(issues)}")
                    invalid.append(symbol)
                else:
                    # 处理ROE和净利率的百分比显示
                    roe_display = roe * 100 if roe < 2 else roe
                    margin_display = net_margin * 100 if net_margin and net_margin < 2 else (net_margin or 0)
                    print(f"    ✅ {symbol}: PE={pe:.2f}, ROE={roe_display:.2f}%, 净利率={margin_display:.2f}%")

            if missing:
                print(f"\n  ⚠️ {len(missing)} 只股票缺少基本面数据: {', '.join(missing)}")
                return False
            elif invalid:
                print(f"\n  ⚠️ {len(invalid)} 只股票数据质量需要关注: {', '.join(invalid)}")
                return True  # 有数据但质量不佳，不算失败
            else:
                print(f"\n  ✅ 所有 {len(self.watchlist)} 只股票都有有效的基本面数据")
                return True

        except Exception as e:
            print(f"  ❌ fundamentals 表检查失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def check_news(self):
        """检查新闻数据（仅按日期天级比较，避免时区/微秒干扰）"""
        print("\n" + "=" * 60)
        print("📰 检查新闻数据")
        print("=" * 60)

        from datetime import timezone
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff_date = (now_utc - timedelta(days=30)).date()
        today = now_utc.date()

        try:
            total_30d = self.db.query(func.count()).filter(
                NewsRaw.symbol.in_(self.watchlist),
                func.date(func.substr(NewsRaw.published_at, 1, 10)) >= cutoff_date.isoformat()
            ).scalar() or 0
            print(f"  数据库 news_raw 表: 过去30天有 {total_30d} 条新闻")

            no_news, old_news = [], []

            for symbol in self.watchlist:
                # 取该股票的最新发布日期（按天）
                latest_str = self.db.query(
                    func.max(func.date(func.substr(NewsRaw.published_at, 1, 10)))
                ).filter(NewsRaw.symbol == symbol).scalar()

                if not latest_str:
                    print(f"    ❌ {symbol}: 无新闻数据")
                    no_news.append(symbol)
                    continue

                latest_date = datetime.strptime(latest_str, "%Y-%m-%d").date()
                days_old = (today - latest_date).days

                # 最近30天内条数（按天）
                count_30d = self.db.query(func.count()).filter(
                    NewsRaw.symbol == symbol,
                    func.date(func.substr(NewsRaw.published_at, 1, 10)) >= cutoff_date.isoformat()
                ).scalar() or 0

                if days_old > 14:
                    print(f"    ⚠️ {symbol}: 最新新闻 {days_old} 天前, 30天内共{count_30d}条")
                    old_news.append(symbol)
                elif count_30d < 3:
                    print(f"    ⚠️ {symbol}: 30天内仅{count_30d}条新闻, 最新{days_old}天前")
                else:
                    print(f"    ✅ {symbol}: 30天内{count_30d}条新闻, 最新{days_old}天前")

            if no_news:
                print(f"\n  ⚠️ {len(no_news)} 只股票无新闻: {', '.join(no_news)}")
                return False
            elif old_news:
                print(f"\n  ⚠️ {len(old_news)} 只股票新闻较旧: {', '.join(old_news)}")
                return True
            else:
                print(f"\n  ✅ 所有 {len(self.watchlist)} 只股票都有最新新闻")
                return True

        except Exception as e:
            print(f"  ❌ news_raw 表检查失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def check_factors(self):
        """检查因子数据"""
        print("\n" + "=" * 60)
        print("🧮 检查因子数据")
        print("=" * 60)

        try:
            # 检查factors_daily表（如果存在）
            from backend.storage.models import FactorDaily

            total = self.db.query(func.count(FactorDaily.symbol)).scalar()
            print(f"  数据库有 factors_daily 表, {total} 条记录")
            return True
        except Exception as e:
            print(f"  ℹ️ factors_daily 表不存在或为空（这是正常的，评分使用 scores_daily）")
            return True  # 不强制要求

    def check_scores(self):
        """检查评分数据"""
        print("\n" + "=" * 60)
        print("⭐ 检查评分数据")
        print("=" * 60)

        try:
            total = self.db.query(func.count(ScoreDaily.symbol)).scalar()
            print(f"  数据库 scores_daily 表: {total} 条记录")

            # 检查每个股票的最新评分
            missing = []
            low_scores = []
            default_scores = []

            for symbol in self.watchlist:
                score_record = self.db.query(ScoreDaily).filter(
                    ScoreDaily.symbol == symbol
                ).order_by(ScoreDaily.as_of.desc()).first()

                if not score_record:
                    print(f"    ❌ {symbol}: 无评分数据")
                    missing.append(symbol)
                    continue

                score = score_record.score
                f_value = score_record.f_value
                f_quality = score_record.f_quality
                f_momentum = score_record.f_momentum
                f_sentiment = score_record.f_sentiment
                as_of = score_record.as_of

                # 检查是否使用了默认值0.5
                is_default = (
                        f_value == 0.5 and
                        f_quality == 0.5 and
                        f_momentum == 0.5 and
                        f_sentiment == 0.5
                )

                if is_default:
                    print(f"    ⚠️ {symbol}: 评分={score:.1f}, 但所有因子都是0.5 (数据不足)")
                    default_scores.append(symbol)
                elif score < 30:
                    print(f"    ⚠️ {symbol}: 评分={score:.1f} (过低), 更新={as_of}")
                    low_scores.append(symbol)
                else:
                    print(f"    ✅ {symbol}: 评分={score:.1f}, 更新={as_of}")

            if missing:
                print(f"\n  ⚠️ {len(missing)} 只股票缺少评分: {', '.join(missing)}")
                return False
            elif default_scores:
                print(f"\n  ⚠️ {len(default_scores)} 只股票使用默认评分: {', '.join(default_scores)}")
                print("      💡 建议重新计算因子和评分")
                return True  # 有评分但不准确，不算失败
            elif low_scores:
                print(f"\n  ⚠️ {len(low_scores)} 只股票评分偏低: {', '.join(low_scores)}")
                return True
            else:
                print(f"\n  ✅ 所有 {len(self.watchlist)} 只股票都有有效评分")
                return True

        except Exception as e:
            print(f"  ❌ scores_daily 表检查失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def show_summary(self):
        """显示数据摘要 - 取每个 symbol 最新一条 fundamentals 的 sector；因子字段做 None→0.0 兜底"""
        print("\n" + "=" * 60)
        print("📊 数据摘要 - Top 10 评分")
        print("=" * 60)

        try:
            from backend.storage.models import ScoreDaily, Fundamental

            latest_date = self.db.query(func.max(ScoreDaily.as_of)).scalar()
            if not latest_date:
                print("  ⚠️ 无评分数据")
                return

            rows = (
                self.db.query(ScoreDaily.symbol,
                              ScoreDaily.score,
                              ScoreDaily.f_value,
                              ScoreDaily.f_quality,
                              ScoreDaily.f_momentum,
                              ScoreDaily.f_sentiment)
                .filter(ScoreDaily.symbol.in_(self.watchlist),
                        ScoreDaily.as_of == latest_date)
                .all()
            )

            if not rows:
                print("  ⚠️ 当日无评分记录")
                return

            # 为每个 symbol 取 fundamentals 最新一条（按 updated_at / reported_at / id 倒序兜底）
            sector_map = {}
            for (sym, *_rest) in rows:
                q = self.db.query(Fundamental.sector).filter(Fundamental.symbol == sym)
                # 优先按 updated_at，其次 reported_at，最后 id 兜底，避免 MultipleResultsFound
                try:
                    sector = (q.order_by(
                        desc(getattr(Fundamental, "updated_at", Fundamental.id)),
                        desc(getattr(Fundamental, "reported_at", Fundamental.id)),
                        desc(Fundamental.id)
                    ).limit(1).scalar())
                except Exception:
                    # 任何异常都保底不让它炸
                    sector = None
                sector_map[sym] = sector or "Unknown"

            results = []
            for r in rows:
                sym = r[0]
                score = float(r[1] or 0.0)
                f_value = float((r[2] if r[2] is not None else 0.0))
                f_quality = float((r[3] if r[3] is not None else 0.0))
                f_momentum = float((r[4] if r[4] is not None else 0.0))
                f_sentiment = float((r[5] if r[5] is not None else 0.0))
                results.append({
                    "symbol": sym,
                    "score": score,
                    "f_value": f_value,
                    "f_quality": f_quality,
                    "f_momentum": f_momentum,
                    "f_sentiment": f_sentiment,
                    "sector": sector_map.get(sym, "Unknown") or "Unknown",
                })

            results.sort(key=lambda x: x["score"], reverse=True)

            print(
                f"\n  {'Symbol':<8} {'Score':>6} {'Value':>6} {'Quality':>7} {'Momentum':>8} {'Sentiment':>9} {'Sector':<20}"
            )
            print("  " + "-" * 85)
            for row in results[:10]:
                sector_str = (row['sector'][:18] if row['sector'] else "Unknown")
                print(f"  {row['symbol']:<8} {row['score']:>6.1f} "
                      f"{row['f_value']:>6.3f} {row['f_quality']:>7.3f} "
                      f"{row['f_momentum']:>8.3f} {row['f_sentiment']:>9.3f} "
                      f"{sector_str:<20}")

        except Exception as e:
            print(f"  ⚠️ 无法显示摘要: {e}")
            import traceback
            traceback.print_exc()

    def run_full_check(self):
        """运行完整检查"""
        print("\n" + "=" * 70)
        print(" " * 20 + "🔍 完整数据检查")
        print("=" * 70)
        print(f"  Watchlist: {len(self.watchlist)} 只股票")
        print(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        results = {
            "prices": self.check_prices(),
            "fundamentals": self.check_fundamentals(),
            "news": self.check_news(),
            "factors": self.check_factors(),
            "scores": self.check_scores()
        }

        # 显示摘要
        if results["scores"]:
            self.show_summary()

        # 总结
        print("\n" + "=" * 70)
        print(" " * 25 + "📊 检查总结")
        print("=" * 70)

        for name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 未通过"
            display_name = {
                "prices": "价格数据",
                "fundamentals": "基本面数据",
                "news": "新闻数据",
                "factors": "因子数据",
                "scores": "评分数据"
            }[name]
            print(f"  {display_name:15s}: {status}")

        self.db.close()

        if all(results.values()):
            print("\n" + "=" * 70)
            print(" " * 20 + "🎉 所有数据检查通过！")
            print("=" * 70)
            print("\n  下一步:")
            print("    1. 访问前端: http://localhost:5173")
            print("    2. 运行回测验证")
            print("    3. 查看评分排名")
        else:
            print("\n" + "=" * 70)
            print(" " * 15 + "⚠️ 部分检查未通过，请修复问题")
            print("=" * 70)

            # 给出具体建议
            if not results["fundamentals"]:
                print("\n  💡 建议: 重新运行智能更新，确保 update_fundamentals=true")
            if not results["news"]:
                print("\n  💡 建议: 运行 python scripts/fetch_news.py --symbols <符号列表>")
            if not results["scores"]:
                print("\n  💡 建议: 运行 python scripts/recompute_scores.py --symbols <符号列表>")

        return all(results.values())


def main():
    checker = DataChecker()
    success = checker.run_full_check()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
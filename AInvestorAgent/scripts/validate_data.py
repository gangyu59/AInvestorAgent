# scripts/validate_data.py
"""
数据完整性验证脚本
在真实投资前必须运行此脚本确认数据质量
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.storage.db import SessionLocal
from backend.storage.models import PriceDaily, NewsRaw, Fundamental, ScoreDaily, PortfolioSnapshot
from sqlalchemy import func, distinct
from datetime import datetime, timedelta
import json


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_header(title):
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BLUE}{title:^70}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_pass(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")


def print_fail(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")


def print_warn(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")


def validate_data():
    """验证数据库中的数据质量"""
    db = SessionLocal()
    issues = []

    try:
        print_header("AInvestorAgent 数据验证报告")

        # ========== 1. 价格数据验证 ==========
        print(f"{Colors.BLUE}【1】价格数据验证{Colors.END}")

        price_count = db.query(PriceDaily).count()
        symbol_count = db.query(func.count(distinct(PriceDaily.symbol))).scalar()
        latest_date = db.query(func.max(PriceDaily.date)).scalar()

        print(f"   总价格记录数: {price_count:,}")
        print(f"   股票数量: {symbol_count}")
        print(f"   最新数据日期: {latest_date}")

        if price_count < 5000:
            print_warn(f"价格数据量偏少 ({price_count}条)，建议至少5000条")
            issues.append("价格数据量不足")
        else:
            print_pass("价格数据量充足")

        # 检查数据新鲜度
        if latest_date:
            days_old = (datetime.now().date() - latest_date).days
            if days_old > 2:
                print_warn(f"价格数据已过时 {days_old} 天")
                issues.append(f"价格数据过时{days_old}天")
            else:
                print_pass(f"价格数据新鲜 (最近更新: {days_old}天前)")

        # 检查主要股票数据完整性
        test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "SPY"]
        for symbol in test_symbols:
            one_year_ago = datetime.now().date() - timedelta(days=365)
            count = db.query(PriceDaily).filter(
                PriceDaily.symbol == symbol,
                PriceDaily.date >= one_year_ago
            ).count()

            if count < 200:
                print_fail(f"   {symbol}: 仅 {count} 个数据点 (期望≥200)")
                issues.append(f"{symbol}价格数据不足")
            else:
                print_pass(f"   {symbol}: {count} 个数据点")

        # ========== 2. 新闻数据验证 ==========
        print(f"\n{Colors.BLUE}【2】新闻数据验证{Colors.END}")

        news_count = db.query(NewsRaw).count()
        news_symbols = db.query(func.count(distinct(NewsRaw.symbol))).scalar()
        latest_news = db.query(func.max(NewsRaw.published_at)).scalar()

        print(f"   总新闻记录数: {news_count:,}")
        print(f"   覆盖股票数: {news_symbols}")
        if latest_news:
            print(f"   最新新闻时间: {latest_news}")

        if news_count < 100:
            print_warn(f"新闻数据量偏少 ({news_count}条)")
            issues.append("新闻数据量不足")
        else:
            print_pass("新闻数据量充足")

        # 检查新闻情绪分布
        from backend.storage.models import NewsScore
        scored_count = db.query(NewsScore).count()
        print(f"   已评分新闻: {scored_count:,}")

        if scored_count < news_count * 0.8:
            print_warn(f"部分新闻未评分 ({scored_count}/{news_count})")
            issues.append("新闻评分不完整")
        else:
            print_pass("新闻评分完整")

        # ========== 3. 基本面数据验证 ==========
        print(f"\n{Colors.BLUE}【3】基本面数据验证{Colors.END}")

        fund_count = db.query(Fundamental).count()
        fund_symbols = db.query(func.count(distinct(Fundamental.symbol))).scalar()

        print(f"   基本面记录数: {fund_count}")
        print(f"   覆盖股票数: {fund_symbols}")

        if fund_count < symbol_count * 0.5:
            print_warn("基本面数据覆盖率低于50%")
            issues.append("基本面数据不足")
        else:
            print_pass("基本面数据覆盖充分")

        # 检查关键字段完整性
        null_pe = db.query(Fundamental).filter(Fundamental.pe.is_(None)).count()
        null_pb = db.query(Fundamental).filter(Fundamental.pb.is_(None)).count()

        if null_pe > fund_count * 0.3:
            print_warn(f"PE数据缺失率: {null_pe / fund_count * 100:.1f}%")
        if null_pb > fund_count * 0.3:
            print_warn(f"PB数据缺失率: {null_pb / fund_count * 100:.1f}%")

        # ========== 4. 评分数据验证 ==========
        print(f"\n{Colors.BLUE}【4】评分数据验证{Colors.END}")

        score_count = db.query(func.count(ScoreDaily.id)).scalar()
        score_symbols = db.query(func.count(distinct(ScoreDaily.symbol))).scalar()
        latest_score_date = db.query(func.max(ScoreDaily.as_of)).scalar()

        print(f"   评分记录数: {score_count:,}")
        print(f"   覆盖股票数: {score_symbols}")
        print(f"   最新评分日期: {latest_score_date}")

        if score_count == 0:
            print_fail("没有评分数据！")
            issues.append("评分数据为空")
        else:
            print_pass("评分数据存在")

        # 检查评分范围
        invalid_scores = db.query(ScoreDaily).filter(
            (ScoreDaily.score < 0) | (ScoreDaily.score > 100)
        ).count()

        if invalid_scores > 0:
            print_fail(f"发现 {invalid_scores} 个无效评分 (不在0-100范围)")
            issues.append("存在无效评分")
        else:
            print_pass("所有评分在有效范围内")

        # ========== 5. 组合快照验证 ==========
        print(f"\n{Colors.BLUE}【5】组合快照验证{Colors.END}")

        snapshot_count = db.query(PortfolioSnapshot).count()
        print(f"   组合快照数: {snapshot_count}")

        if snapshot_count == 0:
            print_warn("没有历史组合快照")
        else:
            print_pass(f"存在 {snapshot_count} 个历史快照")

            # 检查最近的快照
            latest_snapshot = db.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.created_at.desc()
            ).first()

            if latest_snapshot:
                print(f"   最新快照日期: {latest_snapshot.as_of}")
                if latest_snapshot.holdings_json:
                    holdings = json.loads(latest_snapshot.holdings_json)
                    print(f"   持仓数量: {len(holdings)}")

                    # 验证权重总和
                    total_weight = sum(h.get('weight', 0) for h in holdings)
                    if 99 <= total_weight <= 101:
                        print_pass(f"权重总和: {total_weight:.2f}% (正常)")
                    else:
                        print_fail(f"权重总和异常: {total_weight:.2f}%")
                        issues.append("组合权重总和异常")

        # ========== 总结 ==========
        print_header("验证总结")

        if not issues:
            print_pass("✓ 所有验证通过！数据质量良好。")
            print_pass("✓ 系统已准备好进行测试投资。")
            return True
        else:
            print_fail(f"发现 {len(issues)} 个问题：")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
            print_warn("\n建议修复上述问题后再进行真实投资。")
            return False

    except Exception as e:
        print_fail(f"验证过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = validate_data()
    sys.exit(0 if success else 1)
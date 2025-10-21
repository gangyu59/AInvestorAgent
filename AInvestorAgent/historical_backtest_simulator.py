#!/usr/bin/env python3
"""
历史数据回测模拟器
用过去1年的真实数据模拟Paper Trading
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from pathlib import Path

from backend.storage.db import SessionLocal
from backend.storage.models import PriceDaily, ScoreDaily
from backend.scoring.scorer import compute_factors, aggregate_score
from backend.portfolio.allocator import propose_portfolio
from backend.portfolio.constraints import Constraints

import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')


class HistoricalBacktestSimulator:
    """历史数据回测模拟器"""

    def __init__(self,
                 watchlist: List[str],
                 initial_capital: float = 100000.0,
                 start_date: str = None,  # "2024-01-01"
                 end_date: str = None):  # "2024-12-31"

        self.watchlist = [s.upper() for s in watchlist]
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {symbol: shares}

        # 设置回测时间范围（默认过去1年）
        if end_date:
            self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            self.end_date = date.today()

        if start_date:
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            self.start_date = self.end_date - timedelta(days=365)

        # 历史记录
        self.history = []
        self.trades = []

        print(f"📅 回测期间: {self.start_date} → {self.end_date}")
        print(f"📊 股票池: {len(self.watchlist)}只")
        print(f"💰 初始资金: ${initial_capital:,.2f}\n")

    def load_historical_prices(self) -> pd.DataFrame:
        """从数据库加载历史价格"""
        print("📥 加载历史价格数据...")

        with SessionLocal() as db:
            query = db.query(PriceDaily).filter(
                PriceDaily.symbol.in_(self.watchlist),
                PriceDaily.date >= self.start_date,
                PriceDaily.date <= self.end_date
            ).order_by(PriceDaily.date)

            records = query.all()

        if not records:
            raise ValueError("❌ 未找到历史价格数据！请先运行: python scripts/fetch_prices.py")

        # 转换为DataFrame
        data = []
        for r in records:
            data.append({
                "date": r.date,
                "symbol": r.symbol,
                "close": r.close
            })

        df = pd.DataFrame(data)

        # 透视表: date × symbol
        prices_pivot = df.pivot(index='date', columns='symbol', values='close')

        # 填充缺失值（前向填充）
        prices_pivot = prices_pivot.fillna(method='ffill').fillna(method='bfill')

        print(f"✅ 已加载 {len(prices_pivot)} 个交易日的数据")
        print(f"   覆盖股票: {prices_pivot.columns.tolist()}\n")

        return prices_pivot

    def get_trading_dates(self, prices_df: pd.DataFrame, frequency: str = 'W') -> List[date]:
        """获取交易日期（每周/每月）"""
        # 使用pandas的resample获取周末日期
        dates = pd.to_datetime(prices_df.index)
        resampled = dates.to_series().resample(frequency).last()

        # 转换回date对象
        trading_dates = [d.date() for d in resampled.index]

        print(f"📅 生成 {len(trading_dates)} 个调仓日期 (频率: {frequency})")
        return trading_dates

    def calculate_scores_at_date(self, asof_date: date, lookback_days: int = 90) -> Dict[str, float]:
        """
        计算某个历史日期的评分

        Args:
            asof_date: 评分截止日期
            lookback_days: 向前看多少天的数据
        """
        with SessionLocal() as db:
            scores = {}

            for symbol in self.watchlist:
                try:
                    # 使用历史数据计算因子
                    row = compute_factors(
                        db,
                        [symbol],
                        asof=asof_date,
                        lookback_days=lookback_days
                    )[0] if compute_factors(db, [symbol], asof=asof_date) else None

                    if row:
                        score = aggregate_score(row)
                        scores[symbol] = float(score)
                    else:
                        scores[symbol] = 50.0  # 默认分数

                except Exception as e:
                    print(f"   ⚠️ {symbol} 评分失败: {e}")
                    scores[symbol] = 50.0

            return scores

    def generate_portfolio_at_date(
            self,
            asof_date: date,
            min_score: float = 50.0
    ) -> List[Dict]:
        """
        生成某个历史日期的组合建议
        """
        # 1. 计算评分
        scores = self.calculate_scores_at_date(asof_date)

        # 2. 筛选候选
        candidates = [
            {"symbol": sym, "score": score}
            for sym, score in scores.items()
            if score >= min_score
        ]

        # 按分数排序，取top10
        candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:10]

        if len(candidates) < 3:
            print(f"   ⚠️ 候选股票不足3只，降低min_score重试")
            candidates = sorted(
                [{"symbol": sym, "score": score} for sym, score in scores.items()],
                key=lambda x: x["score"],
                reverse=True
            )[:8]

        # 3. 调用组合优化
        with SessionLocal() as db:
            # 临时写入分数（用于allocator读取）
            for c in candidates:
                score_row = ScoreDaily(
                    symbol=c["symbol"],
                    as_of=asof_date,
                    score=c["score"],
                    f_value=0.5, f_quality=0.5, f_momentum=0.5, f_sentiment=0.5,
                    version_tag="backtest_v1"
                )
                db.merge(score_row)
            db.commit()

            # 生成组合
            constraints = Constraints(
                max_single=0.30,
                max_sector=0.50,
                min_positions=3,
                max_positions=10
            )

            holdings, _ = propose_portfolio(
                db,
                [c["symbol"] for c in candidates],
                constraints
            )

        return holdings

    def rebalance(
            self,
            current_date: date,
            new_holdings: List[Dict],
            prices: pd.Series
    ):
        """
        执行调仓

        Args:
            current_date: 当前日期
            new_holdings: 新组合 [{"symbol": "AAPL", "weight": 0.3}, ...]
            prices: 当日价格 Series
        """
        # 计算当前组合市值
        holdings_value = sum(
            shares * prices.get(sym, 0)
            for sym, shares in self.positions.items()
        )
        total_value = self.cash + holdings_value

        # 清仓不在新组合中的股票
        for symbol in list(self.positions.keys()):
            if symbol not in [h["symbol"] for h in new_holdings]:
                shares = self.positions[symbol]
                price = prices.get(symbol, 0)

                if price > 0:
                    proceeds = shares * price * 0.999  # 扣除0.1%成本
                    self.cash += proceeds

                    self.trades.append({
                        "date": current_date,
                        "symbol": symbol,
                        "action": "SELL",
                        "shares": shares,
                        "price": price,
                        "value": proceeds
                    })

                del self.positions[symbol]

        # 调整持仓到目标权重
        for holding in new_holdings:
            symbol = holding["symbol"]
            target_weight = holding["weight"]
            target_value = total_value * target_weight
            price = prices.get(symbol, 0)

            if price == 0:
                continue

            target_shares = int(target_value / price)
            current_shares = self.positions.get(symbol, 0)

            if target_shares == current_shares:
                continue

            diff = target_shares - current_shares
            trade_value = abs(diff) * price

            if diff > 0:  # 买入
                cost = trade_value * 1.001  # 加0.1%成本
                if self.cash >= cost:
                    self.positions[symbol] = target_shares
                    self.cash -= cost

                    self.trades.append({
                        "date": current_date,
                        "symbol": symbol,
                        "action": "BUY",
                        "shares": diff,
                        "price": price,
                        "value": cost
                    })

            elif diff < 0:  # 卖出
                proceeds = trade_value * 0.999
                self.positions[symbol] = target_shares
                self.cash += proceeds

                self.trades.append({
                    "date": current_date,
                    "symbol": symbol,
                    "action": "SELL",
                    "shares": abs(diff),
                    "price": price,
                    "value": proceeds
                })

    def calculate_portfolio_value(self, prices: pd.Series) -> float:
        """计算组合总市值"""
        holdings_value = sum(
            shares * prices.get(sym, 0)
            for sym, shares in self.positions.items()
        )
        return self.cash + holdings_value

    def run_backtest(self, rebalance_frequency: str = 'W-MON'):
        """
        运行回测

        Args:
            rebalance_frequency: 调仓频率
                'W-MON': 每周一
                'MS': 每月初
        """
        print("🚀 开始历史回测...")

        # 1. 加载历史价格
        prices_df = self.load_historical_prices()

        # 2. 确定调仓日期
        trading_dates = self.get_trading_dates(prices_df, rebalance_frequency)

        # 3. 逐日回测
        print(f"\n{'=' * 70}")
        print(f"开始逐日模拟 ({len(prices_df)} 个交易日)")
        print(f"{'=' * 70}\n")

        for idx, current_date_idx in enumerate(prices_df.index):
            # 统一转换为date对象
            if isinstance(current_date_idx, pd.Timestamp):
                current_date = current_date_idx.date()
            elif isinstance(current_date_idx, datetime):
                current_date = current_date_idx.date()
            else:
                current_date = current_date_idx

            prices_today = prices_df.loc[current_date_idx]

            # 检查是否需要调仓
            if current_date in trading_dates:
                week_num = trading_dates.index(current_date) + 1
                print(f"📅 第{week_num}周 - {current_date}")

                try:
                    # 生成新组合
                    new_holdings = self.generate_portfolio_at_date(current_date)

                    print(f"   📊 新组合: {len(new_holdings)}只股票")
                    for h in new_holdings[:3]:
                        print(f"      {h['symbol']}: {h['weight'] * 100:.1f}%")

                    # 执行调仓
                    self.rebalance(current_date, new_holdings, prices_today)

                except Exception as e:
                    print(f"   ❌ 调仓失败: {e}")

            # 记录每日净值
            total_value = self.calculate_portfolio_value(prices_today)
            nav = total_value / self.initial_capital

            self.history.append({
                "date": current_date,
                "nav": nav,
                "total_value": total_value,
                "cash": self.cash,
                "positions": len(self.positions)
            })

        print(f"\n{'=' * 70}")
        print("✅ 回测完成")
        print(f"{'=' * 70}\n")

        self.generate_report()

    def generate_report(self):
        """生成回测报告"""
        df = pd.DataFrame(self.history)

        if df.empty:
            print("❌ 无历史数据")
            return

        # 计算指标
        initial_nav = df['nav'].iloc[0]
        final_nav = df['nav'].iloc[-1]
        total_return = (final_nav / initial_nav - 1) * 100

        # 最大回撤
        df['peak'] = df['nav'].cummax()
        df['drawdown'] = (df['nav'] - df['peak']) / df['peak'] * 100
        max_drawdown = df['drawdown'].min()

        # 夏普比率
        df['return'] = df['nav'].pct_change()
        sharpe = df['return'].mean() / df['return'].std() * np.sqrt(252) if df['return'].std() > 0 else 0

        # 胜率
        wins = (df['return'] > 0).sum()
        total = len(df['return'].dropna())
        winrate = wins / total * 100 if total > 0 else 0

        # 打印报告
        print("=" * 70)
        print("📊 回测结果")
        print("=" * 70)
        print(f"回测期间: {self.start_date} → {self.end_date}")
        print(f"初始资金: ${self.initial_capital:,.2f}")
        print(f"最终净值: {final_nav:.4f}")
        print(f"最终市值: ${df['total_value'].iloc[-1]:,.2f}")
        print()
        print(f"总收益率: {total_return:+.2f}%")
        print(f"年化收益: {(pow(final_nav / initial_nav, 365 / len(df)) - 1) * 100:.2f}%")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"夏普比率: {sharpe:.3f}")
        print(f"日胜率: {winrate:.1f}%")
        print()
        print(f"交易次数: {len(self.trades)}笔")
        print(f"调仓次数: {len([t for t in self.trades if t['action'] == 'BUY']) // 2}次")
        print("=" * 70)

        # 保存详细数据
        output_dir = Path("tests/reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        df.to_csv(output_dir / "historical_backtest_nav.csv", index=False)
        pd.DataFrame(self.trades).to_csv(output_dir / "historical_backtest_trades.csv", index=False)

        # 绘制图表
        self.plot_results(df)

        print(f"\n📁 报告已保存:")
        print(f"   - 净值曲线: tests/reports/historical_backtest_nav.csv")
        print(f"   - 交易记录: tests/reports/historical_backtest_trades.csv")
        print(f"   - 可视化图: tests/reports/historical_backtest_chart.png")

    def plot_results(self, df: pd.DataFrame):
        """绘制回测结果"""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.patch.set_facecolor('#0f172a')

        for ax in axes:
            ax.set_facecolor('#1e293b')
            ax.spines['top'].set_color('#334155')
            ax.spines['bottom'].set_color('#334155')
            ax.spines['left'].set_color('#334155')
            ax.spines['right'].set_color('#334155')
            ax.tick_params(colors='#94a3b8')
            ax.grid(True, alpha=0.2, color='#475569')

        # 1. 净值曲线
        axes[0].plot(df['date'], df['nav'], color='#22c55e', linewidth=2, label='组合净值')
        axes[0].axhline(y=1.0, color='#64748b', linestyle='--', alpha=0.5, label='基准')
        axes[0].set_ylabel('净值', color='#e2e8f0', fontsize=11)
        axes[0].set_title('AInvestorAgent 历史回测 - 净值曲线',
                          color='#60a5fa', fontsize=14, fontweight='bold', pad=15)
        axes[0].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0')

        # 2. 回撤
        axes[1].fill_between(df['date'], df['drawdown'], 0,
                             color='#ef4444', alpha=0.6, label='回撤')
        axes[1].set_ylabel('回撤 (%)', color='#e2e8f0', fontsize=11)
        axes[1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0')

        # 3. 持仓数量
        axes[2].plot(df['date'], df['positions'], color='#3b82f6', linewidth=1.5, label='持仓数量')
        axes[2].set_ylabel('持仓数量', color='#e2e8f0', fontsize=11)
        axes[2].set_xlabel('日期', color='#e2e8f0', fontsize=11)
        axes[2].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0')

        plt.tight_layout()
        plt.savefig('tests/reports/historical_backtest_chart.png',
                    dpi=150, bbox_inches='tight', facecolor='#0f172a')
        plt.close()


def main():
    """主函数"""
    # 你的watchlist
    watchlist = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META", "SPY",
        "APP", "ORCL", "CEG", "VST", "LEU", "IREN", "AVGO", "AMD",
        "NBIS", "INOD", "CRWV", "SHOP"
    ]

    # 创建模拟器（过去1年）
    sim = HistoricalBacktestSimulator(
        watchlist=watchlist,
        initial_capital=100000.0,
        start_date="2024-01-01",  # 或 None（自动计算1年前）
        end_date=None  # None = 今天
    )

    # 运行回测（每周调仓）
    sim.run_backtest(rebalance_frequency='W-MON')

    print("\n✅ 历史回测完成！")


if __name__ == "__main__":
    main()
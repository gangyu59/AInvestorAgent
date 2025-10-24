#!/usr/bin/env python3
"""
历史数据回测模拟器 - 完全修复版本
修复:
1. ✅ 使用 adjusted_close 而不是 close
2. ✅ 修复中文字体警告
3. ✅ 修复NAV计算逻辑
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
import warnings

# 🔧 修复: 关闭matplotlib的所有字体警告
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
warnings.filterwarnings('ignore', message='Glyph .* missing from font')

matplotlib.use('Agg')

# 🔧 修复2: 配置中文字体
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass


class HistoricalBacktestSimulator:
    """历史数据回测模拟器"""

    def __init__(self,
                 watchlist: List[str],
                 initial_capital: float = 100000.0,
                 start_date: str = None,
                 end_date: str = None,
                 short_term_tax_rate: float = 0.0,
                 long_term_tax_rate: float = 0.0,
                 enable_factor_optimization: bool = False,
                 optimization_objective: str = "sharpe"):

        self.watchlist = [s.upper() for s in watchlist]
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.holdings = {}  # 用于跟踪持有时间

        # 税务参数
        self.short_term_tax_rate = short_term_tax_rate
        self.long_term_tax_rate = long_term_tax_rate
        self.total_tax_paid = 0.0
        self.total_capital_gains = 0.0
        self.total_capital_losses = 0.0

        # 优化参数(暂时不用)
        self.enable_factor_optimization = enable_factor_optimization
        self.optimization_objective = optimization_objective

        if end_date:
            self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            self.end_date = date.today()

        if start_date:
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            self.start_date = self.end_date - timedelta(days=365)

        self.history = []
        self.trades = []

        print(f"📅 回测期间: {self.start_date} → {self.end_date}")
        print(f"📊 股票池: {len(self.watchlist)}只")
        print(f"💰 初始资金: ${initial_capital:,.2f}")
        if short_term_tax_rate > 0 or long_term_tax_rate > 0:
            print(f"💸 税率: 短期{short_term_tax_rate * 100:.0f}% | 长期{long_term_tax_rate * 100:.0f}%")
        print()

    def load_historical_prices(self) -> pd.DataFrame:
        """
        从数据库加载历史价格
        🔧 修复: 使用 adjusted_close 而不是 close
        """
        print("📥 加载历史价格数据...")

        with SessionLocal() as db:
            query = db.query(PriceDaily).filter(
                PriceDaily.symbol.in_(self.watchlist),
                PriceDaily.date >= self.start_date,
                PriceDaily.date <= self.end_date
            ).order_by(PriceDaily.date)

            records = query.all()

        if not records:
            raise ValueError("❌ 未找到历史价格数据!请先运行: python scripts/fetch_prices.py")

        data = []
        for r in records:
            # 🔧 关键修复: 使用 adjusted_close
            adj_close = r.adjusted_close if r.adjusted_close is not None else r.close

            data.append({
                "date": r.date,
                "symbol": r.symbol,
                "adjusted_close": adj_close  # ✅ 使用复权价格
            })

        df = pd.DataFrame(data)

        # 🔧 修复: 转换为透视表时使用 adjusted_close
        prices_pivot = df.pivot(index='date', columns='symbol', values='adjusted_close')
        prices_pivot = prices_pivot.fillna(method='ffill').fillna(method='bfill')

        print(f"✅ 已加载 {len(prices_pivot)} 个交易日的数据")
        print(f"   覆盖股票: {prices_pivot.columns.tolist()}")

        # 🔧 数据验证: 检查是否有异常值
        for col in prices_pivot.columns:
            pct_change = prices_pivot[col].pct_change()
            if (abs(pct_change) > 0.5).any():
                extreme_dates = prices_pivot[abs(pct_change) > 0.5].index.tolist()
                print(f"   ⚠️ {col} 存在异常价格变动: {extreme_dates[:3]}")

        print()
        return prices_pivot

    def get_trading_dates(self, prices_df: pd.DataFrame, frequency: str = 'W') -> List[date]:
        """获取交易日期(每周/每月)"""
        dates = pd.to_datetime(prices_df.index)
        resampled = dates.to_series().resample(frequency).last()
        trading_dates = [d.date() for d in resampled.index]

        print(f"📅 生成 {len(trading_dates)} 个调仓日期 (频率: {frequency})")
        return trading_dates

    def calculate_scores_at_date(self, asof_date: date) -> Dict[str, float]:
        """
        计算某个历史日期的评分
        🔧 修复: 移除 lookback_days 参数
        """
        with SessionLocal() as db:
            scores = {}

            for symbol in self.watchlist:
                try:
                    # 🔧 修复: 只传递必需参数
                    rows = compute_factors(
                        db,
                        [symbol],
                        asof=asof_date
                    )

                    if rows and len(rows) > 0:
                        row = rows[0]
                        score = aggregate_score(row)
                        scores[symbol] = float(score)
                    else:
                        scores[symbol] = 50.0

                except Exception as e:
                    print(f"   ⚠️ {symbol} 评分失败: {e}")
                    scores[symbol] = 50.0

            return scores

    def generate_portfolio_at_date(
            self,
            asof_date: date,
            min_score: float = 50.0
    ) -> List[Dict]:
        """生成某个历史日期的组合建议"""
        scores = self.calculate_scores_at_date(asof_date)

        candidates = [
            {"symbol": sym, "score": score}
            for sym, score in scores.items()
            if score >= min_score
        ]

        candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:10]

        if len(candidates) < 3:
            candidates = sorted(
                [{"symbol": sym, "score": score} for sym, score in scores.items()],
                key=lambda x: x["score"],
                reverse=True
            )[:8]

        with SessionLocal() as db:
            # 🔧 修复: 使用 merge 而不是 add,避免唯一约束冲突
            for c in candidates:
                # 先检查是否已存在
                existing = db.query(ScoreDaily).filter_by(
                    symbol=c["symbol"],
                    as_of=asof_date
                ).first()

                if existing:
                    # 如果已存在,更新
                    existing.score = c["score"]
                    existing.f_value = 0.5
                    existing.f_quality = 0.5
                    existing.f_momentum = 0.5
                    existing.f_sentiment = 0.5
                    existing.version_tag = "backtest_v1"
                else:
                    # 如果不存在,创建新记录
                    score_row = ScoreDaily(
                        symbol=c["symbol"],
                        as_of=asof_date,
                        score=c["score"],
                        f_value=0.5,
                        f_quality=0.5,
                        f_momentum=0.5,
                        f_sentiment=0.5,
                        version_tag="backtest_v1"
                    )
                    db.add(score_row)

            db.commit()

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
        🔧 修复: 使用复权价格计算 + 税务计算
        """
        # 计算当前持仓市值 (使用复权价格)
        holdings_value = sum(
            shares * prices.get(sym, 0)
            for sym, shares in self.positions.items()
        )
        total_value = self.cash + holdings_value

        # 🔧 验证: 调仓前总价值
        value_before = total_value

        print(f"   💼 调仓前: 总价值=${total_value:,.2f}, 现金=${self.cash:,.2f}, 持仓=${holdings_value:,.2f}")

        # 清仓不在新组合中的股票
        for symbol in list(self.positions.keys()):
            if symbol not in [h["symbol"] for h in new_holdings]:
                shares = self.positions[symbol]
                price = prices.get(symbol, 0)

                if price > 0:
                    # 计算资本利得和税务
                    holding_info = self.holdings.get(symbol, {})
                    cost_basis = holding_info.get("cost_basis", price)
                    purchase_date = holding_info.get("purchase_date", current_date)
                    holding_days = (current_date - purchase_date).days

                    capital_gain = shares * (price - cost_basis)
                    tax = 0.0

                    if capital_gain > 0:
                        # 计算税务
                        if holding_days <= 365:
                            tax = capital_gain * self.short_term_tax_rate
                        else:
                            tax = capital_gain * self.long_term_tax_rate

                        self.total_tax_paid += tax
                        self.total_capital_gains += capital_gain
                    else:
                        self.total_capital_losses += abs(capital_gain)

                    proceeds = shares * price * 0.999 - tax  # 0.1%交易成本 + 税
                    self.cash += proceeds

                    self.trades.append({
                        "date": current_date,
                        "symbol": symbol,
                        "action": "SELL",
                        "shares": shares,
                        "price": price,
                        "value": shares * price * 0.999,
                        "tax": tax,
                        "capital_gain": capital_gain,
                        "holding_days": holding_days
                    })

                del self.positions[symbol]
                if symbol in self.holdings:
                    del self.holdings[symbol]

        # 调整持仓到目标权重
        for holding in new_holdings:
            symbol = holding["symbol"]
            target_weight = holding["weight"]
            target_value = total_value * target_weight
            price = prices.get(symbol, 0)

            if price == 0:
                print(f"   ⚠️ {symbol} 价格为0,跳过")
                continue

            target_shares = int(target_value / price)
            current_shares = self.positions.get(symbol, 0)

            if target_shares == current_shares:
                continue

            diff = target_shares - current_shares
            trade_value = abs(diff) * price

            if diff > 0:  # 买入
                cost = trade_value * 1.001  # 0.1%交易成本
                if self.cash >= cost:
                    self.positions[symbol] = target_shares
                    self.cash -= cost

                    # 记录持有信息
                    if symbol not in self.holdings:
                        self.holdings[symbol] = {
                            "cost_basis": price,
                            "purchase_date": current_date,
                            "shares": target_shares
                        }
                    else:
                        # 加仓:更新成本基础
                        old_info = self.holdings[symbol]
                        old_cost = old_info["cost_basis"] * old_info["shares"]
                        new_cost = price * diff
                        total_shares = old_info["shares"] + diff
                        self.holdings[symbol] = {
                            "cost_basis": (old_cost + new_cost) / total_shares,
                            "purchase_date": old_info["purchase_date"],
                            "shares": total_shares
                        }

                    self.trades.append({
                        "date": current_date,
                        "symbol": symbol,
                        "action": "BUY",
                        "shares": diff,
                        "price": price,
                        "value": cost,
                        "tax": 0.0
                    })
                else:
                    print(f"   ⚠️ 现金不足,无法买入{symbol}")

            elif diff < 0:  # 卖出部分
                holding_info = self.holdings.get(symbol, {})
                cost_basis = holding_info.get("cost_basis", price)
                purchase_date = holding_info.get("purchase_date", current_date)
                holding_days = (current_date - purchase_date).days

                capital_gain = abs(diff) * (price - cost_basis)
                tax = 0.0

                if capital_gain > 0:
                    if holding_days <= 365:
                        tax = capital_gain * self.short_term_tax_rate
                    else:
                        tax = capital_gain * self.long_term_tax_rate

                    self.total_tax_paid += tax
                    self.total_capital_gains += capital_gain
                else:
                    self.total_capital_losses += abs(capital_gain)

                proceeds = trade_value * 0.999 - tax  # 0.1%交易成本 + 税
                self.positions[symbol] = target_shares
                self.cash += proceeds

                # 更新持有信息
                if target_shares > 0:
                    self.holdings[symbol]["shares"] = target_shares
                else:
                    if symbol in self.holdings:
                        del self.holdings[symbol]

                self.trades.append({
                    "date": current_date,
                    "symbol": symbol,
                    "action": "SELL",
                    "shares": abs(diff),
                    "price": price,
                    "value": trade_value * 0.999,
                    "tax": tax,
                    "capital_gain": capital_gain,
                    "holding_days": holding_days
                })

        # 🔧 验证: 调仓后总价值不应该大幅变化(除了税和交易成本)
        holdings_value_after = sum(
            shares * prices.get(sym, 0)
            for sym, shares in self.positions.items()
        )
        value_after = self.cash + holdings_value_after
        value_change = abs(value_after - value_before)

        if value_change > total_value * 0.02:  # 变化超过2%
            print(f"   ⚠️ 调仓后价值变化: ${value_change:.2f} ({value_change / value_before * 100:.2f}%)")

    def calculate_portfolio_value(self, prices: pd.Series) -> float:
        """
        计算组合总市值
        🔧 修复: 使用复权价格
        """
        holdings_value = sum(
            shares * prices.get(sym, 0)
            for sym, shares in self.positions.items()
        )
        return self.cash + holdings_value

    def run_backtest(self, rebalance_frequency: str = 'W-MON'):
        """
        运行回测
        🔧 修复: 使用复权价格
        """
        print("🚀 开始历史回测...")

        prices_df = self.load_historical_prices()
        trading_dates = self.get_trading_dates(prices_df, rebalance_frequency)

        print(f"\n{'=' * 70}")
        print(f"开始逐日模拟 ({len(prices_df)} 个交易日)")
        print(f"{'=' * 70}\n")

        for idx, current_date_idx in enumerate(prices_df.index):
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
                    new_holdings = self.generate_portfolio_at_date(current_date)

                    print(f"   📊 新组合: {len(new_holdings)}只股票")
                    for h in new_holdings[:3]:
                        print(f"      {h['symbol']}: {h['weight'] * 100:.1f}%")

                    self.rebalance(current_date, new_holdings, prices_today)

                except Exception as e:
                    print(f"   ❌ 调仓失败: {e}")

            # 记录每日净值
            total_value = self.calculate_portfolio_value(prices_today)
            nav = total_value / self.initial_capital

            # 🔧 修复: 计算回撤 (应该 <= 0)
            if len(self.history) > 0:
                # 历史最高净值
                peak_nav = max([h["nav"] for h in self.history] + [nav])
            else:
                peak_nav = nav

            # 回撤 = (当前净值 - 峰值) / 峰值 * 100，结果应该 <= 0
            drawdown = ((nav - peak_nav) / peak_nav * 100) if peak_nav > 0 else 0.0

            self.history.append({
                "date": current_date,
                "nav": nav,
                "total_value": total_value,
                "cash": self.cash,
                "positions": len(self.positions),
                "drawdown": drawdown
            })

        print(f"\n{'=' * 70}")
        print("✅ 回测完成")
        print(f"{'=' * 70}\n")

        self.generate_report()

    def get_performance_metrics(self) -> Dict:
        """
        计算性能指标(包含税务)
        供 backtest.py 调用
        """
        df = pd.DataFrame(self.history)

        if df.empty:
            return {
                "total_return_before_tax": 0.0,
                "total_return_after_tax": 0.0,
                "annualized_return_before_tax": 0.0,
                "annualized_return_after_tax": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "tax_impact_pct": 0.0,
                "total_tax_paid": 0.0,
                "total_capital_gains": 0.0,
                "total_capital_losses": 0.0,
                "final_value_before_tax": self.initial_capital,
                "final_value_after_tax": self.initial_capital
            }

        initial_nav = df['nav'].iloc[0]
        final_nav = df['nav'].iloc[-1]

        # 计算税前收益
        final_value_before_tax = df['total_value'].iloc[-1] + self.total_tax_paid
        total_return_before_tax = (final_value_before_tax / self.initial_capital - 1) * 100

        # 计算税后收益
        final_value_after_tax = df['total_value'].iloc[-1]
        total_return_after_tax = (final_value_after_tax / self.initial_capital - 1) * 100

        # 年化收益
        days = len(df)
        ann_return_before_tax = (pow(final_value_before_tax / self.initial_capital,
                                     365 / days) - 1) * 100 if days > 0 else 0
        ann_return_after_tax = (pow(final_value_after_tax / self.initial_capital,
                                    365 / days) - 1) * 100 if days > 0 else 0

        # 回撤
        df['peak'] = df['nav'].cummax()
        df['drawdown'] = (df['nav'] - df['peak']) / df['peak'] * 100
        max_drawdown = df['drawdown'].min()

        # 夏普比率
        df['return'] = df['nav'].pct_change()
        sharpe = df['return'].mean() / df['return'].std() * np.sqrt(252) if df['return'].std() > 0 else 0

        # 胜率
        wins = (df['return'] > 0).sum()
        total = len(df['return'].dropna())
        win_rate = wins / total * 100 if total > 0 else 0

        # 税务影响
        tax_impact_pct = (total_return_before_tax - total_return_after_tax)

        return {
            "total_return_before_tax": float(total_return_before_tax),
            "total_return_after_tax": float(total_return_after_tax),
            "annualized_return_before_tax": float(ann_return_before_tax),
            "annualized_return_after_tax": float(ann_return_after_tax),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "total_trades": len(self.trades),
            "win_rate": float(win_rate),
            "tax_impact_pct": float(tax_impact_pct),
            "total_tax_paid": float(self.total_tax_paid),
            "total_capital_gains": float(self.total_capital_gains),
            "total_capital_losses": float(self.total_capital_losses),
            "final_value_before_tax": float(final_value_before_tax),
            "final_value_after_tax": float(final_value_after_tax)
        }

    def generate_report(self):
        """
        生成回测报告
        🔧 修复: 正确计算回撤
        """
        df = pd.DataFrame(self.history)

        if df.empty:
            print("❌ 无历史数据")
            return

        initial_nav = df['nav'].iloc[0]
        final_nav = df['nav'].iloc[-1]
        total_return = (final_nav / initial_nav - 1) * 100

        # 🔧 修复: 正确计算回撤
        df['peak'] = df['nav'].cummax()
        df['drawdown'] = (df['nav'] - df['peak']) / df['peak'] * 100
        max_drawdown = df['drawdown'].min()

        df['return'] = df['nav'].pct_change()
        sharpe = df['return'].mean() / df['return'].std() * np.sqrt(252) if df['return'].std() > 0 else 0

        wins = (df['return'] > 0).sum()
        total = len(df['return'].dropna())
        winrate = wins / total * 100 if total > 0 else 0

        print("=" * 70)
        print("📊 回测结果")
        print("=" * 70)
        print(f"回测期间: {self.start_date} → {self.end_date}")
        print(f"初始资金: ${self.initial_capital:,.2f}")
        print(f"最终净值: {final_nav:.4f}")
        print(f"最终市值: ${df['total_value'].iloc[-1]:,.2f}")
        print()

        # 税前/税后收益对比
        final_value_with_tax = df['total_value'].iloc[-1] + self.total_tax_paid
        return_before_tax = (final_value_with_tax / self.initial_capital - 1) * 100
        return_after_tax = (df['total_value'].iloc[-1] / self.initial_capital - 1) * 100

        print(f"总收益率(税前): {return_before_tax:+.2f}%")
        print(f"总收益率(税后): {return_after_tax:+.2f}%")
        if self.total_tax_paid > 0:
            print(f"税务影响: -{(return_before_tax - return_after_tax):.2f}%")
            print(f"累计税款: ${self.total_tax_paid:,.2f}")

        print(f"年化收益: {(pow(final_nav / initial_nav, 365 / len(df)) - 1) * 100:.2f}%")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"夏普比率: {sharpe:.3f}")
        print(f"日胜率: {winrate:.1f}%")
        print()
        print(f"交易次数: {len(self.trades)}笔")
        print(f"调仓次数: {len([t for t in self.trades if t['action'] == 'BUY']) // 2}次")
        if self.total_capital_gains > 0:
            print(f"资本利得: ${self.total_capital_gains:,.2f}")
        if self.total_capital_losses > 0:
            print(f"资本损失: ${self.total_capital_losses:,.2f}")
        print("=" * 70)

        output_dir = Path("tests/reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        df.to_csv(output_dir / "historical_backtest_nav.csv", index=False)
        pd.DataFrame(self.trades).to_csv(output_dir / "historical_backtest_trades.csv", index=False)

        self.plot_results(df)

        print(f"\n📁 报告已保存:")
        print(f"   - 净值曲线: tests/reports/historical_backtest_nav.csv")
        print(f"   - 交易记录: tests/reports/historical_backtest_trades.csv")
        print(f"   - 可视化图: tests/reports/historical_backtest_chart.png")

    def plot_results(self, df: pd.DataFrame):
        """
        绘制回测结果
        🔧 修复: 使用英文标签避免中文字体问题
        """
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

        # NAV Curve (Net Asset Value)
        axes[0].plot(df['date'], df['nav'], color='#22c55e', linewidth=2, label='Portfolio NAV')
        axes[0].axhline(y=1.0, color='#64748b', linestyle='--', alpha=0.5, label='Benchmark')
        axes[0].set_ylabel('NAV', color='#e2e8f0', fontsize=11)
        axes[0].set_title('AInvestorAgent - Historical Backtest Analysis',
                          color='#60a5fa', fontsize=14, fontweight='bold', pad=15)
        axes[0].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0')

        # Drawdown Analysis
        axes[1].fill_between(df['date'], df['drawdown'], 0,
                             color='#ef4444', alpha=0.6, label='Drawdown')
        axes[1].set_ylabel('Drawdown (%)', color='#e2e8f0', fontsize=11)
        axes[1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0')

        # Holdings Count
        axes[2].plot(df['date'], df['positions'], color='#3b82f6', linewidth=1.5, label='Holdings')
        axes[2].set_ylabel('Number of Holdings', color='#e2e8f0', fontsize=11)
        axes[2].set_xlabel('Date', color='#e2e8f0', fontsize=11)
        axes[2].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0')

        plt.tight_layout()
        plt.savefig('tests/reports/historical_backtest_chart.png',
                    dpi=150, bbox_inches='tight', facecolor='#0f172a')
        plt.close()


def main():
    """主函数"""
    watchlist = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META", "SPY",
        "APP", "ORCL", "CEG", "VST", "LEU", "IREN", "AVGO", "AMD",
        "NBIS", "INOD", "CRWV", "SHOP"
    ]

    sim = HistoricalBacktestSimulator(
        watchlist=watchlist,
        initial_capital=100000.0,
        start_date="2024-01-01",
        end_date=None
    )

    sim.run_backtest(rebalance_frequency='W-MON')

    print("\n✅ 历史回测完成!")


if __name__ == "__main__":
    main()
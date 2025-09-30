"""
AInvestorAgent 30天实盘模拟测试
在真实投资前，用虚拟账户跟踪系统表现
"""
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端

class PaperTradingSimulator:
    """实盘模拟器"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # {symbol: shares}
        self.history = []
        self.base_url = "http://localhost:8000"
        self.log_file = Path("tests/reports/paper_trading_log.jsonl")
        self.start_date = datetime.now()

    def log_event(self, event_type: str, data: dict):
        """记录事件到日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        print(f"[{entry['timestamp']}] {event_type}: {data.get('message', '')}")

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """获取当前价格"""
        prices = {}
        for symbol in symbols:
            try:
                response = requests.get(
                    f"{self.base_url}/api/prices/{symbol}?range=1D",
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("prices"):
                        prices[symbol] = data["prices"][-1]["close"]
            except Exception as e:
                self.log_event("ERROR", {
                    "message": f"获取{symbol}价格失败",
                    "error": str(e)
                })
        return prices

    def calculate_portfolio_value(self, prices: Dict[str, float]) -> float:
        """计算组合总值"""
        holdings_value = sum(
            shares * prices.get(symbol, 0)
            for symbol, shares in self.positions.items()
        )
        return self.current_capital + holdings_value

    def rebalance(self, new_holdings: List[Dict]):
        """调仓"""
        self.log_event("REBALANCE_START", {
            "message": f"开始调仓，当前持仓{len(self.positions)}支"
        })

        # 获取当前价格
        all_symbols = list(set(
            [h["symbol"] for h in new_holdings] +
            list(self.positions.keys())
        ))
        prices = self.get_current_prices(all_symbols)

        # 计算当前总市值
        total_value = self.calculate_portfolio_value(prices)

        # 清算不在新组合中的持仓
        for symbol in list(self.positions.keys()):
            if symbol not in [h["symbol"] for h in new_holdings]:
                shares = self.positions[symbol]
                price = prices.get(symbol, 0)
                proceeds = shares * price * 0.999  # 扣除0.1%成本
                self.current_capital += proceeds
                del self.positions[symbol]

                self.log_event("SELL", {
                    "symbol": symbol,
                    "shares": shares,
                    "price": price,
                    "proceeds": proceeds
                })

        # 买入新持仓或调整权重
        for holding in new_holdings:
            symbol = holding["symbol"]
            target_weight = holding["weight"] / 100  # 转为小数
            target_value = total_value * target_weight
            price = prices.get(symbol, 0)

            if price == 0:
                self.log_event("WARNING", {
                    "message": f"{symbol}价格无法获取，跳过"
                })
                continue

            target_shares = int(target_value / price)
            current_shares = self.positions.get(symbol, 0)

            if target_shares != current_shares:
                diff = target_shares - current_shares
                cost = abs(diff) * price * 1.001  # 加0.1%成本

                if diff > 0:  # 买入
                    if self.current_capital >= cost:
                        self.positions[symbol] = target_shares
                        self.current_capital -= cost
                        self.log_event("BUY", {
                            "symbol": symbol,
                            "shares": diff,
                            "price": price,
                            "cost": cost
                        })
                else:  # 卖出
                    self.positions[symbol] = target_shares
                    self.current_capital += cost * 0.998  # 扣除双边成本
                    self.log_event("SELL", {
                        "symbol": symbol,
                        "shares": -diff,
                        "price": price,
                        "proceeds": cost * 0.998
                    })

        # 记录调仓后状态
        final_value = self.calculate_portfolio_value(prices)
        self.log_event("REBALANCE_COMPLETE", {
            "message": "调仓完成",
            "positions": len(self.positions),
            "cash": self.current_capital,
            "total_value": final_value
        })

    def run_weekly_update(self, week_num: int):
        """每周更新"""
        print(f"\n{'='*60}")
        print(f"第 {week_num} 周 - {datetime.now().strftime('%Y-%m-%d')}")
        print(f"{'='*60}")

        try:
            # 调用系统生成新组合
            response = requests.post(
                f"{self.base_url}/api/orchestrator/decide",
                json={"topk": 10},
                timeout=120
            )

            if response.status_code != 200:
                self.log_event("ERROR", {
                    "message": "组合生成失败",
                    "status_code": response.status_code
                })
                return False

            data = response.json()
            holdings = data.get("holdings", [])

            if not holdings:
                self.log_event("WARNING", {
                    "message": "未获取到组合建议"
                })
                return False

            # 执行调仓
            self.rebalance(holdings)

            # 记录每日净值
            prices = self.get_current_prices(list(self.positions.keys()))
            nav = self.calculate_portfolio_value(prices) / self.initial_capital

            self.history.append({
                "date": datetime.now().isoformat(),
                "week": week_num,
                "nav": nav,
                "cash": self.current_capital,
                "positions": len(self.positions),
                "holdings": [
                    {
                        "symbol": s,
                        "shares": sh,
                        "value": sh * prices.get(s, 0)
                    }
                    for s, sh in self.positions.items()
                ]
            })

            print(f"\n当前净值: {nav:.4f}")
            print(f"现金余额: ${self.current_capital:,.2f}")
            print(f"持仓数量: {len(self.positions)}支")

            return True

        except Exception as e:
            self.log_event("ERROR", {
                "message": "周度更新失败",
                "error": str(e)
            })
            return False

    def run_simulation(self, weeks: int = 4):
        """运行模拟（默认4周 = 30天）"""
        print("🚀 开始30天实盘模拟")
        print(f"初始资金: ${self.initial_capital:,.2f}")
        print(f"模拟周数: {weeks}周")
        print(f"开始日期: {self.start_date.strftime('%Y-%m-%d')}\n")

        self.log_event("SIMULATION_START", {
            "initial_capital": self.initial_capital,
            "weeks": weeks
        })

        for week in range(1, weeks + 1):
            success = self.run_weekly_update(week)
            if not success:
                print(f"⚠️ 第{week}周更新失败，继续...")

        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("生成测试报告")
        print("="*60)

        if not self.history:
            print("❌ 无历史数据，无法生成报告")
            return

        # 计算指标
        df = pd.DataFrame(self.history)
        initial_nav = 1.0
        final_nav = df['nav'].iloc[-1]
        total_return = (final_nav - initial_nav) / initial_nav

        # 计算最大回撤
        df['peak'] = df['nav'].cummax()
        df['drawdown'] = (df['nav'] - df['peak']) / df['peak']
        max_drawdown = df['drawdown'].min()

        # 计算Sharpe（简化版）
        returns = df['nav'].pct_change().dropna()
        sharpe = returns.mean() / returns.std() * (252 ** 0.5) if len(returns) > 1 else 0

        # 生成文本报告
        report = f"""
# AInvestorAgent 30天实盘模拟报告

**模拟期间**: {self.start_date.strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}
**初始资金**: ${self.initial_capital:,.2f}

## 📊 业绩概览

| 指标 | 数值 |
|------|------|
| 总收益率 | {total_return:.2%} |
| 最终净值 | {final_nav:.4f} |
| 最大回撤 | {max_drawdown:.2%} |
| Sharpe比率 | {sharpe:.3f} |
| 调仓次数 | {len(self.history)} 次 |

## 📈 净值曲线

（见图表: paper_trading_nav.png）

## ⚠️ 风险提示

1. 本报告基于历史数据模拟，不代表未来表现
2. 实盘交易可能面临滑点、流动性等额外风险
3. 建议初始投资金额 ≤ 总资金的10%

## ✅ 就绪度评估

"""

        # 评估就绪度
        issues = []
        if total_return < -0.05:
            issues.append("❌ 模拟期收益为负")
        if max_drawdown < -0.15:
            issues.append("⚠️ 最大回撤超过15%")
        if sharpe < 0.5:
            issues.append("⚠️ Sharpe比率低于0.5")

        if not issues:
            report += "✅ **系统表现良好，可以考虑小额实盘**\n"
        else:
            report += "⚠️ **发现以下问题，建议进一步优化:**\n\n"
            for issue in issues:
                report += f"- {issue}\n"

        # 保存报告
        report_file = Path("tests/reports/PAPER_TRADING_REPORT.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✓ 报告已保存: {report_file}")

        # 绘制净值曲线
        self.plot_nav_curve(df)

        # 保存详细数据
        df.to_csv("tests/reports/paper_trading_history.csv", index=False)
        print(f"✓ 历史数据已保存: tests/reports/paper_trading_history.csv")

    def plot_nav_curve(self, df: pd.DataFrame):
        """绘制净值曲线"""
        plt.figure(figsize=(12, 6))
        plt.style.use('dark_background')

        # 净值曲线
        plt.subplot(2, 1, 1)
        plt.plot(df.index, df['nav'], color='#4CAF50', linewidth=2, label='组合净值')
        plt.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='初始净值')
        plt.ylabel('净值')
        plt.title('AInvestorAgent 30天实盘模拟 - 净值曲线', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(alpha=0.3)

        # 回撤曲线
        plt.subplot(2, 1, 2)
        plt.fill_between(df.index, df['drawdown'] * 100, 0,
                         color='#F44336', alpha=0.5, label='回撤')
        plt.ylabel('回撤 (%)')
        plt.xlabel('周数')
        plt.legend()
        plt.grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig('tests/reports/paper_trading_nav.png', dpi=150, bbox_inches='tight')
        print(f"✓ 图表已保存: tests/reports/paper_trading_nav.png")
        plt.close()

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='AInvestorAgent 实盘模拟测试')
    parser.add_argument('--capital', type=float, default=100000,
                       help='初始资金（默认: 100000）')
    parser.add_argument('--weeks', type=int, default=4,
                       help='模拟周数（默认: 4周）')

    args = parser.parse_args()

    simulator = PaperTradingSimulator(initial_capital=args.capital)
    simulator.run_simulation(weeks=args.weeks)

    print("\n✅ 30天实盘模拟完成！")
    print("\n📄 查看报告:")
    print("   - 报告: tests/reports/PAPER_TRADING_REPORT.md")
    print("   - 图表: tests/reports/paper_trading_nav.png")
    print("   - 数据: tests/reports/paper_trading_history.csv")
    print("   - 日志: tests/reports/paper_trading_log.jsonl")

if __name__ == "__main__":
    main()
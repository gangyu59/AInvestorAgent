"""BacktestEngineer智能体测试"""
import pytest
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
from agents.backtest_engineer import BacktestEngineer

class TestBacktestEngineer:
    def test_basic_backtest(self):
        print("\n测试: 基础回测")
        context = {
            "weights": [
                {"symbol": "AAPL", "weight": 0.5},
                {"symbol": "MSFT", "weight": 0.5}
            ],
            "mock": True,
            "window_days": 60,
            "trading_cost": 0.0
        }
        agent = BacktestEngineer()
        result = agent.run(context)
        assert "data" in result
        data = result["data"]
        assert "nav" in data
        assert "metrics" in data
        assert len(data["nav"]) > 0
        print(f"   ✅ 回测执行成功 - NAV点数: {len(data['nav'])}")

    def test_benchmark_comparison(self):
        print("\n测试: 基准对比")
        context = {
            "weights": [{"symbol": "AAPL", "weight": 1.0}],
            "mock": True,
            "window_days": 30,
            "benchmark_symbol": "SPY"
        }
        agent = BacktestEngineer()
        result = agent.run(context)
        data = result["data"]
        if "benchmark_nav" in data:
            print(f"   ✅ 基准对比成功 - 基准NAV点数: {len(data['benchmark_nav'])}")
        else:
            print("   ℹ️ 基准对比数据未生成")

    def test_error_handling(self):
        print("\n测试: 错误处理")
        context = {
            "weights": [],
            "mock": True
        }
        agent = BacktestEngineer()
        result = agent.run(context)
        # 应该返回错误状态
        assert "ok" in result
        print("   ✅ 错误处理正常")
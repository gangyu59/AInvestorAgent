"""PortfolioManager智能体测试"""
import pytest
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
from agents.portfolio_manager import PortfolioManager

class TestPortfolioManager:
    def test_weight_allocation(self):
        print("\n测试: 权重分配")
        scores = {
            "AAPL": {"score": 85},
            "MSFT": {"score": 80},
            "GOOGL": {"score": 75},
            "NVDA": {"score": 70}
        }
        pm = PortfolioManager()
        result = pm.act(scores=scores)
        assert "weights" in result
        weights = result["weights"]
        total_weight = sum(w["weight"] for w in weights)
        assert 0.99 <= total_weight <= 1.01
        print(f"   ✅ 权重分配成功 - 持仓数: {len(weights)}, 总权重: {total_weight:.2%}")

    def test_single_stock(self):
        print("\n测试: 单股票权重")
        scores = {
            "AAPL": {"score": 90}
        }
        pm = PortfolioManager()
        result = pm.act(scores=scores)
        weights = result["weights"]
        assert len(weights) == 1
        assert weights[0]["weight"] == 1.0
        print(f"   ✅ 单股票权重正确: {weights[0]['weight']:.1%}")

    def test_empty_scores(self):
        print("\n测试: 空分数处理")
        scores = {}
        pm = PortfolioManager()
        result = pm.act(scores=scores)
        assert "ok" in result
        if not result["ok"]:
            print("   ✅ 空分数正确处理")
        else:
            weights = result.get("weights", [])
            print(f"   ℹ️ 返回空权重列表: {len(weights)}")
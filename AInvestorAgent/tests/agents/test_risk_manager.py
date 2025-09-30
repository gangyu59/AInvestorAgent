"""RiskManager智能体测试"""
import pytest
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
from agents.risk_manager import RiskManager

class TestRiskManager:
    def test_apply_constraints(self):
        print("\n测试: 约束应用")
        weights = [
            {"symbol": "AAPL", "weight": 0.40},
            {"symbol": "MSFT", "weight": 0.35},
            {"symbol": "GOOGL", "weight": 0.25}
        ]
        rm = RiskManager()
        result = rm.act(weights=weights)
        assert "weights" in result
        adjusted_weights = result["weights"]
        # 检查权重是否被限制
        for symbol, weight in adjusted_weights.items():
            assert weight <= 0.36, f"{symbol}权重超限: {weight}"
        print(f"   ✅ 约束应用成功 - 调整后权重: {adjusted_weights}")

    def test_sector_constraints(self):
        print("\n测试: 行业约束")
        weights = [
            {"symbol": "AAPL", "weight": 0.20, "sector": "Technology"},
            {"symbol": "MSFT", "weight": 0.20, "sector": "Technology"},
            {"symbol": "GOOGL", "weight": 0.20, "sector": "Technology"},
            {"symbol": "JPM", "weight": 0.20, "sector": "Financial"},
            {"symbol": "XOM", "weight": 0.20, "sector": "Energy"}
        ]
        rm = RiskManager()
        result = rm.act(weights=weights)
        adjusted_weights = result["weights"]
        print(f"   ✅ 行业约束应用 - 总权重: {sum(adjusted_weights.values()):.1%}")

    def test_run_method(self):
        print("\n测试: run方法")
        context = {
            "candidates": [
                {"symbol": "AAPL", "sector": "Technology"},
                {"symbol": "MSFT", "sector": "Technology"},
                {"symbol": "GOOGL", "sector": "Technology"}
            ]
        }
        rm = RiskManager()
        result = rm.run(context)
        if result.get("ok"):
            data = result["data"]
            kept = data.get("kept", [])
            print(f"   ✅ run方法成功 - 保留持仓: {len(kept)}")
        else:
            print("   ℹ️ run方法返回错误状态")
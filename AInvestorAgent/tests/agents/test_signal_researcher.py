"""SignalResearcher智能体测试"""
import pytest
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
from agents.signal_researcher import SignalResearcher

class TestSignalResearcher:
    def test_extract_factors(self):
        print("\n测试: 因子提取")
        context = {
            "symbol": "AAPL",
            "prices": [{"close": 180.0 + i} for i in range(60)],
            "fundamentals": {"pe": 25.0, "roe": 0.30},
            "news_raw": [{"title": "Positive news", "summary": "Good earnings"}],
            "mock": True
        }
        researcher = SignalResearcher()
        result = researcher.run(context)
        assert "factors" in result
        factors = result["factors"]
        required_factors = ["value", "quality", "momentum", "sentiment"]
        for factor in required_factors:
            assert factor in factors
            assert 0 <= factors[factor] <= 1
        print(f"   ✅ 因子提取成功 - 分数: {result.get('score', 0)}")

    def test_act_method(self):
        print("\n测试: act方法")
        researcher = SignalResearcher()
        result = researcher.act(symbol="MSFT", mock=True)
        assert "factors" in result
        assert "score" in result
        print(f"   ✅ act方法成功 - 符号: {result.get('symbol')}")

    def test_missing_data(self):
        print("\n测试: 缺失数据处理")
        context = {
            "symbol": "TEST",
            # 不提供价格和基本面数据
            "mock": True
        }
        researcher = SignalResearcher()
        result = researcher.run(context)
        assert "factors" in result
        assert "score" in result
        print(f"   ✅ 缺失数据处理成功 - 默认分数: {result.get('score', 0)}")

    def test_error_recovery(self):
        print("\n测试: 错误恢复")
        context = {
            "symbol": "ERROR",  # 可能触发错误的符号
            "prices": "invalid_data",  # 无效的价格数据
            "mock": True
        }
        researcher = SignalResearcher()
        result = researcher.run(context)
        # 即使有错误，也应该返回有效结果
        assert "factors" in result
        assert "score" in result
        print(f"   ✅ 错误恢复成功 - 仍返回分数: {result.get('score', 0)}")
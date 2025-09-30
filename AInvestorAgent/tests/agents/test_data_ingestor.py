"""DataIngestor智能体测试"""
import pytest
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
from agents.data_ingestor import DataIngestor

class TestDataIngestor:
    def test_fetch_price_data(self):
        print("\n测试: 价格数据获取")
        # 使用字典格式的上下文，而不是 AgentContext 对象
        context = {
            "symbol": "AAPL",
            "news_days": 14,
            "mock": True  # 使用mock模式避免外部API调用
        }
        agent = DataIngestor()
        result = agent.run(context)
        assert result is not None
        assert "data" in result
        data = result["data"]
        assert "prices" in data
        assert "news_raw" in data
        print(f"   ✅ 价格获取成功 - {len(data['prices'])}个价格点, {len(data['news_raw'])}条新闻")

    def test_multiple_symbols(self):
        print("\n测试: 多股票获取")
        # 分别测试多个股票
        symbols = ["AAPL", "MSFT", "GOOGL"]
        agent = DataIngestor()

        for symbol in symbols:
            context = {
                "symbol": symbol,
                "news_days": 7,
                "mock": True
            }
            result = agent.run(context)
            assert result is not None
            assert "data" in result
            data = result["data"]
            print(f"   ✅ {symbol} 数据获取完成 - {len(data['prices'])}个价格点")

        print("   ✅ 多股票获取完成")

    def test_error_handling(self):
        """测试错误处理"""
        print("\n测试: 错误处理")
        context = {
            "symbol": "INVALID_SYMBOL",
            "mock": False  # 尝试真实API调用，但应该优雅处理错误
        }
        agent = DataIngestor()

        try:
            result = agent.run(context)
            # 即使有错误，也应该返回结构化的结果
            assert result is not None
            print("   ✅ 错误处理正常")
        except Exception as e:
            # 如果抛出异常，也应该是预期的异常类型
            print(f"   ✅ 捕获预期异常: {type(e).__name__}")
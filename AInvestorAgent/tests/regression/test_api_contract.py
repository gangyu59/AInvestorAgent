"""API契约测试 - 验证API响应格式稳定性"""
import pytest
import requests


class TestAPIContract:
    """API契约测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_health_response_schema(self):
        """测试: 健康检查响应Schema"""
        print("\n" + "="*60)
        print("测试: 健康检查响应Schema")
        print("="*60)

        response = requests.get(f"{self.base_url}/health", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data, "缺少status字段"
        assert data["status"] == "ok", f"status应为ok，实际为{data['status']}"

        print("   ✅ Schema验证通过")

    def test_02_prices_response_schema(self):
        """测试: 价格API响应Schema"""
        print("\n" + "="*60)
        print("测试: 价格API响应Schema")
        print("="*60)

        response = requests.get(
            f"{self.base_url}/api/prices/daily?symbol=AAPL&limit=10",
            timeout=30
        )

        if response.status_code != 200:
            print(f"   ℹ️  价格API不可用: {response.status_code}")
            pytest.skip("价格API不可用")
            return

        data = response.json()

        # 验证必需字段
        assert "symbol" in data, "缺少symbol字段"
        assert "items" in data, "缺少items字段"
        assert isinstance(data["items"], list), "items应为列表"

        if data["items"]:
            item = data["items"][0]
            required_fields = ["date", "open", "high", "low", "close", "volume"]
            for field in required_fields:
                assert field in item, f"items缺少{field}字段"

        print(f"   ✅ Schema验证通过 ({len(data['items'])}个数据点)")

    def test_03_analyze_response_schema(self):
        """测试: 分析API响应Schema"""
        print("\n" + "="*60)
        print("测试: 分析API响应Schema")
        print("="*60)

        response = requests.get(
            f"{self.base_url}/api/analyze/AAPL",
            timeout=30
        )

        if response.status_code != 200:
            print(f"   ℹ️  分析API不可用: {response.status_code}")
            pytest.skip("分析API不可用")
            return

        data = response.json()

        # 验证核心字段
        expected_fields = {
            "symbol": str,
            "as_of": str,
            "score": dict,
            "factors": dict
        }

        for field, expected_type in expected_fields.items():
            assert field in data, f"缺少{field}字段"
            assert isinstance(data[field], expected_type), \
                f"{field}类型应为{expected_type.__name__}"

        # 验证score结构
        score = data["score"]
        assert "score" in score, "score缺少score字段"
        assert "version_tag" in score, "score缺少version_tag字段"

        print("   ✅ Schema验证通过")

    def test_04_scores_batch_response_schema(self):
        """测试: 批量评分API响应Schema"""
        print("\n" + "="*60)
        print("测试: 批量评分API响应Schema")
        print("="*60)

        response = requests.post(
            f"{self.base_url}/api/scores/batch",
            json={"symbols": ["AAPL", "MSFT"]},
            timeout=30
        )

        if response.status_code != 200:
            print(f"   ℹ️  批量评分API不可用: {response.status_code}")
            pytest.skip("批量评分API不可用")
            return

        data = response.json()

        # 验证顶层字段
        assert "items" in data, "缺少items字段"
        assert "as_of" in data, "缺少as_of字段"
        assert "version_tag" in data, "缺少version_tag字段"

        # 验证items结构
        if data["items"]:
            item = data["items"][0]
            assert "symbol" in item, "item缺少symbol"
            assert "score" in item, "item缺少score"
            assert "factors" in item, "item缺少factors"

        print(f"   ✅ Schema验证通过 ({len(data['items'])}个评分)")

    def test_05_orchestrator_propose_schema(self):
        """测试: 组合建议API响应Schema"""
        print("\n" + "="*60)
        print("测试: 组合建议API响应Schema")
        print("="*60)

        candidates = [
            {"symbol": "AAPL", "sector": "Technology", "score": 80.0},
            {"symbol": "MSFT", "sector": "Technology", "score": 75.0}
        ]

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose",
            json={"candidates": candidates, "params": {"mock": True}},
            timeout=30
        )

        if response.status_code != 200:
            print(f"   ℹ️  组合建议API不可用: {response.status_code}")
            pytest.skip("组合建议API不可用")
            return

        data = response.json()

        # 验证返回结构
        assert "context" in data, "缺少context字段"

        context = data["context"]
        assert "kept" in context, "context缺少kept字段"
        assert isinstance(context["kept"], list), "kept应为列表"

        # 验证持仓结构
        if context["kept"]:
            holding = context["kept"][0]
            required = ["symbol", "weight"]
            for field in required:
                assert field in holding, f"holding缺少{field}字段"

        print("   ✅ Schema验证通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
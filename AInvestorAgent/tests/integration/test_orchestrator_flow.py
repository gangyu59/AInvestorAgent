"""
编排器流程测试
测试Orchestrator的完整工作流程和智能体协调
"""
import pytest
import requests
import time
from typing import Dict, Any


class TestOrchestratorBasicFlow:
    """编排器基础流程测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url
        self.timeout = 120

    def test_01_dispatch_pipeline(self):
        """测试: Dispatch管道"""
        print("\n" + "="*60)
        print("测试: Dispatch管道")
        print("="*60)

        response = requests.post(
            f"{self.base_url}/api/orchestrator/dispatch",
            json={
                "symbol": "AAPL",  # 修改：使用单个symbol而非symbols数组
                "params": {"mock": True, "news_days": 14}
            },
            timeout=self.timeout
        )

        if response.status_code == 404:
            print("   ℹ️  /dispatch端点未实现，跳过")
            pytest.skip("Dispatch endpoint not implemented")
            return

        assert response.status_code == 200
        data = response.json()

        # 验证返回结构
        assert "context" in data
        assert "trace" in data

        context = data["context"]
        assert "factors" in context
        assert "score" in context

        print(f"   ✅ Symbol: {context.get('symbol')}")
        print(f"   ✅ Score: {context.get('score')}")
        print(f"   ✅ Trace步骤: {len(data['trace'])}")

    def test_02_propose_pipeline(self):
        """测试: Propose管道"""
        print("\n" + "="*60)
        print("测试: Propose管道")
        print("="*60)

        # 准备候选股票
        candidates = [
            {"symbol": "AAPL", "sector": "Technology", "score": 85.0},
            {"symbol": "MSFT", "sector": "Technology", "score": 82.0},
            {"symbol": "GOOGL", "sector": "Technology", "score": 80.0}
        ]

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose",
            json={
                "candidates": candidates,
                "params": {"mock": True}
            },
            timeout=self.timeout
        )

        if response.status_code == 404:
            print("   ℹ️  /propose端点未实现")
            pytest.skip("Propose endpoint not implemented")
            return

        assert response.status_code == 200
        data = response.json()

        # 验证返回结构
        assert "context" in data
        context = data["context"]

        assert "kept" in context, "context缺少kept字段"
        assert "concentration" in context, "context缺少concentration字段"

        print(f"   ✅ 组合生成: {len(context['kept'])}支")
        print(f"   ✅ 行业分布: {context.get('concentration', {})}")

    def test_03_propose_backtest_pipeline(self):
        """测试: Propose+Backtest管道"""
        print("\n" + "="*60)
        print("测试: Propose+Backtest管道")
        print("="*60)

        candidates = [
            {"symbol": "AAPL", "sector": "Technology", "score": 85.0},
            {"symbol": "MSFT", "sector": "Technology", "score": 82.0}
        ]

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose_backtest",
            json={
                "candidates": candidates,
                "params": {
                    "mock": True,
                    "window_days": 180
                }
            },
            timeout=self.timeout
        )

        if response.status_code == 404:
            print("   ℹ️  /propose_backtest端点未实现")
            pytest.skip("Propose+Backtest endpoint not implemented")
            return

        assert response.status_code == 200
        data = response.json()

        # 验证返回结构
        assert "context" in data
        context = data["context"]

        required_fields = ["kept", "dates", "nav", "metrics"]
        for field in required_fields:
            assert field in context, f"缺少字段: {field}"

        print(f"   ✅ 组合+回测完成")
        print(f"   ✅ NAV点数: {len(context.get('nav', []))}")
        print(f"   ✅ 指标: {context.get('metrics', {})}")


class TestOrchestratorTracing:
    """编排器追踪测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_trace_creation(self):
        """测试: Trace创建"""
        print("\n" + "="*60)
        print("测试: Trace创建")
        print("="*60)

        # 使用dispatch端点测试trace
        response = requests.post(
            f"{self.base_url}/api/orchestrator/dispatch",
            json={
                "symbol": "AAPL",
                "params": {"mock": True}
            },
            timeout=60
        )

        if response.status_code != 200:
            pytest.skip("Dispatch endpoint unavailable")
            return

        data = response.json()

        assert "trace" in data
        trace = data["trace"]
        assert len(trace) > 0

        print(f"   ✅ Trace步骤数: {len(trace)}")

        # 验证trace结构
        for step in trace:
            assert "agent" in step
            print(f"   📊 Agent: {step.get('agent')}")

    def test_02_trace_persistence(self):
        """测试: Trace持久化"""
        print("\n" + "="*60)
        print("测试: Trace持久化")
        print("="*60)

        # 执行两次dispatch
        symbols = ["AAPL", "MSFT"]
        results = []

        for symbol in symbols:
            response = requests.post(
                f"{self.base_url}/api/orchestrator/dispatch",
                json={
                    "symbol": symbol,
                    "params": {"mock": True}
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                results.append(data)

        if len(results) == 2:
            print(f"   ✅ 成功执行{len(results)}次dispatch")
            print(f"   ✅ Symbol 1: {results[0].get('context', {}).get('symbol')}")
            print(f"   ✅ Symbol 2: {results[1].get('context', {}).get('symbol')}")


class TestOrchestratorErrorHandling:
    """编排器错误处理测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_missing_parameters(self):
        """测试: 缺少必要参数"""
        print("\n" + "="*60)
        print("测试: 缺少必要参数")
        print("="*60)

        # dispatch缺少symbol
        response = requests.post(
            f"{self.base_url}/api/orchestrator/dispatch",
            json={"params": {}},
            timeout=10
        )

        # 应该返回错误
        if response.status_code in [400, 422]:
            print(f"   ✅ 正确返回错误: {response.status_code}")
        else:
            print(f"   ⚠️  状态码: {response.status_code}")

    def test_02_invalid_candidates(self):
        """测试: 无效候选列表"""
        print("\n" + "="*60)
        print("测试: 无效候选列表")
        print("="*60)

        test_cases = [
            {"candidates": [], "desc": "空候选列表"},
            {"candidates": [{"symbol": "INVALID"}], "desc": "缺少必要字段"},
        ]

        for case in test_cases:
            response = requests.post(
                f"{self.base_url}/api/orchestrator/propose",
                json=case,
                timeout=10
            )

            print(f"   {case['desc']}: {response.status_code}")

    def test_03_timeout_handling(self):
        """测试: 超时处理"""
        print("\n" + "="*60)
        print("测试: 超时处理")
        print("="*60)

        try:
            response = requests.post(
                f"{self.base_url}/api/orchestrator/dispatch",
                json={"symbol": "AAPL", "params": {"mock": False}},
                timeout=5  # 很短的超时
            )
            print(f"   ✅ 请求在超时前完成: {response.status_code}")
        except requests.Timeout:
            print(f"   ✅ 超时处理正常")


class TestOrchestratorPerformance:
    """编排器性能测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_mock_mode_speed(self):
        """测试: Mock模式速度"""
        print("\n" + "="*60)
        print("测试: Mock模式速度")
        print("="*60)

        times = []
        for i in range(3):
            start = time.time()
            response = requests.post(
                f"{self.base_url}/api/orchestrator/dispatch",
                json={"symbol": "AAPL", "params": {"mock": True}},
                timeout=30
            )
            elapsed = time.time() - start

            if response.status_code == 200:
                times.append(elapsed)
                print(f"   第{i+1}次: {elapsed:.2f}秒")

        if times:
            avg = sum(times) / len(times)
            print(f"\n   平均耗时: {avg:.2f}秒")

            if avg < 5:
                print(f"   ✅ Mock模式性能优秀 (<5秒)")
            else:
                print(f"   ⚠️  Mock模式较慢")

    def test_02_real_mode_speed(self):
        """测试: 真实模式速度"""
        print("\n" + "="*60)
        print("测试: 真实模式速度")
        print("="*60)

        start = time.time()
        response = requests.post(
            f"{self.base_url}/api/orchestrator/dispatch",
            json={"symbol": "AAPL", "params": {"mock": False}},
            timeout=120
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            print(f"   耗时: {elapsed:.2f}秒")

            if elapsed < 60:
                print(f"   ✅ 性能达标 (<60秒)")
            else:
                print(f"   ⚠️  性能较慢: {elapsed:.2f}秒")


class TestOrchestratorMetrics:
    """编排器指标测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_metrics_endpoint(self):
        """测试: 指标端点"""
        print("\n" + "="*60)
        print("测试: 指标端点")
        print("="*60)

        response = requests.get(
            f"{self.base_url}/api/metrics",
            timeout=10
        )

        if response.status_code == 404:
            print("   ℹ️  /metrics端点未实现")
            return

        assert response.status_code == 200
        data = response.json()

        print(f"   ✅ 指标端点可用")
        print(f"   📊 返回字段: {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
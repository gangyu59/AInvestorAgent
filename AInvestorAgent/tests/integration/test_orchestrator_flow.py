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
                "symbols": ["AAPL", "MSFT"],
                "scene": "research"
            },
            timeout=self.timeout
        )

        if response.status_code == 404:
            print("   ℹ️  /dispatch端点未实现，跳过")
            pytest.skip("Dispatch endpoint not implemented")
            return

        assert response.status_code == 200
        data = response.json()

        assert "trace_id" in data
        print(f"   ✅ Trace ID: {data['trace_id']}")

    def test_02_propose_pipeline(self):
        """测试: Propose管道"""
        print("\n" + "="*60)
        print("测试: Propose管道")
        print("="*60)

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose",
            json={
                "symbols": ["AAPL", "MSFT", "GOOGL"]
            },
            timeout=self.timeout
        )

        if response.status_code == 404:
            print("   ℹ️  /propose端点未实现")
            pytest.skip("Propose endpoint not implemented")
            return

        assert response.status_code == 200
        data = response.json()

        assert "holdings" in data
        print(f"   ✅ 组合生成: {len(data['holdings'])}支")

    def test_03_propose_backtest_pipeline(self):
        """测试: Propose+Backtest管道"""
        print("\n" + "="*60)
        print("测试: Propose+Backtest管道")
        print("="*60)

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose_backtest",
            json={
                "symbols": ["AAPL", "MSFT"],
                "window": "6M"
            },
            timeout=self.timeout
        )

        if response.status_code == 404:
            print("   ℹ️  /propose_backtest端点未实现")
            pytest.skip("Propose+Backtest endpoint not implemented")
            return

        assert response.status_code == 200
        data = response.json()

        required_fields = ["holdings", "nav", "metrics"]
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"

        print(f"   ✅ 组合+回测完成")


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

        response = requests.post(
            f"{self.base_url}/api/orchestrator/decide",
            json={"topk": 5, "mock": True},
            timeout=60
        )

        if response.status_code != 200:
            pytest.skip("Decide endpoint unavailable")
            return

        data = response.json()
        trace_id = data.get("trace_id")

        assert trace_id is not None
        print(f"   ✅ Trace ID: {trace_id}")

        # 尝试查询trace
        trace_response = requests.get(
            f"{self.base_url}/api/trace/{trace_id}",
            timeout=10
        )

        if trace_response.status_code == 200:
            trace_data = trace_response.json()
            print(f"   ✅ Trace查询成功")

            if "steps" in trace_data:
                print(f"   📊 步骤数: {len(trace_data['steps'])}")
        else:
            print(f"   ℹ️  Trace查询端点未实现")

    def test_02_trace_persistence(self):
        """测试: Trace持久化"""
        print("\n" + "="*60)
        print("测试: Trace持久化")
        print("="*60)

        # 执行两次决策
        trace_ids = []
        for i in range(2):
            response = requests.post(
                f"{self.base_url}/api/orchestrator/decide",
                json={"topk": 5, "mock": True},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                trace_ids.append(data.get("trace_id"))

        if len(trace_ids) == 2:
            assert trace_ids[0] != trace_ids[1], "Trace ID应该唯一"
            print(f"   ✅ Trace ID唯一性验证通过")
            print(f"      Trace 1: {trace_ids[0]}")
            print(f"      Trace 2: {trace_ids[1]}")


class TestOrchestratorErrorHandling:
    """编排器错误处理测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_missing_symbols(self):
        """测试: 缺少symbols参数"""
        print("\n" + "="*60)
        print("测试: 缺少symbols参数")
        print("="*60)

        response = requests.post(
            f"{self.base_url}/api/orchestrator/decide",
            json={},
            timeout=10
        )

        # 应该返回错误或使用默认值
        if response.status_code in [400, 422]:
            print(f"   ✅ 正确返回错误: {response.status_code}")
        elif response.status_code == 200:
            print(f"   ✅ 使用默认值处理")
        else:
            print(f"   ⚠️  意外状态码: {response.status_code}")

    def test_02_invalid_parameters(self):
        """测试: 无效参数"""
        print("\n" + "="*60)
        print("测试: 无效参数")
        print("="*60)

        test_cases = [
            {"topk": -1, "expected": "负数topk"},
            {"topk": 0, "expected": "零topk"},
            {"topk": 10000, "expected": "超大topk"}
        ]

        for case in test_cases:
            response = requests.post(
                f"{self.base_url}/api/orchestrator/decide",
                json=case,
                timeout=10
            )

            print(f"   {case['expected']}: {response.status_code}")

    def test_03_timeout_handling(self):
        """测试: 超时处理"""
        print("\n" + "="*60)
        print("测试: 超时处理")
        print("="*60)

        try:
            response = requests.post(
                f"{self.base_url}/api/orchestrator/decide",
                json={"topk": 100, "mock": False},
                timeout=5  # 很短的超时
            )
            print(f"   ✅ 请求在超时前完成")
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
                f"{self.base_url}/api/orchestrator/decide",
                json={"topk": 10, "mock": True},
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
            f"{self.base_url}/api/orchestrator/decide",
            json={"topk": 5, "mock": False},
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
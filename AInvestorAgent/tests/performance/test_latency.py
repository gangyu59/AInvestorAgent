"""
性能和延迟测试
测试系统响应时间和吞吐量
"""
import pytest
import requests
import time
import statistics
from typing import List


class TestEndpointLatency:
    """端点延迟测试"""

    def test_01_health_endpoint_latency(self, base_url):
        """测试: 健康检查端点延迟"""
        print("\n" + "="*60)
        print("测试: 健康检查端点延迟")
        print("="*60)

        latencies = []
        iterations = 10

        for i in range(iterations):
            start = time.time()
            response = requests.get(f"{base_url}/health", timeout=5)
            latency = (time.time() - start) * 1000  # 转换为毫秒

            if response.status_code == 200:
                latencies.append(latency)

        if latencies:
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

            print(f"   📊 平均延迟: {avg_latency:.2f}ms")
            print(f"   📊 P95延迟: {p95_latency:.2f}ms")
            print(f"   📊 最小: {min(latencies):.2f}ms")
            print(f"   📊 最大: {max(latencies):.2f}ms")

            # 目标: 平均延迟 <100ms
            if avg_latency < 100:
                print(f"   ✅ 延迟优秀")
            elif avg_latency < 500:
                print(f"   ✅ 延迟良好")
            else:
                print(f"   ⚠️  延迟较高")

    def test_02_price_api_latency(self, base_url):
        """测试: 价格API延迟"""
        print("\n" + "="*60)
        print("测试: 价格API延迟")
        print("="*60)

        latencies = []
        symbol = "AAPL"

        for i in range(5):
            start = time.time()
            response = requests.get(
                f"{base_url}/api/prices/{symbol}?range=1M",
                timeout=30
            )
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                latencies.append(latency)

        if latencies:
            avg_latency = statistics.mean(latencies)

            print(f"   📊 平均延迟: {avg_latency:.2f}ms")

            # 目标: <2秒
            if avg_latency < 2000:
                print(f"   ✅ 延迟达标 (<2s)")
            else:
                print(f"   ⚠️  延迟超标: {avg_latency/1000:.2f}s")

    def test_03_decide_endpoint_latency(self, base_url):
        """测试: 决策端点延迟"""
        print("\n" + "="*60)
        print("测试: 决策端点延迟")
        print("="*60)

        latencies = []

        for i in range(3):
            print(f"\n   第{i+1}次测试...")
            start = time.time()

            response = requests.post(
                f"{base_url}/api/orchestrator/decide",
                json={"topk": 10, "mock": False},
                timeout=120
            )

            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                latencies.append(latency)
                print(f"      延迟: {latency/1000:.2f}s")

        if latencies:
            avg_latency = statistics.mean(latencies)

            print(f"\n   📊 平均延迟: {avg_latency/1000:.2f}秒")

            # 目标: <60秒
            if avg_latency < 60000:
                print(f"   ✅ 延迟达标 (<60s)")
            else:
                print(f"   ⚠️  延迟超标")


class TestThroughput:
    """吞吐量测试"""

    def test_01_concurrent_health_checks(self, base_url):
        """测试: 并发健康检查"""
        print("\n" + "="*60)
        print("测试: 并发健康检查")
        print("="*60)

        import concurrent.futures

        def single_request():
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                return response.status_code == 200
            except:
                return False

        concurrent_level = 10
        print(f"\n   并发请求数: {concurrent_level}")

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_level) as executor:
            futures = [executor.submit(single_request) for _ in range(concurrent_level)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed = time.time() - start

        success_count = sum(results)
        throughput = success_count / elapsed

        print(f"   📊 成功: {success_count}/{concurrent_level}")
        print(f"   📊 总耗时: {elapsed:.2f}秒")
        print(f"   📊 吞吐量: {throughput:.2f} req/s")

        assert success_count >= concurrent_level * 0.8, "成功率<80%"

    def test_02_sequential_api_calls(self, base_url):
        """测试: 顺序API调用"""
        print("\n" + "="*60)
        print("测试: 顺序API调用")
        print("="*60)

        symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]

        start = time.time()
        success_count = 0

        for symbol in symbols:
            try:
                response = requests.get(
                    f"{base_url}/api/prices/{symbol}?range=1M",
                    timeout=30
                )
                if response.status_code == 200:
                    success_count += 1
            except:
                pass

        elapsed = time.time() - start

        print(f"   📊 成功: {success_count}/{len(symbols)}")
        print(f"   📊 总耗时: {elapsed:.2f}秒")
        print(f"   📊 平均每次: {elapsed/len(symbols):.2f}秒")

        assert success_count >= len(symbols) * 0.8


class TestCachingPerformance:
    """缓存性能测试"""

    def test_01_repeated_price_requests(self, base_url):
        """测试: 重复价格请求（测试缓存）"""
        print("\n" + "="*60)
        print("测试: 重复价格请求（缓存效果）")
        print("="*60)

        symbol = "AAPL"
        url = f"{base_url}/api/prices/{symbol}?range=1M"

        # 第一次请求（冷启动）
        start = time.time()
        response1 = requests.get(url, timeout=30)
        first_latency = (time.time() - start) * 1000

        # 第二次请求（可能命中缓存）
        start = time.time()
        response2 = requests.get(url, timeout=30)
        second_latency = (time.time() - start) * 1000

        print(f"   📊 第一次请求: {first_latency:.2f}ms")
        print(f"   📊 第二次请求: {second_latency:.2f}ms")

        if second_latency < first_latency * 0.8:
            print(f"   ✅ 缓存生效（提速{((first_latency-second_latency)/first_latency)*100:.1f}%）")
        else:
            print(f"   ℹ️  缓存可能未实现或未生效")


class TestLoadHandling:
    """负载处理测试"""

    def test_01_sustained_load(self, base_url):
        """测试: 持续负载"""
        print("\n" + "="*60)
        print("测试: 持续负载（30秒）")
        print("="*60)

        duration = 30  # 秒
        start_time = time.time()
        request_count = 0
        success_count = 0

        print(f"\n   开始持续请求...")

        while time.time() - start_time < duration:
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                request_count += 1
                if response.status_code == 200:
                    success_count += 1
            except:
                request_count += 1

            time.sleep(0.1)  # 100ms间隔

        elapsed = time.time() - start_time
        success_rate = success_count / request_count if request_count > 0 else 0
        avg_rps = request_count / elapsed

        print(f"\n   📊 总请求: {request_count}")
        print(f"   📊 成功: {success_count}")
        print(f"   📊 成功率: {success_rate:.1%}")
        print(f"   📊 平均RPS: {avg_rps:.2f}")

        assert success_rate >= 0.95, f"成功率过低: {success_rate:.1%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
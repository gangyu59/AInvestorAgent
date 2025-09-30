"""吞吐量测试 - 测量系统处理能力"""
import pytest
import requests
import time
import statistics


class TestThroughput:
    """吞吐量测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_requests_per_second(self):
        """测试: 每秒请求数（RPS）"""
        print("\n" + "="*60)
        print("测试: 每秒请求数")
        print("="*60)

        duration = 10  # 测试10秒
        start = time.time()
        count = 0
        successes = 0

        while time.time() - start < duration:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=1)
                count += 1
                if response.status_code == 200:
                    successes += 1
            except:
                count += 1
            time.sleep(0.05)  # 50ms间隔

        elapsed = time.time() - start
        rps = count / elapsed
        success_rate = successes / count if count > 0 else 0

        print(f"   📊 总请求: {count}")
        print(f"   📊 成功: {successes}")
        print(f"   📊 吞吐量: {rps:.2f} req/s")
        print(f"   📊 成功率: {success_rate:.1%}")

        assert success_rate >= 0.9, f"成功率过低: {success_rate:.1%}"

    def test_02_burst_capacity(self):
        """测试: 突发容量"""
        print("\n" + "="*60)
        print("测试: 突发容量")
        print("="*60)

        burst_size = 50
        start = time.time()

        import concurrent.futures

        def single_request():
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                return response.status_code == 200
            except:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=burst_size) as executor:
            futures = [executor.submit(single_request) for _ in range(burst_size)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed = time.time() - start
        success_count = sum(results)

        print(f"   📊 突发请求: {burst_size}")
        print(f"   📊 成功: {success_count}")
        print(f"   📊 总耗时: {elapsed:.2f}秒")
        print(f"   📊 成功率: {success_count/burst_size:.1%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
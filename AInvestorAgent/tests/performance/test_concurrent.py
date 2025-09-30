"""
并发测试 - 优化版（添加超时控制）
测试系统在并发请求下的稳定性
"""
import pytest
import asyncio
import aiohttp
from typing import List, Dict
import time

API_BASE = "http://127.0.0.1:8000"

# 添加总超时控制
GLOBAL_TIMEOUT = 45  # 总测试时间不超过 45 秒
REQUEST_TIMEOUT = 10  # 单个请求超时 10 秒

class ConcurrentTester:
    def __init__(self):
        self.results: List[Dict] = []
        self.timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async def make_request(self, session: aiohttp.ClientSession, url: str, idx: int):
        """发起单个请求"""
        start = time.time()
        try:
            async with session.get(url, timeout=self.timeout) as response:
                duration = time.time() - start
                return {
                    'index': idx,
                    'status': response.status,
                    'duration': duration,
                    'success': response.status == 200
                }
        except asyncio.TimeoutError:
            return {
                'index': idx,
                'status': 0,
                'duration': time.time() - start,
                'success': False,
                'error': 'timeout'
            }
        except Exception as e:
            return {
                'index': idx,
                'status': 0,
                'duration': time.time() - start,
                'success': False,
                'error': str(e)
            }

    async def run_concurrent_requests(self, endpoint: str, count: int):
        """并发执行多个请求"""
        url = f"{API_BASE}{endpoint}"

        async with aiohttp.ClientSession() as session:
            tasks = [
                self.make_request(session, url, i)
                for i in range(count)
            ]

            # 使用 asyncio.wait_for 添加总超时
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=GLOBAL_TIMEOUT
                )
                return results
            except asyncio.TimeoutError:
                return [{'success': False, 'error': 'global_timeout'}] * count


@pytest.mark.asyncio
async def test_health_concurrent():
    """测试健康检查接口并发性能"""
    print("\n🔄 测试 /health 并发...")

    tester = ConcurrentTester()
    results = await tester.run_concurrent_requests("/api/health", count=20)

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    avg_duration = sum(r['duration'] for r in results if isinstance(r, dict)) / len(results)

    print(f"   ✓ 成功: {success_count}/20")
    print(f"   ⏱ 平均延迟: {avg_duration:.3f}s")

    assert success_count >= 18, f"成功率过低: {success_count}/20"
    assert avg_duration < 2.0, f"平均延迟过高: {avg_duration:.3f}s"


@pytest.mark.asyncio
async def test_prices_concurrent():
    """测试价格查询接口并发性能"""
    print("\n🔄 测试 /prices 并发...")

    tester = ConcurrentTester()
    results = await tester.run_concurrent_requests(
        "/api/prices/AAPL?range=1M&refresh=false",
        count=10
    )

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))

    print(f"   ✓ 成功: {success_count}/10")

    assert success_count >= 8, f"成功率过低: {success_count}/10"


@pytest.mark.asyncio
async def test_mixed_concurrent():
    """测试混合端点并发"""
    print("\n🔄 测试混合端点并发...")

    endpoints = [
        "/api/health",
        "/api/prices/AAPL?range=1M&refresh=false",
        "/api/fundamentals/AAPL",
        "/api/metrics/AAPL"
    ]

    tester = ConcurrentTester()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, endpoint in enumerate(endpoints * 3):  # 每个端点 3 次
            tasks.append(tester.make_request(session, f"{API_BASE}{endpoint}", i))

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=GLOBAL_TIMEOUT
            )
        except asyncio.TimeoutError:
            results = [{'success': False, 'error': 'global_timeout'}] * len(tasks)

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    total = len(tasks)

    print(f"   ✓ 成功: {success_count}/{total}")
    print(f"   📊 成功率: {success_count/total*100:.1f}%")

    assert success_count >= total * 0.7, f"成功率过低: {success_count}/{total}"


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 并发测试 (优化版)")
    print("=" * 60)

    # 运行测试
    pytest.main([__file__, "-v", "-s"])
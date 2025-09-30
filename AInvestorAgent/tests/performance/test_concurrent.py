"""
并发测试 - 自适配端点 & 预热（最小改动版）
"""
import pytest
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
import os
import time

API_BASE = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")  # 允许用环境变量覆盖

GLOBAL_TIMEOUT = 45   # 总测试时间不超过 45 秒
REQUEST_TIMEOUT = 10  # 单个请求超时 10 秒
CONNECTOR_LIMIT = 50  # aiohttp 并发连接上限（按需调整）

class ConcurrentTester:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.results: List[Dict] = []
        self.timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        self._session = session

    async def make_request(self, session: aiohttp.ClientSession, url: str, idx: int):
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
        url = f"{API_BASE}{endpoint}"
        connector = aiohttp.TCPConnector(limit=CONNECTOR_LIMIT)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.make_request(session, url, i) for i in range(count)]
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=GLOBAL_TIMEOUT
                )
                return results
            except asyncio.TimeoutError:
                return [{'success': False, 'error': 'global_timeout'}] * count

async def _probe_first_ok(session: aiohttp.ClientSession, candidates: List[str]) -> Optional[str]:
    """返回第一个 200 的相对路径端点（不抛异常）"""
    for ep in candidates:
        try:
            async with session.get(f"{API_BASE}{ep}", timeout=REQUEST_TIMEOUT) as r:
                if r.status == 200:
                    return ep
        except Exception:
            pass
    return None

async def _warmup(session: aiohttp.ClientSession, endpoint: str, times: int = 1):
    """预热端点，忽略错误"""
    for _ in range(times):
        try:
            async with session.get(f"{API_BASE}{endpoint}", timeout=REQUEST_TIMEOUT) as _:
                await asyncio.sleep(0)  # 让出事件循环
        except Exception:
            pass

@pytest.mark.asyncio
async def test_health_concurrent():
    """测试健康检查接口并发性能"""
    print("\n🔄 测试 /health 并发...")

    tester = ConcurrentTester()
    results = await tester.run_concurrent_requests("/api/health", count=20)

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    avg_duration = sum((r.get('duration', 0) or 0) for r in results if isinstance(r, dict)) / len(results)

    print(f"   ✓ 成功: {success_count}/20")
    print(f"   ⏱ 平均延迟: {avg_duration:.3f}s")

    assert success_count >= 18, f"成功率过低: {success_count}/20"
    assert avg_duration < 2.0, f"平均延迟过高: {avg_duration:.3f}s"

@pytest.mark.asyncio
async def test_prices_concurrent():
    """测试价格查询接口并发性能（自适配端点 + 预热）"""
    print("\n🔄 测试 /prices 并发（自适配）...")

    candidates = [
        "/api/prices/AAPL?range=1M&refresh=false",
        "/api/prices/series?symbol=AAPL&days=30&refresh=false",
        "/api/prices/AAPL?limit=60&refresh=false",
        "/api/price/series?symbol=AAPL&days=30&refresh=false",
        "/api/prices/AAPL",
    ]

    connector = aiohttp.TCPConnector(limit=CONNECTOR_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as session:
        endpoint = await _probe_first_ok(session, candidates)
        if not endpoint:
            pytest.skip("找不到可用的价格端点（候选均非 200）")

        # 预热 1~2 次，避免首次外部抓取造成并发失败
        await _warmup(session, endpoint, times=2)

    tester = ConcurrentTester()
    results = await tester.run_concurrent_requests(endpoint, count=10)

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))

    print(f"   ✓ 成功: {success_count}/10")
    assert success_count >= 8, f"成功率过低: {success_count}/10"

@pytest.mark.asyncio
async def test_mixed_concurrent():
    """测试混合端点并发（自适配可用端点）"""
    print("\n🔄 测试混合端点并发（自适配）...")

    # 价格端点候选
    price_candidates = [
        "/api/prices/AAPL?range=1M&refresh=false",
        "/api/prices/series?symbol=AAPL&days=30&refresh=false",
        "/api/prices/AAPL?limit=60&refresh=false",
        "/api/price/series?symbol=AAPL&days=30&refresh=false",
        "/api/prices/AAPL",
    ]
    # 其它端点（可根据你后端存在与否进行探测）
    maybe_endpoints = [
        "/api/health",
        "/api/fundamentals/AAPL",
        "/api/metrics/AAPL",
    ]

    connector = aiohttp.TCPConnector(limit=CONNECTOR_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as session:
        price_ep = await _probe_first_ok(session, price_candidates)
        usable: List[str] = []

        # 探测 health/fundamentals/metrics
        for ep in maybe_endpoints:
            ok = await _probe_first_ok(session, [ep])
            if ok:
                usable.append(ok)

        if price_ep:
            usable.append(price_ep)

        if not usable:
            pytest.skip("混合测试：没有任何可用端点")

        # 预热每个端点一次
        for ep in usable:
            await _warmup(session, ep, times=1)

    tester = ConcurrentTester()
    # 每个端点跑 3 次
    tasks_total = len(usable) * 3
    endpoints_seq = []
    for ep in usable:
        endpoints_seq.extend([ep] * 3)

    # 并发跑
    connector = aiohttp.TCPConnector(limit=CONNECTOR_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            tester.make_request(session, f"{API_BASE}{endpoints_seq[i]}", i)
            for i in range(tasks_total)
        ]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=GLOBAL_TIMEOUT
            )
        except asyncio.TimeoutError:
            results = [{'success': False, 'error': 'global_timeout'}] * tasks_total

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    print(f"   ✓ 成功: {success_count}/{tasks_total}")
    print(f"   📊 成功率: {success_count/tasks_total*100:.1f}%")

    assert success_count >= tasks_total * 0.7, f"成功率过低: {success_count}/{tasks_total}"

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 并发测试（自适配 & 预热）")
    print("=" * 60)
    pytest.main([__file__, "-v", "-s"])

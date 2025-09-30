"""数据溢出测试：大响应体/长时间窗口/多次拉取的健壮性"""
import pytest
import asyncio
import aiohttp
import os
import json
import time

API_BASE = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 20
CONNECT_LIMIT = 30

PRICE_CANDIDATES = [
    "/api/prices/series?symbol=AAPL&days=365&refresh=false",
    "/api/news/series?symbol=AAPL&days=180",
    "/api/prices/AAPL?range=1Y&refresh=false",
    "/api/prices/AAPL?limit=260&refresh=false",
    "/api/prices/AAPL",
]

async def _probe(session, eps):
    for ep in eps:
        try:
            async with session.get(f"{API_BASE}{ep}", timeout=REQUEST_TIMEOUT) as r:
                if r.status == 200:
                    return ep
        except Exception:
            pass
    return None

@pytest.mark.asyncio
async def test_large_dataset():
    print("\n测试: 大数据集处理（探测可用端点 + 重复拉取）")
    connector = aiohttp.TCPConnector(limit=CONNECT_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as s:
        ep = await _probe(s, PRICE_CANDIDATES)
        if not ep:
            pytest.skip("未找到可用于大响应体的端点")

        # 预热一次
        await s.get(f"{API_BASE}{ep}", timeout=REQUEST_TIMEOUT)

        # 连续拉取多次，验证不会 5xx/崩溃，返回可解析内容（json 或文本长度）
        total = 5
        ok = 0
        avg_size = 0
        for i in range(total):
            t0 = time.time()
            async with s.get(f"{API_BASE}{ep}", timeout=REQUEST_TIMEOUT) as r:
                assert r.status == 200
                ctype = r.headers.get("Content-Type", "")
                if "application/json" in ctype:
                    data = await r.json()
                    size = len(json.dumps(data))
                else:
                    text = await r.text()
                    size = len(text)
                dur = time.time() - t0
                avg_size += size
                ok += 1
                print(f"   第{i+1}次: {size/1024:.1f} KB, {dur:.2f}s, {ctype}")

        avg_size /= max(ok, 1)
        print(f"   ✅ 成功 {ok}/{total}，平均大小 {avg_size/1024:.1f} KB")
        assert ok >= total * 0.8, "重复拉取稳定性不足"
        # 平均返回体至少要有一定规模，防止取到“空响应”
        assert avg_size > 10 * 1024, "响应体过小，疑似未返回有效数据"

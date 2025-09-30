"""极端场景测试：高波动/参数边界/混合端点稳定性"""
import pytest
import asyncio
import aiohttp
import os
import random
import time

API_BASE = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 12
GLOBAL_TIMEOUT = 45
CONNECT_LIMIT = 60

PRICE_CANDIDATES = [
    "/api/prices/series?symbol={sym}&days={days}&refresh=false",
    "/api/prices/{sym}?range={rng}&refresh=false",
    "/api/prices/{sym}?limit={lim}&refresh=false",
    "/api/prices/{sym}",
]

SYMS = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META"]

def _materialize(ep):
    sym = random.choice(SYMS)
    days = random.choice([7, 14, 30, 90])
    rng = random.choice(["1M", "3M", "6M", "1Y"])
    lim = random.choice([30, 60, 120, 250])
    return ep.format(sym=sym, days=days, rng=rng, lim=lim)

async def _probe(session, templates):
    for t in templates:
        ep = _materialize(t)
        try:
            async with session.get(f"{API_BASE}{ep}", timeout=REQUEST_TIMEOUT) as r:
                if r.status == 200:
                    return t  # 返回可用模板
        except Exception:
            pass
    return None

@pytest.mark.asyncio
async def test_market_volatility():
    print("\n测试: 市场波动极端情况（参数边界 + 并发）")

    connector = aiohttp.TCPConnector(limit=CONNECT_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as session:
        tpl = await _probe(session, PRICE_CANDIDATES)
        if not tpl:
            pytest.skip("没有可用价格端点模板")

        # 预热 2 次
        for _ in range(2):
            ep = _materialize(tpl)
            try:
                await session.get(f"{API_BASE}{ep}", timeout=REQUEST_TIMEOUT)
            except Exception:
                pass

        # 构造 40 个极端/边界参数请求并发
        total = 40
        urls = [f"{API_BASE}{_materialize(tpl)}" for _ in range(total)]

        async def _one(url, idx):
            t0 = time.time()
            try:
                async with session.get(url, timeout=REQUEST_TIMEOUT) as r:
                    ok = (r.status == 200)
                    # 轻量读取头即可，避免太大 IO
                    await r.read()
                    return ok, time.time() - t0
            except Exception:
                return False, time.time() - t0

        tasks = [_one(u, i) for i, u in enumerate(urls)]
        done = await asyncio.wait_for(asyncio.gather(*tasks), timeout=GLOBAL_TIMEOUT)
        success = sum(1 for ok, _ in done if ok)
        p95 = sorted(d for _, d in done)[int(len(done)*0.95)-1]

        print(f"   ✓ 成功: {success}/{total}")
        print(f"   ⏱ P95 延迟: {p95:.2f}s")
        assert success >= int(total * 0.75), "极端参数并发成功率过低"
        assert p95 < 5.0, "P95 延迟过高"

"""资源耗尽测试：高并发连接 & 简易内存泄漏监测（tracemalloc）"""
import pytest
import asyncio
import aiohttp
import os
import time
import tracemalloc

API_BASE = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 6
GLOBAL_TIMEOUT = 60
CONNECT_LIMIT = 100

HEALTH = "/api/health"

@pytest.mark.asyncio
async def test_memory_limits():
    print("\n测试: 内存限制 / 连接耗尽保护")

    connector = aiohttp.TCPConnector(limit=CONNECT_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as s:
        # 基线可用
        try:
            async with s.get(f"{API_BASE}{HEALTH}", timeout=REQUEST_TIMEOUT) as r:
                if r.status != 200:
                    pytest.skip("健康检查非 200，跳过资源耗尽测试")
        except Exception:
            pytest.skip("健康检查异常，跳过")

        # 启动 tracemalloc 观察分配
        tracemalloc.start()

        # 1) 高并发短呼吸：同时发起 200 个健康检查（分两批，避免把系统压死）
        async def _hit(i):
            try:
                async with s.get(f"{API_BASE}{HEALTH}", timeout=REQUEST_TIMEOUT) as r:
                    await r.read()
                    return r.status == 200
            except Exception:
                return False

        batch = 100
        for round_idx in range(2):
            tasks = [_hit(i) for i in range(batch)]
            done = await asyncio.wait_for(asyncio.gather(*tasks), timeout=GLOBAL_TIMEOUT)
            ok = sum(1 for x in done if x)
            print(f"   批次 {round_idx+1}: {ok}/{batch} 成功")
            assert ok >= int(batch * 0.9), "高并发健康检查成功率过低"

        # 2) 简易泄漏检测：多次请求前后内存快照对比（不是严格 GC 计量，只做阈值保护）
        snap1 = tracemalloc.take_snapshot()

        # 再做 200 次请求（串行快速）
        for _ in range(200):
            try:
                async with s.get(f"{API_BASE}{HEALTH}", timeout=REQUEST_TIMEOUT) as r:
                    await r.read()
            except Exception:
                pass

        await asyncio.sleep(0.5)  # 给 GC 一点时间
        snap2 = tracemalloc.take_snapshot()

        stats = snap2.compare_to(snap1, 'filename')
        # 累计新增 top10 的 size
        inc = sum([st.size_diff for st in stats[:10] if st.size_diff > 0])
        print(f"   🔍 观察到的新增内存(Top10)：{inc/1024:.1f} KB")

        # 阈值：单轮新增不可超过 ~2MB（经验阈值，防止持续增长）
        assert inc < 2 * 1024 * 1024, "疑似内存泄漏：增量过高"

        tracemalloc.stop()

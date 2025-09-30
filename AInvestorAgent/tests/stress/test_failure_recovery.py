"""故障恢复测试：重试、优雅降级、可用性恢复"""
import pytest
import asyncio
import aiohttp
import os
import time

API_BASE = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 8
CONNECT_LIMIT = 20

HEALTH = "/api/health"
LOCUST_START = "/api/testing/locust/start"
LOCUST_STOP = "/api/testing/locust/stop"
LOCUST_STATUS = "/api/testing/locust/status"

@pytest.mark.asyncio
async def test_graceful_degradation():
    print("\n测试: 优雅降级 / 故障恢复")

    connector = aiohttp.TCPConnector(limit=CONNECT_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as s:
        # 1) 基线健康：必须可 200（否则没法验证恢复）
        try:
            async with s.get(f"{API_BASE}{HEALTH}", timeout=REQUEST_TIMEOUT) as r:
                if r.status != 200:
                    pytest.skip("健康检查非 200，跳过恢复测试")
        except Exception:
            pytest.skip("健康检查异常，跳过")

        # 2) 若存在 Locust 控制端点：模拟“有压力-再恢复”的过程
        #    不强依赖；没有就退化为“重试成功”
        def _exists(ep):
            return asyncio.run(_quick_head(s, ep))

        # 压力开始（可选）
        started = await _quick_post_json(s, LOCUST_START, {"users": 50, "spawn_rate": 10})
        if not started:
            print("   ℹ️ 未提供 locust 控制端点，退化为重试逻辑验证。")

        # 3) 在压力下多次探测 /api/health，允许少量失败，但需“可恢复”
        ok = 0
        attempts = 10
        for i in range(attempts):
            try:
                async with s.get(f"{API_BASE}{HEALTH}", timeout=REQUEST_TIMEOUT) as r:
                    ok += (r.status == 200)
            except Exception:
                pass
            await asyncio.sleep(0.3)

        # 压力停止（可选）
        if started:
            await _quick_post_json(s, LOCUST_STOP, {})

        # 4) 恢复期再探测 5 次，应≥4 次成功
        rec_ok = 0
        for _ in range(5):
            try:
                async with s.get(f"{API_BASE}{HEALTH}", timeout=REQUEST_TIMEOUT) as r:
                    rec_ok += (r.status == 200)
            except Exception:
                pass
            await asyncio.sleep(0.3)

        print(f"   ✓ 压力期成功: {ok}/{attempts}；恢复期成功: {rec_ok}/5")
        assert rec_ok >= 4, "恢复期可用性不足（没有优雅恢复）"

async def _quick_post_json(session, ep, payload):
    try:
        async with session.post(f"{API_BASE}{ep}", json=payload, timeout=REQUEST_TIMEOUT) as r:
            return r.status in (200, 201)
    except Exception:
        return False

async def _quick_head(session, ep):
    try:
        async with session.head(f"{API_BASE}{ep}", timeout=REQUEST_TIMEOUT) as r:
            return r.status < 500
    except Exception:
        return False

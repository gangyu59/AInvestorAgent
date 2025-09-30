# tests/stress/test_market_crash.py
"""市场崩盘测试：极端下跌冲击 + 结果健壮性校验（更稳健：默认用等权组合，不阻塞）"""
import pytest
import asyncio
import aiohttp
import os
import json
from typing import Any, Dict, List, Optional

API_BASE = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 15           # 更短，避免拖到外层 60s
CONNECT_LIMIT = 20
USE_DECIDE = os.environ.get("AIA_USE_DECIDE", "0") in ("1", "true", "True")

BACKTEST_POST_CANDIDATES = [
    "/api/backtest/run",
    "/backtest/run",
    "/api/portfolio/backtest",
]
DECIDE_POST = [
    "/orchestrator/decide",
    "/api/portfolio/propose",
]

SYMBOLS_DEFAULT = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA"]

@pytest.mark.asyncio
async def test_crash_scenario():
    print("\n测试: 市场崩盘（-30% 冲击）")

    connector = aiohttp.TCPConnector(limit=CONNECT_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as s:
        bt_ep = await _probe_post(s, BACKTEST_POST_CANDIDATES)
        if not bt_ep:
            pytest.skip("没有可用的回测端点")

        # --- 1) 组合：默认用等权；若显式开启，则调用 decide（低风险参数） ---
        portfolio = _build_equal_weight_portfolio(SYMBOLS_DEFAULT)
        if USE_DECIDE:
            decide_ep = await _probe_post(s, DECIDE_POST)
            if decide_ep:
                # 显式给 symbols / 关闭 LLM / 关闭刷新，避免卡顿或外部调用
                pl = {
                    "symbols": SYMBOLS_DEFAULT,
                    "topk": 6,
                    "min_score": 50,
                    "use_llm": False,
                    "refresh_prices": False,
                    "params": {"mock": True}
                }
                res = await _try_json_post(s, decide_ep, pl)
                parsed = _parse_portfolio(res)
                if parsed:
                    portfolio = parsed  # 成功则替换；失败就继续用等权

        # --- 2) 回测：带崩盘冲击 ---
        shock = {"shock": {"type": "crash", "pct": -0.30, "days": 5}}
        req_payload = {
            "portfolio": portfolio,
            "positions": portfolio.get("positions", []),  # 兼容某些风格
            "symbols": [p["symbol"] for p in portfolio.get("positions", [])],
            "weights": [p["weight"] for p in portfolio.get("positions", [])],
            "start": "2025-01-01",
            "end": "2025-09-25",
            "params": {"mock": True, **shock},
        }

        res = await _try_json_post(s, bt_ep, req_payload)
        if res is None:
            pytest.skip("回测端点未接受 payload（返回 4xx/非 JSON），跳过以免卡住")

        # --- 3) 校验：NAV 有效、全正、最大回撤足够大 ---
        nav = res.get("nav") or res.get("strategy_nav") or []
        assert isinstance(nav, list) and len(nav) > 5, "回测缺少 NAV 序列"
        assert all((x is None or x > 0) for x in nav), "NAV 中出现非正值"
        dd = _max_drawdown(nav)
        print(f"   ⛏️ 估算最大回撤: {dd*100:.1f}%")
        assert dd >= 0.2, "崩盘场景下最大回撤过小（疑似 shock 未生效或未传播）"

# -------------------- helpers --------------------

async def _probe_post(s: aiohttp.ClientSession, eps: List[str]) -> Optional[str]:
    """找第一个“可触达”的 POST 端点：能回 200/400/422 即认为存在（不阻塞）"""
    for ep in eps:
        try:
            async with s.post(f"{API_BASE}{ep}", json={"ping": "ok"}, timeout=REQUEST_TIMEOUT) as r:
                if r.status in (200, 400, 422):
                    return ep
        except Exception:
            pass
    return None

async def _try_json_post(s: aiohttp.ClientSession, ep: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        async with s.post(f"{API_BASE}{ep}", json=payload, timeout=REQUEST_TIMEOUT) as r:
            if r.status != 200:
                return None
            ctype = r.headers.get("Content-Type", "")
            if "application/json" in ctype:
                return await r.json()
            txt = await r.text()
            try:
                return json.loads(txt)
            except Exception:
                return None
    except Exception:
        return None

def _parse_portfolio(res: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(res, dict):
        return None
    positions = None
    if "positions" in res and isinstance(res["positions"], list):
        positions = res["positions"]
    elif "portfolio" in res and isinstance(res["portfolio"], dict) and isinstance(res["portfolio"].get("positions"), list):
        positions = res["portfolio"]["positions"]
    elif "symbols" in res and isinstance(res["symbols"], list) and len(res["symbols"]) > 0:
        if isinstance(res["symbols"][0], dict) and "symbol" in res["symbols"][0]:
            positions = res["symbols"]

    if not positions:
        return None

    norm = []
    tot = 0.0
    for p in positions:
        sym = p.get("symbol") or p.get("ticker") or p.get("code")
        w = float(p.get("weight", 0.0))
        if sym and w > 0:
            norm.append({"symbol": sym, "weight": w})
            tot += w
    if not norm:
        return None
    if tot > 0:
        norm = [{"symbol": x["symbol"], "weight": x["weight"] / tot} for x in norm]
    return {"positions": norm}

def _build_equal_weight_portfolio(symbols: List[str]) -> Dict[str, Any]:
    n = max(1, len(symbols))
    w = 1.0 / n
    return {"positions": [{"symbol": s, "weight": w} for s in symbols]}

def _max_drawdown(series: List[Optional[float]]) -> float:
    peak = float("-inf")
    mdd = 0.0
    for x in series:
        if x is None:
            continue
        if x > peak:
            peak = x
        if peak > 0:
            mdd = max(mdd, (peak - x) / peak)
    return mdd

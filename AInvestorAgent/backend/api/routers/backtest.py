from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import hashlib, time, math, json, urllib.request

router = APIRouter(prefix="/backtest", tags=["backtest"])

# ---------- 请求模型 ----------
class WeightItem(BaseModel):
    symbol: str
    weight: float

class RunBacktestReq(BaseModel):
    snapshot_id: Optional[str] = None
    weights: Optional[List[WeightItem]] = None
    window: Optional[str] = None            # "1Y" | "6M" | "90D" | "252"
    window_days: Optional[int] = 252
    trading_cost: Optional[float] = 0.001
    rebalance: Optional[str] = "weekly"
    max_trades_per_week: Optional[int] = 3
    benchmark_symbol: Optional[str] = "SPY"
    mock: Optional[bool] = False

# ---------- 工具 ----------
def parse_window_days(win: Optional[str], fallback: int = 252) -> int:
    if not win: return fallback
    w = win.strip().upper()
    try:
        if w.endswith("Y"): return int(round(float(w[:-1]) * 252))
        if w.endswith("M"): return int(round(float(w[:-1]) * 21))
        if w.endswith("W"): return int(round(float(w[:-1]) * 5))
        if w.endswith("D"): return max(int(float(w[:-1])), 5)
        return max(int(float(w)), 5)
    except Exception:
        return fallback

def compute_drawdown(nav: List[float]) -> List[float]:
    dd, peak = [], -float("inf")
    for v in nav or []:
        v = float(v or 0.0)
        peak = max(peak, v)
        dd.append((v/peak - 1.0) if peak > 0 else 0.0)
    return dd

def compute_metrics(nav: List[float]) -> Dict[str, float]:
    if not nav: return {"ann_return": 0.0, "sharpe": 0.0, "max_dd": 0.0, "win_rate": 0.0}
    rets = []
    for i in range(1, len(nav)):
        p0, p1 = nav[i-1], nav[i]
        rets.append(p1/p0 - 1 if p0 > 0 else 0.0)
    n = len(rets) or 1
    total = nav[-1] or 1.0
    ann = (total ** (252.0 / n) - 1.0) if total > 0 else 0.0
    peak, mdd = nav[0] or 1.0, 0.0
    for v in nav:
        if v > peak: peak = v
        if peak > 0: mdd = max(mdd, 1.0 - v/peak)
    if len(rets) >= 2:
        mean = sum(rets)/len(rets)
        var  = sum((r-mean)**2 for r in rets) / (len(rets)-1)
        std  = math.sqrt(var)
        sharpe = (mean/std*math.sqrt(252)) if std > 0 else 0.0
    else:
        sharpe = 0.0
    return {"ann_return": float(ann), "sharpe": float(sharpe), "max_dd": float(mdd), "win_rate": 0.0}


def fetch_price_series_local(symbol: str, days: int) -> List[Dict[str, Any]]:
    """修复版：使用正确的API路径并解析返回格式"""
    url = f"http://127.0.0.1:8000/api/prices/daily?symbol={symbol}&limit={days}"
    print(f"DEBUG: 正在调用 {url}")  # 调试信息

    try:
        with urllib.request.urlopen(url, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))

        print(f"DEBUG: 收到数据结构: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A'}")

        # 解析你的API返回格式：{"symbol":"AAPL","items":[...]}
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
            print(f"DEBUG: 解析到 {len(items)} 条价格记录")
            # 转换为统一格式
            result = []
            for item in items:
                result.append({
                    "date": item.get("date", ""),
                    "close": float(item.get("close", 0)),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "volume": item.get("volume", 0)
                })
            return result
        elif isinstance(data, list):
            return data
        else:
            return data.get("series") or data.get("data") or []

    except Exception as e:
        print(f"获取 {symbol} 价格数据失败: {e}")
        return []

def local_backtest(weights: List[Dict[str, Any]], days: int, benchmark: str = "SPY") -> Dict[str, Any]:
    # 1) 拉价格
    series_maps = []
    for w in weights:
        sym = str(w.get("symbol") or "").upper().strip()
        wt  = float(w.get("weight") or 0.0)
        if not sym or wt <= 0: continue
        arr = fetch_price_series_local(sym, days)
        m = { (d.get("date") or "")[:10].replace("-", ""): float(d.get("close") or 0.0)
              for d in arr if d.get("date") and d.get("close") }
        if len(m) >= 60:
            series_maps.append((sym, wt, m))
    if not series_maps:
        return {"dates": [], "nav": [], "benchmark_nav": [], "drawdown": [], "metrics": {}}

    # 2) 对齐日期交集
    dates = sorted(set.intersection(*(set(m.keys()) for _,_,m in series_maps)))
    if len(dates) < 10:
        return {"dates": [], "nav": [], "benchmark_nav": [], "drawdown": [], "metrics": {}}

    # 3) 归一化权重 + 组合 NAV
    total_w = sum(max(0.0, float(w)) for _, w, _ in series_maps) or 1.0
    ws = [(sym, float(w)/total_w, m) for sym, w, m in series_maps]

    nav = [1.0]
    for i in range(1, len(dates)):
        d0, d1 = dates[i-1], dates[i]
        r = 0.0
        for _, w, m in ws:
            p0, p1 = m.get(d0, 0.0), m.get(d1, 0.0)
            r += w * ((p1/p0 - 1.0) if p0 > 0 else 0.0)
        nav.append(nav[-1] * (1.0 + r))

    # 4) 基准
    bm_nav = []
    try:
        bm_arr = fetch_price_series_local(benchmark, days)
        bm = { (d.get("date") or "")[:10].replace("-", ""): float(d.get("close") or 0.0)
               for d in bm_arr if d.get("date") and d.get("close") }
        bdates = [d for d in dates if d in bm]
        if len(bdates) >= 2:
            start = bm[bdates[0]] or 1.0
            bm_nav = [ (bm[d]/start) if start > 0 else 1.0 for d in bdates ]
            if len(bm_nav) != len(nav): bm_nav = []
    except Exception:
        bm_nav = []

    dd = compute_drawdown(nav)
    metrics = compute_metrics(nav)
    iso_dates = [ f"{d[0:4]}-{d[4:6]}-{d[6:8]}" for d in dates ]
    return { "dates": iso_dates, "nav": nav, "benchmark_nav": bm_nav, "drawdown": dd, "metrics": metrics }

# ---------- 主路由 ----------
# 替换 backtest.py 中的 /run 路由函数
@router.post("/run")
def run_backtest(req: RunBacktestReq):
    window_days = parse_window_days(req.window, req.window_days or 252)

    # 🛟 直接走降级分支：需要weights。
    raw_weights: List[Dict[str, Any]] = []
    if req.weights:
        # 兼容 WeightItem 或 dict
        for w in req.weights:
            if isinstance(w, dict):
                raw_weights.append({"symbol": w.get("symbol"), "weight": w.get("weight")})
            else:
                w2 = w.model_dump()
                raw_weights.append({"symbol": w2.get("symbol"), "weight": w2.get("weight")})

    if not raw_weights:
        raise HTTPException(status_code=422, detail="请传 weights（或提供 snapshot_id → weights 的查询接口以支持降级回测）")

    # 直接使用本地回测（已修复的版本）
    local = local_backtest(raw_weights, window_days, req.benchmark_symbol or "SPY")
    backtest_id = "bt_" + hashlib.md5(
        f"local|{window_days}|{req.trading_cost}|{req.rebalance or 'weekly'}|{time.time()}".encode("utf-8")
    ).hexdigest()[:10]

    return {
        "success": True,
        **local,
        "params": {
            "window": req.window or f"{window_days}D",
            "cost": req.trading_cost,
            "rebalance": req.rebalance or "weekly",
            "max_trades_per_week": req.max_trades_per_week or 3,
        },
        "version_tag": "bt_local_v1",
        "backtest_id": backtest_id,
    }
# backtest.py — 统一到 /api/backtest/run，并兼容 holdings；更健壮的日期并集 + 前向填充
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple
import hashlib, time, math, json, urllib.request

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

# ---------- 请求模型 ----------
class WeightItem(BaseModel):
    symbol: str
    weight: float

class RunBacktestReq(BaseModel):
    snapshot_id: Optional[str] = None
    weights: Optional[List[WeightItem]] = None
    holdings: Optional[List[Dict[str, Any]]] = None

    window: Optional[str] = None             # "1Y" | "6M" | "90D" | "252"
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
    """
    使用已有价格接口：/api/prices/daily?symbol=XXX&limit=N
    标准化输出：[{"date":"YYYY-MM-DD","close":...}, ...]（按时间升序）
    """
    url = f"http://127.0.0.1:8000/api/prices/daily?symbol={symbol}&limit={days}"
    try:
        with urllib.request.urlopen(url, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
            out = []
            for it in items:
                out.append({"date": it.get("date",""), "close": float(it.get("close", 0))})
            # 部分数据可能是倒序，这里统一按日期升序
            out = [x for x in out if x["date"]]
            out.sort(key=lambda x: x["date"])
            return out
        elif isinstance(data, list):
            out = []
            for it in data:
                d = it.get("date") if isinstance(it, dict) else None
                c = it.get("close") if isinstance(it, dict) else None
                if d and c is not None:
                    out.append({"date": d, "close": float(c)})
            out.sort(key=lambda x: x["date"])
            return out
        else:
            arr = data.get("series") or data.get("data") or []
            out = []
            for it in arr:
                d = it.get("date")
                c = it.get("close")
                if d and c is not None:
                    out.append({"date": d, "close": float(c)})
            out.sort(key=lambda x: x["date"])
            return out
    except Exception:
        return []

def _has_enough_prices(symbol: str, need_days: int) -> bool:
    arr = fetch_price_series_local(symbol, max(need_days+60, 420))
    return len(arr) >= int(need_days * 0.8)  # 放宽为 80% 覆盖率

def _ensure_prices_sync(symbols: List[str], need_days: int = 252) -> None:
    """
    回测前兜底：若价格不足，调用 /api/prices/fetch 拉全量；失败不抛异常
    """
    base = "http://127.0.0.1:8000"
    for s in symbols:
        s = (s or "").upper().strip()
        if not s:
            continue
        if _has_enough_prices(s, need_days):
            continue
        url = f"{base}/api/prices/fetch?symbol={s}&adjusted=true&outputsize=full"
        try:
            with urllib.request.urlopen(url, timeout=60) as _:
                pass
        except Exception:
            pass

def _reindex_union_forward_fill(series_maps: List[Tuple[str, float, Dict[str, float]]],
                                min_cov: float = 0.6
                               ) -> Tuple[List[str], List[Tuple[str, float, List[Optional[float]]]], List[str]]:
    """
    把每个标的的日期→收盘价 map 重采样到**并集日期**，用前向填充补缺；
    如果某标的覆盖率低于 min_cov（如 60%），则**丢弃**该标的。
    返回：dates, usable_series, dropped_symbols
    """
    if not series_maps:
        return [], [], []

    # 日期并集（字符串 YYYY-MM-DD）
    all_dates = sorted(set().union(*[set(m.keys()) for _,_,m in series_maps]))
    if len(all_dates) < 10:
        return [], [], [sym for sym,_,_ in series_maps]

    usable = []
    dropped = []
    for sym, w, mp in series_maps:
        # 原始覆盖率
        cov = sum(1 for d in all_dates if d in mp) / float(len(all_dates))
        if cov < min_cov:
            dropped.append(sym)
            continue

        # 前向填充
        seq: List[Optional[float]] = []
        last = None
        for d in all_dates:
            v = mp.get(d)
            if v is None:
                seq.append(last)
            else:
                last = float(v)
                seq.append(last)
        # 仍有大量 None（完全没首值），丢弃
        if all(x is None for x in seq):
            dropped.append(sym)
            continue
        usable.append((sym, w, seq))

    return all_dates, usable, dropped

def local_backtest(weights: List[Dict[str, Any]], days: int, benchmark: str = "SPY") -> Dict[str, Any]:
    # 1) 拉价格（多给些天数，保证覆盖）
    series_maps = []
    debug_rows = []
    for w in weights:
        sym = str(w.get("symbol") or "").upper().strip()
        wt  = float(w.get("weight") or 0.0)
        if not sym or wt <= 0:
            continue
        arr = fetch_price_series_local(sym, max(days+120, 600))
        mp = { (d.get("date") or "")[:10]: float(d.get("close") or 0.0)
               for d in arr if d.get("date") and d.get("close") is not None }
        debug_rows.append({"symbol": sym, "points": len(mp)})
        if len(mp) >= 10:
            series_maps.append((sym, wt, mp))

    if not series_maps:
        return {"dates": [], "nav": [], "benchmark_nav": [], "drawdown": [], "metrics": {}, "debug": {"symbols": debug_rows, "dropped": []}}

    # 2) 日期并集 + 前向填充，并按覆盖率过滤（<60%丢弃）
    dates, usable, dropped = _reindex_union_forward_fill(series_maps, min_cov=0.4)
    if len(dates) < 10 or not usable:
        return {"dates": [], "nav": [], "benchmark_nav": [], "drawdown": [], "metrics": {}, "debug": {"symbols": debug_rows, "dropped": dropped}}

    # 3) 归一化权重（基于 usable）
    total_w = sum(max(0.0, float(w)) for _, w, _ in usable) or 1.0
    ws = [(sym, float(w)/total_w, seq) for sym, w, seq in usable]

    # 4) 组合 NAV（用前向填充后的价序列）
    nav = [1.0]
    for i in range(1, len(dates)):
        r = 0.0
        for _, w, seq in ws:
            p0, p1 = seq[i-1], seq[i]
            if p0 and p1 and p0 > 0:
                r += w * (p1/p0 - 1.0)
            # 如果该标的在该日仍为 None（极少数），视为 0 收益
        nav.append(nav[-1] * (1.0 + r))

    # 5) 基准对齐到同一 dates（并做前向填充）
    bm_nav: List[float] = []
    try:
        bm_arr = fetch_price_series_local(benchmark, max(days+120, 600))
        bm = { (d.get("date") or "")[:10]: float(d.get("close") or 0.0)
               for d in bm_arr if d.get("date") and d.get("close") is not None }
        bm_seq: List[Optional[float]] = []
        last = None
        for d in dates:
            v = bm.get(d)
            if v is None:
                bm_seq.append(last)
            else:
                last = float(v)
                bm_seq.append(last)
        # 归一
        if bm_seq and bm_seq[0]:
            start = bm_seq[0]
            bm_nav = [ (x/start) if (x and start) else None for x in bm_seq ]
            # 用组合的有效点位做截断（避免 None）
            for i, x in enumerate(bm_nav):
                if x is None:
                    # 若仍为 None，就用最近的有效值
                    bm_nav[i] = bm_nav[i-1] if i > 0 else 1.0
        else:
            bm_nav = []
    except Exception:
        bm_nav = []

    dd = compute_drawdown(nav)
    metrics = compute_metrics(nav)
    return {
        "dates": dates,  # 已经是 "YYYY-MM-DD"
        "nav": nav,
        "benchmark_nav": bm_nav[:len(nav)] if bm_nav else [],
        "drawdown": dd[:len(nav)],
        "metrics": metrics,
        "debug": {
            "symbols": debug_rows,
            "used": [sym for sym,_,_ in usable],
            "dropped": dropped,
            "dates_cnt": len(dates),
        }
    }

def _align_lengths_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    dates = data.get("dates") or []
    nav = data.get("nav") or []
    k = min(len(dates), len(nav))
    if k <= 0:
        data["dates"], data["nav"] = [], []
        data["benchmark_nav"] = []
        data["drawdown"] = []
        data["metrics"] = {}
        return data
    data["dates"] = dates[:k]
    data["nav"] = nav[:k]
    if isinstance(data.get("benchmark_nav"), list):
        data["benchmark_nav"] = data["benchmark_nav"][:k]
    if isinstance(data.get("drawdown"), list):
        data["drawdown"] = data["drawdown"][:k]
    return data

# ---------- 主路由 ----------
@router.post("/run")
def run_backtest(req: RunBacktestReq):
    window_days = parse_window_days(req.window, req.window_days or 252)

    # 接受 weights 或 holdings（可同时传，合并归一化）
    merged: Dict[str, float] = {}

    if req.weights:
        for w in req.weights:
            if isinstance(w, dict):
                s = (w.get("symbol") or "").upper().strip()
                v = float(w.get("weight") or 0.0)
            else:
                d = w.model_dump()
                s = (d.get("symbol") or "").upper().strip()
                v = float(d.get("weight") or 0.0)
            if s:
                merged[s] = merged.get(s, 0.0) + v

    if req.holdings:
        for h in req.holdings:
            s = (str(h.get("symbol")) if h.get("symbol") is not None else "").upper().strip()
            v = float(h.get("weight") or 0.0)
            if s:
                merged[s] = merged.get(s, 0.0) + v

    if not merged and req.snapshot_id:
        # TODO: 若你支持 snapshot → weights 的查询，在此填充 merged
        pass

    if not merged:
        raise HTTPException(status_code=422, detail="请传 weights 或 holdings（或提供 snapshot_id → weights 的查询）")

    # 归一化
    total = sum(max(0.0, v) for v in merged.values())
    if total <= 0:
        raise HTTPException(status_code=422, detail="sum(weights) must be > 0")
    raw_weights = [{"symbol": s, "weight": v/total} for s, v in merged.items()]

    # 价格兜底（含基准）
    all_syms = [w["symbol"] for w in raw_weights]
    if req.benchmark_symbol:
        all_syms.append((req.benchmark_symbol or "SPY").upper())
    _ensure_prices_sync(all_syms, need_days=window_days)

    # 本地回测
    local = local_backtest(raw_weights, window_days, req.benchmark_symbol or "SPY")
    local = _align_lengths_payload(local)

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
        "version_tag": "bt_local_v2_union_ffill",
        "backtest_id": backtest_id,
    }

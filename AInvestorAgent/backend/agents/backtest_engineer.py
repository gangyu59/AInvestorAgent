from __future__ import annotations
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone
from math import sqrt
from .base_agent import Agent, ok, fail

class BacktestEngineer(Agent):
    """
    最小回测工程师：
      - 输入：kept(最终持仓) 或 weights([{symbol, weight}])，窗口(start/end 或 window_days)
      - 输出：dates/nav/drawdown/metrics（可直接画图）
      - 可选：benchmark_symbol（默认 SPY），mock(True) 离线演示
    """
    name = "backtest_engineer"
    desc = "周频再平衡的最小回测（含交易成本与指标）"

    def __init__(self, context: Dict[str, Any] | None = None):
        # Agent 基类没有 __init__ 方法，所以不需要调用 super()
        self.context = context or {}

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        kept = ctx.get("kept")
        weights_arr = ctx.get("weights")
        if not kept and not weights_arr:
            return fail(self.name, "需要 kept 或 weights 作为回测权重输入", {})

        use_mock = bool(ctx.get("mock", False))
        window_days = int(ctx.get("window_days", 120))
        end = ctx.get("end") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start = ctx.get("start") or (datetime.fromisoformat(end) - timedelta(days=window_days)).strftime("%Y-%m-%d")
        tc = float(ctx.get("trading_cost", 0.001))
        bench = ctx.get("benchmark_symbol", "SPY")

        # 组装权重
        if kept:
            weights = {p["symbol"]: float(p["weight"]) for p in kept}
        else:
            weights = {w["symbol"]: float(w["weight"]) for w in weights_arr}

        # 拉取价格并对齐
        price_map = {}
        for sym in weights.keys():
            series = _load_prices(sym, start, end, use_mock)
            if not series:
                return fail(self.name, f"未获得 {sym} 的价格数据", {})
            price_map[sym] = sorted(series, key=lambda x: x.get("date", ""))

        dates, closes = _align_by_date(price_map)
        if not dates:
            return fail(self.name, "无可用对齐交易日", {})
        result = _portfolio_nav(dates, closes, weights, tc)

        # 基准
        bench_series = _load_prices(bench, start, end, use_mock)
        bench_series = sorted(bench_series, key=lambda x: x.get("date", ""))
        bench_dates = [p["date"] for p in bench_series]
        bench_closes = [p["close"] for p in bench_series]
        # 对齐到组合 dates
        bench_map = {d: c for d, c in zip(bench_dates, bench_closes)}
        bseq = []
        for d in result["dates"]:
            if d in bench_map:
                bseq.append(bench_map[d])
            elif bseq:
                bseq.append(bseq[-1])
        if bseq:
            base = bseq[0]
            result["benchmark_nav"] = [round(x / base, 6) for x in bseq]
        else:
            result["benchmark_nav"] = []

        return ok(self.name, result, {"window": [start, end], "mock": use_mock})



def _load_prices(symbol: str, start: str, end: str, use_mock: bool) -> List[Dict[str, Any]]:
    if use_mock:
        # 120 根“缓慢上升”的模拟数据（便于离线可视）
        base = 100.0
        series = []
        d0 = datetime.fromisoformat(start)
        for i in range(120):
            d = d0 + timedelta(days=i)
            if d.weekday() >= 5:  # 跳过周末
                continue
            series.append({"date": d.strftime("%Y-%m-%d"), "close": round(base + i * 0.15, 4)})
        return series
    # 真实数据：走你已有的 AlphaVantage 或 DB
    try:
        # 用 backend.ingestion 作为包前缀，保证文件里的 '..core.config' 这类相对导入能解析
        from backend.ingestion.alpha_vantage_client import get_prices_range
        return get_prices_range(symbol, start_date=start, end_date=end)
    except Exception:
        from backend.ingestion.alpha_vantage_client import get_prices_for_symbol
        series = get_prices_for_symbol(symbol, limit=400)
        series = sorted(series, key=lambda x: x.get("date", ""))
        return [p for p in series if start <= p.get("date", "") <= end]

def _align_by_date(price_map: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[str], Dict[str, List[float]]]:
    # 对齐为相同 trading days（缺失用前值填充）
    # dates 升序
    all_dates = sorted(set(d for s in price_map.values() for d in [p["date"] for p in s]))
    closes = {sym: [] for sym in price_map}
    last_val = {sym: None for sym in price_map}
    idx_by_date = {sym: {p["date"]: p["close"] for p in series} for sym, series in price_map.items()}
    for d in all_dates:
        for sym in price_map:
            v = idx_by_date[sym].get(d, last_val[sym])
            if v is None:
                # 若起始日还没有值，则跳过该日（尚未上市/数据缺失）
                continue
            closes[sym].append(v)
            last_val[sym] = v
    # 统一裁剪：取所有股票都有值的区间
    min_len = min(len(v) for v in closes.values()) if closes else 0
    dates = [d for d in all_dates][-min_len:] if min_len > 0 else []
    for sym in closes:
        closes[sym] = closes[sym][-min_len:]
    return dates, closes

def _daily_returns(series: List[float]) -> List[float]:
    rets = []
    for i in range(1, len(series)):
        a, b = series[i-1], series[i]
        rets.append(0.0 if a == 0 else (b - a) / a)
    return rets

def _rebalance_schedule(dates: List[str], freq: str = "W-MON") -> List[int]:
    # 简化：每周一（如果列表中存在该日）；否则取该周第一个交易日；返回索引
    idxs = []
    prev_week = None
    for i, d in enumerate(dates):
        dt = datetime.fromisoformat(d)
        wk = dt.isocalendar()[:2]  # (year, week)
        if wk != prev_week:
            idxs.append(i)
            prev_week = wk
    return idxs

def _portfolio_nav(dates: List[str], closes: Dict[str, List[float]], weights: Dict[str, float],
                   tc: float = 0.001) -> Dict[str, Any]:
    # 计算组合净值，周频再平衡；tc 为双边成本（万1=0.001）
    syms = list(weights.keys())
    # 归一化权重
    tw = sum(weights.values()) or 1.0
    w_target = {s: weights[s] / tw for s in syms}

    # 计算每支股票的日收益
    rets = {s: _daily_returns(closes[s]) for s in syms}
    # dates 对齐后，收益序列长度 = len(dates)-1
    n = len(dates)
    if n <= 1:
        return {"dates": dates, "nav": [1.0], "turnover": 0.0, "drawdown": [0.0]}

    nav = [1.0]
    # 初始持仓（按目标权重建仓，计一次成本）
    turnover = sum(abs(w_target[s]) for s in syms)
    nav[-1] *= (1 - tc * turnover)

    rebalance_points = set(_rebalance_schedule(dates))
    cur_w = dict(w_target)

    for t in range(1, n):
        # 组合当日收益
        day_ret = sum(cur_w[s] * rets[s][t-1] for s in syms)
        nav.append(nav[-1] * (1 + day_ret))

        if t in rebalance_points:
            # 调整到目标权重，计算换手
            # 近似：假设昨日收盘后按 nav[-1] 进行权重调整
            # 组合当前权重受价格变化而漂移，这里不精细复原，取简单近似：完全再平衡
            delta = sum(abs(cur_w[s] - w_target[s]) for s in syms)
            turnover += delta
            nav[-1] *= (1 - tc * delta)
            cur_w = dict(w_target)

    # 计算回撤
    dd = []
    peak = -1e18
    for v in nav:
        peak = max(peak, v)
        dd.append(0.0 if peak == 0 else (v - peak) / peak)

    # 组合日收益（从 nav 推导）
    port_daily = [nav[i] / nav[i-1] - 1 for i in range(1, len(nav))]

    # 年化收益率: 使用CAGR公式 (复合年增长率)
    if port_daily and nav[0] > 0:
        total_return = nav[-1] / nav[0]
        years = len(port_daily) / 252.0
        ann = (total_return ** (1.0 / years)) - 1.0 if years > 0 and total_return > 0 else 0.0
    else:
        ann = 0.0

    # Sharpe比率: (avg_daily / std_daily) * sqrt(252)
    if port_daily:
        avg_d = sum(port_daily) / len(port_daily)
        var_d = sum((x - avg_d) ** 2 for x in port_daily) / max(len(port_daily) - 1, 1)
        std_d = var_d ** 0.5
        sharpe = (avg_d / std_d) * (252 ** 0.5) if std_d > 1e-12 else 0.0
    else:
        sharpe = 0.0

    win = sum(1 for x in port_daily if x > 0) / max(1, len(port_daily))
    max_dd = min(dd) if dd else 0.0

    return {
        "dates": dates,
        "nav": [round(x, 6) for x in nav],
        "drawdown": [round(x, 6) for x in dd],
        "metrics": {
            "ann_return": round(ann, 6),
            "annualized_return": round(ann, 6),  # 兼容旧字段名
            "max_dd": round(max_dd, 6),
            "mdd": round(max_dd, 6),             # 兼容前端
            "max_drawdown": round(max_dd, 6),     # 兼容backtest.py命名
            "sharpe": round(sharpe, 4),
            "win_rate": round(win, 4),
            "turnover": round(turnover, 6),
        }
    }


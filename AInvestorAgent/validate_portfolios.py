# validate_portfolios.py
import json, urllib.request, urllib.error, random, time, os
from collections import defaultdict, Counter

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")

UNIVERSES = [
    # 常见大盘科技 + 中概
    ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","ORCL","AVGO","PDD","BABA"],
    # 加点金融/消费/工业
    ["JPM","BAC","WFC","C","V","MA","HD","COST","NKE","CAT","HON","UNP","AMT","NEE","LIN"],
    # 能源/原材料/公用事业混合
    ["XOM","CVX","COP","SLB","EOG","BHP","RIO","FCX","NEM","SCCO","DUK","SO","D","EXC"],
]

SETTINGS = [
    dict(topk=25, min_score=55),  # 宽松
    dict(topk=20, min_score=60),  # 常用
    dict(topk=15, min_score=65),  # 偏严
]

def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def check_constraints(holdings, min_pos, max_pos, max_stock=0.30, max_sector=0.50):
    assert holdings and isinstance(holdings, list), "空 holdings"
    # 唯一性
    syms = [ (h.get("symbol") or "").upper() for h in holdings ]
    assert len(syms) == len(set(syms)), f"重复持仓: { [k for k,c in Counter(syms).items() if c>1] }"

    # 权重和
    wsum = sum(float(h.get("weight",0)) for h in holdings)
    assert 0.99 <= wsum <= 1.01, f"权重和异常: {wsum}"

    # 非负/非 NaN
    for h in holdings:
        w = float(h.get("weight",0))
        assert w >= 0, f"{h.get('symbol')} 权重为负"
        # 可按需加 isnan 检查

    # 单票上限
    wmax = max(float(h.get("weight",0)) for h in holdings)
    assert wmax <= max_stock + 1e-9, f"单票>{max_stock}: {wmax}"

    # 持仓数量
    n = len(holdings)
    assert min_pos <= n <= max_pos, f"持仓数不在[{min_pos},{max_pos}]，n={n}"

    # 行业集中度
    by = defaultdict(float)
    for h in holdings:
        sec = (h.get("sector") or "Unknown").strip()
        by[sec] += float(h.get("weight",0))
    worst = max(by.items(), key=lambda kv: kv[1])
    assert worst[1] <= max_sector + 1e-9, f"行业>{max_sector}: {worst}"
    return dict(wsum=wsum, wmax=wmax, n=n, sector_dist=dict(by))

def run_decide(universe, setting, min_pos=6, max_pos=10, use_llm=True):
    payload = {
        "symbols": universe,
        "topk": setting["topk"],
        "min_score": setting["min_score"],
        "use_llm": use_llm,
        "params": {
            "risk.max_stock": 0.30,
            "risk.max_sector": 0.50,
            "risk.min_positions": min_pos,
            "risk.max_positions": max_pos
        }
    }
    return post_json("/orchestrator/decide", payload)

def run_backtest_from_holdings(holdings):
    payload = {
        "holdings": [{"symbol": h["symbol"], "weight": h["weight"]} for h in holdings],
        "window_days": 252,
        "rebalance": "weekly",
        "trading_cost": 0.001
    }
    return post_json("/api/backtest/run", payload)

def main():
    random.seed(42)
    failures = []
    print(f"API_BASE = {API_BASE}")

    for uix, uni in enumerate(UNIVERSES, 1):
        for s in SETTINGS:
            for use_llm in (True, False):
                tag = f"U{uix}-topk{s['topk']}-min{s['min_score']}-{'llm' if use_llm else 'rules'}"
                try:
                    resp = run_decide(uni, s, min_pos=6, max_pos=10, use_llm=use_llm)
                    holds = resp.get("holdings", [])
                    meta = check_constraints(holds, min_pos=6, max_pos=10)
                    print(f"[PASS] {tag}  n={meta['n']} wsum={meta['wsum']:.4f} wmax={meta['wmax']:.3f} sectors={list(meta['sector_dist'].items())[:3]}")
                    # 简单回测 smoke test
                    bt = run_backtest_from_holdings(holds)
                    dates = bt.get("dates") or bt.get("data",{}).get("dates")
                    nav = bt.get("nav") or bt.get("data",{}).get("nav")
                    assert dates and nav and len(dates)==len(nav), "回测返回空或长度不一致"
                except Exception as e:
                    failures.append((tag, str(e)))
                    print(f"[FAIL] {tag}: {e}")
                time.sleep(0.3)

    print("\n=== SUMMARY ===")
    if failures:
        for tag, err in failures[:10]:
            print(f"FAIL {tag}: {err}")
        print(f"\nTotal FAIL = {len(failures)} (see above).")
        raise SystemExit(1)
    else:
        print("All tests passed ✅")

if __name__ == "__main__":
    main()

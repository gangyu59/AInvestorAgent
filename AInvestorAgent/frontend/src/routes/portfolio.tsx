import { useEffect, useMemo, useState } from "react";
import { decideNow, type DecideResponse, runBacktest, type BacktestResponse } from "../services/endpoints";

export default function PortfolioPage() {
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<DecideResponse | null>(null);
  const [bt, setBt] = useState<BacktestResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pool, setPool] = useState("AAPL, MSFT, NVDA, AMZN, GOOGL");

  const weights = useMemo(
    () => Object.entries(res?.context?.weights || {}).sort((a, b) => b[1] - a[1]),
    [res]
  );

  // 首次自动生成一次
  useEffect(() => { void onDecide(); /* eslint-disable-next-line */ }, []);

  async function onDecide() {
    setLoading(true);
    setErr(null);
    try {
      const symbols = pool.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);

      // ① 调决策
      const r = await decideNow({ symbols });

      // ② 前端兜底：若没权重/订单，就用“等权 + kept 全部”
      const fromSvc = r?.context?.weights || {};
      const hasWeights = Object.keys(fromSvc).length > 0;

      const weights = hasWeights ? fromSvc : makeEqualWeights(symbols);
      const orders  = (r?.context?.orders && r.context.orders.length ? r.context.orders : []);
      const kept    = (r?.context?.kept && r.context.kept.length ? r.context.kept : (orders.length ? [] : symbols));

      // ③ 立刻落到页面（甜甜圈/建议表马上有内容）
      setRes({
        context: {
          ...r.context,
          weights,
          orders,
          kept,
          // 给一个标记，方便你在 UI 上区分是否为 mock（不显示也没事）
          version_tag: r.context?.version_tag || (hasWeights ? undefined : "mock-equal-weight"),
        }
      });

      // ④ 回测：有就用；没有就尝试跑一次。失败静默，不影响上面的展示
      if (r?.context?.backtest) {
        setBt(r.context.backtest);
      } else {
        runBacktest({ symbols: Object.keys(weights), weeks: 52, rebalance: "weekly" })
          .then(setBt)
          .catch(() => setBt(null));
      }
    } catch (e: any) {
      // 只有“决策失败”才显示红条；即便失败也保持原来已有内容
      setErr(e?.message || "生成失败");
    } finally {
      setLoading(false);
    }
  }


  // 调色板（10 色循环）
  const palette = [
    "#6ea8fe", "#ffe066", "#63e6be", "#faa2c1", "#ffd8a8",
    "#a5d8ff", "#b2f2bb", "#e599f7", "#ffa8a8", "#c5f6fa",
  ];


  const donut = useMemo(() => {
    const W = 360, H = 360, R = 140, C = 24, CX = W / 2, CY = H / 2;
    const list = weights.slice(0, 8); // 只画前 8
    const total = list.reduce((s, [, w]) => s + w, 0) || 1;
    let acc = 0;
    const arcs = list.map(([sym, w]) => {
      const a0 = (acc / total) * 2 * Math.PI; acc += w;
      const a1 = (acc / total) * 2 * Math.PI;
      return { sym, w, a0, a1 };
    });
    function arc(a0: number, a1: number) {
      const r = R, ir = R - C;
      const x0 = CX + r * Math.cos(a0), y0 = CY + r * Math.sin(a0);
      const x1 = CX + r * Math.cos(a1), y1 = CY + r * Math.sin(a1);
      const xi0 = CX + ir * Math.cos(a0), yi0 = CY + ir * Math.sin(a0);
      const xi1 = CX + ir * Math.cos(a1), yi1 = CY + ir * Math.sin(a1);
      const large = a1 - a0 > Math.PI ? 1 : 0;
      return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} L ${xi1} ${yi1} A ${ir} ${ir} 0 ${large} 0 ${xi0} ${yi0} Z`;
    }
    return { W, H, CX, CY, arcs, arc };
  }, [weights]);

  return (
    <div className="page">
      <div className="page-header" style={{ gap: 8 }}>
        <h2>组合建议</h2>
        <input defaultValue={pool} onBlur={e => setPool(e.currentTarget.value)} style={{ minWidth: 360 }} />
        <button className="btn btn-primary" onClick={onDecide} disabled={loading}>
          {loading ? "生成中…" : "重新生成"}
        </button>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b" }}>
          <div className="card-body">{err}</div>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><h3>权重分布</h3></div>
          <div className="card-body" style={{display: "flex", gap: 16}}>
            <svg width={donut.W} height={donut.H}>
              {donut.arcs.map((a, i) => (
                  <path
                      key={i}
                      d={donut.arc(a.a0, a.a1)}
                      fill={palette[i % palette.length]}   // 关键：显式填充
                      stroke="transparent"                 // 防止被全局 stroke 影响
                  />
              ))}
              <text x={donut.CX} y={donut.CY} textAnchor="middle" dominantBaseline="middle" fontSize="18">Weight</text>
            </svg>
            <ul className="list">
              {weights.slice(0, 12).map(([sym, w], i) => (
                  <li key={sym} style={{display: "flex", alignItems: "center", gap: 8}}>
                  <span style={{
                    width: 8, height: 8, borderRadius: 9999,
                    background: palette[i % palette.length]
                  }}/>
                                <span>{sym} {(w * 100).toFixed(1)}%</span>
                              </li>
                          ))}
                          {weights.length === 0 && <li>无数据</li>}
            </ul>

          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>交易建议</h3></div>
          <div className="card-body">
            <div className="table">
              <div className="thead"><span>Symbol</span><span>Action</span><span>Target</span></div>
              <div className="tbody">
                {(res?.context?.orders || []).map((o, i) => (
                    <div className="row" key={i}>
                    <span>{o.symbol}</span>
                    <span>{o.action}</span>
                    <span>{o.weight != null ? (o.weight * 100).toFixed(1) + "%" : "-"}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="hint" style={{ marginTop: 8 }}>
              Kept: {(res?.context?.kept || []).join(", ") || "—"}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><h3>最近回测（1Y, weekly）</h3></div>
        {bt ? <NavChart bt={bt} /> : <div className="card-body">无回测数据</div>}
      </div>
    </div>
  );
}

function NavChart({ bt }: { bt: BacktestResponse }) {
  const W = 940, H = 240, P = 24;
  const nav = bt.nav || [];
  const bn = bt.benchmark_nav || [];
  const n = Math.max(nav.length, bn.length);
  if (!n) return <div className="card-body">无数据</div>;

  const all = [...nav, ...bn].filter((v) => typeof v === "number");
  const min = Math.min(...all), max = Math.max(...all), rng = (max - min) || 1;
  const x = (i: number) => P + (W - 2 * P) * (i / ((n - 1) || 1));
  const y = (v: number) => P + (H - 2 * P) * (1 - (v - min) / rng);

  function path(arr: number[]) {
    let p = "";
    for (let i = 0; i < arr.length; i++) {
      const v = arr[i];
      if (!Number.isFinite(v)) continue;
      p += `${p ? "L" : "M"} ${x(i)} ${y(v)} `;
    }
    return p.trim();
  }

  return (
    <svg width={W} height={H} style={{ display: "block" }}>
      <path d={path(nav)} fill="none" strokeWidth={2} />
      {bn.length > 0 && <path d={path(bn)} fill="none" strokeWidth={1.5} strokeOpacity={0.6} />}
      <text x={W - 90} y={18} fontSize="12">Ann: {fmtPct(bt.metrics?.ann_return)}</text>
      <text x={W - 90} y={36} fontSize="12">MDD: {fmtPct(bt.metrics?.mdd)}</text>
      <text x={W - 90} y={54} fontSize="12">Sharpe: {bt.metrics?.sharpe?.toFixed(2) ?? "-"}</text>
    </svg>
  );
}

function fmtPct(p?: number) { return p == null ? "-" : (p * 100).toFixed(1) + "%"; }

function makeEqualWeights(symbols: string[]): Record<string, number> {
  const list = symbols.map(s => s.trim().toUpperCase()).filter(Boolean);
  if (!list.length) return {};
  const w = 1 / list.length;
  return Object.fromEntries(list.map(s => [s, w]));
}

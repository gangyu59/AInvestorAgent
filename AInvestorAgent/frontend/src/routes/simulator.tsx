// frontend/src/routes/simulator.tsx
import { useEffect, useState, useRef } from "react";
import { BACKTEST_RUN, PRICES } from "../services/endpoints";

const NAV_COLOR = "#6ea8fe";
const BM_COLOR  = "#ffd43b";

type BacktestResponse = {
  dates?: string[];
  nav?: number[];
  benchmark_nav?: number[];
  drawdown?: number[];
  metrics?: { ann_return?: number; sharpe?: number; max_dd?: number; win_rate?: number; mdd?: number };
  params?: { window?: string; cost?: number; rebalance?: string; max_trades_per_week?: number };
  version_tag?: string;
  backtest_id?: string;
};
type PricePoint = { date: string; close: number };

export default function SimulatorPage() {
  const [pool, setPool] = useState("AAPL, MSFT, NVDA");
  const [bt, setBt] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const chartRef = useRef<HTMLDivElement | null>(null);

  // 从 URL 读取 sid（由 Portfolio 页跳转而来）
  function readSid(): string | null {
    const hash = window.location.hash || "";
    const i = hash.indexOf("?");
    if (i < 0) return null;
    const sp = new URLSearchParams(hash.slice(i + 1));
    return sp.get("sid") || sp.get("snapshot_id");
  }

  async function apiRunBacktestBySnapshot(snapshot_id: string): Promise<BacktestResponse> {
    const r = await fetch(BACKTEST_RUN, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        snapshot_id,
        window: "1Y",
        trading_cost: 0.001,
        rebalance: "weekly",
        max_trades_per_week: 3,
        benchmark_symbol: "SPY",
      }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  async function fetchPriceSeries(symbol: string, opts: { limit?: number } = {}): Promise<PricePoint[]> {
    const days = Math.max(5, opts.limit || 520);
    const url = PRICES(symbol, days); // 使用 endpoints.ts 中的 PRICES 函数

    console.log(`DEBUG: 正在获取 ${symbol} 价格，URL: ${url}`); // 调试信息

    try {
      const r = await fetch(url, { method: "GET" });
      if (!r.ok) {
        throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      }

      const data = await r.json();
      console.log(`DEBUG: ${symbol} 价格数据:`, data); // 调试信息

      // 根据你的 endpoints.ts 中的格式解析
      if (data && data.items && Array.isArray(data.items)) {
        const result = data.items.map((item: any) => ({
        date: item.date,
        close: +(item.close || 0),  // 使用 + 操作符转数字
        open: +(item.open || item.close || 0),
        high: +(item.high || item.close || 0),
        low: +(item.low || item.close || 0),
        volume: item.volume || 0
      })).filter((x: any) => x.date && Number.isFinite(x.close));

        console.log(`DEBUG: ${symbol} 解析后数据条数: ${result.length}`);
        return result;
      } else if (Array.isArray(data)) {
        return data;
      }

      console.warn(`DEBUG: ${symbol} 数据格式不符合预期:`, data);
      return [];
    } catch (e) {
      console.error(`获取 ${symbol} 价格失败:`, e);
      return [];
    }
  }

  async function run() {
    console.log("DEBUG: 开始回测");
    setLoading(true);
    setErr(null);
    const sid = readSid();
    const symbols = pool.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);

    console.log("DEBUG: snapshot_id =", sid);
    console.log("DEBUG: symbols =", symbols);

    try {
      // 1) 如果有 sid，优先使用后端回测
      if (sid) {
        console.log("DEBUG: 尝试使用 snapshot_id 回测");
        try {
          const r = await apiRunBacktestBySnapshot(sid);
          console.log("DEBUG: snapshot 回测结果:", r);
          if (r && (r.nav?.length || r.dates?.length)) {
            setBt(r);
            return;
          }
        } catch (e) {
          console.warn("DEBUG: snapshot 回测失败:", e);
        }
      }

      // 2) 前端等权重回测兜底
      console.log("DEBUG: 开始前端等权重回测");
      if (symbols.length === 0) {
        setErr("请提供有效的股票代码");
        return;
      }

      const local = await localEqualWeightBacktest(symbols, fetchPriceSeries);
      console.log("DEBUG: 前端回测结果:", local);

      if (local.nav?.length) {
        setBt(local);
      } else {
        setErr("回测未产生有效数据");
      }
    } catch (e: any) {
      console.error("DEBUG: 回测总体失败:", e);
      setErr(e?.message || "回测失败");
    } finally {
      setLoading(false);
    }
  }

  function exportCSV() {
    if (!bt) return;
    const dates = bt.dates || [];
    const nav = bt.nav || [];
    const bn = bt.benchmark_nav || [];
    const dd = (bt as any)?.drawdown ?? computeDrawdown(nav);
    const rows = [["date", "nav", "benchmark_nav", "drawdown"],
      ...dates.map((d, i) => [d, nav[i] ?? "", bn[i] ?? "", dd[i] ?? ""])
    ];
    const csv = rows.map(r => r.map(x => `"${String(x).replace(/"/g,'""')}"`).join(",")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `backtest_${new Date().toISOString().slice(0,16).replace(/[:T]/g,"-")}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
  }

  async function exportPNG(): Promise<void> {
    const root = chartRef.current;
    if (!root) return;
    const svg = root.querySelector('svg') as SVGSVGElement | null;
    if (!svg) return;

    const xml = new XMLSerializer().serializeToString(svg);
    const url = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xml);
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error('SVG image load failed'));
      img.src = url;
    });

    const canvas = document.createElement('canvas');
    canvas.width = svg.clientWidth || 940;
    canvas.height = svg.clientHeight || 260;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(img, 0, 0);
    const png = canvas.toDataURL('image/png');

    const a = document.createElement('a');
    a.href = png;
    a.download = 'equity_curve.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  useEffect(() => { void run(); /* mount 一次 */ }, []);

  return (
    <div className="page">
      <div className="page-header" style={{gap: 8}}>
        <h2>回测与模拟</h2>
        <input
          defaultValue={pool}
          onBlur={(e) => setPool(e.currentTarget.value)}
          style={{minWidth: 340}}
          placeholder="无 sid 时，使用这里的股票池做等权兜底回测"
        />
        <button className="btn btn-primary" onClick={run} disabled={loading}>
          {loading ? "回测中…" : "重新回测"}
        </button>
        <button className="btn" onClick={exportPNG} disabled={!bt}>导出 PNG</button>
        <button className="btn" onClick={exportCSV} disabled={!bt}>导出 CSV</button>
      </div>

      {err && (
        <div className="card" style={{borderColor: "#ff6b6b"}}>
          <div className="card-body">{err}</div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>NAV vs Benchmark</h3>
          {bt && (
            <div className="hint" style={{opacity: 0.75}}>
              window={(bt as any)?.params?.window ?? "-"} ·
              cost={(bt as any)?.params?.cost ?? "-"} ·
              rebalance={(bt as any)?.params?.rebalance ?? "-"} ·
              ver={(bt as any)?.version_tag ?? "-"}
            </div>
          )}
        </div>
        <div ref={chartRef}>
          {bt ? <NavChart bt={bt}/> : <div className="card-body">无数据</div>}
        </div>
      </div>

      {/* 回撤图 */}
      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-header"><h3>回撤</h3></div>
        {bt ? (
          <DrawdownChart
            dates={bt.dates || []}
            dd={(bt as any)?.drawdown ?? computeDrawdown(bt.nav || [])}
          />
        ) : (
          <div className="card-body">无数据</div>
        )}
      </div>

      {/* 指标面板 */}
      {bt && (
        <div className="card" style={{ marginTop: 12 }}>
          <div className="card-header"><h3>指标</h3></div>
          <div className="card-body" style={{ display: "flex", gap: 16 }}>
            <MetricCard label="年化" value={fmtPct(bt.metrics?.ann_return)} />
            <MetricCard label="Sharpe" value={fmtNum(bt.metrics?.sharpe, 2)} />
            <MetricCard label="最大回撤" value={fmtPct((bt as any)?.metrics?.max_dd ?? bt.metrics?.mdd)} />
            <MetricCard label="胜率" value={fmtPct((bt as any)?.metrics?.win_rate)} />
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------
   前端兜底：等权组合回测（与你原逻辑一致）
-------------------------------- */
async function localEqualWeightBacktest(
  symbols: string[],
  fetchPriceSeriesFn: (s: string, opts?: {limit?: number}) => Promise<PricePoint[]>
): Promise<BacktestResponse> {
  if (!symbols.length) return {nav: [], benchmark_nav: [], dates: [], metrics: {}};
  const limit = 520;
  const series = await Promise.all(symbols.map((s) => fetchPriceSeriesFn(s, {limit})));

  const valid: { sym: string; arr: PricePoint[] }[] = [];
  for (let i = 0; i < symbols.length; i++) {
    const arr = series[i] || [];
    if (arr.length >= 60) valid.push({sym: symbols[i], arr });
  }
  if (!valid.length) return { nav: [], benchmark_nav: [], dates: [], metrics: {} };

  const maps = valid.map(({ arr }) =>
    new Map(arr.map((p) => [keyDate(p.date), p.close]))
  );
  let dates = Array.from(maps[0].keys()).filter((d) =>
    maps.every((m) => m.has(d))
  );
  dates.sort();

  const nav: number[] = [];
  const rets: number[] = [];
  if (dates.length > 1) {
    nav.push(1);
    for (let i = 1; i < dates.length; i++) {
      const d0 = dates[i - 1];
      const d1 = dates[i];
      const rEach: number[] = [];
      for (const m of maps) {
        const p0 = m.get(d0)!;
        const p1 = m.get(d1)!;
        if (p0 && p1) rEach.push(p1 / p0 - 1);
      }
      const r = rEach.length > 0 ? rEach.reduce((a, b) => a + b, 0) / rEach.length : 0;
      rets.push(r);
      nav.push(nav[nav.length - 1] * (1 + r));
    }
  }

  // 基准：SPY
  let benchmark_nav: number[] = [];
  try {
    const spy = await fetchPriceSeriesFn("SPY", { limit });
    if (spy.length > 60) {
      const bm = new Map(spy.map((p) => [keyDate(p.date), p.close]));
      const bdates = dates.filter((d) => bm.has(d));
      if (bdates.length > 1) {
        const start = bm.get(bdates[0])!;
        benchmark_nav = bdates.map((d) => bm.get(d)! / start);
      }
      if (benchmark_nav.length !== nav.length) benchmark_nav = [];
    }
  } catch {
    benchmark_nav = [];
  }

  const metrics = calcMetricsFromNav(nav, rets);
  return { nav, benchmark_nav, dates, metrics, params: { window: "1Y", cost: 0, rebalance: "daily" }, version_tag: "local_eqw_v1" };
}

function keyDate(s: string): string { return s.slice(0, 10).replace(/-/g, ""); }
function calcMetricsFromNav(nav: number[], rets: number[]) {
  if (!nav.length) return {};
  const n = rets.length || 1;
  const total = nav[nav.length - 1] || 1;
  const ann_return = Math.pow(total, 252 / n) - 1;
  let peak = nav[0] || 1, mdd = 0;
  for (const v of nav) { if (v > peak) peak = v; if (peak > 0) mdd = Math.max(mdd, 1 - v/peak); }
  const mean = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const variance = rets.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (Math.max(rets.length - 1, 1));
  const std = Math.sqrt(variance);
  const sharpe = std > 0 ? (mean / std) * Math.sqrt(252) : 0;
  return { ann_return, mdd, sharpe };
}

/* ---------------- UI：简洁 NAV 图 ---------------- */
function NavChart({ bt }: { bt: BacktestResponse }) {
  const W = 940, H = 260, P = 24;
  const nav = bt.nav || [];
  const bn = bt.benchmark_nav || [];
  const n = Math.max(nav.length, bn.length);
  if (!n) return <div className="card-body">无数据</div>;

  const all = [...nav, ...bn].filter((v) => typeof v === "number");
  const min = Math.min(...all), max = Math.max(...all), rng = max - min || 1;
  const x = (i: number) => P + ((W - 2 * P) * i) / ((n - 1) || 1);
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
      {/* 组合 NAV：蓝色 */}
      <path d={path(nav)} fill="none" stroke={NAV_COLOR} strokeWidth={2} />
      {/* 基准 NAV：黄色 */}
      {bn.length > 0 && (
        <path d={path(bn)} fill="none" stroke={BM_COLOR} strokeWidth={1.5} strokeOpacity={0.9} />
      )}
      <text x={W - 120} y={18} fontSize="12">Ann: {fmtPct(bt.metrics?.ann_return)}</text>
      <text x={W - 120} y={36} fontSize="12">MDD: {fmtPct((bt.metrics?.max_dd ?? bt.metrics?.mdd))}</text>
      <text x={W - 120} y={54} fontSize="12">Sharpe: {fmtNum(bt.metrics?.sharpe, 2)}</text>
    </svg>
  );
}

function fmtPct(p?: number) { return p == null ? "-" : (p * 100).toFixed(1) + "%"; }
function computeDrawdown(nav: number[]): number[] {
  const dd: number[] = []; let peak = -Infinity;
  for (const v of nav || []) { if (typeof v !== "number") { dd.push(0); continue; } peak = Math.max(peak, v); dd.push(peak > 0 ? v / peak - 1 : 0); }
  return dd;
}
function DrawdownChart({ dates, dd }: { dates: string[]; dd: number[] }) {
  const W = 940, H = 180, P = 24;
  const n = dd.length; if (!n) return <div className="card-body">无数据</div>;
  const min = Math.min(...dd), max = Math.max(...dd); const rng = (max - min) || 1;
  const x = (i: number) => P + ((W - 2 * P) * i) / ((n - 1) || 1);
  const y = (v: number) => P + (H - 2 * P) * (1 - (v - min) / rng);
  let d = `M ${x(0)} ${y(0)} `; dd.forEach((v, i) => { d += `L ${x(i)} ${y(v)} `; }); d += `L ${x(n - 1)} ${y(0)} Z`;
  return (
    <svg width={W} height={H} style={{ display: "block" }}>
      <path d={d} fill="currentColor" fillOpacity={0.15} stroke="none" />
      <path d={dd.reduce((p,v,i)=>p+`${p?"L":"M"} ${x(i)} ${y(v)} `,"")} fill="none" strokeWidth={1.5} />
    </svg>
  );
}
function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card" style={{ padding: 12, minWidth: 140 }}>
      <div style={{ opacity: 0.7 }}>{label}</div>
      <div style={{ fontSize: 20 }}>{value}</div>
    </div>
  );
}
const fmtNum = (x?: number, d = 2) => (x == null ? "-" : Number.isFinite(x) ? x.toFixed(d) : "-");

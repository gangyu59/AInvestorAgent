import { useEffect, useState, useRef } from "react";
import {
  runBacktest,
  fetchPriceSeries,
  type BacktestResponse,
  type PricePoint,
} from "../services/endpoints";

const NAV_COLOR = "#6ea8fe";
const BM_COLOR  = "#ffd43b";

export default function SimulatorPage() {
  const [pool, setPool] = useState("AAPL, MSFT, NVDA");
  const [bt, setBt] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const chartRef = useRef<HTMLDivElement | null>(null);

  async function run() {
    setLoading(true);
    setErr(null);
    const symbols = pool
      .split(",")
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);

    try {
      // ① 先尝试服务端回测
      const r = await runBacktest({ symbols, weeks: 52, rebalance: "weekly" });
      if (r && (r.nav?.length || r.benchmark_nav?.length)) {
        setBt(r);
      } else {
        // ② 拿不到就前端兜底：用价格接口做等权回测
        const local = await localEqualWeightBacktest(symbols);
        setBt(local);
      }
    } catch (e: any) {
      // ③ 即使接口抛错，也用前端兜底，保证有图
      try {
        const local = await localEqualWeightBacktest(symbols);
        setBt(local);
      } catch (ee: any) {
        setErr(ee?.message || "回测失败");
      }
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
    // 1) 安全获取容器和 svg
    const root = chartRef.current;
    if (!root) return;
    const svg = root.querySelector('svg') as SVGSVGElement | null;
    if (!svg) return;

    // 2) SVG -> PNG
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

  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
      <div className="page">
        <div className="page-header" style={{gap: 8}}>
          <h2>回测与模拟</h2>
          <input
              defaultValue={pool}
              onBlur={(e) => setPool(e.currentTarget.value)}
              style={{minWidth: 340}}
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
   前端兜底：等权组合回测
   - 用 /api/prices/daily（已验证可用）取价
   - 与 SPY 做对比（获取失败则只画组合）
-------------------------------- */

async function localEqualWeightBacktest(
    symbols: string[]
): Promise<BacktestResponse> {
  if (!symbols.length) {
    return {nav: [], benchmark_nav: [], dates: [], metrics: {}};
  }

  // 取最近 520 个交易日，足够覆盖 1 年+
  const limit = 520;

  // 拉取每只股票的价格
  const series = await Promise.all(
      symbols.map((s) => fetchPriceSeries(s, {limit}))
  );

  // 过滤掉无数据的股票
  const valid: { sym: string; arr: PricePoint[] }[] = [];
  for (let i = 0; i < symbols.length; i++) {
    const arr = series[i] || [];
    if (arr.length >= 60) valid.push({sym: symbols[i], arr });
  }
  if (!valid.length) return { nav: [], benchmark_nav: [], dates: [], metrics: {} };

  // 按日期对齐：取交集，升序
  const maps = valid.map(({ arr }) =>
    new Map(arr.map((p) => [keyDate(p.date), p.close]))
  );
  let dates = Array.from(maps[0].keys()).filter((d) =>
    maps.every((m) => m.has(d))
  );
  dates.sort();

  // 计算每日组合收益（等权，每日再平衡）
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
      const r =
        rEach.length > 0
          ? rEach.reduce((a, b) => a + b, 0) / rEach.length
          : 0;
      rets.push(r);
      nav.push(nav[nav.length - 1] * (1 + r));
    }
  }

  // 基准：SPY（失败则为空）
  let benchmark_nav: number[] = [];
  try {
    const spy = await fetchPriceSeries("SPY", { limit });
    if (spy.length > 60) {
      const bm = new Map(spy.map((p) => [keyDate(p.date), p.close]));
      const bn: number[] = [];
      for (let i = 0; i < dates.length; i++) {
        const d = dates[i];
        if (!bm.has(d)) continue;
      }
      // 对齐后计算 NAV
      const bdates = dates.filter((d) => bm.has(d));
      if (bdates.length > 1) {
        const start = bm.get(bdates[0])!;
        benchmark_nav = bdates.map((d) => bm.get(d)! / start);
      }
      // 若对齐不足，则置空
      if (benchmark_nav.length !== nav.length) benchmark_nav = [];
    }
  } catch {
    benchmark_nav = [];
  }

  const metrics = calcMetricsFromNav(nav, rets);

  return { nav, benchmark_nav, dates, metrics };
}

function keyDate(s: string): string {
  // 粗暴归一化日期 key，兼容 "2023-01-01" / "20230101" / "2023-01-01T15:30:00Z"
  return s.slice(0, 10).replace(/-/g, "");
}

function calcMetricsFromNav(nav: number[], rets: number[]): {
  ann_return?: number;
  mdd?: number;
  sharpe?: number;
} {
  if (!nav.length) return {};
  // 年化：按交易日 252
  const n = rets.length || 1;
  const total = nav[nav.length - 1];
  const ann_return = Math.pow(total, 252 / n) - 1;

  // 最大回撤
  let peak = nav[0] || 1;
  let mdd = 0;
  for (const v of nav) {
    if (v > peak) peak = v;
    const dd = peak > 0 ? 1 - v / peak : 0;
    if (dd > mdd) mdd = dd;
  }

  // Sharpe：日均/日波动 * sqrt(252)
  const mean =
    rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const variance =
    rets.reduce((a, b) => a + Math.pow(b - mean, 2), 0) /
    (Math.max(rets.length - 1, 1));
  const std = Math.sqrt(variance);
  const sharpe = std > 0 ? (mean / std) * Math.sqrt(252) : 0;

  return { ann_return, mdd, sharpe };
}

/* ---------------- UI：简洁 NAV 图 ---------------- */

function NavChart({ bt }: { bt: BacktestResponse }) {
  const W = 940,
    H = 260,
    P = 24;
  const nav = bt.nav || [];
  const bn = bt.benchmark_nav || [];
  const n = Math.max(nav.length, bn.length);
  if (!n) return <div className="card-body">无数据</div>;

  const all = [...nav, ...bn].filter((v) => typeof v === "number");
  const min = Math.min(...all),
    max = Math.max(...all),
    rng = max - min || 1;
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
      <path
        d={path(nav)}
        fill="none"
        stroke={BM_COLOR}  // stroke={BM_COLOR}    显式设置颜色
        strokeWidth={2}
      />
      {/* 基准 NAV：黄色（有就画） */}
      {bn.length > 0 && (
        <path
          d={path(bn)}
          fill="none"
          stroke="#ffd43b"     // ✅ 显式设置颜色
          strokeWidth={1.5}
          strokeOpacity={0.9}
        />
      )}
      <text x={W - 120} y={18} fontSize="12">Ann: {fmtPct(bt.metrics?.ann_return)}</text>
      <text x={W - 120} y={36} fontSize="12">MDD: {fmtPct(bt.metrics?.mdd)}</text>
      <text x={W - 120} y={54} fontSize="12">Sharpe: {bt.metrics?.sharpe?.toFixed(2) ?? "-"}</text>
    </svg>
  );
}

function fmtPct(p?: number) {
  return p == null ? "-" : (p * 100).toFixed(1) + "%";
}

function computeDrawdown(nav: number[]): number[] {
  const dd: number[] = [];
  let peak = -Infinity;
  for (const v of nav || []) {
    if (typeof v !== "number") { dd.push(0); continue; }
    peak = Math.max(peak, v);
    dd.push(peak > 0 ? v / peak - 1 : 0);  // 0, -0.01, ...
  }
  return dd;
}

function DrawdownChart({ dates, dd }: { dates: string[]; dd: number[] }) {
  const W = 940, H = 180, P = 24;
  const n = dd.length;
  if (!n) return <div className="card-body">无数据</div>;
  const min = Math.min(...dd), max = Math.max(...dd);
  const rng = (max - min) || 1;
  const x = (i: number) => P + ((W - 2 * P) * i) / ((n - 1) || 1);
  const y = (v: number) => P + (H - 2 * P) * (1 - (v - min) / rng);
  // 面积路径（以 0 为闭合）
  let d = `M ${x(0)} ${y(0)} `;
  dd.forEach((v, i) => { d += `L ${x(i)} ${y(v)} `; });
  d += `L ${x(n - 1)} ${y(0)} Z`;
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

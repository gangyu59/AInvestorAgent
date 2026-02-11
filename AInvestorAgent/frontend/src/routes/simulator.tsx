// 完整修复后的 simulator.tsx
import { useEffect, useState, useRef } from "react";
import { API_BASE } from "../services/endpoints";

const NAV_COLOR = "#6ea8fe";
const BM_COLOR  = "#ffd43b";

type BacktestResponse = {
  dates?: string[];
  nav?: number[];
  benchmark_nav?: number[];
  drawdown?: number[];
  metrics?: { ann_return?: number; sharpe?: number; max_dd?: number; win_rate?: number; winrate?: number; mdd?: number };
  params?: { window?: string; cost?: number; rebalance?: string; max_trades_per_week?: number };
  version_tag?: string;
  backtest_id?: string;
};

type Holding = {
  symbol: string;
  weight: number;
};

type PricePoint = { date: string; close: number };

const BACKTEST_RUN = `${API_BASE}/api/backtest/run`;
// 🔧 修复：使用正确的快照端点
const PORTFOLIO_PROPOSE = `${API_BASE}/api/portfolio/propose`;
const PRICES = (symbol: string, days: number) => `${API_BASE}/api/prices/daily?symbol=${symbol}&limit=${days}`;

export default function SimulatorPage() {
  // 🔧 修复：不设默认值，等待从 URL 或快照加载
  const [pool, setPool] = useState("");
  const [bt, setBt] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const chartRef = useRef<HTMLDivElement | null>(null);
  const hasInitialized = useRef(false);

  // 从 URL 读取 sid（由 Portfolio 页跳转而来）
  function readSid(): string | null {
    const hash = window.location.hash || "";
    const i = hash.indexOf("?");
    if (i < 0) return null;
    const sp = new URLSearchParams(hash.slice(i + 1));
    return sp.get("sid") || sp.get("snapshot_id");
  }

  // 🔧 修复：优先从 sessionStorage 读取
  async function fetchSnapshotData(snapshot_id: string): Promise<{ holdings: Holding[] } | null> {
    try {
      // 🔧 方案0：从 sessionStorage 读取（Portfolio 页面传递的数据）
      console.log("📡 方案0：检查 sessionStorage");
      const cached = sessionStorage.getItem('backtestHoldings');
      if (cached) {
        try {
          const data = JSON.parse(cached);
          if (data.holdings && Array.isArray(data.holdings) && data.holdings.length > 0) {
            console.log("✅ 方案0成功，从 sessionStorage 读取:", data);
            // 清除缓存，避免下次误用
            sessionStorage.removeItem('backtestHoldings');
            return data;
          }
        } catch (e) {
          console.warn("⚠️ sessionStorage 数据解析失败");
        }
      }

      console.log("📡 方案1：尝试直接获取快照", snapshot_id);

      // 方案1：尝试直接获取（如果后端支持）
      try {
        const r = await fetch(`${API_BASE}/api/portfolio/snapshots/${snapshot_id}`);
        if (r.ok) {
          const data = await r.json();
          console.log("✅ 方案1成功，快照数据:", data);
          return data;
        }
      } catch (e) {
        console.log("⚠️ 方案1失败，尝试方案2");
      }

      // 方案2：如果快照端点不存在，通过 propose 重新生成（使用默认池）
      console.log("📡 方案2：使用默认股票池重新生成");
      const defaultSymbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "LLY"];

      const r = await fetch(PORTFOLIO_PROPOSE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols: defaultSymbols }),
      });

      if (!r.ok) {
        console.error("❌ 方案2也失败了");
        return null;
      }

      const data = await r.json();
      console.log("✅ 方案2成功，重新生成的数据:", data);
      return data;

    } catch (e) {
      console.error("❌ 获取快照数据异常:", e);
      return null;
    }
  }

  // 🔧 修复：使用正确的参数格式调用回测 API
  async function apiRunBacktest(holdings: Holding[]): Promise<BacktestResponse> {
    console.log("📡 调用回测 API");
    console.log("📦 holdings 数据:", holdings);

    // ✅ 后端期望的格式：weights 是一个数组 List[WeightItem]
    const weights = holdings.map(h => ({
      symbol: h.symbol,
      weight: h.weight
    }));

    console.log("📦 转换后的 weights 数组:", weights);

    const requestBody = {
      weights: weights,  // List[WeightItem] 格式
      window: "1Y",
      trading_cost: 0.001,
      rebalance: "weekly",
      benchmark_symbol: "SPY"
    };

    console.log("📦 完整请求体:", requestBody);

    const r = await fetch(BACKTEST_RUN, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    console.log("📨 响应状态:", r.status);

    if (!r.ok) {
      const errorText = await r.text();
      console.error("❌ API 错误:", errorText);
      throw new Error(`HTTP ${r.status}: ${errorText}`);
    }

    const result = await r.json();
    console.log("✅ 回测结果:", result);
    return result;
  }

  async function fetchPriceSeries(symbol: string, opts: { limit?: number } = {}): Promise<PricePoint[]> {
    const days = Math.max(5, opts.limit || 520);
    const url = PRICES(symbol, days);

    try {
      const r = await fetch(url, { method: "GET" });
      if (!r.ok) {
        throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      }

      const data = await r.json();
      if (data && data.items && Array.isArray(data.items)) {
        const result = data.items.map((item: any) => ({
          date: item.date,
          close: +(item.close || 0),
          open: +(item.open || item.close || 0),
          high: +(item.high || item.close || 0),
          low: +(item.low || item.close || 0),
          volume: item.volume || 0
        })).filter((x: any) => x.date && Number.isFinite(x.close));
        return result;
      } else if (Array.isArray(data)) {
        return data;
      }
      return [];
    } catch (e) {
      console.error(`获取 ${symbol} 价格失败:`, e);
      return [];
    }
  }

  // 🔧 修复：主回测函数
  async function run() {
    console.log("🎯 开始回测");
    setLoading(true);
    setErr(null);

    const sid = readSid();
    console.log("📋 snapshot_id =", sid);

    try {
      // 方案1: 如果有 snapshot_id，先获取快照数据，再用 holdings 调用回测
      if (sid) {
        console.log("🔄 使用快照回测");
        const snapshot = await fetchSnapshotData(sid);

        if (snapshot && snapshot.holdings && snapshot.holdings.length > 0) {
          console.log("✅ 获取到持仓数据:", snapshot.holdings);

          // 🔧 修复：更新输入框显示当前回测的股票
          const symbols = snapshot.holdings.map(h => h.symbol);
          const symbolsStr = symbols.join(", ");
          console.log("📝 更新输入框为:", symbolsStr);
          setPool(symbolsStr);

          try {
            const result = await apiRunBacktest(snapshot.holdings);

            if (result && (result.nav?.length || result.dates?.length)) {
              console.log("✅ 回测成功");
              setBt(result);
              return;
            } else {
              console.warn("⚠️ 回测返回空数据");
            }
          } catch (e) {
            console.error("❌ 后端回测失败:", e);
            setErr(`后端回测失败: ${(e as any)?.message}`);
            // 继续降级到前端回测
          }
        } else {
          console.warn("⚠️ 快照无持仓数据");
        }
      }

      // 方案2: 使用后端API回测（等权重），确保与首页使用同一引擎
      console.log("🔄 使用后端API等权重回测");
      let symbols = pool.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);

      if (symbols.length === 0) {
        const defaultSymbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"];
        console.log("📝 使用默认股票池:", defaultSymbols);
        setPool(defaultSymbols.join(", "));
        symbols = defaultSymbols;
      }

      // 构造等权重 holdings
      const eqWeight = 1.0 / symbols.length;
      const eqHoldings: Holding[] = symbols.map(s => ({ symbol: s, weight: eqWeight }));

      try {
        // 优先调用后端API，保证与首页同引擎
        const result = await apiRunBacktest(eqHoldings);
        if (result && (result.nav?.length || result.dates?.length)) {
          console.log("✅ 后端等权回测成功");
          setBt(result);
          return;
        }
      } catch (e) {
        console.warn("⚠️ 后端API不可达，降级到前端本地回测:", e);
      }

      // 仅在后端不可达时使用前端本地计算作为fallback
      console.log("🔄 降级：前端本地等权回测");
      const local = await localEqualWeightBacktest(symbols, fetchPriceSeries);
      if (local.nav?.length) {
        setBt(local);
      } else {
        setErr("回测未产生有效数据");
      }
    } catch (e: any) {
      console.error("❌ 回测总体失败:", e);
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

  // 🔧 修复：自动触发回测
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    const sid = readSid();
    console.log("🔍 Simulator 页面加载，snapshot_id =", sid);

    if (sid) {
      console.log("🎯 检测到 snapshot_id，自动触发回测");
      void run();
    } else {
      console.log("📌 无 snapshot_id，等待手动触发");
    }
  }, []);

  return (
    <div className="page">
      <div className="page-header" style={{gap: 8}}>
        <h2>📊 回测与模拟</h2>

        <input
          value={pool}
          onChange={(e) => setPool(e.currentTarget.value)}
          style={{minWidth: 340}}
          placeholder="无 sid 时，使用这里的股票池做等权兜底回测"
        />
        <button className="btn btn-primary" onClick={run} disabled={loading}>
          {loading ? "🔄 回测中…" : "🎯 重新回测"}
        </button>
        <button className="btn" onClick={exportPNG} disabled={!bt}>📥 导出 PNG</button>
        <button className="btn" onClick={exportCSV} disabled={!bt}>📥 导出 CSV</button>
      </div>

      {err && (
        <div className="card" style={{borderColor: "#ff6b6b", backgroundColor: "#fff5f5"}}>
          <div className="card-body" style={{color: "#c92a2a"}}>⚠️ {err}</div>
        </div>
      )}

      {loading && !bt && (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 40 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🔄</div>
            <div style={{ color: '#888' }}>正在运行回测，请稍候...</div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>📈 净值曲线 vs 基准</h3>
          {bt && (
            <div className="hint" style={{opacity: 0.75, fontSize: 12}}>
              窗口: {(bt as any)?.params?.window ?? "1Y"} ·
              成本: {((bt as any)?.params?.cost ?? 0.001) * 100}% ·
              调仓: {(bt as any)?.params?.rebalance ?? "weekly"} ·
              版本: {(bt as any)?.version_tag ?? "v1.0"}
            </div>
          )}
        </div>
        <div ref={chartRef}>
          {bt ? <NavChart bt={bt}/> : <div className="card-body" style={{textAlign: 'center', padding: 40, color: '#888'}}>暂无数据，请先运行回测</div>}
        </div>
      </div>

      {/* 回撤图 */}
      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-header"><h3>📉 最大回撤</h3></div>
        {bt ? (
          <DrawdownChart
            dates={bt.dates || []}
            dd={(bt as any)?.drawdown ?? computeDrawdown(bt.nav || [])}
          />
        ) : (
          <div className="card-body" style={{textAlign: 'center', padding: 40, color: '#888'}}>暂无数据</div>
        )}
      </div>

      {/* 指标面板 */}
      {bt && (
        <div className="card" style={{ marginTop: 12 }}>
          <div className="card-header"><h3>📊 关键指标</h3></div>
          <div className="card-body" style={{ display: "flex", gap: 16, flexWrap: 'wrap' }}>
            <MetricCard label="年化收益" value={fmtPct(bt.metrics?.ann_return)} />
            <MetricCard label="夏普比率" value={fmtNum(bt.metrics?.sharpe, 2)} />
            <MetricCard label="最大回撤" value={fmtPct((bt as any)?.metrics?.max_dd ?? bt.metrics?.mdd)} />
            <MetricCard label="胜率" value={fmtPct(bt.metrics?.winrate ?? (bt.metrics?.win_rate != null ? bt.metrics.win_rate / 100 : undefined))} />
          </div>
        </div>
      )}
    </div>
  );
}

/* 其余辅助函数保持不变 */
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
  let peak = nav[0] || 1, maxDd = 0;
  for (const v of nav) { if (v > peak) peak = v; if (peak > 0) maxDd = Math.max(maxDd, 1 - v/peak); }
  const mdd = -maxDd; // 负数表示回撤，与后端一致
  const mean = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const variance = rets.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (Math.max(rets.length - 1, 1));
  const std = Math.sqrt(variance);
  const sharpe = std > 0 ? (mean / std) * Math.sqrt(252) : 0;
  const winrate = rets.length > 0 ? rets.filter(r => r > 0).length / rets.length : 0;
  return { ann_return, mdd, sharpe, winrate };
}

function NavChart({ bt }: { bt: BacktestResponse }) {
  const W = 940, H = 300, P = 40; // 增加高度和边距以容纳坐标轴
  const nav = bt.nav || [];
  const bn = bt.benchmark_nav || [];
  const dates = bt.dates || [];
  const n = Math.max(nav.length, bn.length);
  if (!n) return <div className="card-body">无数据</div>;

  const all = [...nav, ...bn].filter((v) => typeof v === "number");
  const min = Math.min(...all), max = Math.max(...all), rng = max - min || 1;

  // 图表区域
  const chartLeft = P;
  const chartRight = W - P;
  const chartTop = P;
  const chartBottom = H - P;
  const chartWidth = chartRight - chartLeft;
  const chartHeight = chartBottom - chartTop;

  const x = (i: number) => chartLeft + (chartWidth * i) / ((n - 1) || 1);
  const y = (v: number) => chartTop + chartHeight * (1 - (v - min) / rng);

  function path(arr: number[]) {
    let p = "";
    for (let i = 0; i < arr.length; i++) {
      const v = arr[i];
      if (!Number.isFinite(v)) continue;
      p += `${p ? "L" : "M"} ${x(i)} ${y(v)} `;
    }
    return p.trim();
  }

  // Y轴刻度（净值）
  const yTicks = 5;
  const yTickValues = Array.from({ length: yTicks }, (_, i) =>
    min + (rng * i) / (yTicks - 1)
  );

  // X轴刻度（日期）
  const xTicks = Math.min(6, n); // 最多6个刻度
  const xTickIndices = Array.from({ length: xTicks }, (_, i) =>
    Math.floor((n - 1) * i / (xTicks - 1))
  );

  return (
    <svg width={W} height={H} style={{ display: "block" }}>
      {/* 背景网格线 */}
      {yTickValues.map((val, i) => (
        <line
          key={`grid-y-${i}`}
          x1={chartLeft}
          y1={y(val)}
          x2={chartRight}
          y2={y(val)}
          stroke="currentColor"
          strokeOpacity={0.1}
          strokeDasharray="2,2"
        />
      ))}

      {/* Y轴 */}
      <line
        x1={chartLeft}
        y1={chartTop}
        x2={chartLeft}
        y2={chartBottom}
        stroke="currentColor"
        strokeOpacity={0.3}
      />

      {/* Y轴刻度和标签 */}
      {yTickValues.map((val, i) => (
        <g key={`y-tick-${i}`}>
          <line
            x1={chartLeft - 5}
            y1={y(val)}
            x2={chartLeft}
            y2={y(val)}
            stroke="currentColor"
            strokeOpacity={0.5}
          />
          <text
            x={chartLeft - 10}
            y={y(val)}
            fontSize="11"
            fill="currentColor"
            textAnchor="end"
            dominantBaseline="middle"
            opacity={0.7}
          >
            {val.toFixed(2)}
          </text>
        </g>
      ))}

      {/* X轴 */}
      <line
        x1={chartLeft}
        y1={chartBottom}
        x2={chartRight}
        y2={chartBottom}
        stroke="currentColor"
        strokeOpacity={0.3}
      />

      {/* X轴刻度和标签 */}
      {xTickIndices.map((idx, i) => {
        const date = dates[idx] || "";
        const displayDate = date.slice(5, 10); // 显示 MM-DD
        return (
          <g key={`x-tick-${i}`}>
            <line
              x1={x(idx)}
              y1={chartBottom}
              x2={x(idx)}
              y2={chartBottom + 5}
              stroke="currentColor"
              strokeOpacity={0.5}
            />
            <text
              x={x(idx)}
              y={chartBottom + 18}
              fontSize="11"
              fill="currentColor"
              textAnchor="middle"
              opacity={0.7}
            >
              {displayDate}
            </text>
          </g>
        );
      })}

      {/* 数据线 */}
      <path d={path(nav)} fill="none" stroke={NAV_COLOR} strokeWidth={2.5} />
      {bn.length > 0 && (
        <path d={path(bn)} fill="none" stroke={BM_COLOR} strokeWidth={2} strokeOpacity={0.8} />
      )}

      {/* 图例 */}
      <g transform={`translate(${W - 140}, 20)`}>
        <rect x={0} y={0} width={12} height={12} fill={NAV_COLOR} />
        <text x={18} y={10} fontSize="12" fill="currentColor">组合</text>

        {bn.length > 0 && (
          <>
            <rect x={0} y={20} width={12} height={12} fill={BM_COLOR} />
            <text x={18} y={30} fontSize="12" fill="currentColor">基准 (SPY)</text>
          </>
        )}
      </g>

      {/* 指标文本 */}
      <text x={W - 140} y={60} fontSize="12" fill="currentColor" opacity={0.8}>
        Ann: {fmtPct(bt.metrics?.ann_return)}
      </text>
      <text x={W - 140} y={78} fontSize="12" fill="currentColor" opacity={0.8}>
        MDD: {fmtPct((bt.metrics?.max_dd ?? bt.metrics?.mdd))}
      </text>
      <text x={W - 140} y={96} fontSize="12" fill="currentColor" opacity={0.8}>
        Sharpe: {fmtNum(bt.metrics?.sharpe, 2)}
      </text>
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
  const W = 940, H = 220, P = 40; // 增加边距
  const n = dd.length;
  if (!n) return <div className="card-body">无数据</div>;

  const min = Math.min(...dd);
  const max = Math.max(...dd, 0); // 确保包含0
  const rng = (max - min) || 1;

  // 图表区域
  const chartLeft = P;
  const chartRight = W - P;
  const chartTop = P;
  const chartBottom = H - P;
  const chartWidth = chartRight - chartLeft;
  const chartHeight = chartBottom - chartTop;

  const x = (i: number) => chartLeft + (chartWidth * i) / ((n - 1) || 1);
  const y = (v: number) => chartTop + chartHeight * (1 - (v - min) / rng);

  // 面积路径
  let areaPath = `M ${x(0)} ${y(0)} `;
  dd.forEach((v, i) => { areaPath += `L ${x(i)} ${y(v)} `; });
  areaPath += `L ${x(n - 1)} ${y(0)} Z`;

  // 线条路径
  const linePath = dd.reduce((p, v, i) => p + `${p ? "L" : "M"} ${x(i)} ${y(v)} `, "");

  // Y轴刻度
  const yTicks = 5;
  const yTickValues = Array.from({ length: yTicks }, (_, i) =>
    min + (rng * i) / (yTicks - 1)
  );

  // X轴刻度
  const xTicks = Math.min(6, n);
  const xTickIndices = Array.from({ length: xTicks }, (_, i) =>
    Math.floor((n - 1) * i / (xTicks - 1))
  );

  return (
    <svg width={W} height={H} style={{ display: "block" }}>
      {/* 背景网格线 */}
      {yTickValues.map((val, i) => (
        <line
          key={`grid-y-${i}`}
          x1={chartLeft}
          y1={y(val)}
          x2={chartRight}
          y2={y(val)}
          stroke="currentColor"
          strokeOpacity={0.1}
          strokeDasharray="2,2"
        />
      ))}

      {/* Y轴 */}
      <line
        x1={chartLeft}
        y1={chartTop}
        x2={chartLeft}
        y2={chartBottom}
        stroke="currentColor"
        strokeOpacity={0.3}
      />

      {/* Y轴刻度和标签 */}
      {yTickValues.map((val, i) => (
        <g key={`y-tick-${i}`}>
          <line
            x1={chartLeft - 5}
            y1={y(val)}
            x2={chartLeft}
            y2={y(val)}
            stroke="currentColor"
            strokeOpacity={0.5}
          />
          <text
            x={chartLeft - 10}
            y={y(val)}
            fontSize="11"
            fill="currentColor"
            textAnchor="end"
            dominantBaseline="middle"
            opacity={0.7}
          >
            {(val * 100).toFixed(1)}%
          </text>
        </g>
      ))}

      {/* X轴 */}
      <line
        x1={chartLeft}
        y1={chartBottom}
        x2={chartRight}
        y2={chartBottom}
        stroke="currentColor"
        strokeOpacity={0.3}
      />

      {/* X轴刻度和标签 */}
      {xTickIndices.map((idx, i) => {
        const date = dates[idx] || "";
        const displayDate = date.slice(5, 10);
        return (
          <g key={`x-tick-${i}`}>
            <line
              x1={x(idx)}
              y1={chartBottom}
              x2={x(idx)}
              y2={chartBottom + 5}
              stroke="currentColor"
              strokeOpacity={0.5}
            />
            <text
              x={x(idx)}
              y={chartBottom + 18}
              fontSize="11"
              fill="currentColor"
              textAnchor="middle"
              opacity={0.7}
            >
              {displayDate}
            </text>
          </g>
        );
      })}

      {/* 面积填充 */}
      <path d={areaPath} fill="currentColor" fillOpacity={0.15} stroke="none" />

      {/* 线条 */}
      <path d={linePath} fill="none" stroke="currentColor" strokeWidth={2} />

      {/* 最大回撤标注 */}
      <text x={chartRight - 10} y={20} fontSize="12" fill="currentColor" textAnchor="end" opacity={0.8}>
        Max: {(min * 100).toFixed(2)}%
      </text>
    </svg>
  );
}
function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      padding: '16px 20px',
      minWidth: 140,
      border: '1px solid rgba(255, 255, 255, 0.1)',
      borderRadius: 8,
      background: 'rgba(255, 255, 255, 0.03)',
      backdropFilter: 'blur(10px)'
    }}>
      <div style={{
        opacity: 0.7,
        fontSize: 12,
        marginBottom: 6,
        color: 'currentColor'
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 28,
        fontWeight: 600,
        color: 'currentColor',
        fontFamily: 'monospace'
      }}>
        {value}
      </div>
    </div>
  );
}
const fmtNum = (x?: number, d = 2) => (x == null ? "-" : Number.isFinite(x) ? x.toFixed(d) : "-");
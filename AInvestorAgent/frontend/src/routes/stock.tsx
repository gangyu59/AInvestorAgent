import { useEffect, useMemo, useRef, useState } from "react";

// —— 轻量类型 ——
export type PricePoint = {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
};

export type BatchScoreItem = {
  symbol: string;
  factors?: {
    f_value?: number; f_quality?: number; f_momentum?: number; f_sentiment?: number; f_risk?: number;
  } | null;
  score?: {
    value?: number; quality?: number; momentum?: number; sentiment?: number; score?: number; version_tag?: string;
  } | null;
  updated_at?: string;
};

// —— 本页使用的极小 API 封装（避免依赖你其它 services 文件的导出差异）——
async function fetchDailyPrices(symbol: string, limit = 260): Promise<{ symbol: string; items: PricePoint[] }>{
  const base = (import.meta as any).env?.VITE_API_BASE || "";
  const r = await fetch(`${base}/api/prices/daily?symbol=${encodeURIComponent(symbol)}&limit=${limit}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`GET /api/prices/daily ${r.status}`);
  return r.json();
}
async function fetchScores(symbols: string[]): Promise<{ as_of: string; version_tag: string; items: BatchScoreItem[] }>{
  const base = (import.meta as any).env?.VITE_API_BASE || "";
  const r = await fetch(`${base}/api/scores/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols, mock: false }),
  });
  if (!r.ok) throw new Error(`POST /api/scores/batch ${r.status}`);
  return r.json();
}

// —— 小工具 ——
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
const fmt = (x: any, d = 2) => (typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--");
const pct = (x: any, d = 2) => (typeof x === "number" && Number.isFinite(x) ? `${(x * 100).toFixed(d)}%` : "--");

function sma(points: PricePoint[], n: number): (number | null)[] {
  const out: (number | null)[] = new Array(points.length).fill(null);
  let sum = 0;
  for (let i = 0; i < points.length; i++) {
    sum += points[i].close;
    if (i >= n) sum -= points[i - n].close;
    if (i >= n - 1) out[i] = sum / n;
  }
  return out;
}

const RANGES = [
  { key: "1mo", label: "1M", limit: 22 },
  { key: "3mo", label: "3M", limit: 66 },
  { key: "6mo", label: "6M", limit: 132 },
  { key: "1y",  label: "1Y", limit: 260 },
  { key: "ytd", label: "YTD", limit: 200 },
  { key: "max", label: "MAX", limit: 1000 },
];

function getSymbolFromHash(): string {
  try {
    const h = window.location.hash || "";
    const u = new URL(h.startsWith("#") ? h.slice(1) : h, window.location.origin);
    const q = u.searchParams.get("query") || u.searchParams.get("symbol") || "AAPL";
    return q.split(",")[0].trim().toUpperCase() || "AAPL";
  } catch {
    return "AAPL";
  }
}

export default function StockPage() {
  const [symbol, setSymbol] = useState<string>(getSymbolFromHash());
  const [rangeKey, setRangeKey] = useState<string>("6mo");
  const [series, setSeries] = useState<PricePoint[]>([]);
  const [score, setScore] = useState<BatchScoreItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [hoverI, setHoverI] = useState<number | null>(null);
  const [showMA, setShowMA] = useState({ ma5: true, ma10: true, ma20: true, ma60: false });

  // 监听 hash 变化：支持 /#/stock?symbol=TSLA
  useEffect(() => {
    const onHash = () => setSymbol(getSymbolFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // 加载价格 + 评分（评分只取本票的总分显示）
  useEffect(() => {
    let dead = false;
    (async () => {
      setLoading(true); setErr(null);
      try {
        const range = RANGES.find(r => r.key === rangeKey) || RANGES[2];
        const [px, sc] = await Promise.all([
          fetchDailyPrices(symbol, range.limit),
          fetchScores([symbol]).catch(() => ({ items: [] as BatchScoreItem[], as_of: "", version_tag: "" })),
        ]);
        if (dead) return;
        setSeries(px.items || []);
        setScore(sc.items?.find(i => i.symbol === symbol) || null);
      } catch (e: any) {
        if (!dead) setErr(e?.message || "加载失败");
      } finally {
        if (!dead) setLoading(false);
      }
    })();
    return () => { dead = true; };
  }, [symbol, rangeKey]);

  // 视图几何
  const view = useMemo(() => {
    if (!series.length) return null;
    const W = 940;
    const H_PRICE = 320;
    const H_VOL = 86;
    const PAD = { l: 56, r: 16, t: 16, b: 20 };
    const plotW = W - PAD.l - PAD.r;
    const H = H_PRICE + H_VOL + 24;

    const highs = series.map(d => d.high ?? d.close);
    const lows  = series.map(d => d.low  ?? d.close);
    const minP = Math.min(...lows);
    const maxP = Math.max(...highs);
    const padP = (maxP - minP) * 0.05 || 1;
    const yMin = minP - padP;
    const yMax = maxP + padP;

    const vols = series.map(d => d.volume || 0);
    const maxV = Math.max(1, ...vols);

    const n = series.length;
    const x  = (i: number) => PAD.l + (plotW * i) / (Math.max(1, n - 1));
    const y  = (p: number) => PAD.t + (H_PRICE - (H_PRICE * (p - yMin)) / (yMax - yMin));
    const yV = (v: number) => PAD.t + H_PRICE + 16 + (H_VOL - (H_VOL * v) / maxV);

    const barSpace = plotW / Math.max(1, n);
    const candleW = clamp(barSpace * 0.6, 3, 18);

    const gridLines = Array.from({ length: 5 }, (_, k) => {
      const py = PAD.t + (H_PRICE * k) / 4;
      const v  = yMax - (k * (yMax - yMin)) / 4;
      return { py, v };
    });

    const ma5  = sma(series, 5);
    const ma10 = sma(series, 10);
    const ma20 = sma(series, 20);
    const ma60 = sma(series, 60);

    return { W, H, H_PRICE, H_VOL, PAD, plotW, x, y, yV, candleW, gridLines, ma: { ma5, ma10, ma20, ma60 } };
  }, [series]);

  const hover = useMemo(() => {
    if (!view || !series.length || hoverI == null) return null;
    const i = clamp(hoverI, 0, series.length - 1);
    const d = series[i];
    const prevClose = i > 0 ? series[i - 1].close : d.close;
    const chg = (d.close - prevClose) / (prevClose || 1);
    return { i, d, chg };
  }, [hoverI, series, view]);

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!view || !series.length) return;
    const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    const px = e.clientX - rect.left;
    const i = Math.round(((px - view.PAD.l) / (view.plotW || 1)) * (series.length - 1));
    setHoverI(clamp(i, 0, series.length - 1));
  }

  return (
    <div className="page" style={{ padding: 16 }}>
      {/* 头部 */}
      <div className="page-header" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <h2 style={{ margin: 0 }}>{symbol}</h2>
        {/* ✅ 小心：score 是对象，这里只渲染数值字段，避免黑屏 */}
        {typeof (score?.score?.score) === "number" && (
          <div className="pill">Score {score!.score!.score}</div>
        )}
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          {RANGES.map(r => (
            <button
              key={r.key}
              className={`btn ${rangeKey === r.key ? "btn-primary" : ""}`}
              onClick={() => setRangeKey(r.key)}
            >{r.label}</button>
          ))}
          <div className="ma-toggle" style={{ display: "flex", gap: 8, color: "#9fb3c8" }}>
            <label><input type="checkbox" checked={showMA.ma5}  onChange={e => setShowMA(v => ({...v, ma5: e.target.checked}))}/> MA5</label>
            <label><input type="checkbox" checked={showMA.ma10} onChange={e => setShowMA(v => ({...v, ma10: e.target.checked}))}/> MA10</label>
            <label><input type="checkbox" checked={showMA.ma20} onChange={e => setShowMA(v => ({...v, ma20: e.target.checked}))}/> MA20</label>
            <label><input type="checkbox" checked={showMA.ma60} onChange={e => setShowMA(v => ({...v, ma60: e.target.checked}))}/> MA60</label>
          </div>
        </div>
      </div>

      {loading && <div style={{ margin: "12px 0" }}>加载中…</div>}
      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b", marginTop: 8 }}>
          <div className="card-body">{err}</div>
        </div>
      )}

      {!loading && !err && view && series.length > 0 && (
        <div className="chart-wrap" ref={wrapRef}>
          <svg width={view.W} height={view.H} onMouseMove={onMove} onMouseLeave={() => setHoverI(null)}>
            <rect x={0} y={0} width={view.W} height={view.H} fill="transparent" />

            {/* 价格网格 */}
            {view.gridLines.map((g, idx) => (
              <g key={idx}>
                <line x1={view.PAD.l} y1={g.py} x2={view.W - view.PAD.r} y2={g.py} stroke="#2b3444" strokeDasharray="4 4" />
                <text x={8} y={g.py + 4} fontSize="12" fill="#9fb3c8">{fmt(g.v)}</text>
              </g>
            ))}

            {/* 价格/量分隔线 */}
            <line x1={view.PAD.l} y1={view.PAD.t + view.H_PRICE + 8} x2={view.W - view.PAD.r} y2={view.PAD.t + view.H_PRICE + 8} stroke="#2b3444" />

            {/* 蜡烛 + 成交量 */}
            {series.map((d, i) => {
              const up = d.close >= (d.open ?? d.close);
              const color = up ? "#e54d42" : "#1bc47d"; // 红涨绿跌（贴近国内习惯）
              const cx = view.x(i);
              const yOpen = view.y(d.open ?? d.close);
              const yClose = view.y(d.close);
              const yHigh = view.y(d.high ?? d.close);
              const yLow  = view.y(d.low  ?? d.close);
              const bodyY = Math.min(yOpen, yClose);
              const bodyH = Math.max(1, Math.abs(yClose - yOpen));
              const x0 = cx - view.candleW / 2;

              const maxVol = Math.max(1, ...series.map(s => s.volume || 0));
              const vH = Math.max(1, (view.H_VOL * (d.volume || 0)) / maxVol);
              const vY = view.PAD.t + view.H_PRICE + 16 + (view.H_VOL - vH);
              const vX = cx - view.candleW / 2;

              return (
                <g key={i}>
                  <line x1={cx} y1={yHigh} x2={cx} y2={yLow} stroke={color} strokeWidth={1} />
                  <rect x={x0} y={bodyY} width={view.candleW} height={bodyH} fill={color} opacity={0.9} />
                  <rect x={vX} y={vY} width={view.candleW} height={vH} fill={color} opacity={0.35} />
                </g>
              );
            })}

            {/* MA 折线 */}
            {showMA.ma5  && renderMAPolyline(view, series, view.ma.ma5,  "#f6c945")}
            {showMA.ma10 && renderMAPolyline(view, series, view.ma.ma10, "#8ab4ff")}
            {showMA.ma20 && renderMAPolyline(view, series, view.ma.ma20, "#ff8ab3")}
            {showMA.ma60 && renderMAPolyline(view, series, view.ma.ma60, "#9be39b")}

            {/* X 轴日期刻度（6个） */}
            {Array.from({ length: 6 }, (_, k) => Math.round((series.length - 1) * (k / 5))).map((i, idx) => {
              const d = series[i]; const dt = new Date(d.date);
              const label = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
              return (
                <text key={idx} x={view.x(i)} y={view.PAD.t + view.H_PRICE + 36} fontSize="12" fill="#9fb3c8" textAnchor="middle">{label}</text>
              );
            })}

            {/* 十字线 */}
            {hover && (
              <line x1={view.x(hover.i)} y1={view.PAD.t} x2={view.x(hover.i)} y2={view.PAD.t + view.H_PRICE + 16 + view.H_VOL} stroke="#8899aa" strokeDasharray="3 3" />
            )}
          </svg>

          {/* 悬浮卡片（HTML 叠加） */}
          {hover && (
            <div className="chart-tooltip" style={{ position: "absolute", left: clamp(view!.x(hover.i) + 8, 8, view!.W - 220), top: 8, background: "#fff", color: "#111", padding: 10, borderRadius: 8, boxShadow: "0 4px 10px rgba(0,0,0,.08)", fontSize: 12 }}>
              <div className="tt-title" style={{ fontWeight: 700, marginBottom: 6 }}>{new Date(hover.d.date).toLocaleDateString()}</div>
              <div className="tt-grid" style={{ display: "grid", gridTemplateColumns: "36px 1fr 36px 1fr", gap: 6 }}>
                <span>开</span><b>{fmt(hover.d.open ?? hover.d.close)}</b>
                <span>高</span><b>{fmt(hover.d.high ?? hover.d.close)}</b>
                <span>低</span><b>{fmt(hover.d.low  ?? hover.d.close)}</b>
                <span>收</span><b>{fmt(hover.d.close)}</b>
                <span>涨跌</span><b style={{ color: hover.chg >= 0 ? "#e54d42" : "#1bc47d" }}>{pct(hover.chg)}</b>
                {typeof hover.d.volume !== "undefined" && (<><span>量</span><b>{hover.d.volume}</b></>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function renderMAPolyline(
  view: NonNullable<ReturnType<typeof useMemo>>,
  series: PricePoint[],
  ma: (number | null)[],
  stroke: string
) {
  const pts: string[] = [];
  for (let i = 0; i < series.length; i++) {
    const v = ma[i]; if (v == null) continue;
    pts.push(`${view.x(i)},${view.y(v)}`);
  }
  if (!pts.length) return null;
  return <polyline points={pts.join(" ")} fill="none" stroke={stroke} strokeWidth={1.6} />;
}

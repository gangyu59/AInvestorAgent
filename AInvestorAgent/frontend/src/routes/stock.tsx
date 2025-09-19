import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchPriceSeries,
  type PricePoint,
  scoreBatch,
  type ScoreItem,
} from "../services/endpoints";

type QueryMap = Record<string, string>;

const ranges = [
  { key: "1mo", label: "1M" },
  { key: "3mo", label: "3M" },
  { key: "6mo", label: "6M" },
  { key: "1y", label: "1Y" },
  { key: "ytd", label: "YTD" },
  { key: "max", label: "MAX" },
];

function parseQuery(q?: QueryMap): string[] {
  const raw = (q?.query || "AAPL, MSFT, NVDA").split(",");
  return raw.map(s => s.trim().toUpperCase()).filter(Boolean);
}

function sma(points: PricePoint[], n: number): (number | null)[] {
  const out: (number|null)[] = new Array(points.length).fill(null);
  let sum = 0;
  for (let i = 0; i < points.length; i++) {
    sum += points[i].close;
    if (i >= n) sum -= points[i - n].close;
    if (i >= n - 1) out[i] = sum / n;
  }
  return out;
}

function clamp(v: number, lo: number, hi: number) { return Math.max(lo, Math.min(hi, v)); }
function fmt(n: number) { return n.toFixed(n >= 100 ? 2 : 3); }
function fmtPct(p: number) { return (p * 100).toFixed(2) + "%"; }

export default function StockPage({ query }: { query?: QueryMap }) {
  const [range, setRange] = useState("6mo");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [series, setSeries] = useState<PricePoint[]>([]);
  const [score, setScore] = useState<ScoreItem | null>(null);

  const list = parseQuery(query);
  const symbol = list[0] || "AAPL";

  // 交互状态
  const [hoverI, setHoverI] = useState<number | null>(null);
  const [showMA, setShowMA] = useState({ ma5: true, ma10: true, ma20: true, ma60: false });
  const wrapRef = useRef<HTMLDivElement | null>(null);

  // 拉取价格序列 + 评分（评分仅在标题旁做辅助，不露出表格）
  useEffect(() => {
    let dead = false;
    (async () => {
      setLoading(true); setErr(null);
      try {
        const pPrices = fetchPriceSeries(symbol, { range, limit: 260 });
        const pScores = scoreBatch([symbol]).catch(() => [] as ScoreItem[]);

        const px = await pPrices;
        const scores = await pScores;

        if (dead) return;
        setSeries(px);
        setScore(scores.find(s => s.symbol === symbol) || null);
      } catch (e: any) {
        if (!dead) setErr(e?.message || "加载失败");
      } finally {
        if (!dead) setLoading(false);
      }
    })();
    return () => { dead = true; };
  }, [symbol, range]);

  // 计算图形坐标（价格主图 + 成交量副图）
  const view = useMemo(() => {
    if (!series.length) return null;

    const W = 940;            // 画布宽
    const H_PRICE = 320;      // 价格主图高
    const H_VOL = 86;         // 成交量副图高
    const H = H_PRICE + H_VOL + 24; // 总高（含间距）
    const PAD = { l: 56, r: 16, t: 16, b: 20 };
    const plotW = W - PAD.l - PAD.r;

    const closes = series.map(d => d.close);
    const highs  = series.map(d => d.high ?? d.close);
    const lows   = series.map(d => d.low  ?? d.close);
    const minP = Math.min(...lows);
    const maxP = Math.max(...highs);
    const padP = (maxP - minP) * 0.05 || 1; // 上下预留 5%
    const yMin = minP - padP;
    const yMax = maxP + padP;

    const vols = series.map(d => d.volume || 0);
    const maxV = Math.max(1, ...vols);

    const n = series.length;
    const x = (i: number) => PAD.l + (plotW * i) / (n - 1 || 1);
    const y = (p: number) => PAD.t + (H_PRICE - (H_PRICE * (p - yMin)) / (yMax - yMin));
    const yV = (v: number) => PAD.t + H_PRICE + 16 + (H_VOL - (H_VOL * v) / maxV);

    // 蜡烛宽度（蜡烛间留白 40%）
    const barSpace = plotW / (n || 1);
    const candleW = clamp(barSpace * 0.6, 3, 18);
    const wickXOffset = 0.5; // 细线居中微调

    // 价格网格（5条）
    const gridLines = Array.from({ length: 5 }, (_, k) => {
      const py = PAD.t + (H_PRICE * k) / 4;
      const v  = yMax - (k * (yMax - yMin)) / 4;
      return { py, v };
    });

    // 移动平均
    const ma5  = sma(series, 5);
    const ma10 = sma(series, 10);
    const ma20 = sma(series, 20);
    const ma60 = sma(series, 60);

    return {
      W, H, H_PRICE, H_VOL, PAD, plotW,
      x, y, yV,
      candleW, wickXOffset,
      gridLines,
      ma: { ma5, ma10, ma20, ma60 },
    };
  }, [series]);

  // 悬浮工具信息
  const hover = useMemo(() => {
    if (!view || !series.length || hoverI == null) return null;
    const i = clamp(hoverI, 0, series.length - 1);
    const d = series[i];
    const prevClose = i > 0 ? series[i - 1].close : d.close;
    const chg = (d.close - prevClose) / (prevClose || 1);
    return { i, d, chg };
  }, [hoverI, series, view]);

  // 交互：鼠标坐标映射到索引
  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!view || !wrapRef.current || !series.length) return;
    const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    const px = e.clientX - rect.left;
    const i = Math.round(((px - view.PAD.l) / (view.plotW || 1)) * (series.length - 1));
    setHoverI(clamp(i, 0, series.length - 1));
  }

  function onLeave() { setHoverI(null); }

  return (
    <div className="page">
      {/* 页头 */}
      <div className="page-header">
        <h2 style={{marginRight: 8}}>{symbol}</h2>
        {score && <div className="pill">Score {score.score}</div>}
        <div className="actions" style={{marginLeft: "auto", gap: 6}}>
          {ranges.map(r => (
            <button
              key={r.key}
              className={`btn ${range === r.key ? "btn-primary" : ""}`}
              onClick={() => setRange(r.key)}
            >{r.label}</button>
          ))}
          {/* MA 切换 */}
          <div className="ma-toggle">
            <label><input type="checkbox" checked={showMA.ma5}  onChange={e => setShowMA(v => ({...v, ma5: e.target.checked}))}/>MA5</label>
            <label><input type="checkbox" checked={showMA.ma10} onChange={e => setShowMA(v => ({...v, ma10: e.target.checked}))}/>MA10</label>
            <label><input type="checkbox" checked={showMA.ma20} onChange={e => setShowMA(v => ({...v, ma20: e.target.checked}))}/>MA20</label>
            <label><input type="checkbox" checked={showMA.ma60} onChange={e => setShowMA(v => ({...v, ma60: e.target.checked}))}/>MA60</label>
          </div>
        </div>
      </div>

      {loading && <div style={{margin:"12px 0"}}>加载中…</div>}
      {err && <div className="card" style={{borderColor:"#ff6b6b"}}><div className="card-body">{err}</div></div>}

      {!loading && !err && view && series.length > 0 && (
        <div className="chart-wrap" ref={wrapRef}>
          <svg
            width={view.W}
            height={view.H}
            onMouseMove={onMove}
            onMouseLeave={onLeave}
          >
            {/* 背景 */}
            <rect x={0} y={0} width={view.W} height={view.H} fill="transparent" />

            {/* 价格网格线与刻度 */}
            {view.gridLines.map((g, idx) => (
              <g key={idx}>
                <line x1={view.PAD.l} y1={g.py} x2={view.W - view.PAD.r} y2={g.py} stroke="#2b3444" strokeDasharray="4 4" />
                <text x={8} y={g.py + 4} fontSize="12" fill="#9fb3c8">{fmt(g.v)}</text>
              </g>
            ))}

            {/* 成交量底部分隔线 */}
            <line
              x1={view.PAD.l} y1={view.PAD.t + view.H_PRICE + 8}
              x2={view.W - view.PAD.r} y2={view.PAD.t + view.H_PRICE + 8}
              stroke="#2b3444"
            />

            {/* 蜡烛 + 影线 + 成交量柱 */}
            {series.map((d, i) => {
              const up = (d.close >= (d.open ?? d.close));
              const color = up ? "#e54d42" : "#1bc47d"; // 红涨绿跌（贴近国内习惯）
              const cx = view.x(i);
              const yOpen = view.y(d.open ?? d.close);
              const yClose = view.y(d.close);
              const yHigh = view.y(d.high ?? d.close);
              const yLow  = view.y(d.low  ?? d.close);
              const bodyY = Math.min(yOpen, yClose);
              const bodyH = Math.max(1, Math.abs(yClose - yOpen));
              const x0 = cx - view.candleW / 2;

              // 成交量
              const vH = Math.max(1, (view.H_VOL * (d.volume || 0)) / Math.max(1, Math.max(...series.map(s => s.volume || 0))));
              const vY = view.PAD.t + view.H_PRICE + 16 + (view.H_VOL - vH);
              const vX = cx - view.candleW / 2;

              return (
                <g key={i}>
                  {/* 影线 */}
                  <line x1={cx + view.wickXOffset} y1={yHigh} x2={cx + view.wickXOffset} y2={yLow} stroke={color} strokeWidth="1" />
                  {/* 实体 */}
                  <rect x={x0} y={bodyY} width={view.candleW} height={bodyH} fill={color} opacity={0.9} />
                  {/* 成交量条 */}
                  <rect x={vX} y={vY} width={view.candleW} height={vH} fill={color} opacity={0.35} />
                </g>
              );
            })}

            {/* MA 折线覆盖 */}
            {showMA.ma5 && renderMAPath(view, series, view.ma.ma5, "#f6c945")}
            {showMA.ma10 && renderMAPath(view, series, view.ma.ma10, "#8ab4ff")}
            {showMA.ma20 && renderMAPath(view, series, view.ma.ma20, "#ff8ab3")}
            {showMA.ma60 && renderMAPath(view, series, view.ma.ma60, "#9be39b")}

            {/* X 轴日期（约 6 个刻度） */}
            {Array.from({length: 6}, (_, k) => Math.round((series.length - 1) * (k/5))).map((i, idx) => {
              const d = series[i];
              const dt = new Date(d.date);
              const label = `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,"0")}-${String(dt.getDate()).padStart(2,"0")}`;
              return (
                <text key={idx} x={view.x(i)} y={view.PAD.t + view.H_PRICE + 36} fontSize="12" fill="#9fb3c8" textAnchor="middle">
                  {label}
                </text>
              );
            })}

            {/* 十字线 / 悬浮 */}
            {hover && (
              <>
                <line
                  x1={view.x(hover.i)} y1={view.PAD.t}
                  x2={view.x(hover.i)} y2={view.PAD.t + view.H_PRICE + 16 + view.H_VOL}
                  stroke="#8899aa" strokeDasharray="3 3"
                />
              </>
            )}
          </svg>

          {/* 悬浮信息（HTML 覆盖层） */}
          {hover && (
            <div className="chart-tooltip" style={{left: clamp(view.x(hover.i) + 8, 8, view.W - 220), top: 8}}>
              <div className="tt-title">
                {new Date(hover.d.date).toLocaleDateString()}
              </div>
              <div className="tt-grid">
                <span>开</span><b>{fmt(hover.d.open ?? hover.d.close)}</b>
                <span>高</span><b>{fmt(hover.d.high ?? hover.d.close)}</b>
                <span>低</span><b>{fmt(hover.d.low  ?? hover.d.close)}</b>
                <span>收</span><b>{fmt(hover.d.close)}</b>
                <span>涨跌</span><b style={{color: hover.chg>=0 ? "#e54d42" : "#1bc47d"}}>{fmtPct(hover.chg)}</b>
                {typeof hover.d.volume !== "undefined" && (<><span>量</span><b>{hover.d.volume}</b></>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** 渲染 MA 折线路径 */
function renderMAPath(
  view: ReturnType<typeof useMemo> extends infer T ? T : never,
  series: PricePoint[],
  ma: (number | null)[],
  stroke: string
) {
  // 生成 path
  let path = "";
  for (let i = 0; i < series.length; i++) {
    const v = ma[i];
    if (v == null) continue;
    const cmd = path ? "L" : "M";
    path += `${cmd} ${ (view as any).x(i).toFixed(1) } ${ (view as any).y(v).toFixed(1) } `;
  }
  if (!path) return null;
  return <path d={path.trim()} fill="none" stroke={stroke} strokeWidth={1.6} />;
}

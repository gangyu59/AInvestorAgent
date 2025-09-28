import { useEffect, useMemo, useRef, useState } from "react";

// 轻量类型
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

// API封装
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

// 新增：智能分析API
async function fetchSmartAnalysis(symbol: string): Promise<any> {
  const base = (import.meta as any).env?.VITE_API_BASE || "";
  const r = await fetch(`${base}/api/analyze/smart/${encodeURIComponent(symbol)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  if (!r.ok) throw new Error(`POST /api/analyze/smart/${symbol} ${r.status}`);
  return r.json();
}

// 小工具
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

  // 新增：智能分析相关状态
  const [smartAnalysis, setSmartAnalysis] = useState<any>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [hoverI, setHoverI] = useState<number | null>(null);
  const [showMA, setShowMA] = useState({ ma5: true, ma10: true, ma20: true, ma60: false });

  // 监听 hash 变化
  useEffect(() => {
    const onHash = () => setSymbol(getSymbolFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // 加载价格 + 评分
  useEffect(() => {
    let dead = false;

    async function loadData() {
      setLoading(true);
      setErr(null);

      try {
        const range = RANGES.find(r => r.key === rangeKey) || RANGES[2];

        // 分别处理，不用Promise.all
        const px = await fetchDailyPrices(symbol, range.limit);
        let sc;
        try {
          sc = await fetchScores([symbol]);
        } catch {
          sc = { items: [], as_of: "", version_tag: "" };
        }

        if (dead) return;
        setSeries(px.items || []);
        setScore(sc.items.find(item => item.symbol === symbol) || null);

      } catch (e: any) {
        if (!dead) setErr(e?.message || "加载失败");
      } finally {
        if (!dead) setLoading(false);
      }
    }

    loadData();
    return () => { dead = true; };
  }, [symbol, rangeKey]);

  // 新增：智能分析函数
  const runSmartAnalysis = async () => {
    setAnalysisLoading(true);
    try {
      const result = await fetchSmartAnalysis(symbol);
      setSmartAnalysis(result);
    } catch (error: any) {
      setErr(`AI分析失败: ${error?.message || '未知错误'}`);
      console.error('Smart analysis failed:', error);
    } finally {
      setAnalysisLoading(false);
    }
  }

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
              const color = up ? "#e54d42" : "#1bc47d";
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

            {/* X 轴日期刻度 */}
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

          {/* 悬浮卡片 */}
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

      {/* 新增：分析卡片区域 */}
      {!loading && !err && (
        <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>

          {/* AI智能分析卡片 */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>AI智能分析</h3>
              <button
                onClick={runSmartAnalysis}
                disabled={analysisLoading}
                className={`btn ${analysisLoading ? '' : 'btn-primary'}`}
                style={{ fontSize: '14px', padding: '6px 12px' }}
              >
                {analysisLoading ? '分析中...' : '开始AI分析'}
              </button>
            </div>
            <div className="card-body">
              {smartAnalysis?.analysis ? (
                <div style={{ display: 'grid', gap: 12 }}>

                  {/* 基础评分 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8f9fa', borderRadius: '6px' }}>
                    <span>综合评分</span>
                    <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#2563eb' }}>
                      {smartAnalysis.analysis.score || '--'}/100
                    </span>
                  </div>

                  {/* 因子分解 */}
                  {smartAnalysis.analysis.factors && (
                    <div>
                      <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>因子分析</h4>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, fontSize: '13px' }}>
                        <div>价值: {fmt(smartAnalysis.analysis.factors.value, 2)}</div>
                        <div>质量: {fmt(smartAnalysis.analysis.factors.quality, 2)}</div>
                        <div>动量: {fmt(smartAnalysis.analysis.factors.momentum, 2)}</div>
                        <div>情绪: {fmt(smartAnalysis.analysis.factors.sentiment, 2)}</div>
                      </div>
                    </div>
                  )}

                  {/* LLM分析结果 */}
                  {smartAnalysis.analysis.llm_analysis && (
                    <div>
                      <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>AI投资建议</h4>
                      <div style={{ fontSize: '13px', lineHeight: '1.4' }}>
                        {smartAnalysis.analysis.llm_analysis.recommendation && (
                          <div style={{ marginBottom: 6 }}>
                            <span style={{ fontWeight: 600 }}>建议: </span>
                            <span style={{
                              color: smartAnalysis.analysis.llm_analysis.recommendation.includes('买入') ? '#059669' :
                                     smartAnalysis.analysis.llm_analysis.recommendation.includes('卖出') ? '#dc2626' : '#6b7280'
                            }}>
                              {smartAnalysis.analysis.llm_analysis.recommendation}
                            </span>
                          </div>
                        )}
                        {smartAnalysis.analysis.llm_analysis.confidence && (
                          <div style={{ marginBottom: 6 }}>
                            <span style={{ fontWeight: 600 }}>信心度: </span>
                            {smartAnalysis.analysis.llm_analysis.confidence}/10
                          </div>
                        )}
                        {smartAnalysis.analysis.llm_analysis.logic && (
                          <div style={{ marginBottom: 6 }}>
                            <span style={{ fontWeight: 600 }}>核心逻辑: </span>
                            {smartAnalysis.analysis.llm_analysis.logic}
                          </div>
                        )}
                        {smartAnalysis.analysis.llm_analysis.risk && (
                          <div style={{ marginBottom: 6 }}>
                            <span style={{ fontWeight: 600 }}>风险提示: </span>
                            <span style={{ color: '#dc2626' }}>
                              {smartAnalysis.analysis.llm_analysis.risk}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 错误处理 */}
                  {smartAnalysis.analysis.llm_analysis?.error && (
                    <div style={{ fontSize: '13px', color: '#dc2626', fontStyle: 'italic' }}>
                      LLM分析暂时不可用: {smartAnalysis.analysis.llm_analysis.error}
                    </div>
                  )}

                </div>
              ) : (
                <div style={{ textAlign: 'center', color: '#6b7280', fontSize: '14px', padding: '20px 0' }}>
                  点击"开始AI分析"获取技术指标和投资建议
                </div>
              )}
            </div>
          </div>

          {/* 量化评分详情卡片 */}
          {score?.score && (
            <div className="card">
              <div className="card-header">
                <h3>量化评分详情</h3>
              </div>
              <div className="card-body">
                <div style={{ display: 'grid', gap: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8f9fa', borderRadius: '6px' }}>
                    <span>总分</span>
                    <span style={{ fontSize: '18px', fontWeight: 'bold' }}>
                      {score.score.score || '--'}/100
                    </span>
                  </div>

                  {/* 评分分解条形图 */}
                  {score.score && (
                    <div style={{ fontSize: '13px' }}>
                      <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>评分构成</h4>
                      {[
                        { label: '价值', value: score.score.value, color: '#3b82f6' },
                        { label: '质量', value: score.score.quality, color: '#10b981' },
                        { label: '动量', value: score.score.momentum, color: '#f59e0b' },
                        { label: '情绪', value: score.score.sentiment, color: '#8b5cf6' }
                      ].map(item => (
                        <div key={item.label} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                          <span style={{ width: '40px', fontSize: '12px' }}>{item.label}</span>
                          <div style={{ flex: 1, height: '16px', background: '#e5e7eb', borderRadius: '8px', marginLeft: 8, marginRight: 8, overflow: 'hidden' }}>
                            <div
                              style={{
                                height: '100%',
                                background: item.color,
                                width: `${Math.max(0, Math.min(100, (item.value || 0)))}%`,
                                transition: 'width 0.3s ease'
                              }}
                            />
                          </div>
                          <span style={{ width: '35px', fontSize: '12px', textAlign: 'right' }}>
                            {fmt(item.value, 0)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {score.updated_at && (
                    <div style={{ fontSize: '12px', color: '#6b7280', textAlign: 'right' }}>
                      更新时间: {new Date(score.updated_at).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}

function renderMAPolyline(
  view: any,  // 修复：改为any类型，避免复杂的泛型推断
  series: PricePoint[],
  ma: (number | null)[],
  stroke: string
) {
  const pts: string[] = [];
  for (let i = 0; i < series.length; i++) {
    const v = ma[i];
    if (v == null) continue;
    pts.push(`${view.x(i)},${view.y(v)}`);
  }
  if (!pts.length) return null;
  return <polyline points={pts.join(" ")} fill="none" stroke={stroke} strokeWidth={1.6} />;
}
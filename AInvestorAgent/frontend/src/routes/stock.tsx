import { useEffect, useMemo, useState } from "react";
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

function formatDate(d: string) {
  const t = new Date(d);
  const m = String(t.getMonth() + 1).padStart(2, "0");
  const day = String(t.getDate()).padStart(2, "0");
  return `${t.getFullYear()}-${m}-${day}`;
}

export default function StockPage({ query }: { query?: QueryMap }) {
  const [range, setRange] = useState("6mo");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [series, setSeries] = useState<PricePoint[]>([]);
  const [score, setScore] = useState<ScoreItem | null>(null);

  const list = parseQuery(query);
  const symbol = list[0] || "AAPL";

  // 拉取价格序列 + 评分（并发启动，分别 await，避免 Promise.all 的类型联合）
  useEffect(() => {
    let dead = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const pPrices = fetchPriceSeries(symbol, { range, limit: 260 });
        const pScores = scoreBatch([symbol]).catch(
          () => [] as ScoreItem[]
        );

        const px = await pPrices;               // PricePoint[]
        const scores = await pScores;           // ScoreItem[]

        if (dead) return;
        setSeries(px);
        const found: ScoreItem | undefined = scores.find(
          (s: ScoreItem) => s.symbol === symbol
        );
        setScore(found ?? null);
      } catch (e: any) {
        if (!dead) setErr(e?.message || "加载失败");
      } finally {
        if (!dead) setLoading(false);
      }
    })();
    return () => {
      dead = true;
    };
  }, [symbol, range]);

  // 计算图形坐标
  const view = useMemo(() => {
    if (!series.length) return null;
    const w = 820, h = 260, pad = 24;
    const xs = series.map((_, i) => i);
    const ys = series.map(d => d.close);

    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const x = (i: number) =>
      pad + (w - pad * 2) * (i - xs[0]) / (xs[xs.length - 1] - xs[0] || 1);
    const y = (v: number) =>
      pad + (h - pad * 2) * (1 - (v - minY) / (maxY - minY || 1));

    const path = series
      .map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d.close).toFixed(1)}`)
      .join(" ");
    const area = `M ${x(xs[0]).toFixed(1)} ${y(minY).toFixed(1)} L ${path.slice(2)} L ${x(xs[xs.length - 1]).toFixed(1)} ${y(minY).toFixed(1)} Z`;

    return { w, h, pad, minY, maxY, path, area, x, y };
  }, [series]);

  return (
    <div className="page">
      <div className="page-header">
        <h2>{symbol}</h2>
        <div className="actions">
          {ranges.map(r => (
            <button
              key={r.key}
              className={`btn ${range === r.key ? "btn-primary" : ""}`}
              onClick={() => setRange(r.key)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="hint">
        {score ? <>Score: <b>{score.score}</b>（{score.as_of || "—"}）</> : "Score: 载入中…"}
      </div>

      {loading && <div style={{ margin: "12px 0" }}>加载中…</div>}
      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b" }}>
          <div className="card-body">{err}</div>
        </div>
      )}

      {!loading && !err && view && (
        <div className="chart card">
          <svg width={view.w} height={view.h}>
            <defs>
              <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopOpacity="0.25" />
                <stop offset="100%" stopOpacity="0" />
              </linearGradient>
            </defs>
            <line x1="24" y1="24" x2={view.w - 24} y2="24" stroke="#2b3444" strokeDasharray="4 4" />
            <line x1="24" y1={view.h - 24} x2={view.w - 24} y2={view.h - 24} stroke="#2b3444" strokeDasharray="4 4" />

            <path d={view.area} fill="url(#areaFill)" />
            <path d={view.path} fill="none" strokeWidth="2" />

            <text x={view.w - 60} y={24} fontSize="12" fill="#9fb3c8">
              {view.maxY.toFixed(2)}
            </text>
            <text x={view.w - 60} y={view.h - 10} fontSize="12" fill="#9fb3c8">
              {view.minY.toFixed(2)}
            </text>
          </svg>
        </div>
      )}

      <div className="card">
        <div className="card-header"><h3>Recent 30d</h3></div>
        <div className="table">
          <div className="thead">
            <span>Date</span><span>Open</span><span>High</span><span>Low</span><span>Close</span><span>Volume</span>
          </div>
          <div className="tbody">
            {series.slice(-30).reverse().map((d, i) => (
              <div className="row" key={i}>
                <span>{formatDate(d.date)}</span>
                <span>{d.open.toFixed(2)}</span>
                <span>{d.high.toFixed(2)}</span>
                <span>{d.low.toFixed(2)}</span>
                <span>{d.close.toFixed(2)}</span>
                <span>{d.volume ?? "-"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="hint">
        在首页搜索框输入代码后会跳到本页（`/#/stock?query=...`），本页自动按第一个代码加载。
      </div>
    </div>
  );
}

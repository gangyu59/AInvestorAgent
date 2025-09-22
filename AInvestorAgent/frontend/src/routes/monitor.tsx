import { useEffect, useMemo, useRef, useState } from "react";
import { fetchSentimentBrief, type SentimentBrief } from "../services/endpoints";

export default function MonitorPage() {
  const [q, setQ] = useState("AAPL, MSFT, NVDA, AMZN, GOOGL");
  const [brief, setBrief] = useState<SentimentBrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // === 让图表自适应容器宽度，避免被裁切 ===
  const chartWrapRef = useRef<HTMLDivElement | null>(null);
  const [wrapW, setWrapW] = useState(940);
  useEffect(() => {
    const resize = () => {
      const w = chartWrapRef.current?.clientWidth ?? 940;
      setWrapW(Math.max(320, Math.min(1200, w)));
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const symbols = q.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
      const b = await fetchSentimentBrief(symbols, 14);
      setBrief(b);
    } catch (e: any) {
      setErr(e?.message || "获取失败");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  // === 计算 SVG 路径（带上下 10% 缓冲，避免顶端被“顶住”） ===
  const chart = useMemo(() => {
    const s = brief?.series || [];
    if (!s.length) return null;
    const W = wrapW, H = 260;
    const PT = 24, PB = 28, PL = 24, PR = 24;

    const xs = s.map((_, i) => i);
    const ys = s.map(p => p.score);
    const rawMin = Math.min(0, ...ys);
    const rawMax = Math.max(0, ...ys);
    const pad = Math.max(0.1, (rawMax - rawMin) * 0.1); // 10% 头/脚留白
    const min = rawMin - pad, max = rawMax + pad;
    const rng = (max - min) || 1;

    const x = (i: number) => PL + (W - PL - PR) * (i / ((xs.length - 1) || 1));
    const y = (v: number) => PT + (H - PT - PB) * (1 - (v - min) / rng);

    let path = "";
    for (let i = 0; i < s.length; i++) {
      path += `${i ? "L" : "M"} ${x(i)} ${y(ys[i])} `;
    }
    const area = `M ${x(0)} ${y(0)} ${path.slice(1)} L ${x(s.length - 1)} ${y(0)} Z`;

    return { W, H, x, y, path, area };
  }, [brief, wrapW]);

  return (
    <div className="page">
      <div className="page-header" style={{ gap: 8 }}>
        <h2>舆情与监控</h2>
        <input
          defaultValue={q}
          onBlur={(e) => setQ(e.currentTarget.value)}
          onKeyDown={(e) => e.key === "Enter" && load()}
          style={{ minWidth: 360 }}
        />
        <button className="btn btn-primary" onClick={load} disabled={loading}>
          {loading ? "加载中…" : "刷新"}
        </button>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b" }}>
          <div className="card-body">{err}</div>
        </div>
      )}

      {/* ====== 情绪时间轴 ====== */}
      <div className="card">
        <div className="card-header"><h3>情绪时间轴（14日）</h3></div>
        <div
          className="card-body"
          ref={chartWrapRef}
          style={{
            padding: 12,
            overflow: "visible",      // 关键：不要裁切 SVG 顶部
          }}
        >
          {chart ? (
            <svg
              viewBox={`0 0 ${chart.W} ${chart.H}`}
              width="100%"
              height={chart.H}
              style={{ display: "block", overflow: "visible" }}  // 关键
            >
              {/* 面积 */}
              <path d={chart.area} fill="#6ea8fe" fillOpacity={0.15} />
              {/* 折线 */}
              <path d={chart.path} fill="none" stroke="#6ea8fe" strokeWidth={2} />
              {/* 0 轴虚线 */}
              <line
                x1={12}
                y1={chart.y(0)}
                x2={chart.W - 12}
                y2={chart.y(0)}
                stroke="#2b3444"
                strokeDasharray="4 4"
              />
            </svg>
          ) : (
            <div>暂无数据</div>
          )}
        </div>
      </div>

      {/* ====== 最新新闻（可滚动） ====== */}
      <div className="card">
        <div className="card-header"><h3>最新新闻</h3></div>
        <div
          className="card-body"
          style={{
            maxHeight: 420,           // 固定一个可视高度
            overflowY: "auto",        // 关键：滚动显示
            padding: 12,
          }}
        >
          <ul className="news-list" style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {(brief?.latest_news || []).map((n, i) => (
              <li
                key={i}
                style={{
                  margin: "8px 0",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  lineHeight: 1.35,
                }}
              >
                <a href={n.url} target="_blank" rel="noreferrer" style={{ flex: 1 }}>
                  {n.title}
                </a>
                {/* 情绪小圆角标签：负红/正绿/中性灰 */}
                <span
                  className="pill"
                  style={{
                    minWidth: 34,
                    textAlign: "center",
                    fontSize: 12,
                    borderRadius: 999,
                    padding: "2px 8px",
                    background:
                      n.score > 0.2 ? "rgba(16,185,129,.15)" :
                      n.score < -0.2 ? "rgba(239,68,68,.15)" : "rgba(148,163,184,.15)",
                    color:
                      n.score > 0.2 ? "rgb(16,185,129)" :
                      n.score < -0.2 ? "rgb(239,68,68)" : "rgb(148,163,184)",
                  }}
                >
                  {Number(n.score ?? 0).toFixed(1)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

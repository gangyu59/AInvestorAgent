// frontend/src/components/dashboard/MarketSentiment.tsx
import { useEffect, useState } from "react";
import { fetchSentimentBrief, type SentimentBrief } from "../../services/endpoints";

const fmt = (x: any, d = 1) => (typeof x === "number" ? x.toFixed(d) : "--");

export function MarketSentiment({ symbols }: { symbols?: string[] }) {
  const [sentiment, setSentiment] = useState<SentimentBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 使用实际有数据的股票
  const defaultSymbols = ["AAPL", "AMZN", "APP", "ARM", "AVGO"];
  const actualSymbols = symbols && symbols.length > 0 ? symbols : defaultSymbols;

  useEffect(() => {
    async function loadSentiment() {
      setLoading(true);
      setError(null);
      try {
        console.log("📊 MarketSentiment: 加载情绪数据", actualSymbols);
        const data = await fetchSentimentBrief(actualSymbols, 14);
        console.log("✅ MarketSentiment: 数据加载成功", data);
        setSentiment(data);
      } catch (e: any) {
        console.error("❌ MarketSentiment: 加载失败", e);
        setError(e?.message || "加载失败");
      } finally {
        setLoading(false);
      }
    }

    loadSentiment();
  }, [actualSymbols.join(",")]); // 当symbols改变时重新加载

  const items = sentiment?.latest_news || [];
  const series = sentiment?.series || [];

  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">市场情绪</h3>
        <button onClick={() => (window.location.hash = "#/monitor")}>查看详情 →</button>
      </div>

      <div className="dashboard-card-body">
        {/* 情绪趋势迷你图 */}
        <div className="dashboard-sentiment-chart sentiment-mini-line">
          {!loading && series.length > 0 ? (
            <svg width="100%" height="100%" viewBox="0 0 100 40" preserveAspectRatio="none">
              <polyline
                points={series
                  .map((p, i) => {
                    const x = (i / Math.max(series.length - 1, 1)) * 100;
                    // 将 -1~1 映射到 5~35 (上下留白)
                    const y = 20 - p.score * 10;
                    return `${x},${Math.max(5, Math.min(35, y))}`;
                  })
                  .join(" ")}
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
              />
              {/* 0轴参考线 */}
              <line x1="0" y1="20" x2="100" y2="20" stroke="#334155" strokeDasharray="2 2" opacity="0.3" />
            </svg>
          ) : (
            <svg width="100%" height="100%" viewBox="0 0 100 40" preserveAspectRatio="none">
              <line x1="0" y1="20" x2="100" y2="20" stroke="#334155" strokeWidth="2" opacity="0.3" />
            </svg>
          )}
        </div>

        <div className="dashboard-news-section">
          <h4 style={{ margin: "10px 0 8px 0" }}>最新动态 ({items.length})</h4>

          {loading && <div className="skeleton" style={{ height: 180, borderRadius: 10 }}></div>}

          {!loading && error && (
            <div className="dashboard-empty-state">
              <p style={{ color: "#ef4444" }}>⚠️ {error}</p>
              <button className="dashboard-btn-primary" onClick={() => window.location.reload()}>
                重新加载
              </button>
            </div>
          )}

          {!loading && !error && items.length === 0 && (
            <div className="dashboard-empty-state">
              <p>暂无新闻数据</p>
              <button className="dashboard-btn-primary" onClick={() => (window.location.hash = "#/monitor")}>
                去舆情监控页
              </button>
            </div>
          )}

          {!loading && !error && items.length > 0 && (
            <div className="news-scroll">
              {items.slice(0, 10).map((news: any, i: number) => (
                <div key={i} className="dashboard-news-item">
                  <div className="dashboard-news-content">
                    <a
                      className="dashboard-news-title"
                      href={news.url || "#"}
                      target="_blank"
                      rel="noreferrer"
                      title={news.title}
                    >
                      {news.title}
                    </a>
                    <span
                      className={
                        "dashboard-news-sentiment " +
                        (news.score > 0.2 ? "positive" : news.score < -0.2 ? "negative" : "neutral")
                      }
                      style={{
                        background:
                          news.score > 0.2
                            ? "rgba(16,185,129,.15)"
                            : news.score < -0.2
                            ? "rgba(239,68,68,.15)"
                            : "rgba(148,163,184,.15)",
                        color:
                          news.score > 0.2
                            ? "rgb(16,185,129)"
                            : news.score < -0.2
                            ? "rgb(239,68,68)"
                            : "rgb(148,163,184)",
                      }}
                    >
                      {news.score > 0 ? "+" : ""}
                      {fmt(news.score, 2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
const fmt = (x: any, d = 1) => (typeof x === "number" ? x.toFixed(d) : "--");

export function MarketSentiment({ sentiment }: { sentiment: any }) {
  const loading = !!(sentiment && (sentiment.loading || sentiment.isLoading));
  const items = (sentiment?.latest_news || sentiment?.news || []) as any[];

  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">市场情绪</h3>
        <button onClick={() => (window.location.hash = "#/monitor")}>查看详情 →</button>
      </div>

      <div className="dashboard-card-body">
        <div className="dashboard-sentiment-chart sentiment-mini-line">
          <svg width="100%" height="100%" viewBox="0 0 100 40" preserveAspectRatio="none">
            <polyline points="0,28 15,25 30,30 45,20 60,22 75,18 90,20 100,15" fill="none" stroke="#10b981" strokeWidth="2" />
          </svg>
        </div>

        <div className="dashboard-news-section">
          <h4 style={{ margin: "10px 0 8px 0" }}>最新动态</h4>

          {loading && <div className="skeleton" style={{ height: 180, borderRadius: 10 }}></div>}

          {!loading && (!items || items.length === 0) && (
            <div className="dashboard-empty-state">
              <p>暂无新闻或情绪数据</p>
              <button className="dashboard-btn-primary" onClick={() => (window.location.hash = "#/monitor")}>
                去舆情监控页
              </button>
            </div>
          )}

          {!loading && items && items.length > 0 && (
            <div className="news-scroll">
              {items.slice(0, 10).map((news: any, i: number) => (
                <div key={i} className="dashboard-news-item">
                  <div className="dashboard-news-content">
                    <a className="dashboard-news-title" href={news.url || "#"} target="_blank" rel="noreferrer">
                      {news.title}
                    </a>
                    <span
                      className={
                        "dashboard-news-sentiment " +
                        (news.score > 0 ? "positive" : news.score < 0 ? "negative" : "neutral")
                      }
                    >
                      {news.score > 0 ? "+" : ""}
                      {fmt(news.score, 1)}
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

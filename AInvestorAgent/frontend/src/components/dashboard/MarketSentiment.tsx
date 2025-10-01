const fmt = (x: any, d = 1) => typeof x === "number" ? x.toFixed(d) : "--";

export function MarketSentiment({ sentiment }: { sentiment: any }) {
  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">市场情绪</h3>
        <button onClick={() => window.location.hash = '#/monitor'}>查看详情 →</button>
      </div>
      <div className="dashboard-card-body">
        <div className="dashboard-sentiment-chart">
          <svg width="100%" height="100%"><line x1="0" y1="30" x2="100%" y2="30" stroke="#374151" strokeWidth="1"/><path d="M 0,40 Q 25,20 50,25 T 100,15" fill="none" stroke="#10b981" strokeWidth="2"/></svg>
        </div>
        <div className="dashboard-news-section">
          <h4>最新动态</h4>
          <div className="dashboard-news-list">
            {sentiment?.latest_news?.slice(0, 3).map((news: any, i: number) => (
              <div key={i} className="dashboard-news-item">
                <div className="dashboard-news-content">
                  <span className="dashboard-news-title">{news.title}</span>
                  <span className={`dashboard-news-sentiment ${news.score > 0 ? 'positive' : news.score < 0 ? 'negative' : 'neutral'}`}>{news.score > 0 ? '+' : ''}{fmt(news.score, 1)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
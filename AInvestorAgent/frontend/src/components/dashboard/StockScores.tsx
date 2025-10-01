export function StockScores({ scores }: { scores: any[] }) {
  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">股票池评分</h3>
        <button onClick={() => window.location.hash = '#/stock'}>查看更多 →</button>
      </div>
      <div className="dashboard-card-body">
        <div className="dashboard-scores-grid dashboard-scores-header"><span>代码</span><span>评分分布</span><span>总分</span><span>操作</span></div>
        {scores.slice(0, 5).map((item) => (
          <div key={item.symbol} className="dashboard-scores-grid">
            <span className="dashboard-scores-symbol">{item.symbol}</span>
            <svg width="100" height="30" className="dashboard-radar">
              {(() => {
                const factors = item.score?.factors || {};
                const order = ["value", "quality", "momentum", "growth", "news"];
                const vals = order.map(k => Math.max(0, Math.min(1, factors[k] || 0)));
                const cx = 15, cy = 15, r = 12, n = order.length;
                const points = vals.map((v, i) => {
                  const angle = -Math.PI / 2 + i * (2 * Math.PI / n);
                  const radius = r * v;
                  const x = cx + radius * Math.cos(angle);
                  const y = cy + radius * Math.sin(angle);
                  return `${x},${y}`;
                }).join(" ");
                return (<><circle cx={cx} cy={cy} r={r} fill="none" stroke="#374151" strokeWidth="1"/><polygon points={points} fill="rgba(59, 130, 246, 0.2)" stroke="#3b82f6" strokeWidth="1.5"/></>);
              })()}
            </svg>
            <span className={`dashboard-scores-total ${item.score?.score >= 80 ? 'good' : item.score?.score >= 70 ? 'mid' : 'bad'}`}>{item.score?.score || '--'}</span>
            <button className="dashboard-btn dashboard-btn-secondary" onClick={() => window.location.hash = `#/stock?query=${item.symbol}`}>详情</button>
          </div>
        ))}
      </div>
    </div>
  );
}
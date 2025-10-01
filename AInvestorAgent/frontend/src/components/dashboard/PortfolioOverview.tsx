const fmt = (x: any, d = 2) => typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--";
const pct = (x: any, d = 1) => x == null || !Number.isFinite(+x) ? "--" : `${(+x * 100).toFixed(d)}%`;

export function PortfolioOverview({ snapshot, keptTop5, decide, onDecide }: any) {
  return (
    <section className="dashboard-section">
      <h2 className="dashboard-section-title">投资组合概览</h2>
      <div className="dashboard-grid dashboard-grid-auto">
        <div className="dashboard-card">
          <div className="dashboard-card-header">
            <h3 className="dashboard-card-title">组合表现</h3>
            <button onClick={() => window.location.hash = '#/portfolio'}>查看详情 →</button>
          </div>
          <div className="dashboard-card-body">
            <div className="dashboard-kpi-grid">
              <div className="dashboard-kpi"><p className="dashboard-kpi-label">年化收益</p><p className={`dashboard-kpi-value large ${(snapshot?.metrics?.ann_return ?? 0) >= 0 ? 'up' : 'down'}`}>{pct(snapshot?.metrics?.ann_return, 1)}</p></div>
              <div className="dashboard-kpi"><p className="dashboard-kpi-label">夏普比率</p><p className="dashboard-kpi-value large neutral">{fmt(snapshot?.metrics?.sharpe, 2)}</p></div>
              <div className="dashboard-kpi"><p className="dashboard-kpi-label">最大回撤</p><p className="dashboard-kpi-value medium down">{pct(snapshot?.metrics?.mdd, 1)}</p></div>
              <div className="dashboard-kpi"><p className="dashboard-kpi-label">胜率</p><p className="dashboard-kpi-value medium up">{snapshot?.metrics?.winrate ? `${Math.round(snapshot.metrics.winrate * 100)}%` : '--'}</p></div>
            </div>
          </div>
        </div>

        <div className="dashboard-card">
          <div className="dashboard-card-header">
            <h3 className="dashboard-card-title">Top 5 持仓</h3>
            <button onClick={() => window.location.hash = '#/portfolio'}>查看详情 →</button>
          </div>
          <div className="dashboard-card-body">
            <div className="dashboard-holdings">
              {keptTop5.map(([sym, weight]: [string, number]) => (
                <div key={sym} className="dashboard-holding-item">
                  <span className="dashboard-holding-symbol">{sym}</span>
                  <span className="dashboard-holding-weight">{pct(weight, 1)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="dashboard-card">
          <div className="dashboard-card-header">
            <h3 className="dashboard-card-title">最新AI决策</h3>
            <button onClick={() => window.location.hash = '#/portfolio'}>查看详情 →</button>
          </div>
          <div className="dashboard-card-body">
            {decide?.context?.kept?.length ? (
              <div>
                <div className="dashboard-decision-summary">
                  <div className="dashboard-metric"><span className="dashboard-metric-label">选中股票</span><span className="dashboard-metric-value">{decide.context.kept.length} 只</span></div>
                  <div className="dashboard-metric"><span className="dashboard-metric-label">决策方法</span><span className="dashboard-metric-value">{decide?.context?.version_tag?.includes('ai') ? 'AI增强' : '传统算法'}</span></div>
                </div>
                <div className="dashboard-holdings-preview">
                  {decide.context.kept.slice(0, 4).map((symbol: string) => (
                    <div key={symbol} className="dashboard-holding-chip">
                      <span className="symbol">{symbol}</span>
                      <span className="weight">{((decide?.context?.weights?.[symbol] || 0) * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                  {decide.context.kept.length > 4 && <span className="dashboard-more">+{decide.context.kept.length - 4} 更多</span>}
                </div>
              </div>
            ) : (
              <div className="dashboard-empty-state">
                <span>暂无决策记录</span>
                <button onClick={onDecide} className="dashboard-btn dashboard-btn-primary">开始AI决策</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
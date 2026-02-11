// frontend/src/components/dashboard/PortfolioOverview.tsx
const fmt = (x: any, d = 2) => (typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--");
const pct = (x: any, d = 1) => (x == null || !Number.isFinite(+x) ? "--" : `${(+x * 100).toFixed(d)}%`);

type Props = {
  snapshot?: any;
  keptTop5?: Array<[string, number]>;
  onDecide?: () => void;
};

export function PortfolioOverview({ snapshot, keptTop5, onDecide }: Props) {
  // 🔧 确保keptTop5是数组
  const safeKeptTop5 = Array.isArray(keptTop5) ? keptTop5 : [];

  // 🔧 判断是否有数据
  const hasData = snapshot?.snapshot_id && safeKeptTop5.length > 0;

  // 🔧 构建正确的跳转链接
  const viewDetailLink = snapshot?.snapshot_id
    ? `#/portfolio?sid=${snapshot.snapshot_id}`
    : '#/portfolio';

  return (
    <div className="dashboard-card po-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">💼 投资组合概览</h3>
        {/* 🔧 始终显示"查看详情"按钮,可以查看或创建组合 */}
        <button
          className="dashboard-btn dashboard-btn-secondary"
          onClick={() => (window.location.hash = viewDetailLink)}
        >
          {hasData ? '查看详情 →' : '创建组合 →'}
        </button>
      </div>

      <div className="dashboard-card-body po-body">
        {/* 左:组合KPI */}
        <section className="po-panel">
          <h4 className="po-subtitle">组合KPI</h4>
          <div className="po-kpi-grid">
            <div className="kpi">
              <div className="label">年化收益</div>
              <div className="value">{pct(snapshot?.metrics?.ann_return, 2)}</div>
            </div>
            <div className="kpi">
              <div className="label">最大回撤</div>
              <div className="value">{pct(snapshot?.metrics?.mdd, 1)}</div>
            </div>
            <div className="kpi">
              <div className="label">Sharpe</div>
              <div className="value">{fmt(snapshot?.metrics?.sharpe, 2)}</div>
            </div>
            <div className="kpi">
              <div className="label">胜率</div>
              <div className="value">{pct(snapshot?.metrics?.winrate, 1)}</div>
            </div>
          </div>

          <div className="po-top5">
            <div className="text-sm text-gray-400 mb-1">Top 5 持仓权重</div>
            {safeKeptTop5.length > 0 ? (
              <div className="weights-list">
                {safeKeptTop5.map(([sym, w]) => (
                  <div key={sym} className="weights-row">
                    <span className="weights-sym">{sym}</span>
                    <div className="weights-bar">
                      <div className="weights-fill" style={{ width: `${Math.min(100, w * 100)}%` }} />
                    </div>
                    <span className="weights-val">{pct(w, 1)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '24px 16px',
                color: 'rgba(255,255,255,0.4)',
                fontSize: 13
              }}>
                📊 暂无组合数据
                <br />
                <span style={{ fontSize: 12, opacity: 0.7 }}>
                  点击下方「立即决策」生成AI推荐组合
                </span>
              </div>
            )}
          </div>
        </section>

        {/* 右:AI 建议 */}
        <section className="po-panel">
          <h4 className="po-subtitle">🤖 AI 建议</h4>
          <p className="po-paragraph">
            {hasData
              ? "基于最新评分与风控,建议维持当前配置,并关注高波动标的的仓位变化。"
              : "使用AI智能分析市场数据,为您生成风险可控、收益优化的投资组合。"}
          </p>

          {/* 🔧 优化:根据是否有数据显示不同按钮 */}
          <div className="po-actions">
            <button
              className="dashboard-btn dashboard-btn-primary"
              onClick={onDecide}
              style={{ flex: 1 }}
            >
              {hasData ? '🔄 重新决策' : '✨ 立即决策'}
            </button>

            {/* 🔧 合并:只在有数据时显示"查看组合"作为辅助按钮 */}
            {hasData && (
              <button
                className="dashboard-btn dashboard-btn-secondary"
                onClick={() => (window.location.hash = viewDetailLink)}
                style={{ flex: 1, marginLeft: 8 }}
              >
                📊 查看组合
              </button>
            )}
          </div>

          {/* 🔧 新增:版本信息 */}
          {hasData && snapshot.version_tag && (
            <div style={{
              marginTop: 12,
              fontSize: 11,
              color: 'rgba(255,255,255,0.4)',
              textAlign: 'center'
            }}>
              版本: {snapshot.version_tag}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
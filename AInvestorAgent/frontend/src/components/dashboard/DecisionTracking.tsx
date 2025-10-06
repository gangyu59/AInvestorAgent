import { useState } from 'react';

interface DecisionTrackingProps {
  latestDecision: {
    date: string;
    holdings_count: number;
    version_tag: string;
    performance?: {
      today_change: number;
      total_return: number;
      days_since: number;
    };
  } | null;
  onViewHistory: () => void;
}

export function DecisionTracking({ latestDecision, onViewHistory }: DecisionTrackingProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  if (!latestDecision) {
    return (
      <div className="dashboard-card">
        <div className="dashboard-card-header">
          <h3 className="dashboard-card-title">📊 组合表现</h3>
        </div>
        <div className="dashboard-card-body">
          <div className="decision-empty">
            <p className="decision-empty-text">暂无活跃组合</p>
            <p className="decision-empty-hint">点击顶部"AI决策"按钮生成投资组合</p>
          </div>
        </div>
      </div>
    );
  }

  const perf = latestDecision.performance;
  const todayChangeClass = perf && perf.today_change > 0 ? 'up' :
                           perf && perf.today_change < 0 ? 'down' : 'neutral';
  const totalReturnClass = perf && perf.total_return > 0 ? 'up' :
                           perf && perf.total_return < 0 ? 'down' : 'neutral';

  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">📊 组合表现</h3>
        <button
          className="decision-history-btn"
          onClick={onViewHistory}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          历史 →
        </button>
        {showTooltip && (
          <div className="decision-tooltip">查看历史决策记录</div>
        )}
      </div>

      <div className="dashboard-card-body">
        <div className="decision-current">
          <div className="decision-meta">
            <span className="decision-meta-item">
              <span className="decision-meta-label">决策时间</span>
              <span className="decision-meta-value">{latestDecision.date}</span>
            </span>
            <span className="decision-meta-item">
              <span className="decision-meta-label">持仓</span>
              <span className="decision-meta-value">{latestDecision.holdings_count} 支</span>
            </span>
            <span className="decision-meta-item">
              <span className="decision-meta-label">版本</span>
              <span className="decision-meta-value">{latestDecision.version_tag}</span>
            </span>
          </div>

          {perf && (
            <div className="decision-performance">
              <div className="decision-perf-grid">
                <div className="decision-perf-item">
                  <span className="decision-perf-label">今日涨跌</span>
                  <span className={`decision-perf-value ${todayChangeClass}`}>
                    {perf.today_change > 0 ? '+' : ''}
                    {perf.today_change.toFixed(2)}%
                  </span>
                </div>
                <div className="decision-perf-item">
                  <span className="decision-perf-label">累计收益</span>
                  <span className={`decision-perf-value ${totalReturnClass}`}>
                    {perf.total_return > 0 ? '+' : ''}
                    {perf.total_return.toFixed(2)}%
                  </span>
                </div>
                <div className="decision-perf-item">
                  <span className="decision-perf-label">持有天数</span>
                  <span className="decision-perf-value neutral">
                    {perf.days_since} 天
                  </span>
                </div>
              </div>
            </div>
          )}

          {perf && perf.days_since > 7 && (
            <div className="decision-suggestion">
              💡 距上次决策已 {perf.days_since} 天，建议重新评估市场变化
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
import { useState, useEffect } from 'react';

interface LatestDecision {
  date: string;
  holdings_count: number;
  version_tag: string;
  performance?: {
    today_change: number;
    total_return: number;
    days_since: number;
  };
}

interface DecisionTrackingProps {
  onViewHistory: () => void;
}

export function DecisionTracking({ onViewHistory }: DecisionTrackingProps) {
  const [latestDecision, setLatestDecision] = useState<LatestDecision | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    loadLatestDecision();
  }, []);

  const loadLatestDecision = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/portfolio/snapshots/latest');
      if (response.ok) {
        const data = await response.json();

        // 计算持有天数
        const snapshotDate = new Date(data.as_of);
        const today = new Date();
        const daysSince = Math.floor((today.getTime() - snapshotDate.getTime()) / (1000 * 60 * 60 * 24));

        setLatestDecision({
          date: data.as_of,
          holdings_count: data.holdings?.length || 0,
          version_tag: data.version_tag || 'v1.0',
          performance: {
            today_change: 0, // 需要额外计算，暂用占位
            total_return: (data.metrics?.ann_return || 0) * 100,
            days_since: daysSince
          }
        });
      }
    } catch (error) {
      console.error('Failed to load latest decision:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-card">
        <div className="dashboard-card-header">
          <h3 className="dashboard-card-title">📊 组合表现</h3>
        </div>
        <div className="dashboard-card-body">
          <div className="decision-empty">加载中...</div>
        </div>
      </div>
    );
  }

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
                  <span className="decision-perf-label">年化收益</span>
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
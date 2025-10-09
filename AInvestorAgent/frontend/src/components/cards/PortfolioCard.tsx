import { useMemo } from 'react';

// 格式化函数
const fmt = (x: any, d = 2) =>
  (typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--");

const pct = (x: any, d = 1) =>
  (x == null || !Number.isFinite(+x) ? "--" : `${(+x * 100).toFixed(d)}%`);

interface Holding {
  symbol: string;
  weight: number;
  score?: number;
}

interface Metrics {
  ann_return?: number;
  mdd?: number;
  sharpe?: number;
  winrate?: number;
}

interface Snapshot {
  portfolio_id?: string;
  snapshot_id?: string;
  created_at?: string;
  version_tag?: string;
  holdings?: Holding[];
  metrics?: Metrics;
}

interface PortfolioCardProps {
  snapshot?: Snapshot | null;  // 允许 null
  loading?: boolean;
  onViewDetail?: () => void;
  onRefresh?: () => void;
}

export function PortfolioCard({
  snapshot,
  loading = false,
  onViewDetail,
  onRefresh
}: PortfolioCardProps) {
  // 提取 Top5 持仓
  const top5Holdings = useMemo(() => {
    if (!snapshot?.holdings) return [];
    return [...snapshot.holdings]
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 5);
  }, [snapshot?.holdings]);

  // 计算组合总价值（权重总和应该接近1）
  const totalValue = useMemo(() => {
    if (!snapshot?.holdings) return 0;
    return snapshot.holdings.reduce((sum: number, h: Holding) => sum + h.weight, 0);
  }, [snapshot?.holdings]);

  if (loading) {
    return (
      <div className="dashboard-card">
        <div className="dashboard-card-header">
          <h3 className="dashboard-card-title">💼 投资组合概览</h3>
        </div>
        <div className="dashboard-card-body flex items-center justify-center py-8">
          <div className="text-gray-400">加载中...</div>
        </div>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="dashboard-card">
        <div className="dashboard-card-header">
          <h3 className="dashboard-card-title">💼 投资组合概览</h3>
        </div>
        <div className="dashboard-card-body">
          <div className="text-center py-8 text-gray-400">
            <p className="mb-4">暂无组合数据</p>
            <button
              className="dashboard-btn dashboard-btn-primary"
              onClick={() => window.location.hash = '#/portfolio'}
            >
              创建组合
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-card portfolio-card">
      {/* 卡片头部 */}
      <div className="dashboard-card-header">
        <div className="flex items-center gap-2">
          <h3 className="dashboard-card-title">💼 投资组合概览</h3>
          {snapshot.version_tag && (
            <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
              {snapshot.version_tag}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {onRefresh && (
            <button
              className="dashboard-btn dashboard-btn-secondary text-sm"
              onClick={onRefresh}
              title="刷新数据"
            >
              🔄
            </button>
          )}
          <button
            className="dashboard-btn dashboard-btn-secondary"
            onClick={onViewDetail || (() => window.location.hash = '#/portfolio')}
          >
            查看详情 →
          </button>
        </div>
      </div>

      {/* 卡片主体：两列布局 */}
      <div className="dashboard-card-body grid grid-cols-2 gap-6">
        {/* 左列：关键指标 */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">📊 关键指标</h4>

          <div className="space-y-3">
            <MetricRow
              label="年化收益"
              value={pct(snapshot.metrics?.ann_return, 2)}
              trend={snapshot.metrics?.ann_return}
              icon="📈"
            />
            <MetricRow
              label="最大回撤"
              value={pct(snapshot.metrics?.mdd, 1)}
              trend={snapshot.metrics?.mdd}
              icon="📉"
              invertTrend
            />
            <MetricRow
              label="夏普比率"
              value={fmt(snapshot.metrics?.sharpe, 2)}
              trend={snapshot.metrics?.sharpe}
              icon="⚖️"
            />
            <MetricRow
              label="胜率"
              value={pct(snapshot.metrics?.winrate, 1)}
              trend={snapshot.metrics?.winrate}
              icon="🎯"
            />
          </div>

          {/* 组合统计 */}
          <div className="pt-3 border-t border-gray-700/50 text-xs text-gray-400">
            <div className="flex justify-between mb-1">
              <span>持仓数量</span>
              <span className="font-mono">{snapshot.holdings?.length || 0} 只</span>
            </div>
            {snapshot.created_at && (
              <div className="flex justify-between">
                <span>更新时间</span>
                <span className="font-mono">
                  {new Date(snapshot.created_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* 右列：Top5 持仓 */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">⭐ Top5 持仓</h4>

          {top5Holdings.length > 0 ? (
            <div className="space-y-2.5">
              {top5Holdings.map((holding, idx) => (
                <div key={holding.symbol} className="holdings-row">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-gray-400">#{idx + 1}</span>
                    <span
                      className="font-semibold text-blue-400 cursor-pointer hover:text-blue-300 transition-colors"
                      onClick={() => window.location.hash = `#/stock?query=${holding.symbol}`}
                    >
                      {holding.symbol}
                    </span>
                    {holding.score && (
                      <span className="text-xs text-gray-500">
                        分数: {holding.score.toFixed(1)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                        style={{ width: `${Math.min(100, holding.weight * 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono min-w-[3rem] text-right">
                      {pct(holding.weight, 1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4 text-gray-500 text-sm">
              暂无持仓数据
            </div>
          )}

          {/* 快速操作 */}
          <div className="pt-3 border-t border-gray-700/50 flex gap-2">
            <button
              className="flex-1 dashboard-btn dashboard-btn-primary text-sm py-2"
              onClick={() => window.location.hash = '#/simulator'}
            >
              📊 回测
            </button>
            <button
              className="flex-1 dashboard-btn dashboard-btn-secondary text-sm py-2"
              onClick={() => {
                // 触发导出功能（后续实现）
                console.log('Export portfolio:', snapshot);
                alert('导出功能开发中...');
              }}
            >
              📥 导出
            </button>
          </div>
        </div>
      </div>

      {/* 卡片底部：AI 建议摘要 */}
      <div className="dashboard-card-footer bg-gradient-to-r from-blue-900/20 to-purple-900/20 p-4 rounded-b-lg">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🤖</span>
          <div className="flex-1">
            <p className="text-sm text-gray-300 leading-relaxed">
              基于最新市场数据与因子评分，当前组合配置合理。
              建议关注高波动标的，必要时调整权重以控制风险。
            </p>
            <button
              className="mt-2 text-xs text-blue-400 hover:text-blue-300 underline"
              onClick={onViewDetail || (() => window.location.hash = '#/portfolio')}
            >
              查看完整分析 →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// 辅助组件：指标行
interface MetricRowProps {
  label: string;
  value: string;
  trend?: number;
  icon?: string;
  invertTrend?: boolean;
}

function MetricRow({ label, value, trend, icon, invertTrend = false }: MetricRowProps) {
  const getTrendColor = () => {
    if (trend == null) return 'text-gray-400';
    const isPositive = invertTrend ? trend < 0 : trend > 0;
    return isPositive ? 'text-green-400' : 'text-red-400';
  };

  const getTrendIcon = () => {
    if (trend == null) return '';
    const isPositive = invertTrend ? trend < 0 : trend > 0;
    return isPositive ? '↑' : '↓';
  };

  return (
    <div className="flex items-center justify-between py-2 px-3 rounded bg-gray-800/50 hover:bg-gray-800/70 transition-colors">
      <div className="flex items-center gap-2">
        {icon && <span className="text-base">{icon}</span>}
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-sm font-mono font-semibold ${getTrendColor()}`}>
          {value}
        </span>
        {trend != null && (
          <span className={`text-xs ${getTrendColor()}`}>
            {getTrendIcon()}
          </span>
        )}
      </div>
    </div>
  );
}
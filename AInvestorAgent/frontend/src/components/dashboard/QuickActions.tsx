type Props = {
  onUpdate: () => void;
};

export function QuickActions({ onUpdate }: Props) {
  return (
    <div className="dashboard-card quick-actions">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">快速操作</h3>
      </div>
      <div className="dashboard-card-body">
        <button onClick={onUpdate} className="dashboard-btn dashboard-btn-primary w-full">
          🔄 一键更新所有数据
        </button>

        <p className="text-sm text-gray-400 mt-3">
          自动执行：价格（近一周）→ 基本面（可选）→ 新闻情绪（近7天）→ 因子 → 评分
        </p>

        <div className="pt-3 border-t border-gray-700 mt-3">
          <p className="text-xs text-gray-500 mb-2">
            💡 提示：AI只从 Watchlist 中选择股票进行组合
          </p>
          <button
            onClick={() => (window.location.hash = "#/manage")}
            className="dashboard-btn dashboard-btn-secondary"
            style={{ height: 34, padding: "0 10px" }}
          >
            前往管理页面 →
          </button>
        </div>
      </div>
    </div>
  );
}

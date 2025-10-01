export function QuickActions({ onUpdate }: { onUpdate: () => void }) {
  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header"><h3 className="dashboard-card-title">快速操作</h3></div>
      <div className="dashboard-card-body">
        <button onClick={onUpdate} className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all shadow-lg">🔄 一键更新所有数据</button>
        <p className="text-sm text-gray-400 mt-4">自动执行：价格（近一周）→ 基本面（可选）→ 新闻情绪（近7天）→ 因子 → 评分</p>
        <div className="pt-4 border-t border-gray-700 mt-4">
          <p className="text-xs text-gray-500 mb-2">💡 提示：AI只从Watchlist中选择股票进行组合</p>
          <button onClick={() => window.location.hash = '#/manage'} className="text-sm text-blue-400 hover:underline">前往管理页面 →</button>
        </div>
      </div>
    </div>
  );
}
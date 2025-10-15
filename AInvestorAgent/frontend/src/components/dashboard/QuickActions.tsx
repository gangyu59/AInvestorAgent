// frontend/src/components/dashboard/QuickActions.tsx
import { useState } from "react";
import { API_BASE } from "../../services/endpoints";

interface UpdateResult {
  symbol: string;
  success: boolean;
  prices_added: number;
  news_added: number;
  error?: string;
  mode: string;
  before_count: number;
  after_count: number;
}

interface UpdateResponse {
  total: number;
  success: number;
  failed: number;
  results: UpdateResult[];
  duration_seconds: number;
}

interface DataCoverageItem {
  symbol: string;
  count: number;
  first_date: string | null;
  last_date: string | null;
  needs_full: boolean;
  reason: string;
  status: string;
}

export function QuickActions({
  onUpdate,
  watchlist
}: {
  onUpdate: () => void;
  watchlist?: string[];
}) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateProgress, setUpdateProgress] = useState<{
    current: number;
    total: number;
    currentSymbol: string;
    results: UpdateResult[];
  } | null>(null);
  const [coverageData, setCoverageData] = useState<DataCoverageItem[]>([]);

  // 🔍 检查数据覆盖情况
  const checkCoverage = async () => {
    if (!watchlist || watchlist.length === 0) {
      alert("关注列表为空,请先添加股票");
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/api/batch/coverage?symbols=${watchlist.join(',')}`
      );

      if (!response.ok) throw new Error('检查失败');

      const data = await response.json();
      setCoverageData(data.symbols);
      setShowUpdateModal(true);
    } catch (error: any) {
      console.error("检查数据覆盖失败:", error);
      alert(`检查失败: ${error.message}`);
    }
  };

  // 🔄 执行批量更新
  const executeUpdate = async (forceFull: boolean = false) => {
    if (!watchlist || watchlist.length === 0) {
      alert("关注列表为空");
      return;
    }

    setIsUpdating(true);
    setUpdateProgress({
      current: 0,
      total: watchlist.length,
      currentSymbol: watchlist[0],
      results: []
    });

    try {
      console.log("🚀 开始批量更新:", watchlist);

      const response = await fetch(`${API_BASE}/api/batch/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: watchlist,
          force_full: forceFull,
          update_prices: true,
          update_news: false, // TODO: 后续支持新闻更新
          update_fundamentals: false
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result: UpdateResponse = await response.json();

      console.log("✅ 更新完成:", result);

      // 显示结果
      setUpdateProgress(prev => prev ? {
        ...prev,
        current: result.total,
        results: result.results
      } : null);

      // 3秒后关闭
      setTimeout(() => {
        setShowUpdateModal(false);
        setUpdateProgress(null);
        onUpdate(); // 触发父组件刷新
      }, 3000);

    } catch (error: any) {
      console.error("❌ 更新失败:", error);
      alert(`更新失败: ${error.message}`);
    } finally {
      setIsUpdating(false);
    }
  };

  // 快速回测
  const handleQuickBacktest = async () => {
    try {
      console.log("🎯 快速回测:获取最新组合快照");

      const response = await fetch(`${API_BASE}/api/portfolio/snapshots/latest`);

      if (!response.ok) {
        if (response.status === 404) {
          alert("暂无组合快照,请先在组合页面创建一个投资组合。");
          window.location.hash = "#/portfolio";
          return;
        }
        throw new Error(`获取快照失败: HTTP ${response.status}`);
      }

      const snapshot = await response.json();
      console.log("✅ 获取到最新快照:", snapshot);

      if (!snapshot.holdings || snapshot.holdings.length === 0) {
        alert("当前快照无持仓数据,请重新生成组合。");
        window.location.hash = "#/portfolio";
        return;
      }

      const backtestData = {
        holdings: snapshot.holdings.map((h: any) => ({
          symbol: h.symbol,
          weight: h.weight
        })),
        snapshot_id: snapshot.snapshot_id,
        as_of: snapshot.as_of,
        from: 'quickaction'
      };

      sessionStorage.setItem('backtestHoldings', JSON.stringify(backtestData));
      console.log("💾 数据已保存到 sessionStorage");

      window.location.hash = `#/simulator?sid=${encodeURIComponent(snapshot.snapshot_id)}`;

    } catch (error: any) {
      console.error("❌ 快速回测失败:", error);
      alert(`启动回测失败: ${error.message}\n\n请检查后端服务是否正常运行。`);
    }
  };

  return (
    <>
      <div className="dashboard-card quick-actions-card">
        <div className="dashboard-card-header">
          <h3 className="dashboard-card-title">⚡ 快速操作</h3>
        </div>

        <div className="dashboard-card-body">
          <div className="action-grid">
            {/* 管理关注列表 */}
            <button
              onClick={() => (window.location.hash = "#/manage")}
              className="action-btn action-btn-primary"
            >
              <div className="action-icon">📌</div>
              <div className="action-content">
                <div className="action-title">管理关注列表</div>
                <div className="action-desc">添加/删除股票</div>
              </div>
            </button>

            {/* 批量评分 */}
            <button
              onClick={() => (window.location.hash = "#/manage?tab=scoring")}
              className="action-btn action-btn-info"
            >
              <div className="action-icon">📊</div>
              <div className="action-content">
                <div className="action-title">批量评分</div>
                <div className="action-desc">分析关注股票</div>
              </div>
            </button>

            {/* 🔄 智能更新数据 */}
            <button
              onClick={checkCoverage}
              className="action-btn action-btn-success"
              disabled={isUpdating}
            >
              <div className="action-icon">
                {isUpdating ? '⏳' : '🔄'}
              </div>
              <div className="action-content">
                <div className="action-title">
                  {isUpdating ? '更新中...' : '智能更新'}
                </div>
                <div className="action-desc">
                  {isUpdating ? '请稍候' : '自动补充历史'}
                </div>
              </div>
            </button>

            {/* 查看所有股票 */}
            <button
              onClick={() => (window.location.hash = "#/stock")}
              className="action-btn action-btn-secondary"
            >
              <div className="action-icon">🔍</div>
              <div className="action-content">
                <div className="action-title">个股分析</div>
                <div className="action-desc">详细研究报告</div>
              </div>
            </button>

            {/* 组合管理 */}
            <button
              onClick={() => (window.location.hash = "#/portfolio")}
              className="action-btn action-btn-warning"
            >
              <div className="action-icon">💼</div>
              <div className="action-content">
                <div className="action-title">组合管理</div>
                <div className="action-desc">查看/调整持仓</div>
              </div>
            </button>

            {/* 回测模拟 */}
            <button
              onClick={handleQuickBacktest}
              className="action-btn action-btn-purple"
            >
              <div className="action-icon">📈</div>
              <div className="action-content">
                <div className="action-title">回测模拟</div>
                <div className="action-desc">验证当前组合</div>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* 🎯 数据更新模态框 */}
      {showUpdateModal && (
        <div className="update-modal-overlay" onClick={() => !isUpdating && setShowUpdateModal(false)}>
          <div className="update-modal" onClick={e => e.stopPropagation()}>
            <div className="update-modal-header">
              <h3>📊 数据更新中心</h3>
              {!isUpdating && (
                <button
                  onClick={() => setShowUpdateModal(false)}
                  className="close-btn"
                >×</button>
              )}
            </div>

            {/* 数据覆盖情况 */}
            {!isUpdating && coverageData.length > 0 && (
              <div className="coverage-section">
                <h4>当前数据状态</h4>
                <div className="coverage-table">
                  <div className="coverage-header">
                    <span>股票</span>
                    <span>数据点</span>
                    <span>状态</span>
                    <span>建议</span>
                  </div>
                  {coverageData.map(item => (
                    <div key={item.symbol} className="coverage-row">
                      <span className="symbol-col">{item.symbol}</span>
                      <span className="count-col">{item.count}</span>
                      <span className={`status-col status-${item.status}`}>
                        {item.status === 'sufficient' ? '✅ 充足' :
                         item.status === 'insufficient' ? '⚠️ 不足' :
                         '❌ 无数据'}
                      </span>
                      <span className="reason-col">{item.reason}</span>
                    </div>
                  ))}
                </div>

                <div className="update-buttons">
                  <button
                    onClick={() => executeUpdate(false)}
                    className="update-btn update-btn-normal"
                  >
                    🔄 增量更新
                    <span className="btn-desc">只获取最新数据(快)</span>
                  </button>
                  <button
                    onClick={() => executeUpdate(true)}
                    className="update-btn update-btn-full"
                  >
                    📥 完整更新
                    <span className="btn-desc">补充全部历史(慢)</span>
                  </button>
                </div>
              </div>
            )}

            {/* 更新进度 */}
            {isUpdating && updateProgress && (
              <div className="progress-section">
                <div className="progress-bar-container">
                  <div
                    className="progress-bar"
                    style={{
                      width: `${(updateProgress.current / updateProgress.total) * 100}%`
                    }}
                  />
                </div>
                <p className="progress-text">
                  正在更新: {updateProgress.currentSymbol}
                  ({updateProgress.current}/{updateProgress.total})
                </p>
              </div>
            )}

            {/* 更新结果 */}
            {updateProgress && updateProgress.results.length > 0 && (
              <div className="results-section">
                <h4>更新结果</h4>
                <div className="results-table">
                  {updateProgress.results.map(result => (
                    <div
                      key={result.symbol}
                      className={`result-row ${result.success ? 'success' : 'failed'}`}
                    >
                      <span className="result-symbol">{result.symbol}</span>
                      <span className="result-mode">{result.mode}</span>
                      <span className="result-count">
                        {result.before_count} → {result.after_count}
                        {result.prices_added > 0 && ` (+${result.prices_added})`}
                      </span>
                      <span className="result-status">
                        {result.success ? '✅' : '❌'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <style>{`
        .quick-actions-card {
          height: 100%;
        }

        .action-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }

        .action-btn {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s;
          text-align: left;
        }

        .action-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .action-btn:not(:disabled):hover {
          transform: translateY(-2px);
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(255, 255, 255, 0.2);
        }

        .action-icon {
          font-size: 28px;
          flex-shrink: 0;
        }

        .action-content {
          flex: 1;
          min-width: 0;
        }

        .action-title {
          font-size: 14px;
          font-weight: 600;
          color: white;
          margin-bottom: 4px;
        }

        .action-desc {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
        }

        .action-btn-success:not(:disabled):hover {
          border-color: rgba(34, 197, 94, 0.5);
          box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
        }

        /* 模态框样式 */
        .update-modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
        }

        .update-modal {
          background: #1e1e2e;
          border-radius: 16px;
          width: 90%;
          max-width: 800px;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .update-modal-header {
          padding: 24px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .update-modal-header h3 {
          margin: 0;
          color: white;
          font-size: 20px;
        }

        .close-btn {
          background: none;
          border: none;
          color: white;
          font-size: 32px;
          cursor: pointer;
          padding: 0;
          width: 32px;
          height: 32px;
          line-height: 32px;
          text-align: center;
          opacity: 0.6;
          transition: opacity 0.2s;
        }

        .close-btn:hover {
          opacity: 1;
        }

        .coverage-section,
        .progress-section,
        .results-section {
          padding: 24px;
        }

        .coverage-section h4,
        .results-section h4 {
          margin: 0 0 16px 0;
          color: white;
          font-size: 16px;
        }

        .coverage-table,
        .results-table {
          background: rgba(255, 255, 255, 0.03);
          border-radius: 8px;
          overflow: hidden;
        }

        .coverage-header {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr 2fr;
          gap: 12px;
          padding: 12px 16px;
          background: rgba(255, 255, 255, 0.05);
          font-size: 12px;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.7);
          text-transform: uppercase;
        }

        .coverage-row {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr 2fr;
          gap: 12px;
          padding: 12px 16px;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          font-size: 14px;
          color: white;
        }

        .status-sufficient {
          color: #22c55e;
        }

        .status-insufficient {
          color: #f59e0b;
        }

        .status-empty {
          color: #ef4444;
        }

        .update-buttons {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-top: 24px;
        }

        .update-btn {
          padding: 16px 20px;
          border-radius: 10px;
          border: 2px solid;
          background: rgba(255, 255, 255, 0.05);
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }

        .btn-desc {
          font-size: 12px;
          font-weight: normal;
          opacity: 0.7;
        }

        .update-btn-normal {
          border-color: #3b82f6;
        }

        .update-btn-normal:hover {
          background: rgba(59, 130, 246, 0.1);
          box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
        }

        .update-btn-full {
          border-color: #8b5cf6;
        }

        .update-btn-full:hover {
          background: rgba(139, 92, 246, 0.1);
          box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
        }

        .progress-bar-container {
          height: 8px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 12px;
        }

        .progress-bar {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          transition: width 0.3s ease;
        }

        .progress-text {
          text-align: center;
          color: rgba(255, 255, 255, 0.8);
          font-size: 14px;
          margin: 0;
        }

        .result-row {
          display: grid;
          grid-template-columns: 100px 80px 1fr 40px;
          gap: 12px;
          padding: 12px 16px;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          font-size: 13px;
          align-items: center;
        }

        .result-row.success {
          background: rgba(34, 197, 94, 0.05);
        }

        .result-row.failed {
          background: rgba(239, 68, 68, 0.05);
        }

        .result-symbol {
          font-weight: 600;
          color: white;
        }

        .result-mode {
          font-size: 11px;
          padding: 4px 8px;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.1);
          text-align: center;
        }

        .result-count {
          color: rgba(255, 255, 255, 0.7);
          font-family: 'Courier New', monospace;
        }

        .result-status {
          text-align: center;
          font-size: 16px;
        }

        @media (max-width: 1200px) {
          .action-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 768px) {
          .update-modal {
            width: 95%;
          }

          .coverage-header,
          .coverage-row {
            grid-template-columns: 1fr 1fr;
            gap: 8px;
          }

          .coverage-header span:nth-child(3),
          .coverage-header span:nth-child(4),
          .coverage-row span:nth-child(3),
          .coverage-row span:nth-child(4) {
            grid-column: 1 / -1;
          }

          .update-buttons {
            grid-template-columns: 1fr;
          }

          .result-row {
            grid-template-columns: 1fr 1fr;
            gap: 8px;
          }

          .result-count {
            grid-column: 1 / -1;
          }
        }
      `}</style>
    </>
  );
}
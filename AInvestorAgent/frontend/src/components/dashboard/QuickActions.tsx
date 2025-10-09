// frontend/src/components/dashboard/QuickActions.tsx
export function QuickActions({ onUpdate }: { onUpdate: () => void }) {
  return (
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

          {/* 一键更新数据 */}
          <button onClick={onUpdate} className="action-btn action-btn-success">
            <div className="action-icon">🔄</div>
            <div className="action-content">
              <div className="action-title">更新数据</div>
              <div className="action-desc">价格/新闻/因子</div>
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
            onClick={() => (window.location.hash = "#/simulator")}
            className="action-btn action-btn-purple"
          >
            <div className="action-icon">📈</div>
            <div className="action-content">
              <div className="action-title">回测模拟</div>
              <div className="action-desc">策略验证</div>
            </div>
          </button>
        </div>
      </div>

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

        .action-btn:hover {
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

        /* 不同颜色主题 */
        .action-btn-primary:hover {
          border-color: rgba(59, 130, 246, 0.5);
          box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
        }

        .action-btn-info:hover {
          border-color: rgba(14, 165, 233, 0.5);
          box-shadow: 0 0 20px rgba(14, 165, 233, 0.2);
        }

        .action-btn-success:hover {
          border-color: rgba(34, 197, 94, 0.5);
          box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
        }

        .action-btn-secondary:hover {
          border-color: rgba(148, 163, 184, 0.5);
          box-shadow: 0 0 20px rgba(148, 163, 184, 0.2);
        }

        .action-btn-warning:hover {
          border-color: rgba(245, 158, 11, 0.5);
          box-shadow: 0 0 20px rgba(245, 158, 11, 0.2);
        }

        .action-btn-purple:hover {
          border-color: rgba(168, 85, 247, 0.5);
          box-shadow: 0 0 20px rgba(168, 85, 247, 0.2);
        }

        @media (max-width: 1200px) {
          .action-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 768px) {
          .action-grid {
            grid-template-columns: 1fr;
          }

          .action-btn {
            padding: 14px;
          }

          .action-icon {
            font-size: 24px;
          }

          .action-title {
            font-size: 13px;
          }

          .action-desc {
            font-size: 11px;
          }
        }
      `}</style>
    </div>
  );
}
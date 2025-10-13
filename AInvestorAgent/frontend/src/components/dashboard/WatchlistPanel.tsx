// frontend/src/components/dashboard/WatchlistPanel.tsx
import { useState, useEffect } from "react";
import { API_BASE } from "../../services/endpoints";  // 修复1: 添加API_BASE导入

interface WatchlistPanelProps {
  list: string[];
  onRemove?: (symbol: string) => void;
  onRefresh?: () => void;  // 修复2: 添加onRefresh定义
}

export function WatchlistPanel({ list, onRemove, onRefresh }: WatchlistPanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredList, setFilteredList] = useState(list);

  useEffect(() => {
    if (searchQuery) {
      setFilteredList(
        list.filter((symbol) =>
          symbol.toLowerCase().includes(searchQuery.toLowerCase())
        )
      );
    } else {
      setFilteredList(list);
    }
  }, [searchQuery, list]);

  // 修复3: 添加handleRemove函数
  const handleRemove = async (symbol: string) => {
    if (!confirm(`确定要从关注列表移除 ${symbol} 吗?`)) {
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/api/watchlist/remove/${symbol}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        throw new Error(`删除失败: ${response.status}`);
      }

      const result = await response.json();
      console.log("✅ 移除成功:", result);

      // 触发刷新回调
      if (onRefresh) {
        onRefresh();
      }
    } catch (e: any) {
      console.error("❌ 删除失败:", e);
      alert(`删除失败: ${e.message}`);
    }
  };

  return (
    <div className="dashboard-card watchlist-card-pro">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">
          📌 关注列表 ({list.length})
        </h3>
        <button
          onClick={() => (window.location.hash = "#/manage")}
          className="btn-manage-pro"
          title="管理"
        >
          管理
        </button>
      </div>

      <div className="dashboard-card-body">
        {list.length === 0 ? (
          <div className="empty-state-pro">
            <div style={{ fontSize: 36, opacity: 0.3, marginBottom: 8 }}>📋</div>
            <p style={{ margin: "0 0 12px 0", fontSize: 13, color: "rgba(255,255,255,0.5)" }}>
              还没有关注股票
            </p>
            <button
              onClick={() => (window.location.hash = "#/manage")}
              className="btn-add-stock"
            >
              添加股票
            </button>
          </div>
        ) : (
          <>
            {/* 搜索框 - 仅在 >8 支时显示 */}
            {list.length > 8 && (
              <div className="search-box-mini">
                <input
                  type="text"
                  placeholder="搜索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="search-input-mini"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="search-clear-mini"
                  >
                    ×
                  </button>
                )}
              </div>
            )}

            {/* 紧凑列表 */}
            <div className="watchlist-scroll-pro">
              {filteredList.length === 0 ? (
                <div style={{ textAlign: "center", padding: 20, color: "rgba(255,255,255,0.4)", fontSize: 13 }}>
                  未找到匹配股票
                </div>
              ) : (
                <table className="watchlist-table-pro">
                  <tbody>
                    {filteredList.map((symbol) => (
                      <tr key={symbol}>
                        <td className="symbol-cell">{symbol}</td>
                        <td className="actions-cell">
                          <button
                            onClick={() =>
                              (window.location.hash = `#/stock?query=${symbol}`)
                            }
                            className="btn-mini btn-view-mini"
                            title="查看"
                          >
                            查看
                          </button>
                          <button
                            onClick={() => handleRemove(symbol)}
                            className="btn-mini btn-remove-mini"
                            title="移除"
                          >
                            ×
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* 底部管理按钮 */}
            <div className="watchlist-footer-pro">
              <button
                onClick={() => (window.location.hash = "#/manage")}
                className="btn-manage-full"
              >
                管理全部 ({list.length}支)
              </button>
            </div>
          </>
        )}
      </div>

      <style>{`
        .watchlist-card-pro {
          display: flex;
          flex-direction: column;
          height: 100%;
          max-height: 600px;
        }

        .dashboard-card-body {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .btn-manage-pro {
          padding: 6px 14px;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.15);
          color: white;
          border-radius: 5px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          transition: all 0.2s;
        }

        .btn-manage-pro:hover {
          background: rgba(255, 255, 255, 0.12);
        }

        .empty-state-pro {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 20px;
          text-align: center;
        }

        .btn-add-stock {
          padding: 8px 20px;
          background: #3b82f6;
          border: none;
          color: white;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
          transition: all 0.2s;
        }

        .btn-add-stock:hover {
          background: #2563eb;
        }

        .search-box-mini {
          position: relative;
          margin-bottom: 10px;
        }

        .search-input-mini {
          width: 100%;
          padding: 7px 28px 7px 10px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 5px;
          color: white;
          font-size: 13px;
        }

        .search-input-mini:focus {
          outline: none;
          border-color: #3b82f6;
          background: rgba(255, 255, 255, 0.08);
        }

        .search-clear-mini {
          position: absolute;
          right: 6px;
          top: 50%;
          transform: translateY(-50%);
          background: rgba(255, 255, 255, 0.1);
          border: none;
          color: white;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          cursor: pointer;
          font-size: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .search-clear-mini:hover {
          background: rgba(255, 255, 255, 0.2);
        }

        .watchlist-scroll-pro {
          flex: 1;
          overflow-y: auto;
          margin: 0 -16px;
          padding: 0 16px;
        }

        .watchlist-scroll-pro::-webkit-scrollbar {
          width: 5px;
        }

        .watchlist-scroll-pro::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.03);
          border-radius: 3px;
        }

        .watchlist-scroll-pro::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 3px;
        }

        .watchlist-table-pro {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }

        .watchlist-table-pro tr {
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .watchlist-table-pro tr:last-child {
          border-bottom: none;
        }

        .watchlist-table-pro tr:hover {
          background: rgba(255, 255, 255, 0.03);
        }

        .symbol-cell {
          padding: 10px 8px;
          font-family: 'Roboto Mono', monospace;
          font-weight: 600;
          color: #60a5fa;
          font-size: 14px;
        }

        .actions-cell {
          padding: 10px 8px;
          text-align: right;
          white-space: nowrap;
        }

        .btn-mini {
          padding: 4px 10px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 11px;
          font-weight: 500;
          transition: all 0.15s;
          margin-left: 4px;
        }

        .btn-view-mini {
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
        }

        .btn-view-mini:hover {
          background: rgba(59, 130, 246, 0.25);
        }

        .btn-remove-mini {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
          font-size: 16px;
          padding: 4px 8px;
          font-weight: 600;
        }

        .btn-remove-mini:hover {
          background: rgba(239, 68, 68, 0.25);
        }

        .watchlist-footer-pro {
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .btn-manage-full {
          width: 100%;
          padding: 9px;
          background: rgba(59, 130, 246, 0.12);
          border: 1px solid rgba(59, 130, 246, 0.25);
          color: #60a5fa;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
          transition: all 0.2s;
        }

        .btn-manage-full:hover {
          background: rgba(59, 130, 246, 0.2);
        }
      `}</style>
    </div>
  );
}
import { useState, useEffect } from "react";

interface WatchlistPanelProps {
  list: string[];
  onRemove?: (symbol: string) => void;
}

export function WatchlistPanel({ list, onRemove }: WatchlistPanelProps) {
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

  return (
    <div className="dashboard-card watchlist-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">
          📌 我的关注列表
          <span className="ml-2 text-sm text-gray-400">
            ({list.length}支)
          </span>
        </h3>
        <button
          onClick={() => (window.location.hash = "#/manage")}
          className="dashboard-btn-icon"
          title="管理关注列表"
        >
          ⚙️
        </button>
      </div>

      <div className="dashboard-card-body">
        {list.length === 0 ? (
          <div className="dashboard-empty-state">
            <div className="empty-icon">📋</div>
            <p className="text-gray-400 mb-3">还没有关注任何股票</p>
            <button
              onClick={() => (window.location.hash = "#/manage")}
              className="dashboard-btn dashboard-btn-primary"
            >
              + 添加股票
            </button>
          </div>
        ) : (
          <>
            {/* 搜索框 */}
            {list.length > 10 && (
              <div className="watchlist-search">
                <input
                  type="text"
                  placeholder="搜索股票代码..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="watchlist-search-input"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="watchlist-search-clear"
                  >
                    ✕
                  </button>
                )}
              </div>
            )}

            {/* 滚动列表 */}
            <div className="watchlist-scroll-container">
              {filteredList.length === 0 ? (
                <div className="text-center text-gray-400 py-4">
                  未找到匹配的股票
                </div>
              ) : (
                <div className="watchlist-items">
                  {filteredList.map((symbol) => (
                    <div key={symbol} className="watchlist-item">
                      <div className="watchlist-item-left">
                        <span className="watchlist-symbol">{symbol}</span>
                        <span className="watchlist-badge">关注中</span>
                      </div>
                      <div className="watchlist-item-actions">
                        <button
                          onClick={() =>
                            (window.location.hash = `#/stock?query=${symbol}`)
                          }
                          className="watchlist-btn watchlist-btn-view"
                          title="查看详情"
                        >
                          查看
                        </button>
                        {onRemove && (
                          <button
                            onClick={() => onRemove(symbol)}
                            className="watchlist-btn watchlist-btn-remove"
                            title="移除"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 底部操作 */}
            <div className="watchlist-footer">
              <button
                onClick={() => (window.location.hash = "#/manage")}
                className="dashboard-btn dashboard-btn-secondary w-full"
              >
                管理关注列表 ({list.length}支)
              </button>
            </div>
          </>
        )}
      </div>

      <style>{`
        .watchlist-card {
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

        .watchlist-search {
          position: relative;
          margin-bottom: 12px;
        }

        .watchlist-search-input {
          width: 100%;
          padding: 8px 32px 8px 12px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 6px;
          color: white;
          font-size: 14px;
          transition: all 0.2s;
        }

        .watchlist-search-input:focus {
          outline: none;
          border-color: #3b82f6;
          background: rgba(255, 255, 255, 0.08);
        }

        .watchlist-search-clear {
          position: absolute;
          right: 8px;
          top: 50%;
          transform: translateY(-50%);
          background: rgba(255, 255, 255, 0.1);
          border: none;
          color: white;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .watchlist-search-clear:hover {
          background: rgba(255, 255, 255, 0.2);
        }

        .watchlist-scroll-container {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
          margin: 0 -16px;
          padding: 0 16px;
        }

        .watchlist-scroll-container::-webkit-scrollbar {
          width: 6px;
        }

        .watchlist-scroll-container::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 3px;
        }

        .watchlist-scroll-container::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 3px;
        }

        .watchlist-scroll-container::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.3);
        }

        .watchlist-items {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .watchlist-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 8px;
          transition: all 0.2s;
        }

        .watchlist-item:hover {
          background: rgba(255, 255, 255, 0.06);
          border-color: rgba(255, 255, 255, 0.15);
          transform: translateX(2px);
        }

        .watchlist-item-left {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .watchlist-symbol {
          font-family: 'Roboto Mono', monospace;
          font-size: 15px;
          font-weight: 600;
          color: #60a5fa;
          letter-spacing: 0.5px;
        }

        .watchlist-badge {
          font-size: 11px;
          padding: 2px 8px;
          background: rgba(34, 197, 94, 0.2);
          color: #22c55e;
          border-radius: 10px;
        }

        .watchlist-item-actions {
          display: flex;
          gap: 6px;
        }

        .watchlist-btn {
          padding: 6px 12px;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .watchlist-btn-view {
          background: rgba(59, 130, 246, 0.2);
          color: #60a5fa;
        }

        .watchlist-btn-view:hover {
          background: rgba(59, 130, 246, 0.3);
          transform: translateY(-1px);
        }

        .watchlist-btn-remove {
          background: rgba(239, 68, 68, 0.2);
          color: #ef4444;
          width: 28px;
          padding: 6px;
        }

        .watchlist-btn-remove:hover {
          background: rgba(239, 68, 68, 0.3);
        }

        .watchlist-footer {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .dashboard-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 20px;
          text-align: center;
        }

        .empty-icon {
          font-size: 48px;
          margin-bottom: 16px;
          opacity: 0.5;
        }

        .dashboard-btn-icon {
          background: rgba(255, 255, 255, 0.1);
          border: none;
          color: white;
          width: 32px;
          height: 32px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 16px;
          transition: all 0.2s;
        }

        .dashboard-btn-icon:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: scale(1.05);
        }
      `}</style>
    </div>
  );
}
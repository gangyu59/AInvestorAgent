import { useState } from 'react';

export function WatchlistPanel({ list }: { list: string[] }) {
  const [expanded, setExpanded] = useState(false);
  const displayCount = expanded ? list.length : Math.min(5, list.length);

  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">📌 我的关注列表 <span className="ml-2 text-sm text-gray-400">({list.length}支)</span></h3>
        <button onClick={() => window.location.hash = '#/manage'}>管理 →</button>
      </div>
      <div className="dashboard-card-body">
        {list.length === 0 ? (
          <div className="dashboard-empty-state">
            <p className="text-gray-400 mb-4">还没有关注任何股票</p>
            <button onClick={() => window.location.hash = '#/manage'} className="dashboard-btn dashboard-btn-primary">添加股票</button>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {list.slice(0, displayCount).map((symbol) => (
                <div key={symbol} className="dashboard-watchlist-item">
                  <span className="dashboard-watchlist-symbol">{symbol}</span>
                  <button onClick={() => window.location.hash = `#/stock?query=${symbol}`} className="dashboard-watchlist-detail-btn">查看</button>
                </div>
              ))}
            </div>
            {list.length > 5 && (
              <button onClick={() => setExpanded(!expanded)} className="w-full mt-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
                {expanded ? '收起 ▲' : `查看全部 ${list.length} 支 ▼`}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
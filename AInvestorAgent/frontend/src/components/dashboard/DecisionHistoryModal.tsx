import { useState, useEffect } from 'react';

interface DecisionRecord {
  id: string;
  date: string;
  holdings_count: number;
  version_tag: string;
  performance?: {
    total_return: number;
    max_dd: number;
  };
}

interface DecisionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDecision: (decisionId: string) => void;
}

export function DecisionHistoryModal({ isOpen, onClose, onSelectDecision }: DecisionHistoryModalProps) {
  const [records, setRecords] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadHistory();
    }
  }, [isOpen]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      // TODO: 替换为实际的后端API
      const response = await fetch('http://localhost:8000/api/portfolio/snapshots');
      if (response.ok) {
        const data = await response.json();
        setRecords(data.snapshots || []);
      } else {
        // Mock 数据作为fallback
        setRecords([
          {
            id: '1',
            date: '2025-10-01',
            holdings_count: 5,
            version_tag: 'v1.2',
            performance: { total_return: 8.5, max_dd: -5.2 }
          },
          {
            id: '2',
            date: '2025-09-24',
            holdings_count: 6,
            version_tag: 'v1.1',
            performance: { total_return: 6.3, max_dd: -7.8 }
          },
          {
            id: '3',
            date: '2025-09-17',
            holdings_count: 7,
            version_tag: 'v1.1',
            performance: { total_return: 12.1, max_dd: -4.5 }
          },
          {
            id: '4',
            date: '2025-09-10',
            holdings_count: 5,
            version_tag: 'v1.0',
            performance: { total_return: -2.3, max_dd: -9.1 }
          }
        ]);
      }
    } catch (error) {
      console.error('Failed to load history:', error);
      // 使用 mock 数据
      setRecords([
        {
          id: '1',
          date: '2025-10-01',
          holdings_count: 5,
          version_tag: 'v1.2',
          performance: { total_return: 8.5, max_dd: -5.2 }
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="history-modal-overlay" onClick={onClose}>
      <div className="history-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* 头部 */}
        <div className="history-modal-header">
          <h2 className="history-modal-title">📜 历史决策记录</h2>
          <button className="history-modal-close" onClick={onClose}>✕</button>
        </div>

        {/* 内容 */}
        <div className="history-modal-body">
          {loading ? (
            <div className="history-loading">加载中...</div>
          ) : records.length === 0 ? (
            <div className="history-empty">
              <p>暂无历史记录</p>
              <p className="history-empty-hint">执行AI决策后记录会保存在这里</p>
            </div>
          ) : (
            <div className="history-list">
              {records.map((record) => (
                <div
                  key={record.id}
                  className="history-item"
                  onClick={() => {
                    onSelectDecision(record.id);
                    onClose();
                  }}
                >
                  <div className="history-item-header">
                    <span className="history-item-date">📅 {record.date}</span>
                    <span className="history-item-tag">{record.version_tag}</span>
                  </div>

                  <div className="history-item-stats">
                    <div className="history-stat">
                      <span className="history-stat-label">持仓</span>
                      <span className="history-stat-value">{record.holdings_count} 支</span>
                    </div>
                    {record.performance && (
                      <>
                        <div className="history-stat">
                          <span className="history-stat-label">累计收益</span>
                          <span className={`history-stat-value ${record.performance.total_return >= 0 ? 'up' : 'down'}`}>
                            {record.performance.total_return > 0 ? '+' : ''}
                            {record.performance.total_return.toFixed(1)}%
                          </span>
                        </div>
                        <div className="history-stat">
                          <span className="history-stat-label">最大回撤</span>
                          <span className="history-stat-value down">
                            {record.performance.max_dd.toFixed(1)}%
                          </span>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="history-item-action">
                    <span>点击查看详情 →</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
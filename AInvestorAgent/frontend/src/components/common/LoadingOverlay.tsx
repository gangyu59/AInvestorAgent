interface LoadingOverlayProps {
  visible: boolean;
  message?: string;
  progress?: number;
  steps?: string[];
  currentStep?: number;
  showResult?: boolean;
  result?: {
    holdings: Array<{
      symbol: string;
      weight: number;
      score?: number;
    }>;
    version_tag?: string;
  } | null;
  onResultClose?: () => void;
  onViewPortfolio?: () => void;
  onRunBacktest?: () => void;
}

export function LoadingOverlay({
  visible,
  message = '加载中...',
  progress = 0,
  steps = [],
  currentStep = 0,
  showResult = false,
  result = null,
  onResultClose,
  onViewPortfolio,
  onRunBacktest
}: LoadingOverlayProps) {
  if (!visible) return null;

  // 显示结果
  if (showResult && result) {
    const holdings = result.holdings || [];
    const totalStocks = holdings.length;

    return (
      <div className="loading-overlay">
        <div className="loading-content loading-result">
          <div className="result-success-icon">✓</div>
          <h2 className="result-title">AI决策完成</h2>
          <p className="result-subtitle">已生成 {totalStocks} 支股票的投资组合</p>

          <div className="result-stats">
            <div className="result-stat">
              <span className="result-stat-label">持仓数量</span>
              <span className="result-stat-value">{totalStocks} 支</span>
            </div>
            <div className="result-stat">
              <span className="result-stat-label">最大单票</span>
              <span className="result-stat-value">
                {Math.max(...holdings.map(h => h.weight * 100)).toFixed(1)}%
              </span>
            </div>
            <div className="result-stat">
              <span className="result-stat-label">版本</span>
              <span className="result-stat-value">{result.version_tag || 'v1.0'}</span>
            </div>
          </div>

          <div className="result-holdings">
            <h3 className="result-holdings-title">推荐持仓</h3>
            <div className="result-table-wrapper">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>股票代码</th>
                    <th>评分</th>
                    <th>占比</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((holding, index) => (
                    <tr key={holding.symbol}>
                      <td className="result-td-rank">#{index + 1}</td>
                      <td className="result-td-symbol">{holding.symbol}</td>
                      <td className="result-td-score">
                        {holding.score ? `${holding.score.toFixed(0)}分` : '-'}
                      </td>
                      <td className="result-td-weight">
                        {(holding.weight * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="result-actions">
            <button className="result-btn-blue" onClick={onResultClose}>
              返回仪表盘
            </button>
            <button className="result-btn-blue" onClick={onRunBacktest}>
              📊 立即回测
            </button>
            <button className="result-btn-blue" onClick={onViewPortfolio}>
              查看详情 →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 加载状态
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <div className="loading-spinner"></div>
        <h3 className="loading-message">{message}</h3>

        {progress > 0 && (
          <>
            <div className="loading-progress">
              <div className="loading-progress-bar" style={{ width: `${progress}%` }}></div>
            </div>
            <p className="loading-progress-text">{progress}%</p>
          </>
        )}

        {steps.length > 0 && (
          <div className="loading-steps">
            <p className="loading-steps-title">步骤 {currentStep + 1} / {steps.length}</p>
            <ul className="loading-steps-list">
              {steps.map((step, index) => (
                <li
                  key={index}
                  className={`loading-step ${
                    index < currentStep ? 'completed' : 
                    index === currentStep ? 'active' : 
                    'pending'
                  }`}
                >
                  {index < currentStep && '✓ '}
                  {index === currentStep && '🔄 '}
                  {step}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
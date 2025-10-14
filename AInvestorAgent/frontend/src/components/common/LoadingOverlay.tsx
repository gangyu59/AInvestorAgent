// frontend/src/components/common/LoadingOverlay.tsx
// 完整代码 - 显示所有股票

interface LoadingOverlayProps {
  visible: boolean;
  message: string;
  progress: number;
  steps: string[];
  currentStep: number;
  showResult: boolean;
  result: {
    ok: boolean;
    message: string;
    details?: string;
    snapshot_id?: string;
    holdings_count?: number;
    all_holdings?: Array<{
      symbol: string;
      weight: number;
      score: number;
      reasons?: string[];
      sector?: string;
    }>;
  } | null;
  onResultClose: () => void;
  onViewPortfolio?: () => void;
  onRunBacktest?: () => void;
}

export function LoadingOverlay({
  visible,
  message,
  progress,
  steps,
  currentStep,
  showResult,
  result,
  onResultClose,
  onViewPortfolio,
  onRunBacktest
}: LoadingOverlayProps) {
  if (!visible) return null;

  // ========== 结果页面 - 显示所有股票 ==========
  if (showResult && result) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
        <div className="max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-8">

            {/* 标题 */}
            <h2 className="text-2xl font-bold text-white mb-2">
              {result.ok ? 'AI决策完成' : '决策失败'}
            </h2>
            <p className="text-gray-400 text-base mb-6">
              {result.message}
            </p>

            {/* 成功：显示所有股票表格 */}
            {result.ok && result.all_holdings && result.all_holdings.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase">
                  持仓明细（共 {result.holdings_count} 只股票）
                </h3>
                <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 overflow-hidden max-h-[400px] overflow-y-auto">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-gray-800/95 backdrop-blur-sm">
                      <tr className="border-b border-gray-700/50">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">排名</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">股票</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">行业</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-400 uppercase">权重</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-400 uppercase">评分</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">入选理由</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/30">
                      {result.all_holdings.map((h, idx) => (
                        <tr key={h.symbol} className="hover:bg-gray-800/30 transition-colors">
                          <td className="px-4 py-3 text-sm text-gray-500">#{idx + 1}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-white">{h.symbol}</td>
                          <td className="px-4 py-3 text-sm text-gray-400">{h.sector || 'Unknown'}</td>
                          <td className="px-4 py-3 text-sm text-green-400 text-right font-semibold tabular-nums">
                            {(h.weight * 100).toFixed(2)}%
                          </td>
                          <td className="px-4 py-3 text-sm text-blue-400 text-right font-semibold tabular-nums">
                            {h.score.toFixed(0)}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                            {h.reasons && h.reasons.length > 0 ? h.reasons[0] : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 失败：错误信息 */}
            {!result.ok && result.details && (
              <div className="mb-6 bg-red-900/20 border border-red-800/50 rounded-lg p-4">
                <p className="text-sm text-red-300 whitespace-pre-wrap">{result.details}</p>
              </div>
            )}

            {/* 按钮 - 渐变蓝色背景 + 白字 */}
            <div className="flex gap-3">
              {result.ok ? (
                <>
                  <button
                    onClick={onResultClose}
                    className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-lg transition-all text-sm font-medium"
                  >
                    稍后查看
                  </button>

                  {result.holdings_count && result.holdings_count > 0 && (
                    <>
                      {onRunBacktest && (
                        <button
                          onClick={() => {
                            onResultClose();
                            onRunBacktest?.();
                          }}
                          className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-lg transition-all text-sm font-medium"
                        >
                          立即回测
                        </button>
                      )}

                      <button
                        onClick={() => {
                          onResultClose();
                          onViewPortfolio?.();
                        }}
                        className="flex-1 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-lg transition-all text-sm font-semibold"
                      >
                        查看完整详情
                      </button>
                    </>
                  )}
                </>
              ) : (
                <>
                  <button
                    onClick={onResultClose}
                    className="flex-1 px-6 py-2.5 bg-gradient-to-r from-gray-700 to-gray-600 hover:from-gray-600 hover:to-gray-500 text-white rounded-lg transition-all text-sm font-medium"
                  >
                    关闭
                  </button>
                  <button
                    onClick={() => {
                      onResultClose();
                      window.location.reload();
                    }}
                    className="flex-1 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-lg transition-all text-sm font-semibold"
                  >
                    重新尝试
                  </button>
                </>
              )}
            </div>

            {/* 底部快照ID */}
            {result.snapshot_id && (
              <div className="mt-6 pt-4 border-t border-gray-800">
                <div className="flex justify-between text-xs text-gray-500">
                  <span>快照ID</span>
                  <code className="font-mono">{result.snapshot_id.slice(0, 12)}</code>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ========== 加载进度页面 ==========
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md">
      <div className="max-w-md w-full mx-4 bg-gray-900 rounded-2xl shadow-2xl border border-gray-800 p-8">
        {/* 进度条 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-400">进度</span>
            <span className="text-sm font-semibold text-blue-400">{progress}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* 当前消息 */}
        <div className="text-center mb-6">
          <div className="text-lg font-semibold text-white">{message}</div>
        </div>

        {/* 步骤列表 */}
        {steps.length > 0 && (
          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-3 p-2 rounded-lg transition-all ${
                  idx === currentStep 
                    ? 'bg-blue-500/20 text-blue-400' 
                    : idx < currentStep 
                      ? 'text-green-400' 
                      : 'text-gray-500'
                }`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                  idx === currentStep 
                    ? 'bg-blue-500/30' 
                    : idx < currentStep 
                      ? 'bg-green-500/30' 
                      : 'bg-gray-700'
                }`}>
                  {idx < currentStep ? '✓' : idx + 1}
                </div>
                <span className="text-sm">{step}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
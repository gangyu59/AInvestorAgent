import { useEffect, useMemo, useState } from "react";
// import useWatchlist from "@/state/useWatchlist";
const useWatchlist = () => ({ list: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"] });

declare global {
  interface Window {
    latestBacktestData: any;
  }
}

const fmt = (x: any, d = 2): string =>
  typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--";
const pct = (x: any, d = 1): string =>
  x == null || !Number.isFinite(+x) ? "--" : `${(+x * 100).toFixed(d)}%`;

const normMetrics = (m: any) => ({
  ann_return: m?.ann_return ?? m?.annReturn ?? null,
  sharpe: m?.sharpe ?? m?.Sharpe ?? null,
  mdd: m?.mdd ?? m?.max_dd ?? m?.maxDD ?? null,
  winrate: m?.winrate ?? m?.win_rate ?? m?.winRate ?? null,
});

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"];

function LoadingOverlay({
  visible,
  message,
  progress = 0,
  steps = [],
  currentStep = 0
}: {
  visible: boolean;
  message: string;
  progress?: number;
  steps?: string[];
  currentStep?: number;
}) {
  if (!visible) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center">
      <div className="bg-[#2d2d44] rounded-lg p-8 max-w-md w-full mx-4 border border-gray-700 shadow-2xl">
        <div className="flex justify-center mb-6">
          <div className="relative w-24 h-24">
            <div
              className="absolute inset-0 border-4 border-transparent border-t-blue-500 border-r-blue-500 rounded-full animate-spin"
              style={{ animationDuration: '1.2s' }}
            />
            <div
              className="absolute inset-2 border-4 border-transparent border-b-purple-500 border-l-purple-500 rounded-full animate-spin"
              style={{ animationDuration: '1.5s', animationDirection: 'reverse' }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-white">{Math.floor(progress)}%</span>
            </div>
          </div>
        </div>

        <h3 className="text-xl font-semibold text-white text-center mb-4">
          {message}
        </h3>

        {steps.length > 0 && (
          <div className="space-y-2 mb-4">
            <div className="text-sm text-gray-400 text-center mb-3">
              步骤 {currentStep + 1} / {steps.length}
            </div>
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  idx < currentStep ? 'bg-green-600 text-white' :
                  idx === currentStep ? 'bg-blue-600 text-white animate-pulse' :
                  'bg-gray-700 text-gray-500'
                }`}>
                  {idx < currentStep ? '✓' : idx + 1}
                </div>
                <span className={`text-sm transition-colors ${
                  idx <= currentStep ? 'text-white font-medium' : 'text-gray-500'
                }`}>
                  {step}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
          <div
            className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        <p className="text-xs text-gray-400 text-center mt-4">
          正在后台处理，请稍候...
        </p>
      </div>
    </div>
  );
}

function SmartSearchBox() {
  const [query, setQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const { list: watchlist } = useWatchlist();

  const suggestions = useMemo(() => {
    if (query.length === 0) {
      return (watchlist || []).slice(0, 20).map(s => ({ symbol: s }));
    }
    return (watchlist || [])
      .filter(s => s.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 10)
      .map(s => ({ symbol: s }));
  }, [query, watchlist]);

  const handleSelect = (symbol: string) => {
    window.location.hash = `#/stock?query=${encodeURIComponent(symbol)}`;
    setShowDropdown(false);
    setQuery('');
  };

  const handleKeyDown = (e: any) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter') {
      if (selectedIndex >= 0) {
        handleSelect(suggestions[selectedIndex].symbol);
      } else if (query) {
        handleSelect(query.toUpperCase());
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  return (
    <div className="relative w-full">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setShowDropdown(true)}
        onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
        onKeyDown={handleKeyDown}
        placeholder="搜索股票代码..."
        className="w-full px-4 py-2 bg-[#1a1a2e] border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
      />

      {showDropdown && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-[#2d2d44] border border-gray-700 rounded-lg shadow-2xl max-h-80 overflow-y-auto z-50">
          {query.length === 0 && (
            <div className="px-4 py-2 text-xs text-gray-500 border-b border-gray-700 font-medium">
              📌 我的关注列表（Top {suggestions.length}）
            </div>
          )}

          {suggestions.map((stock, idx) => (
            <button
              key={stock.symbol}
              onClick={() => handleSelect(stock.symbol)}
              className={`w-full px-4 py-3 flex items-center justify-between hover:bg-gray-700 transition-colors text-left ${
                idx === selectedIndex ? 'bg-gray-700' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-yellow-500">⭐</span>
                <span className="font-semibold text-white">{stock.symbol}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function WatchlistCard() {
  const { list } = useWatchlist();
  const [expanded, setExpanded] = useState(false);
  const displayCount = expanded ? list.length : Math.min(10, list.length);

  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">
          📌 我的关注列表
          <span className="ml-2 text-sm text-gray-400">({list.length}支)</span>
        </h3>
        <button
          onClick={() => window.location.hash = '#/manage'}
          className="text-sm text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1"
        >
          管理列表
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <div className="dashboard-card-body">
        {list.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-400 mb-4">还没有关注任何股票</p>
            <button
              onClick={() => window.location.hash = '#/manage'}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              添加股票
            </button>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {list.slice(0, displayCount).map((symbol) => (
                  <div className="dashboard-watchlist-item">
                    <span className="dashboard-watchlist-symbol">{symbol}</span>
                    <button
                        onClick={() => window.location.hash = `#/stock?query=${symbol}`}
                        className="dashboard-watchlist-detail-btn"
                    >
                      查看
                    </button>
                  </div>
              ))}
            </div>

            {list.length > 10 && (
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="w-full mt-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                {expanded ? '收起 ▲' : `查看全部 ${list.length} 支 ▼`}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function ImprovedDashboard() {
  const { list: watchlist } = useWatchlist();
  const [symbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [decide, setDecide] = useState<any>(null);
  const [scores, setScores] = useState<any[]>([]);
  const [sentiment, setSentiment] = useState<any>(null);
  const [backtest, setBacktest] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [errorMsg, setError] = useState<string | null>(null);

  const [loadingState, setLoadingState] = useState({
    visible: false,
    message: '',
    progress: 0,
    steps: [] as string[],
    currentStep: 0
  });

  useEffect(() => {
    setSnapshot({
      weights: { AAPL: 0.25, MSFT: 0.2, NVDA: 0.15, AMZN: 0.2, GOOGL: 0.2 },
      metrics: { ann_return: 0.15, mdd: -0.12, sharpe: 1.3, winrate: 0.68 },
      version_tag: "ai_v1.2"
    });

    setScores([
      { symbol: "AAPL", score: { score: 82, factors: { value: 0.7, quality: 0.8, momentum: 0.6, growth: 0.9, news: 0.3 } }, as_of: "2025-01-15" },
      { symbol: "MSFT", score: { score: 78, factors: { value: 0.6, quality: 0.9, momentum: 0.7, growth: 0.8, news: 0.5 } }, as_of: "2025-01-15" },
      { symbol: "NVDA", score: { score: 85, factors: { value: 0.4, quality: 0.7, momentum: 0.9, growth: 1.0, news: 0.8 } }, as_of: "2025-01-15" },
      { symbol: "AMZN", score: { score: 75, factors: { value: 0.5, quality: 0.6, momentum: 0.8, growth: 0.7, news: 0.4 } }, as_of: "2025-01-15" },
      { symbol: "GOOGL", score: { score: 80, factors: { value: 0.8, quality: 0.8, momentum: 0.5, growth: 0.6, news: 0.6 } }, as_of: "2025-01-15" }
    ]);

    setSentiment({
      latest_news: [
        { title: "Apple发布新款Vision Pro", url: "#", score: 0.7 },
        { title: "微软Azure增长超预期", url: "#", score: 0.5 },
        { title: "英伟达GPU需求持续强劲", url: "#", score: 0.8 }
      ]
    });

    setBacktest({
      nav: [100, 102, 105, 103, 108, 112, 115, 118, 114, 120],
      benchmark_nav: [100, 101, 103, 102, 105, 108, 109, 112, 110, 115],
      metrics: { ann_return: 0.18, sharpe: 1.4, mdd: -0.08, winrate: 0.72 }
    });
  }, []);

  const keptTop5 = useMemo(() => {
    const weights = snapshot?.weights || {};
    return Object.entries(weights).sort((a, b) => (b[1] as number) - (a[1] as number)).slice(0, 5);
  }, [snapshot]);

  const btM = useMemo(() => normMetrics(backtest?.metrics), [backtest]);

  async function onDecide() {
    setLoadingState({
      visible: true,
      message: '智能决策中',
      progress: 0,
      steps: ['🔍 拉取最新数据', '🧮 计算因子指标', '📊 综合评分', '⚖️ 风险检查', '💼 生成组合'],
      currentStep: 0
    });

    try {
      for (let i = 0; i < 5; i++) {
        await new Promise(resolve => setTimeout(resolve, 400));
        setLoadingState(prev => ({ ...prev, currentStep: i, progress: (i + 1) * 20 }));
      }

      const response = await fetch("http://localhost:8000/orchestrator/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbols: watchlist.length > 0 ? watchlist : symbols,
          topk: 15,
          min_score: 55,
          params: { 'risk.max_stock': 0.3, 'risk.max_sector': 0.5, 'risk.count_range': [5, 15] }
        })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const decideData = await response.json();
      const weights: Record<string, number> = {};
      const kept: string[] = [];

      if (decideData?.holdings) {
        decideData.holdings.forEach((holding: any) => {
          weights[holding.symbol] = holding.weight;
          kept.push(holding.symbol);
        });
      }

      setDecide({ context: { weights, kept, orders: decideData?.orders || [], version_tag: decideData?.version_tag || "ai_v1.3" } });
      setLoadingState(prev => ({ ...prev, progress: 100 }));
      setTimeout(() => {
        setLoadingState({ visible: false, message: '', progress: 0, steps: [], currentStep: 0 });
      }, 500);

    } catch (error) {
      setLoadingState({ visible: false, message: '', progress: 0, steps: [], currentStep: 0 });
      setError(`AI决策失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  async function onRunBacktest() {
    setLoadingState({
      visible: true,
      message: '运行回测',
      progress: 50,
      steps: ['📊 计算净值', '📉 分析回撤'],
      currentStep: 0
    });

    try {
      let weights: Array<{symbol: string; weight: number}> = [];

      if (decide?.context?.weights) {
        weights = Object.entries(decide.context.weights).map(([symbol, weight]) => ({
          symbol,
          weight: Number(weight)
        }));
      } else {
        const useSymbols = watchlist.length > 0 ? watchlist : symbols;
        weights = useSymbols.map(symbol => ({ symbol, weight: 1.0 / useSymbols.length }));
      }

      const response = await fetch("http://localhost:8000/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weights, window_days: 252, trading_cost: 0.001 })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const backtestData = await response.json();
      window.latestBacktestData = backtestData;

      setLoadingState({ visible: false, message: '', progress: 0, steps: [], currentStep: 0 });
      window.location.hash = '#/simulator?from=backtest';

    } catch (error) {
      setLoadingState({ visible: false, message: '', progress: 0, steps: [], currentStep: 0 });
      setError(`回测失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  async function onGenerateReport() {
    const mockReport = `# 投资决策日报
生成时间: ${new Date().toLocaleString()}

## 组合概况
- 持仓股票: ${(watchlist.length > 0 ? watchlist : symbols).join(", ")}
- 当前权重: ${decide?.context?.weights ? 
  Object.entries(decide.context.weights).map(([s, w]) => `${s}(${(Number(w)*100).toFixed(1)}%)`).join(", ") : "等权重"}

## 市场情绪
- 整体情绪偏向积极
- 主要关注科技股走势

## 建议
- 维持当前配置
- 关注市场变化
`;

    const blob = new Blob([mockReport], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `investment_report_${new Date().toISOString().split('T')[0]}.md`;
    a.click();
    URL.revokeObjectURL(url);
    alert("报告已生成并下载！");
  }

  async function onBatchUpdate() {
    if (!watchlist || watchlist.length === 0) {
      alert('Watchlist为空，请先在"管理"页添加股票');
      return;
    }

    setLoadingState({
      visible: true,
      message: '一键更新数据',
      progress: 0,
      steps: ['📈 获取价格数据', '📰 获取新闻', '🧮 计算因子', '⭐ 重算评分'],
      currentStep: 0
    });

    try {
      for (let i = 0; i < 4; i++) {
        await new Promise(resolve => setTimeout(resolve, 800));
        setLoadingState(prev => ({ ...prev, currentStep: i, progress: (i + 1) * 25 }));
      }

      const response = await fetch('http://localhost:8000/api/batch/update_all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: watchlist,
          fetch_prices: true,
          fetch_fundamentals: false,
          fetch_news: true,
          rebuild_factors: true,
          recompute_scores: true,
          days: 7,
          pages: 2
        })
      });

      if (!response.ok) throw new Error('批量更新失败');

      const data = await response.json();
      setLoadingState({ visible: false, message: '', progress: 0, steps: [], currentStep: 0 });
      alert('更新完成！\n' + JSON.stringify(data.results, null, 2));

    } catch (error) {
      setLoadingState({ visible: false, message: '', progress: 0, steps: [], currentStep: 0 });
      alert('更新失败：' + (error instanceof Error ? error.message : '未知错误'));
    }
  }

  return (
    <div className="dashboard-content">
      <LoadingOverlay {...loadingState} />

      <header className="dashboard-header">
        <div className="dashboard-brand">
          <div className="dashboard-logo">AI</div>
          <div>
            <h1 className="dashboard-brand-title">AInvestorAgent</h1>
            <p className="dashboard-brand-subtitle">智能投资决策平台</p>
          </div>
        </div>

        <div className="dashboard-actions">
          <div className="dashboard-search">
            <SmartSearchBox />
          </div>

          <div className="dashboard-cta-group">
            <button onClick={onDecide} className="dashboard-btn dashboard-btn-primary">AI决策</button>
            <button onClick={onRunBacktest} className="dashboard-btn dashboard-btn-secondary">回测</button>
            <button onClick={onGenerateReport} className="dashboard-btn dashboard-btn-secondary">报告</button>
            <button onClick={onBatchUpdate} className="dashboard-btn dashboard-btn-secondary">🔄 更新数据</button>
          </div>
        </div>
      </header>

      {errorMsg && (
        <div className="dashboard-error">
          {errorMsg}
          <button onClick={() => setError(null)} className="ml-4 text-white underline">关闭</button>
        </div>
      )}

      <section className="dashboard-section">
        <h2 className="dashboard-section-title">投资组合概览</h2>
        <div className="dashboard-grid dashboard-grid-auto">

          <div className="dashboard-card">
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">组合表现</h3>
              <button
                onClick={() => window.location.hash = '#/portfolio'}
                className="text-sm text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1"
              >
                查看详情
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
            <div className="dashboard-card-body">
              <div className="dashboard-kpi-grid">
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">年化收益</p>
                  <p className={`dashboard-kpi-value large ${(snapshot?.metrics?.ann_return ?? 0) >= 0 ? 'up' : 'down'}`}>
                    {pct(snapshot?.metrics?.ann_return, 1)}
                  </p>
                </div>
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">夏普比率</p>
                  <p className="dashboard-kpi-value large neutral">{fmt(snapshot?.metrics?.sharpe, 2)}</p>
                </div>
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">最大回撤</p>
                  <p className="dashboard-kpi-value medium down">{pct(snapshot?.metrics?.mdd, 1)}</p>
                </div>
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">胜率</p>
                  <p className="dashboard-kpi-value medium up">
                    {btM.winrate ? `${Math.round(btM.winrate * 100)}%` : '--'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="dashboard-card">
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">Top 5 持仓</h3>
              <button
                onClick={() => window.location.hash = '#/portfolio'}
                className="text-sm text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1"
              >
                查看详情
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
            <div className="dashboard-card-body">
              <div className="dashboard-holdings">
                {keptTop5.map(([sym, weight]) => (
                  <div key={sym} className="dashboard-holding-item">
                    <span className="dashboard-holding-symbol">{sym}</span>
                    <span className="dashboard-holding-weight">{pct(weight, 1)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="dashboard-card">
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">最新AI决策</h3>
              <button
                onClick={() => window.location.hash = '#/portfolio'}
                className="text-sm text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1"
              >
                查看详情
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
            <div className="dashboard-card-body">
              {decide?.context?.kept?.length ? (
                <div>
                  <div className="dashboard-decision-summary">
                    <div className="dashboard-metric">
                      <span className="dashboard-metric-label">选中股票</span>
                      <span className="dashboard-metric-value">{decide.context.kept.length} 只</span>
                    </div>
                    <div className="dashboard-metric">
                      <span className="dashboard-metric-label">决策方法</span>
                      <span className="dashboard-metric-value">
                        {decide?.context?.version_tag?.includes('ai') ? 'AI增强' : '传统算法'}
                      </span>
                    </div>
                  </div>
                  <div className="dashboard-holdings-preview">
                    {decide.context.kept.slice(0, 4).map((symbol: string) => (
                      <div key={symbol} className="dashboard-holding-chip">
                        <span className="symbol">{symbol}</span>
                        <span className="weight">
                          {((decide?.context?.weights?.[symbol] || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                    {(decide?.context?.kept?.length || 0) > 4 && (
                      <span className="dashboard-more">+{(decide?.context?.kept?.length || 0) - 4} 更多</span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <span>暂无决策记录</span>
                  <button onClick={onDecide} className="dashboard-btn dashboard-btn-primary">开始AI决策</button>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="dashboard-section">
        <h2 className="dashboard-section-title">我的关注与操作</h2>
        <div className="dashboard-grid dashboard-grid-2">
          <WatchlistCard />

          <div className="dashboard-card">
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">快速操作</h3>
            </div>
            <div className="dashboard-card-body">
              <div className="space-y-4">
                <button
                    onClick={onBatchUpdate}
                    className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all shadow-lg"
                >
                  🔄 一键更新所有数据
                </button>

                <p className="text-sm text-gray-400">
                  自动执行：价格（近一周）→ 基本面（可选）→ 新闻情绪（近7天）→ 因子 → 评分
                </p>

                <div className="pt-4 border-t border-gray-700">
                  <p className="text-xs text-gray-500 mb-2">
                    💡 提示：AI只从Watchlist中选择股票进行组合
                  </p>
                  <button
                      onClick={() => window.location.hash = '#/manage'}
                      className="text-sm text-blue-400 hover:underline"
                  >
                    前往管理页面 →
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>


      <section className="dashboard-section">
        <div className="dashboard-grid dashboard-grid-2">

        <div className="dashboard-card">
              <div className="dashboard-card-header">
                <h3 className="dashboard-card-title">股票池评分</h3>
                <button
                  onClick={() => window.location.hash = '#/stock'}
                  className="text-sm text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1"
                >
                  查看更多
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
              <div className="dashboard-card-body">
                <div className="dashboard-scores-grid dashboard-scores-header">
                  <span>代码</span>
                  <span>评分分布</span>
                  <span>总分</span>
                  <span>操作</span>
                </div>
                {scores.slice(0, 5).map((item) => (
                  <div key={item.symbol} className="dashboard-scores-grid">
                    <span className="dashboard-scores-symbol">{item.symbol}</span>

                    <svg width="100" height="30" className="dashboard-radar">
                      {(() => {
                        const factors = item.score?.factors || {};
                        const order = ["value", "quality", "momentum", "growth", "news"];
                        const vals = order.map(k => Math.max(0, Math.min(1, factors[k] || 0)));
                        const cx = 15, cy = 15, r = 12, n = order.length;
                        const points = vals.map((v, i) => {
                          const angle = -Math.PI / 2 + i * (2 * Math.PI / n);
                          const radius = r * v;
                          const x = cx + radius * Math.cos(angle);
                          const y = cy + radius * Math.sin(angle);
                          return `${x},${y}`;
                        }).join(" ");

                        return (
                          <>
                            <circle cx={cx} cy={cy} r={r} fill="none" stroke="#374151" strokeWidth="1"/>
                            <polygon
                              points={points}
                              fill="rgba(59, 130, 246, 0.2)"
                              stroke="#3b82f6"
                              strokeWidth="1.5"
                            />
                          </>
                        );
                      })()}
                    </svg>

                    <span className={`dashboard-scores-total ${
                      item.score?.score >= 80 ? 'good' : 
                      item.score?.score >= 70 ? 'mid' : 'bad'
                    }`}>
                      {item.score?.score || '--'}
                    </span>

                    <button
                      className="dashboard-btn dashboard-btn-secondary"
                      onClick={() => window.location.hash = `#/stock?query=${item.symbol}`}
                    >
                      详情
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="dashboard-card">
              <div className="dashboard-card-header">
                <h3 className="dashboard-card-title">市场情绪</h3>
                <button
                  onClick={() => window.location.hash = '#/monitor'}
                  className="text-sm text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1"
                >
                  查看详情
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
              <div className="dashboard-card-body">
                <div className="dashboard-sentiment-chart">
                  <svg width="100%" height="100%">
                    <line x1="0" y1="30" x2="100%" y2="30" stroke="#374151" strokeWidth="1"/>
                    <path
                      d="M 0,40 Q 25,20 50,25 T 100,15"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2"
                    />
                  </svg>
                </div>

                <div className="dashboard-news-section">
                  <h4>最新动态</h4>
                  <div className="dashboard-news-list">
                    {sentiment?.latest_news?.slice(0, 3).map((news: any, i: number) => (
                      <div key={i} className="dashboard-news-item">
                        <div className="dashboard-news-content">
                          <span className="dashboard-news-title">{news.title}</span>
                          <span className={`dashboard-news-sentiment ${
                            news.score > 0 ? 'positive' : 
                            news.score < 0 ? 'negative' : 'neutral'
                          }`}>
                            {news.score > 0 ? '+' : ''}{fmt(news.score, 1)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <footer className="dashboard-footer">
          <div className="dashboard-footer-links">
            <a href="/#/stock" className="dashboard-footer-link">个股分析</a>
            <a href="/#/portfolio" className="dashboard-footer-link">组合管理</a>
            <a href="/#/simulator" className="dashboard-footer-link">回测模拟</a>
            <a href="/#/trading" className="dashboard-footer-link">模拟交易</a>
            <a href="/#/monitor" className="dashboard-footer-link">舆情监控</a>
            <a href="/#/manage" className="dashboard-footer-link">系统管理</a>
          </div>

          <div className="dashboard-footer-info">
            AInvestorAgent v1.3 | 低频投资决策 ≤3次/周 |
            <span className="dashboard-footer-status">● 系统运行正常</span>
          </div>
        </footer>
      </div>      // 关闭 dashboard-content
  );
}
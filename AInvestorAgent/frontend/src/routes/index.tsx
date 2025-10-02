import { useEffect, useMemo, useState } from "react";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { DashboardHeader } from "../components/dashboard/Header";
import { PortfolioOverview } from "../components/dashboard/PortfolioOverview";
import { WatchlistPanel } from "../components/dashboard/WatchlistPanel";
import { QuickActions } from "../components/dashboard/QuickActions";
import { StockScores } from "../components/dashboard/StockScores";
import { MarketSentiment } from "../components/dashboard/MarketSentiment";
import { DashboardFooter } from "../components/dashboard/Footer";

const useWatchlist = () => ({ list: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"] });
declare global { interface Window { latestBacktestData: any; latestDecisionData: any; } }
const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"];

export default function Dashboard() {
  const { list: watchlist } = useWatchlist();
  const [symbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [decide, setDecide] = useState<any>(null);
  const [scores, setScores] = useState<any[]>([]);
  const [sentiment, setSentiment] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [errorMsg, setError] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState({
    visible: false,
    message: '',
    progress: 0,
    steps: [] as string[],
    currentStep: 0,
    showResult: false,  // 新增：是否显示结果
    result: null as any // 新增：结果数据
  });

  useEffect(() => {
    // Mock 数据
    setSnapshot({ weights: { AAPL: 0.25, MSFT: 0.2, NVDA: 0.15, AMZN: 0.2, GOOGL: 0.2 }, metrics: { ann_return: 0.15, mdd: -0.12, sharpe: 1.3, winrate: 0.68 }, version_tag: "ai_v1.2" });
    setScores([
      { symbol: "AAPL", score: { score: 82, factors: { value: 0.7, quality: 0.8, momentum: 0.6, growth: 0.9, news: 0.3 } }, as_of: "2025-01-15" },
      { symbol: "MSFT", score: { score: 78, factors: { value: 0.6, quality: 0.9, momentum: 0.7, growth: 0.8, news: 0.5 } }, as_of: "2025-01-15" },
      { symbol: "NVDA", score: { score: 85, factors: { value: 0.4, quality: 0.7, momentum: 0.9, growth: 1.0, news: 0.8 } }, as_of: "2025-01-15" },
      { symbol: "AMZN", score: { score: 75, factors: { value: 0.5, quality: 0.6, momentum: 0.8, growth: 0.7, news: 0.4 } }, as_of: "2025-01-15" },
      { symbol: "GOOGL", score: { score: 80, factors: { value: 0.8, quality: 0.8, momentum: 0.5, growth: 0.6, news: 0.6 } }, as_of: "2025-01-15" }
    ]);
    setSentiment({ latest_news: [{ title: "Apple发布新款Vision Pro", url: "#", score: 0.7 }, { title: "微软Azure增长超预期", url: "#", score: 0.5 }, { title: "英伟达GPU需求持续强劲", url: "#", score: 0.8 }] });
  }, []);

  const keptTop5 = useMemo(() => {
    const weights = snapshot?.weights || {};
    return Object.entries(weights).sort((a, b) => (b[1] as number) - (a[1] as number)).slice(0, 5);
  }, [snapshot]);

  async function onDecide() {
    setLoadingState({
      visible: true,
      message: '智能决策中',
      progress: 0,
      steps: ['🔍 拉取最新数据', '🧮 计算因子指标', '📊 综合评分', '⚖️ 风险检查', '💼 生成组合'],
      currentStep: 0,
      showResult: false,
      result: null
    });

    try {
      // 模拟步骤进度
      for (let i = 0; i < 5; i++) {
        await new Promise(resolve => setTimeout(resolve, 400));
        setLoadingState(prev => ({
          ...prev,
          currentStep: i,
          progress: (i + 1) * 20
        }));
      }

      const response = await fetch("http://localhost:8000/orchestrator/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbols: watchlist.length > 0 ? watchlist : symbols,
          topk: 15,
          min_score: 55,
          params: {
            'risk.max_stock': 0.3,
            'risk.max_sector': 0.5,
            'risk.count_range': [5, 15]
          }
        })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const decideData = await response.json();

      // 保存决策数据
      setDecide(decideData);
      window.latestDecisionData = decideData;

      // 🎯 关键改动：显示结果在LoadingOverlay内
      setLoadingState({
        visible: true,
        message: '',
        progress: 100,
        steps: [],
        currentStep: 5,
        showResult: true,  // 显示结果
        result: decideData // 传递结果数据
      });

    } catch (error) {
      setLoadingState({
        visible: false,
        message: '',
        progress: 0,
        steps: [],
        currentStep: 0,
        showResult: false,
        result: null
      });
      setError(`AI决策失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  async function onRunBacktest() {
    // 关闭LoadingOverlay
    setLoadingState({
      visible: false,
      message: '',
      progress: 0,
      steps: [],
      currentStep: 0,
      showResult: false,
      result: null
    });

    // 延迟一下再开始回测，让用户看到状态变化
    setTimeout(async () => {
      setLoadingState({
        visible: true,
        message: '运行回测',
        progress: 50,
        steps: ['📊 计算净值', '📉 分析回撤'],
        currentStep: 0,
        showResult: false,
        result: null
      });

      try {
        let weights: Array<{symbol: string; weight: number}> = [];
        if (decide?.holdings) {
          weights = decide.holdings.map((h: any) => ({
            symbol: h.symbol,
            weight: h.weight
          }));
        } else {
          const useSymbols = watchlist.length > 0 ? watchlist : symbols;
          weights = useSymbols.map(symbol => ({
            symbol,
            weight: 1.0 / useSymbols.length
          }));
        }

        const response = await fetch("http://localhost:8000/api/backtest/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            weights,
            window_days: 252,
            trading_cost: 0.001
          })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const backtestData = await response.json();
        window.latestBacktestData = backtestData;

        setLoadingState({
          visible: false,
          message: '',
          progress: 0,
          steps: [],
          currentStep: 0,
          showResult: false,
          result: null
        });
        window.location.hash = '#/simulator?from=backtest';
      } catch (error) {
        setLoadingState({
          visible: false,
          message: '',
          progress: 0,
          steps: [],
          currentStep: 0,
          showResult: false,
          result: null
        });
        setError(`回测失败: ${error instanceof Error ? error.message : '未知错误'}`);
      }
    }, 300);
  }

  async function onGenerateReport() {
    const mockReport = `# 投资决策日报\n生成时间: ${new Date().toLocaleString()}\n\n## 组合概况\n- 持仓股票: ${(watchlist.length > 0 ? watchlist : symbols).join(", ")}\n- 当前权重: ${decide?.holdings ? decide.holdings.map((h: any) => `${h.symbol}(${(h.weight*100).toFixed(1)}%)`).join(", ") : "等权重"}\n\n## 市场情绪\n- 整体情绪偏向积极\n- 主要关注科技股走势\n\n## 建议\n- 维持当前配置\n- 关注市场变化`;
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
      currentStep: 0,
      showResult: false,
      result: null
    });

    try {
      for (let i = 0; i < 4; i++) {
        await new Promise(resolve => setTimeout(resolve, 800));
        setLoadingState(prev => ({
          ...prev,
          currentStep: i,
          progress: (i + 1) * 25
        }));
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

      setLoadingState({
        visible: false,
        message: '',
        progress: 0,
        steps: [],
        currentStep: 0,
        showResult: false,
        result: null
      });

      alert('更新完成！\n' + JSON.stringify(data.results, null, 2));
    } catch (error) {
      setLoadingState({
        visible: false,
        message: '',
        progress: 0,
        steps: [],
        currentStep: 0,
        showResult: false,
        result: null
      });
      alert('更新失败：' + (error instanceof Error ? error.message : '未知错误'));
    }
  }

  // LoadingOverlay 按钮处理
  const handleResultClose = () => {
    setLoadingState({
      visible: false,
      message: '',
      progress: 0,
      steps: [],
      currentStep: 0,
      showResult: false,
      result: null
    });
  };

  const handleViewPortfolio = () => {
    handleResultClose();
    window.location.hash = '#/portfolio';
  };

  const handleRunBacktestFromResult = () => {
    onRunBacktest();
  };

  return (
    <div className="dashboard-content">
      <LoadingOverlay
        visible={loadingState.visible}
        message={loadingState.message}
        progress={loadingState.progress}
        steps={loadingState.steps}
        currentStep={loadingState.currentStep}
        showResult={loadingState.showResult}
        result={loadingState.result}
        onResultClose={handleResultClose}
        onViewPortfolio={handleViewPortfolio}
        onRunBacktest={handleRunBacktestFromResult}
      />

      <DashboardHeader
        watchlist={watchlist}
        onDecide={onDecide}
        onBacktest={onRunBacktest}
        onReport={onGenerateReport}
        onUpdate={onBatchUpdate}
      />

      {errorMsg && (
        <div className="dashboard-error">
          {errorMsg}
          <button onClick={() => setError(null)} className="ml-4 text-white underline">
            关闭
          </button>
        </div>
      )}

      <PortfolioOverview
        snapshot={snapshot}
        keptTop5={keptTop5}
        decide={decide}
        onDecide={onDecide}
      />

      <section className="dashboard-section">
        <h2 className="dashboard-section-title">我的关注与操作</h2>
        <div className="dashboard-grid dashboard-grid-2">
          <WatchlistPanel list={watchlist} />
          <QuickActions onUpdate={onBatchUpdate} />
        </div>
      </section>

      <section className="dashboard-section">
        <div className="dashboard-grid dashboard-grid-2">
          <StockScores scores={scores} />
          <MarketSentiment sentiment={sentiment} />
        </div>
      </section>

      <DashboardFooter />
    </div>
  );
}
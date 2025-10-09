import { useEffect, useMemo, useState } from "react";
import "../styles/home.css";

import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { DashboardHeader } from "../components/dashboard/Header";
import { PortfolioOverview } from "../components/dashboard/PortfolioOverview";
import { WatchlistPanel } from "../components/dashboard/WatchlistPanel";
import { QuickActions } from "../components/dashboard/QuickActions";
import { StockScores } from "../components/dashboard/StockScores";
import { MarketSentiment } from "../components/dashboard/MarketSentiment";
import { DashboardFooter } from "../components/dashboard/Footer";
import { DecisionTracking } from "../components/dashboard/DecisionTracking";
import { DecisionHistoryModal } from "../components/dashboard/DecisionHistoryModal";

interface Stock {
  symbol: string;
  name?: string;
  sector?: string;
}

export default function Dashboard() {
  const [watchlist, setWatchlist] = useState<Stock[]>([]);
  const [decide, setDecide] = useState<any>(null);
  const [scores, setScores] = useState<any[]>([]);
  const [sentiment, setSentiment] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [errorMsg, setError] = useState<string | null>(null);
  const [latestDecision, setLatestDecision] = useState<any>(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  const [loadingState, setLoadingState] = useState({
    visible: false,
    message: "",
    progress: 0,
    steps: [] as string[],
    currentStep: 0,
    showResult: false,
    result: null as any,
  });

  // 从 localStorage 加载关注列表
  useEffect(() => {
    const stored = localStorage.getItem("watchlist");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setWatchlist(parsed);
      } catch (e) {
        console.error("解析关注列表失败:", e);
        // 使用默认列表
        const defaultList = [
          { symbol: "AAPL", name: "Apple Inc.", sector: "Technology" },
          { symbol: "MSFT", name: "Microsoft", sector: "Technology" },
          { symbol: "NVDA", name: "NVIDIA", sector: "Technology" },
          { symbol: "GOOGL", name: "Alphabet", sector: "Technology" },
          { symbol: "AMZN", name: "Amazon", sector: "Consumer" },
        ];
        setWatchlist(defaultList);
        localStorage.setItem("watchlist", JSON.stringify(defaultList));
      }
    } else {
      // 首次使用，设置默认列表
      const defaultList = [
        { symbol: "AAPL", name: "Apple Inc.", sector: "Technology" },
        { symbol: "MSFT", name: "Microsoft", sector: "Technology" },
        { symbol: "NVDA", name: "NVIDIA", sector: "Technology" },
        { symbol: "GOOGL", name: "Alphabet", sector: "Technology" },
        { symbol: "AMZN", name: "Amazon", sector: "Consumer" },
      ];
      setWatchlist(defaultList);
      localStorage.setItem("watchlist", JSON.stringify(defaultList));
    }
  }, []);

  // 监听 localStorage 变化(从管理页面返回时更新)
  useEffect(() => {
    const handleStorageChange = () => {
      const stored = localStorage.getItem("watchlist");
      if (stored) {
        try {
          setWatchlist(JSON.parse(stored));
        } catch (e) {
          console.error("解析关注列表失败:", e);
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    // 也监听 hash 变化(从管理页返回)
    window.addEventListener("hashchange", handleStorageChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("hashchange", handleStorageChange);
    };
  }, []);

  // 首屏示例数据
  useEffect(() => {
    setSnapshot({
      weights: { AAPL: 0.25, MSFT: 0.2, NVDA: 0.15, AMZN: 0.2, GOOGL: 0.2 },
      metrics: { ann_return: 0.15, mdd: -0.12, sharpe: 1.3, winrate: 0.68 },
      version_tag: "ai_v1.2",
    });
    setScores([
      { symbol: "AAPL", score: { score: 82, factors: { value: 0.7, quality: 0.8, momentum: 0.6, growth: 0.9, news: 0.3 } }, as_of: "2025-01-15" },
      { symbol: "MSFT", score: { score: 78, factors: { value: 0.6, quality: 0.9, momentum: 0.7, growth: 0.8, news: 0.5 } }, as_of: "2025-01-15" },
      { symbol: "NVDA", score: { score: 85, factors: { value: 0.4, quality: 0.7, momentum: 0.9, growth: 1.0, news: 0.8 } }, as_of: "2025-01-15" },
      { symbol: "AMZN", score: { score: 75, factors: { value: 0.5, quality: 0.6, momentum: 0.8, growth: 0.7, news: 0.4 } }, as_of: "2025-01-15" },
      { symbol: "GOOGL", score: { score: 80, factors: { value: 0.8, quality: 0.8, momentum: 0.5, growth: 0.6, news: 0.6 } }, as_of: "2025-01-15" },
    ]);
    setSentiment({
      loading: false,
      latest_news: [
        { title: "Apple 发布新款 Vision Pro", url: "#", score: 0.7 },
        { title: "微软 Azure 增长超预期", url: "#", score: 0.5 },
        { title: "英伟达 GPU 需求持续强劲", url: "#", score: 0.8 },
        { title: "META AI 新模型上线", url: "#", score: 0.3 },
        { title: "特斯拉交付数据创新高", url: "#", score: 0.6 },
        { title: "谷歌云拿下大单", url: "#", score: 0.4 },
      ],
    });
    setLatestDecision({
      date: "2025-10-01",
      holdings_count: 5,
      version_tag: "v1.2",
      performance: { today_change: 1.2, total_return: 8.5, days_since: 2 },
    });
  }, []);

  const keptTop5: Array<[string, number]> = useMemo(() => {
    const weights: Record<string, number> = (snapshot && snapshot.weights) || {};
    return Object.entries(weights)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [snapshot]);

  // 从关注列表中移除股票
  const handleRemoveFromWatchlist = (symbol: string) => {
    if (!confirm(`确定要移除 ${symbol} 吗?`)) return;

    const newList = watchlist.filter((s) => s.symbol !== symbol);
    setWatchlist(newList);
    localStorage.setItem("watchlist", JSON.stringify(newList));
  };

  async function onDecide() {
    setLoadingState({
      visible: true,
      message: "智能决策中",
      progress: 0,
      steps: ["🔍 拉取最新数据", "🧮 计算因子指标", "📊 综合评分", "⚖️ 风险检查", "💼 生成组合"],
      currentStep: 0,
      showResult: false,
      result: null,
    });

    try {
      for (let i = 0; i < 5; i++) {
        await new Promise((r) => setTimeout(r, 300));
        setLoadingState((prev) => ({ ...prev, currentStep: i, progress: (i + 1) * 20 }));
      }
      setLoadingState((prev) => ({ ...prev, showResult: true, result: { ok: true } }));
    } catch (e) {
      setLoadingState({ visible: false, message: "", progress: 0, steps: [], currentStep: 0, showResult: false, result: null });
      setError("AI决策失败");
    }
  }

  async function onRunBacktest() {
    window.location.hash = "#/simulator?from=backtest";
  }

  function onGenerateReport() {
    const blob = new Blob(["# 报告示例"], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "report.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  function onBatchUpdate() {
    setLoadingState({
      visible: true,
      message: "一键更新数据",
      progress: 40,
      steps: ["📈 价格", "📰 新闻", "🧮 因子", "⭐ 评分"],
      currentStep: 1,
      showResult: false,
      result: null,
    });
    setTimeout(
      () =>
        setLoadingState({ visible: false, message: "", progress: 0, steps: [], currentStep: 0, showResult: false, result: null }),
      1200
    );
  }

  const handleResultClose = () =>
    setLoadingState({ visible: false, message: "", progress: 0, steps: [], currentStep: 0, showResult: false, result: null });

  // 提取股票代码数组
  const symbolList = watchlist.map((s) => s.symbol);

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
        onViewPortfolio={() => (window.location.hash = "#/portfolio")}
        onRunBacktest={onRunBacktest}
      />

      <DecisionHistoryModal
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
        onSelectDecision={(id: string) => (window.location.hash = `#/portfolio?snapshot_id=${id}`)}
      />

      <DashboardHeader
        watchlist={symbolList}
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

      <section className="grid-12 gap-16 first-row equalize">
        <div className="col-3 col-md-12 card-slot">
          <WatchlistPanel list={symbolList} onRemove={handleRemoveFromWatchlist} />
        </div>
        <div className="col-6 col-md-12 card-slot">
          <PortfolioOverview snapshot={snapshot} keptTop5={keptTop5} onDecide={onDecide} />
        </div>
        <div className="col-3 col-md-12 card-slot">
          <QuickActions onUpdate={onBatchUpdate} />
        </div>
      </section>

      <section className="grid-12 gap-16 second-row equalize">
        <div className="col-4 col-md-12 card-slot">
          <StockScores scores={scores} />
        </div>
        <div className="col-4 col-md-12 card-slot">
          <MarketSentiment sentiment={sentiment} />
        </div>
        <div className="col-4 col-md-12 card-slot">
          <DecisionTracking latestDecision={latestDecision} onViewHistory={() => setShowHistoryModal(true)} />
        </div>
      </section>

      <DashboardFooter />
    </div>
  );
}
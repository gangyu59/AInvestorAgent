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
import { API_BASE } from "../services/endpoints";
import { aiSmartDecide } from "../services/endpoints";
import { getWatchlist } from "../services/endpoints";

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"];

export default function Dashboard() {
  const [symbols, setSymbols] = useState<string[]>([]);
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

  // ===== 首屏示例数据（按你原结构）=====
  useEffect(() => {
    async function loadWatchlist() {
      try {
        const data = await getWatchlist();
        setSymbols(data && data.length > 0 ? data : DEFAULT_SYMBOLS);
      } catch (e) {
        console.error("加载watchlist失败:", e);
        setSymbols(DEFAULT_SYMBOLS);
      }
    }
    loadWatchlist();
  }, []);

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

  // ==== 修复类型：确保 Object.entries 返回 [string, number][] ====
  const keptTop5: Array<[string, number]> = useMemo(() => {
    const weights: Record<string, number> = (snapshot && snapshot.weights) || {};
    return Object.entries(weights)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [snapshot]);

  // 添加刷新函数(供WatchlistPanel使用)
  const refreshWatchlist = async () => {
    try {
      const data = await getWatchlist();
      setSymbols(data && data.length > 0 ? data : DEFAULT_SYMBOLS);
    } catch (e) {
      console.error("刷新失败:", e);
    }
  };

  // ===== 🔧 修复：真正的智能决策函数 =====
  async function onDecide() {
    console.log("🎯 首页：开始智能决策");
    console.log("📋 使用股票列表:", symbols);

    setLoadingState({
      visible: true,
      message: "AI 正在分析市场...",
      progress: 0,
      steps: [
        "📊 拉取最新数据",
        "🧮 计算因子指标",
        "📈 综合评分",
        "⚖️ 风险检查",
        "💼 生成组合"
      ],
      currentStep: 0,
      showResult: false,
      result: null,
    });

    try {
      // 步骤 1: 模拟数据拉取
      setLoadingState(prev => ({ ...prev, currentStep: 0, progress: 20 }));
      await new Promise(r => setTimeout(r, 300));

      // 步骤 2-4: 模拟计算过程
      for (let i = 1; i < 4; i++) {
        setLoadingState(prev => ({ ...prev, currentStep: i, progress: 20 + i * 15 }));
        await new Promise(r => setTimeout(r, 300));
      }

      // 步骤 5: 调用真实 API
      setLoadingState(prev => ({ ...prev, currentStep: 4, progress: 80, message: "生成投资组合..." }));

      // console.log("📡 调用 portfolio/propose API");
      // const response = await fetch(`${API_BASE}/api/portfolio/propose`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ symbols })
      // });
      //
      // if (!response.ok) {
      //   throw new Error(`API 返回错误: ${response.status}`);
      // }
      //
      // const data = await response.json();
      // console.log("✅ 组合生成成功:", data);

      console.log("📡 调用 orchestrator/decide（LLM增强）");
      const data = await aiSmartDecide({
        symbols,
        topk: 15,
        min_score: 60,
        use_llm: true,
        params: {
          "risk.max_stock": 0.30,
          "risk.max_sector": 0.50,
          "risk.min_positions": 6,
          "risk.max_positions": 10,
        },
      });
      console.log("✅ 组合生成成功:", data);


      // 显示成功结果
      setLoadingState(prev => ({
        ...prev,
        progress: 100,
        showResult: true,
        result: {
          ok: true,
          snapshot_id: data.snapshot_id,
          holdings_count: data.holdings?.length || 0,
          message: `成功生成 ${data.holdings?.length || 0} 只股票的投资组合`
        }
      }));

      // 2秒后自动跳转
      setTimeout(() => {
        console.log("🔄 跳转到 portfolio 页面");
        // 方式1: 直接传 symbols 参数让 portfolio 页面调用 API
        window.location.hash = `#/portfolio?symbols=${encodeURIComponent(symbols.join(','))}`;

        // 方式2: 如果有 snapshot_id，直接跳转到快照
        // window.location.hash = `#/portfolio?sid=${data.snapshot_id}`;
      }, 2000);

    } catch (e: any) {
      console.error("❌ 智能决策失败:", e);
      setLoadingState(prev => ({
        ...prev,
        showResult: true,
        result: {
          ok: false,
          message: e?.message || "AI决策失败，请稍后重试"
        }
      }));
      setError(e?.message || "AI决策失败");
    }
  }

  async function onRunBacktest() {
    window.location.hash = "#/simulator?from=backtest";
  }

  function onGenerateReport() {
    const blob = new Blob(["# 报告示例"], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "report.md"; a.click();
    URL.revokeObjectURL(url);
  }

  function onBatchUpdate() {
    setLoadingState({
      visible: true, message: "一键更新数据", progress: 40,
      steps: ["📈 价格", "📰 新闻", "🧮 因子", "⭐ 评分"], currentStep: 1, showResult: false, result: null,
    });
    setTimeout(() => setLoadingState({ visible: false, message: "", progress: 0, steps: [], currentStep: 0, showResult: false, result: null }), 1200);
  }

  const handleResultClose = () => {
    setLoadingState({ visible: false, message: "", progress: 0, steps: [], currentStep: 0, showResult: false, result: null });
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
        onViewPortfolio={() => {
          // 如果有 snapshot_id，跳转到快照查看
          if (loadingState.result?.snapshot_id) {
            window.location.hash = `#/portfolio?sid=${loadingState.result.snapshot_id}`;
          } else {
            // 否则跳转到创建页面
            window.location.hash = `#/portfolio?symbols=${encodeURIComponent(symbols.join(','))}`;
          }
        }}
        onRunBacktest={onRunBacktest}
      />

      <DecisionHistoryModal
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
        onSelectDecision={(id: string) => (window.location.hash = `#/portfolio?snapshot_id=${id}`)}
      />

      <DashboardHeader
        watchlist={symbols}
        onDecide={onDecide}
        onBacktest={onRunBacktest}
        onReport={onGenerateReport}
        onUpdate={onBatchUpdate}
      />

      {errorMsg && (
        <div className="dashboard-error">
          {errorMsg}
          <button onClick={() => setError(null)} className="ml-4 text-white underline">关闭</button>
        </div>
      )}

      <section className="grid-12 gap-16 first-row equalize">
        <div className="col-3 col-md-12 card-slot">
          <WatchlistPanel list={symbols} onRefresh={refreshWatchlist}/>
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
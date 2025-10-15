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
import { aiSmartDecide, getWatchlist } from "../services/endpoints";

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"];

export default function Dashboard() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [decide, setDecide] = useState<any>(null);
  const [scores, setScores] = useState<any[]>([]);
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

  // 🔄 完整的数据加载逻辑
  useEffect(() => {
    async function loadAllData() {
      // 1. 加载watchlist
      try {
        const watchlistData = await getWatchlist();
        if (watchlistData && watchlistData.length > 0) {
          setSymbols(watchlistData);
        } else {
          setSymbols(DEFAULT_SYMBOLS);
        }
      } catch (e) {
        console.error("加载watchlist失败:", e);
        setSymbols(DEFAULT_SYMBOLS);
      }

      // 2. 加载真实的最新组合快照
      try {
        const response = await fetch(`${API_BASE}/api/portfolio/snapshots/latest`);
        if (response.ok) {
          const latestSnapshot = await response.json();
          console.log("✅ 加载最新组合成功:", latestSnapshot);
          setSnapshot({
            weights: latestSnapshot.holdings?.reduce((acc: any, h: any) => {
              acc[h.symbol] = h.weight;
              return acc;
            }, {}) || {},
            metrics: latestSnapshot.metrics || {},
            version_tag: latestSnapshot.version_tag || "v1.0",
            snapshot_id: latestSnapshot.snapshot_id
          });
        } else {
          console.log("⚠️ 暂无组合快照,使用空数据");
          setSnapshot({ weights: {}, metrics: {}, version_tag: "无数据" });
        }
      } catch (e) {
        console.error("加载组合快照失败:", e);
        setSnapshot({ weights: {}, metrics: {}, version_tag: "加载失败" });
      }

      // 3. 其他mock数据(保持不变)
      setScores([
        { symbol: "AAPL", score: { score: 82, factors: { value: 0.7, quality: 0.8, momentum: 0.6, growth: 0.9, news: 0.3 } }, as_of: "2025-01-15" },
        { symbol: "MSFT", score: { score: 78, factors: { value: 0.6, quality: 0.9, momentum: 0.7, growth: 0.8, news: 0.5 } }, as_of: "2025-01-15" },
        { symbol: "NVDA", score: { score: 85, factors: { value: 0.4, quality: 0.7, momentum: 0.9, growth: 1.0, news: 0.8 } }, as_of: "2025-01-15" },
        { symbol: "AMZN", score: { score: 75, factors: { value: 0.5, quality: 0.6, momentum: 0.8, growth: 0.7, news: 0.4 } }, as_of: "2025-01-15" },
        { symbol: "GOOGL", score: { score: 80, factors: { value: 0.8, quality: 0.8, momentum: 0.5, growth: 0.6, news: 0.6 } }, as_of: "2025-01-15" },
      ]);

      // ❌ 删除所有 setSentiment 相关代码（包括注释）
      // 不需要在这里加载sentiment，让MarketSentiment组件自己加载

      // 4. 加载最新决策
      setLatestDecision({
        date: "2025-10-01",
        holdings_count: 5,
        version_tag: "v1.2",
        performance: { today_change: 1.2, total_return: 8.5, days_since: 2 },
      });
    }

    loadAllData();
  }, []);

  // ==== 修复类型:确保 Object.entries 返回 [string, number][] ====
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

  // ===== 🔧 修复:真正的智能决策函数 =====
  // 在你的组件顶部，确保有这些状态定义
  const [isDeciding, setIsDeciding] = useState(false);

  // 完整的 onDecide 函数
  async function onDecide() {
    if (isDeciding) return;  // 防止重复点击

    console.log("🎯 首页:开始智能决策");
    console.log("📋 使用股票列表:", symbols);

    setIsDeciding(true);
    setError(null);

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
      // 步骤 1-4: 模拟进度
      for (let i = 0; i < 4; i++) {
        setLoadingState(prev => ({ ...prev, currentStep: i, progress: 20 + i * 15 }));
        await new Promise(r => setTimeout(r, 300));
      }

      // 步骤 5: 调用真实 API
      setLoadingState(prev => ({
        ...prev,
        currentStep: 4,
        progress: 80,
        message: "生成投资组合..."
      }));

      console.log("📡 调用 orchestrator/decide");
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
      console.log("✅ API返回数据:", data);

      // 优先检查API是否直接返回了holdings
      if (data.holdings && Array.isArray(data.holdings) && data.holdings.length > 0) {
        console.log("✅ API直接返回了holdings，无需查快照");
        const realHoldings = data.holdings;
        const realCount = realHoldings.length;

        setLoadingState(prev => ({
          ...prev,
          progress: 100,
          showResult: true,
          result: {
            ok: true,
            snapshot_id: data.snapshot_id || `temp-${Date.now()}`,
            holdings_count: realCount,
            message: `成功生成 ${realCount} 只股票的投资组合`,
            all_holdings: realHoldings.map((h: any) => ({
              symbol: h.symbol,
              weight: h.weight || 0,
              score: h.score || 0,
              reasons: h.reasons || [],
              sector: h.sector || h.industry || 'Technology'
            }))
          }
        }));
        setIsDeciding(false);
        return;
      }

      // 如果没有直接holdings，才查快照
      const snapshotId = data.snapshot_id;
      if (!snapshotId) {
        throw new Error("API既没有返回holdings，也没有返回快照ID");
      }

      console.log("📡 读取快照数据:", snapshotId);
      const snapshotRes = await fetch(`${API_BASE}/api/portfolio/snapshot/${snapshotId}`);
      const snapshotData = await snapshotRes.json();
      console.log("✅ 快照真实数据:", snapshotData);

      const realHoldings = snapshotData.holdings || [];
      const realCount = realHoldings.length;

      if (realCount === 0) {
        setLoadingState(prev => ({
          ...prev,
          progress: 100,
          showResult: true,
          result: {
            ok: false,
            message: "暂无符合条件的推荐股票",
            details: "可能原因：\n• 股票评分未达标\n• 约束条件过严\n• 数据暂时不可用",
            snapshot_id: snapshotId
          }
        }));
      } else {
        setLoadingState(prev => ({
          ...prev,
          progress: 100,
          showResult: true,
          result: {
            ok: true,
            snapshot_id: snapshotId,
            holdings_count: realCount,
            message: `成功生成 ${realCount} 只股票的投资组合`,
            all_holdings: realHoldings.map((h: any) => ({
              symbol: h.symbol,
              weight: h.weight,
              score: h.score || 0,
              reasons: h.reasons || [],
              sector: h.sector || h.industry || 'Technology'
            }))
          }
        }));
      }

    } catch (e: any) {
      console.error("❌ 智能决策失败:", e);
      setLoadingState(prev => ({
        ...prev,
        progress: 0,
        visible: true,
        showResult: true,
        result: {
          ok: false,
          message: e?.message || "AI决策失败,请稍后重试",
          details: e?.response?.data?.detail || e?.stack || "网络或服务器错误"
        }
      }));
      setError(e?.message || "AI决策失败");
    } finally {
      setIsDeciding(false);
    }
  }

  // 辅助函数：提取快照ID
  function extractSnapshotId(data: any): string | null {
    return data.snapshot_id || data.portfolio_id || data.id || null;
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
          if (loadingState.result?.snapshot_id) {
            window.location.hash = `#/portfolio?sid=${loadingState.result.snapshot_id}`;
          } else {
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
          <StockScores scores={scores}/>
        </div>
        <div className="col-4 col-md-12 card-slot">
          {/* ✅ 传入 symbols 参数 */}
          <MarketSentiment symbols={symbols}/>
        </div>
        <div className="col-4 col-md-12 card-slot">
          <DecisionTracking latestDecision={latestDecision} onViewHistory={() => setShowHistoryModal(true)}/>
        </div>
      </section>

      <DashboardFooter/>
    </div>
  );
}
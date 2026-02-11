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
  const [scores, setScores] = useState<any[]>([]);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [errorMsg, setError] = useState<string | null>(null);
  const [latestDecision, setLatestDecision] = useState<any>(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [isDeciding, setIsDeciding] = useState(false);

  // 🔧 简化的加载状态 - 只用于显示进度,不显示结果
  const [loadingState, setLoadingState] = useState({
    visible: false,
    message: "",
    progress: 0,
    steps: [] as string[],
    currentStep: 0,
  });

  // ✅ 步骤1: 加载watchlist
  useEffect(() => {
    async function loadWatchlist() {
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
    }
    loadWatchlist();
  }, []);

  // ✅ 步骤2: symbols变化时加载真实评分
  useEffect(() => {
    if (symbols.length === 0) return;

    async function loadScores() {
      try {
        console.log("📊 开始加载评分,股票列表:", symbols);
        const response = await fetch(`${API_BASE}/api/scores/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbols, mock: false })
        });

        if (response.ok) {
          const data = await response.json();
          console.log("✅ 真实评分数据:", data);
          setScores(data.items || []);
        } else {
          console.warn("⚠️ 评分API失败,使用空数据");
          setScores([]);
        }
      } catch (e) {
        console.error("❌ 评分加载失败:", e);
        setScores([]);
      }
    }

    loadScores();
  }, [symbols]);

  // ✅ 步骤3: 加载组合快照
  useEffect(() => {
    async function loadSnapshot() {
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
          console.log("⚠️ 暂无组合快照");
          setSnapshot({ weights: {}, metrics: {}, version_tag: "无数据" });
        }
      } catch (e) {
        console.error("加载组合快照失败:", e);
        setSnapshot({ weights: {}, metrics: {}, version_tag: "加载失败" });
      }
    }
    loadSnapshot();
  }, []);

  // ✅ 步骤4: 加载最新决策
  useEffect(() => {
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

  const refreshWatchlist = async () => {
    try {
      const data = await getWatchlist();
      setSymbols(data && data.length > 0 ? data : DEFAULT_SYMBOLS);
    } catch (e) {
      console.error("刷新失败:", e);
    }
  };

  // 🎯 核心修改:决策完成后直接跳转,不显示中间结果页
  async function onDecide() {
    if (isDeciding) return;

    console.log("🎯 首页:开始智能决策");
    console.log("📋 使用股票列表:", symbols);

    setIsDeciding(true);
    setError(null);

    // 显示加载进度
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
    });

    try {
      // 模拟进度更新
      for (let i = 0; i < 4; i++) {
        setLoadingState(prev => ({ ...prev, currentStep: i, progress: 20 + i * 15 }));
        await new Promise(r => setTimeout(r, 300));
      }

      setLoadingState(prev => ({
        ...prev,
        currentStep: 4,
        progress: 80,
        message: "生成投资组合..."
      }));

      // 调用API
      console.log("📡 调用 orchestrator/decide");
      const data = await aiSmartDecide({
        symbols,
        topk: 15,
        min_score: 40,
        use_llm: true,
        params: {
          "risk.max_stock": 0.30,
          "risk.max_sector": 0.50,
          "risk.min_positions": 4,
          "risk.max_positions": 10,
        },
      });
      console.log("✅ API返回数据:", data);

      // 🔧 关键修改:无论API返回什么,都直接跳转到portfolio页
      const snapshotId = data.snapshot_id;

      if (!snapshotId) {
        console.warn("⚠️ API未返回snapshot_id,使用symbols参数跳转");
        // 如果没有snapshot_id,用symbols参数跳转,让portfolio页自己去propose
        window.location.hash = `#/portfolio?symbols=${encodeURIComponent(symbols.join(','))}`;
      } else {
        console.log("✅ 使用snapshot_id跳转:", snapshotId);
        // 有snapshot_id,直接跳转到portfolio页显示结果
        window.location.hash = `#/portfolio?sid=${snapshotId}`;
      }

      // 关闭加载状态
      setLoadingState({
        visible: false,
        message: "",
        progress: 0,
        steps: [],
        currentStep: 0,
      });

    } catch (e: any) {
      console.error("❌ 智能决策失败:", e);

      // 显示错误信息
      setError(e?.message || "AI决策失败,请稍后重试");

      // 关闭加载状态
      setLoadingState({
        visible: false,
        message: "",
        progress: 0,
        steps: [],
        currentStep: 0,
      });

      // 3秒后清除错误信息
      setTimeout(() => setError(null), 3000);
    } finally {
      setIsDeciding(false);
    }
  }

  async function onRunBacktest() {
    // 🔧 修复: 传递当前组合数据到simulator，确保回测使用相同的holdings和权重
    if (snapshot?.snapshot_id && snapshot?.weights && Object.keys(snapshot.weights).length > 0) {
      const holdings = Object.entries(snapshot.weights as Record<string, number>).map(
        ([symbol, weight]) => ({ symbol, weight })
      );
      sessionStorage.setItem('backtestHoldings', JSON.stringify({
        holdings,
        snapshot_id: snapshot.snapshot_id,
      }));
      window.location.hash = `#/simulator?sid=${encodeURIComponent(snapshot.snapshot_id)}`;
    } else {
      window.location.hash = "#/simulator?from=backtest";
    }
  }

  function onGenerateReport() {
    const blob = new Blob(["# 报告示例"], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "report.md"; a.click();
    URL.revokeObjectURL(url);
  }

  // 📄 数据更新后的回调
  function handleDataUpdated() {
    console.log("📄 数据已更新,刷新评分...");
    // 重新加载评分
    if (symbols.length > 0) {
      fetch(`${API_BASE}/api/scores/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols, mock: false })
      })
        .then(r => r.json())
        .then(data => setScores(data.items || []))
        .catch(e => console.error("刷新评分失败:", e));
    }
  }

  return (
    <div className="dashboard-content">
      {/* 🔧 简化的LoadingOverlay - 只显示进度,不显示结果 */}
      {loadingState.visible && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md">
          <div className="max-w-md w-full mx-4 bg-gray-900 rounded-2xl shadow-2xl border border-gray-800 p-8">
            {/* 进度条 */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-400">进度</span>
                <span className="text-sm font-semibold text-blue-400">{loadingState.progress}%</span>
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${loadingState.progress}%` }}
                />
              </div>
            </div>

            {/* 当前消息 */}
            <div className="text-center mb-6">
              <div className="text-lg font-semibold text-white">{loadingState.message}</div>
            </div>

            {/* 步骤列表 */}
            {loadingState.steps.length > 0 && (
              <div className="space-y-2">
                {loadingState.steps.map((step, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center gap-3 p-2 rounded-lg transition-all ${
                      idx === loadingState.currentStep 
                        ? 'bg-blue-500/20 text-blue-400' 
                        : idx < loadingState.currentStep 
                          ? 'text-green-400' 
                          : 'text-gray-500'
                    }`}
                  >
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                      idx === loadingState.currentStep 
                        ? 'bg-blue-500/30' 
                        : idx < loadingState.currentStep 
                          ? 'bg-green-500/30' 
                          : 'bg-gray-700'
                    }`}>
                      {idx < loadingState.currentStep ? '✓' : idx + 1}
                    </div>
                    <span className="text-sm">{step}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

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
        onUpdate={handleDataUpdated}
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
          <QuickActions
            onUpdate={handleDataUpdated}
            watchlist={symbols}
          />
        </div>
      </section>

      <section className="grid-12 gap-16 second-row equalize">
        <div className="col-4 col-md-12 card-slot">
          {scores.length === 0 ? (
            <div className="dashboard-card stock-scores">
              <div className="dashboard-card-header">
                <h3 className="dashboard-card-title">股票池评分</h3>
              </div>
              <div className="dashboard-card-body" style={{textAlign: 'center', padding: '40px 20px', color: '#6b7280'}}>
                <div style={{ fontSize: '48px', marginBottom: 12, opacity: 0.3 }}>📊</div>
                <div style={{ fontSize: '14px', marginBottom: 8 }}>暂无评分数据</div>
                <div style={{ fontSize: '12px', color: '#9ca3af' }}>请先添加股票到Watchlist</div>
              </div>
            </div>
          ) : (
            <StockScores scores={scores}/>
          )}
        </div>
        <div className="col-4 col-md-12 card-slot">
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
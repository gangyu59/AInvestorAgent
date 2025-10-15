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

  const [loadingState, setLoadingState] = useState({
    visible: false,
    message: "",
    progress: 0,
    steps: [] as string[],
    currentStep: 0,
    showResult: false,
    result: null as any,
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

  async function onDecide() {
    if (isDeciding) return;

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

      if (data.holdings && Array.isArray(data.holdings) && data.holdings.length > 0) {
        console.log("✅ API直接返回了holdings,无需查快照");
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

      const snapshotId = data.snapshot_id;
      if (!snapshotId) {
        throw new Error("API既没有返回holdings,也没有返回快照ID");
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
            details: "可能原因:\n• 股票评分未达标\n• 约束条件过严\n• 数据暂时不可用",
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

  // 🔄 数据更新后的回调
  function handleDataUpdated() {
    console.log("🔄 数据已更新,刷新评分...");
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
          {/* ✅ 传递watchlist给QuickActions */}
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
// frontend/src/routes/manage.tsx
import { useEffect, useMemo, useState } from "react";

// 导入雷达图组件
import * as RadarModule from "../components/charts/RadarFactors";
const RadarFactors: any =
  (RadarModule as any).default ??
  (RadarModule as any).RadarFactors ??
  (RadarModule as any);

// ============= API 调用 =============
async function scoreBatch(symbols: string[], mock = false) {
  const resp = await fetch("/api/scores/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols, mock }),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`HTTP ${resp.status} /api/scores/batch ${text}`);
  }
  return (await resp.json()) as {
    as_of?: string;
    version_tag?: string;
    items: BatchItem[];
  };
}

async function searchSymbol(query: string) {
  try {
    const resp = await fetch(`/api/symbols?q=${encodeURIComponent(query)}`);
    if (resp.ok) {
      const data = await resp.json();
      return data.results || [];
    }
  } catch (e) {
    console.error("API搜索失败:", e);
  }

  // Fallback: 直接添加输入的代码
  return [{
    symbol: query.toUpperCase(),
    name: `${query.toUpperCase()} - 未找到详细信息`,
    sector: "未知",
    market_cap: null,
    exchange: "未知"
  }];
}

// ============= 类型定义 =============
type BatchItem = {
  symbol: string;
  factors?: {
    f_value?: number;
    f_quality?: number;
    f_momentum?: number;
    f_sentiment?: number;
    f_risk?: number;
  };
  score?: {
    value?: number;
    quality?: number;
    momentum?: number;
    sentiment?: number;
    score?: number;
    version_tag?: string;
  };
  updated_at?: string;
};

type Stock = {
  symbol: string;
  name?: string;
  sector?: string;
  addedAt?: string;
  market_cap?: number | null;
  exchange?: string;
};

type SortKey = "symbol" | "score" | "value" | "quality" | "momentum" | "sentiment" | "updated_at";

type Tab = "watchlist" | "scoring";

// ============= 辅助函数 =============
function formatMarketCap(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  return `$${value.toFixed(0)}`;
}

// ============= 主组件 =============
export default function ManagePage() {
  // Tab 切换 - 支持 URL 参数
  const [activeTab, setActiveTab] = useState<Tab>(() => {
    const params = new URLSearchParams(window.location.hash.split("?")[1]);
    const tab = params.get("tab");
    return tab === "scoring" ? "scoring" : "watchlist";
  });

  // Watchlist 管理
  const [watchlist, setWatchlist] = useState<Stock[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Stock[]>([]);
  const [searching, setSearching] = useState(false);

  // 批量评分
  const [rows, setRows] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<{ as_of?: string; version?: string } | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [asc, setAsc] = useState(false);
  const [selectedForPortfolio, setSelectedForPortfolio] = useState<string[]>([]);

  // 初始化 watchlist
  useEffect(() => {
    const stored = localStorage.getItem("watchlist");
    if (stored) {
      try {
        setWatchlist(JSON.parse(stored));
      } catch (e) {
        console.error("解析失败:", e);
        initializeDefaultWatchlist();
      }
    } else {
      initializeDefaultWatchlist();
    }
  }, []);

  function initializeDefaultWatchlist() {
    const defaultList: Stock[] = [
      { symbol: "AAPL", name: "Apple Inc.", sector: "Technology", addedAt: "2025-01-01" },
      { symbol: "MSFT", name: "Microsoft", sector: "Technology", addedAt: "2025-01-01" },
      { symbol: "NVDA", name: "NVIDIA", sector: "Technology", addedAt: "2025-01-02" },
      { symbol: "GOOGL", name: "Alphabet", sector: "Technology", addedAt: "2025-01-02" },
      { symbol: "AMZN", name: "Amazon", sector: "Consumer", addedAt: "2025-01-03" },
      { symbol: "META", name: "Meta Platforms", sector: "Technology", addedAt: "2025-01-03" },
      { symbol: "TSLA", name: "Tesla", sector: "Automotive", addedAt: "2025-01-04" },
      { symbol: "AMD", name: "AMD", sector: "Technology", addedAt: "2025-01-04" },
      { symbol: "AVGO", name: "Broadcom", sector: "Technology", addedAt: "2025-01-05" },
      { symbol: "ADBE", name: "Adobe", sector: "Technology", addedAt: "2025-01-05" },
    ];
    setWatchlist(defaultList);
    localStorage.setItem("watchlist", JSON.stringify(defaultList));
  }

  // ========== Watchlist 管理功能 ==========
  async function handleSearch() {
    if (!searchQuery.trim()) {
      alert("请输入股票代码或名称");
      return;
    }
    setSearching(true);
    setSearchResults([]);
    try {
      const results = await searchSymbol(searchQuery);
      setSearchResults(results);
      if (results.length === 0) {
        // 如果API没有结果,允许用户直接添加输入的代码
        setSearchResults([{
          symbol: searchQuery.toUpperCase(),
          name: "未找到匹配结果 - 点击添加此代码",
          sector: "未知",
          market_cap: null,
          exchange: "手动添加"
        }]);
      }
    } catch (e) {
      console.error("搜索失败:", e);
      // 错误时也允许添加
      setSearchResults([{
        symbol: searchQuery.toUpperCase(),
        name: "搜索服务暂时不可用 - 可直接添加代码",
        sector: "未知",
        market_cap: null,
        exchange: "手动添加"
      }]);
    } finally {
      setSearching(false);
    }
  }

  function addToWatchlist(stock: Stock) {
    if (watchlist.some((s) => s.symbol === stock.symbol)) {
      alert("该股票已在关注列表中");
      return;
    }

    const newStock = {
      ...stock,
      addedAt: new Date().toISOString().split("T")[0],
    };

    const newList = [...watchlist, newStock];
    setWatchlist(newList);
    localStorage.setItem("watchlist", JSON.stringify(newList));
    setSearchQuery("");
    setSearchResults([]);
  }

  function removeFromWatchlist(symbol: string) {
    if (!confirm(`确定要移除 ${symbol} 吗?`)) return;

    const newList = watchlist.filter((s) => s.symbol !== symbol);
    setWatchlist(newList);
    localStorage.setItem("watchlist", JSON.stringify(newList));
  }

  function clearWatchlist() {
    if (!confirm("确定要清空所有关注列表吗?")) return;
    setWatchlist([]);
    localStorage.removeItem("watchlist");
  }

  function exportWatchlistCSV() {
    const csv = [
      "股票代码,名称,行业,添加日期",
      ...watchlist.map((s) => `${s.symbol},${s.name || ""},${s.sector || ""},${s.addedAt || ""}`),
    ].join("\n");

    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `watchlist_${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ========== 批量评分功能 ==========
  async function loadScores() {
    const symbols = watchlist.map((s) => s.symbol);
    if (symbols.length === 0) {
      setErr("关注列表为空,请先添加股票");
      return;
    }

    setLoading(true);
    setErr(null);
    try {
      const data = await scoreBatch(symbols, false);
      const items = (data.items || []).filter(Boolean);
      items.sort((a, b) => (b.score?.score || 0) - (a.score?.score || 0));
      setRows(items);
      setInfo({ as_of: data.as_of, version: data.version_tag });
    } catch (e: any) {
      setErr(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === "scoring" && rows.length === 0 && watchlist.length > 0) {
      void loadScores();
    }
  }, [activeTab, watchlist.length]);

  const sortedRows = useMemo(() => {
    const arr = [...rows];
    const getVal = (x: BatchItem) => {
      switch (sortKey) {
        case "symbol":
          return x.symbol;
        case "updated_at":
          return x.updated_at || "";
        case "score":
          return x.score?.score ?? -Infinity;
        case "value":
          return x.score?.value ?? -Infinity;
        case "quality":
          return x.score?.quality ?? -Infinity;
        case "momentum":
          return x.score?.momentum ?? -Infinity;
        case "sentiment":
          return x.score?.sentiment ?? -Infinity;
      }
    };
    arr.sort((a, b) => {
      const va = getVal(a) as any;
      const vb = getVal(b) as any;
      if (va === vb) return 0;
      return (va > vb ? 1 : -1) * (asc ? 1 : -1);
    });
    return arr;
  }, [rows, sortKey, asc]);

  const onSort = (k: SortKey) => {
    if (sortKey === k) setAsc(!asc);
    else {
      setSortKey(k);
      setAsc(false);
    }
  };

  const toggleSelection = (sym: string) => {
    setSelectedForPortfolio((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]
    );
  };

  function goToPortfolioWithSelection() {
    if (selectedForPortfolio.length === 0) {
      alert("请先选择股票");
      return;
    }
    window.location.hash = `#/portfolio?symbols=${selectedForPortfolio.join(",")}`;
  }

  return (
    <div className="manage-page">
      {/* 页面头部 */}
      <div className="manage-header">
        <div>
          <h1 className="manage-title">📊 投资管理中心</h1>
          <p className="manage-subtitle">管理关注列表 · 批量评分 · 组合构建</p>
        </div>
        <button onClick={() => (window.location.hash = "#/")} className="btn-back">
          ← 返回首页
        </button>
      </div>

      {/* Tab 切换 */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === "watchlist" ? "active" : ""}`}
          onClick={() => setActiveTab("watchlist")}
        >
          📌 关注列表管理 ({watchlist.length})
        </button>
        <button
          className={`tab ${activeTab === "scoring" ? "active" : ""}`}
          onClick={() => setActiveTab("scoring")}
        >
          📊 批量评分分析
        </button>
      </div>

      {/* Tab 内容 */}
      <div className="tab-content">
        {activeTab === "watchlist" && (
          <WatchlistTab
            watchlist={watchlist}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchResults={searchResults}
            setSearchResults={setSearchResults}
            searching={searching}
            onSearch={handleSearch}
            onAdd={addToWatchlist}
            onRemove={removeFromWatchlist}
            onClear={clearWatchlist}
            onExport={exportWatchlistCSV}
          />
        )}

        {activeTab === "scoring" && (
          <ScoringTab
            rows={sortedRows}
            loading={loading}
            err={err}
            info={info}
            sortKey={sortKey}
            asc={asc}
            onSort={onSort}
            onRefresh={loadScores}
            selectedForPortfolio={selectedForPortfolio}
            onToggleSelection={toggleSelection}
            onGoToPortfolio={goToPortfolioWithSelection}
          />
        )}
      </div>

      <style>{`
        .manage-page {
          padding: 24px;
          max-width: 1600px;
          margin: 0 auto;
          color: white;
        }

        .manage-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
          padding-bottom: 20px;
          border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }

        .manage-title {
          font-size: 32px;
          font-weight: 700;
          margin: 0 0 8px 0;
        }

        .manage-subtitle {
          color: rgba(255, 255, 255, 0.6);
          margin: 0;
          font-size: 14px;
        }

        .btn-back {
          padding: 10px 20px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          color: white;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 14px;
        }

        .btn-back:hover {
          background: rgba(255, 255, 255, 0.15);
          transform: translateX(-2px);
        }

        .tabs {
          display: flex;
          gap: 8px;
          margin-bottom: 24px;
          border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }

        .tab {
          padding: 12px 24px;
          background: transparent;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          cursor: pointer;
          font-size: 15px;
          font-weight: 500;
          position: relative;
          transition: all 0.2s;
          border-bottom: 3px solid transparent;
        }

        .tab:hover {
          color: rgba(255, 255, 255, 0.9);
          background: rgba(255, 255, 255, 0.05);
        }

        .tab.active {
          color: white;
          border-bottom-color: #3b82f6;
        }

        .tab-content {
          min-height: 500px;
        }

        @media (max-width: 768px) {
          .manage-page {
            padding: 16px;
          }

          .manage-header {
            flex-direction: column;
            gap: 16px;
            align-items: flex-start;
          }

          .tabs {
            overflow-x: auto;
          }

          .tab {
            flex-shrink: 0;
          }
        }
      `}</style>
    </div>
  );
}

// ============= Watchlist Tab =============
function WatchlistTab({
  watchlist,
  searchQuery,
  setSearchQuery,
  searchResults,
  setSearchResults,
  searching,
  onSearch,
  onAdd,
  onRemove,
  onClear,
  onExport,
}: {
  watchlist: Stock[];
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  searchResults: Stock[];
  setSearchResults: (results: Stock[]) => void;
  searching: boolean;
  onSearch: () => void;
  onAdd: (s: Stock) => void;
  onRemove: (sym: string) => void;
  onClear: () => void;
  onExport: () => void;
}) {
  const [filterSector, setFilterSector] = useState<string>("all");

  const sectors = useMemo(() => {
    const unique = new Set(watchlist.map((s) => s.sector).filter((sector): sector is string => Boolean(sector)));
    return ["all", ...Array.from(unique)];
  }, [watchlist]);

  const filteredWatchlist = useMemo(() => {
    if (filterSector === "all") return watchlist;
    return watchlist.filter((s) => s.sector === filterSector);
  }, [watchlist, filterSector]);

  return (
    <div className="watchlist-tab">
      {/* 搜索区域 - 紧凑设计 */}
      <div className="search-section">
        <div className="search-bar">
          <input
            type="text"
            placeholder="搜索股票代码或名称..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && onSearch()}
            className="search-input-compact"
          />
          <button onClick={onSearch} disabled={searching} className="btn-search-compact">
            {searching ? "..." : "搜索"}
          </button>
        </div>

        {/* 搜索结果 - 增强信息展示 */}
        {searchResults.length > 0 && (
          <div className="search-results-compact">
            <div className="results-header">
              找到 {searchResults.length} 个结果
              <button
                onClick={() => setSearchResults([])}
                className="btn-clear-results"
              >
                清除结果
              </button>
            </div>
            <div className="results-list">
              {searchResults.map((stock, idx) => {
                const alreadyAdded = watchlist.some((s) => s.symbol === stock.symbol);
                return (
                  <div key={`${stock.symbol}-${idx}`} className="result-row-enhanced">
                    <div className="result-main">
                      <div className="result-header-row">
                        <span className="result-symbol-large">{stock.symbol}</span>
                        {stock.exchange && (
                          <span className="exchange-badge">{stock.exchange}</span>
                        )}
                        {alreadyAdded && (
                          <span className="already-added-badge">已添加</span>
                        )}
                      </div>
                      <div className="result-name-large">{stock.name || "无公司名称"}</div>
                      <div className="result-details">
                        {stock.sector && (
                          <span className="detail-item">
                            <span className="detail-label">行业:</span>
                            <span className="detail-value">{stock.sector}</span>
                          </span>
                        )}
                        {stock.market_cap && (
                          <span className="detail-item">
                            <span className="detail-label">市值:</span>
                            <span className="detail-value">{formatMarketCap(stock.market_cap)}</span>
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => onAdd(stock)}
                      className={`btn-add-large ${alreadyAdded ? 'disabled' : ''}`}
                      disabled={alreadyAdded}
                    >
                      {alreadyAdded ? '✓ 已添加' : '+ 添加'}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 工具栏 */}
      <div className="toolbar">
        <div className="toolbar-left">
          <h3 className="toolbar-title">当前关注 ({watchlist.length}支)</h3>
          <div className="sector-filters-compact">
            {sectors.map((sector) => (
              <button
                key={sector}
                onClick={() => setFilterSector(sector)}
                className={`filter-chip ${filterSector === sector ? "active" : ""}`}
              >
                {sector === "all" ? "全部" : sector}
              </button>
            ))}
          </div>
        </div>
        <div className="toolbar-right">
          <button onClick={onExport} className="btn-tool" disabled={watchlist.length === 0}>
            导出
          </button>
          <button onClick={onClear} className="btn-tool btn-danger" disabled={watchlist.length === 0}>
            清空
          </button>
        </div>
      </div>

      {/* 列表 - 专业紧凑表格 */}
      {filteredWatchlist.length === 0 ? (
        <div className="empty-compact">
          <div style={{ fontSize: 40, opacity: 0.3, marginBottom: 12 }}>📭</div>
          <p style={{ margin: 0, color: "rgba(255,255,255,0.5)" }}>暂无股票</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="compact-table">
            <thead>
              <tr>
                <th style={{ width: "15%" }}>代码</th>
                <th style={{ width: "30%" }}>名称</th>
                <th style={{ width: "20%" }}>行业</th>
                <th style={{ width: "20%" }}>添加日期</th>
                <th style={{ width: "15%", textAlign: "center" }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredWatchlist.map((stock) => (
                <tr key={stock.symbol}>
                  <td>
                    <span className="symbol-text">{stock.symbol}</span>
                  </td>
                  <td>{stock.name || "--"}</td>
                  <td>
                    {stock.sector && (
                      <span className="sector-pill">{stock.sector}</span>
                    )}
                  </td>
                  <td style={{ color: "rgba(255,255,255,0.5)", fontSize: 13 }}>
                    {stock.addedAt || "--"}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <div className="action-btns">
                      <button
                        onClick={() => (window.location.hash = `#/stock?query=${stock.symbol}`)}
                        className="btn-action btn-view"
                        title="查看详情"
                      >
                        详情
                      </button>
                      <button
                        onClick={() => onRemove(stock.symbol)}
                        className="btn-action btn-delete"
                        title="移除"
                      >
                        ×
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`
        .watchlist-tab {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        /* 搜索区域 */
        .search-section {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 16px;
        }

        .search-bar {
          display: flex;
          gap: 10px;
        }

        .search-input-compact {
          flex: 1;
          padding: 10px 14px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 6px;
          color: white;
          font-size: 14px;
        }

        .search-input-compact:focus {
          outline: none;
          border-color: #3b82f6;
        }

        .btn-search-compact {
          padding: 10px 24px;
          background: #3b82f6;
          border: none;
          color: white;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          font-size: 14px;
        }

        .btn-search-compact:hover:not(:disabled) {
          background: #2563eb;
        }

        .btn-search-compact:disabled {
          opacity: 0.5;
        }

        .search-results-compact {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .results-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 13px;
          color: rgba(255, 255, 255, 0.6);
          margin-bottom: 12px;
        }

        .btn-clear-results {
          padding: 4px 12px;
          background: rgba(239, 68, 68, 0.15);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #ef4444;
          border-radius: 4px;
          cursor: pointer;
          font-size: 11px;
          transition: all 0.2s;
        }

        .btn-clear-results:hover {
          background: rgba(239, 68, 68, 0.25);
        }

        .results-list {
          max-height: 400px;
          overflow-y: auto;
        }

        .result-row-enhanced {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          padding: 14px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 8px;
          margin-bottom: 10px;
          transition: all 0.2s;
        }

        .result-row-enhanced:hover {
          background: rgba(255, 255, 255, 0.06);
          border-color: rgba(255, 255, 255, 0.15);
        }

        .result-main {
          flex: 1;
          min-width: 0;
        }

        .result-header-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
          flex-wrap: wrap;
        }

        .result-symbol-large {
          font-family: 'Roboto Mono', monospace;
          font-weight: 700;
          color: #60a5fa;
          font-size: 18px;
        }

        .exchange-badge {
          padding: 2px 8px;
          background: rgba(168, 85, 247, 0.2);
          color: #a78bfa;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 500;
        }

        .already-added-badge {
          padding: 2px 8px;
          background: rgba(34, 197, 94, 0.2);
          color: #22c55e;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 500;
        }

        .result-name-large {
          color: rgba(255, 255, 255, 0.9);
          font-size: 14px;
          margin-bottom: 8px;
          line-height: 1.4;
        }

        .result-details {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
        }

        .detail-item {
          display: flex;
          gap: 6px;
          font-size: 12px;
        }

        .detail-label {
          color: rgba(255, 255, 255, 0.5);
        }

        .detail-value {
          color: rgba(255, 255, 255, 0.8);
          font-weight: 500;
        }

        .btn-add-large {
          padding: 10px 20px;
          background: rgba(34, 197, 94, 0.2);
          border: 1px solid rgba(34, 197, 94, 0.4);
          color: #22c55e;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 600;
          white-space: nowrap;
          transition: all 0.2s;
          flex-shrink: 0;
        }

        .btn-add-large:hover:not(.disabled) {
          background: rgba(34, 197, 94, 0.3);
          transform: translateY(-1px);
        }

        .btn-add-large.disabled {
          background: rgba(255, 255, 255, 0.05);
          border-color: rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.4);
          cursor: not-allowed;
        }

        /* 工具栏 */
        .toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }

        .toolbar-left {
          display: flex;
          align-items: center;
          gap: 16px;
          flex-wrap: wrap;
        }

        .toolbar-title {
          font-size: 18px;
          font-weight: 600;
          margin: 0;
          color: white;
        }

        .sector-filters-compact {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }

        .filter-chip {
          padding: 5px 12px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.6);
          border-radius: 14px;
          cursor: pointer;
          font-size: 12px;
          transition: all 0.15s;
        }

        .filter-chip:hover {
          background: rgba(255, 255, 255, 0.08);
          color: rgba(255, 255, 255, 0.9);
        }

        .filter-chip.active {
          background: #3b82f6;
          border-color: #3b82f6;
          color: white;
        }

        .toolbar-right {
          display: flex;
          gap: 8px;
        }

        .btn-tool {
          padding: 8px 16px;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.15);
          color: white;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
          transition: all 0.15s;
        }

        .btn-tool:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.12);
        }

        .btn-tool:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }

        .btn-danger {
          border-color: rgba(239, 68, 68, 0.3);
          color: #ef4444;
        }

        .btn-danger:hover:not(:disabled) {
          background: rgba(239, 68, 68, 0.15);
        }

        /* 紧凑表格 */
        .table-wrapper {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          overflow: hidden;
        }

        .compact-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }

        .compact-table thead {
          background: rgba(255, 255, 255, 0.05);
        }

        .compact-table th {
          padding: 12px 16px;
          text-align: left;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.9);
          font-size: 13px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .compact-table td {
          padding: 12px 16px;
          color: rgba(255, 255, 255, 0.8);
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .compact-table tbody tr:hover {
          background: rgba(255, 255, 255, 0.03);
        }

        .compact-table tbody tr:last-child td {
          border-bottom: none;
        }

        .symbol-text {
          font-family: 'Roboto Mono', monospace;
          font-weight: 600;
          color: #60a5fa;
          font-size: 15px;
        }

        .sector-pill {
          display: inline-block;
          padding: 3px 10px;
          background: rgba(139, 92, 246, 0.15);
          color: #a78bfa;
          border-radius: 12px;
          font-size: 12px;
        }

        .action-btns {
          display: flex;
          gap: 6px;
          justify-content: center;
        }

        .btn-action {
          padding: 5px 12px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          transition: all 0.15s;
        }

        .btn-view {
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
        }

        .btn-view:hover {
          background: rgba(59, 130, 246, 0.25);
        }

        .btn-delete {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
          font-size: 18px;
          padding: 5px 10px;
          font-weight: 600;
        }

        .btn-delete:hover {
          background: rgba(239, 68, 68, 0.25);
        }

        .empty-compact {
          text-align: center;
          padding: 60px 20px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
        }

        @media (max-width: 768px) {
          .toolbar {
            flex-direction: column;
            align-items: flex-start;
          }

          .toolbar-right {
            width: 100%;
          }

          .btn-tool {
            flex: 1;
          }

          .table-wrapper {
            overflow-x: auto;
          }

          .compact-table {
            min-width: 600px;
          }
        }
      `}</style>
    </div>
  );
}

// ============= Scoring Tab (省略,与之前相同) =============
function ScoringTab({
  rows,
  loading,
  err,
  info,
  sortKey,
  asc,
  onSort,
  onRefresh,
  selectedForPortfolio,
  onToggleSelection,
  onGoToPortfolio,
}: {
  rows: BatchItem[];
  loading: boolean;
  err: string | null;
  info: { as_of?: string; version?: string } | null;
  sortKey: SortKey;
  asc: boolean;
  onSort: (k: SortKey) => void;
  onRefresh: () => void;
  selectedForPortfolio: string[];
  onToggleSelection: (sym: string) => void;
  onGoToPortfolio: () => void;
}) {
  return (
    <div className="scoring-tab">
      <div className="scoring-header">
        <div>
          <h2 className="section-title">📊 批量评分分析</h2>
          {info && (
            <div className="info-text">
              数据时间: {info.as_of || "--"} · 版本: {info.version || "--"}
            </div>
          )}
        </div>
        <div className="actions">
          {selectedForPortfolio.length > 0 && (
            <button onClick={onGoToPortfolio} className="btn-portfolio">
              🎯 生成组合 ({selectedForPortfolio.length}支)
            </button>
          )}
          <button onClick={onRefresh} disabled={loading} className="btn-refresh">
            {loading ? "加载中..." : "🔄 刷新评分"}
          </button>
        </div>
      </div>

      {err && (
        <div className="error-box">
          ⚠️ {err}
        </div>
      )}

      {rows.length === 0 && !loading && !err && (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <p>暂无评分数据</p>
          <p className="empty-hint">请先在"关注列表管理"中添加股票</p>
        </div>
      )}

      {rows.length > 0 && (
        <div className="table-container">
          <table className="score-table">
            <thead>
              <tr>
                <Th onClick={() => onSort("symbol")} label="代码" active={sortKey === "symbol"} asc={asc} />
                <Th onClick={() => onSort("score")} label="总分" active={sortKey === "score"} asc={asc} />
                <th className="th">迷你雷达</th>
                <Th onClick={() => onSort("value")} label="价值" active={sortKey === "value"} asc={asc} />
                <Th onClick={() => onSort("quality")} label="质量" active={sortKey === "quality"} asc={asc} />
                <Th onClick={() => onSort("momentum")} label="动量" active={sortKey === "momentum"} asc={asc} />
                <Th onClick={() => onSort("sentiment")} label="情绪" active={sortKey === "sentiment"} asc={asc} />
                <Th onClick={() => onSort("updated_at")} label="更新时间" active={sortKey === "updated_at"} asc={asc} />
                <th className="th">版本</th>
                <th className="th">详情</th>
                <th className="th">组合</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const s = r.score || {};
                const radar = {
                  value: (r.factors?.f_value ?? s.value ?? 0) / 100,
                  quality: (r.factors?.f_quality ?? s.quality ?? 0) / 100,
                  momentum: (r.factors?.f_momentum ?? s.momentum ?? 0) / 100,
                  sentiment: (r.factors?.f_sentiment ?? s.sentiment ?? 0) / 100,
                  risk: (r.factors?.f_risk ?? 0) / 100,
                };
                const updated = r.updated_at || info?.as_of || "--";
                const version = s.version_tag || info?.version || "--";
                const isSelected = selectedForPortfolio.includes(r.symbol);

                return (
                  <tr key={r.symbol} className={isSelected ? "selected-row" : ""}>
                    <td className="td td-symbol">{r.symbol}</td>
                    <td className="td td-score">{fmtNum(s.score, 1, "--")}</td>
                    <td className="td">
                      <div style={{ width: 84, height: 72 }}>
                        <RadarFactors data={radar} mini />
                      </div>
                    </td>
                    <td className="td">{fmtNum(s.value, 1, "--")}</td>
                    <td className="td">{fmtNum(s.quality, 1, "--")}</td>
                    <td className="td">{fmtNum(s.momentum, 1, "--")}</td>
                    <td className="td">{fmtNum(s.sentiment, 1, "--")}</td>
                    <td className="td">{updated}</td>
                    <td className="td">{version}</td>
                    <td className="td">
                      <a href={`#/stock?query=${r.symbol}`} className="link">
                        查看
                      </a>
                    </td>
                    <td className="td">
                      <button
                        onClick={() => onToggleSelection(r.symbol)}
                        className={`btn-select ${isSelected ? "selected" : ""}`}
                      >
                        {isSelected ? "✓ 已选" : "加入"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <style>{`
        .scoring-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .section-title {
          font-size: 20px;
          font-weight: 600;
          margin: 0 0 8px 0;
        }

        .info-text {
          color: rgba(255, 255, 255, 0.5);
          font-size: 13px;
          margin-top: 8px;
        }

        .actions {
          display: flex;
          gap: 12px;
        }

        .btn-portfolio {
          padding: 10px 20px;
          background: rgba(34, 197, 94, 0.2);
          border: 1px solid rgba(34, 197, 94, 0.4);
          color: #22c55e;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          transition: all 0.2s;
        }

        .btn-portfolio:hover {
          background: rgba(34, 197, 94, 0.3);
          transform: translateY(-1px);
        }

        .btn-refresh {
          padding: 10px 20px;
          background: rgba(59, 130, 246, 0.2);
          border: 1px solid rgba(59, 130, 246, 0.4);
          color: #60a5fa;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          transition: all 0.2s;
        }

        .btn-refresh:hover:not(:disabled) {
          background: rgba(59, 130, 246, 0.3);
        }

        .btn-refresh:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .error-box {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #ef4444;
          padding: 16px;
          border-radius: 8px;
          margin-bottom: 20px;
        }

        .table-container {
          overflow-x: auto;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 16px;
        }

        .score-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }

        .th {
          text-align: left;
          padding: 12px 8px;
          border-bottom: 2px solid rgba(255, 255, 255, 0.2);
          font-weight: 600;
          color: rgba(255, 255, 255, 0.9);
          white-space: nowrap;
          cursor: pointer;
          user-select: none;
          transition: color 0.2s;
        }

        .th:hover {
          color: #60a5fa;
        }

        .td {
          padding: 12px 8px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          color: rgba(255, 255, 255, 0.8);
        }

        .td-symbol {
          font-family: 'Roboto Mono', monospace;
          font-weight: 600;
          color: #60a5fa;
          font-size: 15px;
        }

        .td-score {
          font-weight: 700;
          color: white;
          font-size: 16px;
        }

        .selected-row {
          background: rgba(34, 197, 94, 0.1);
        }

        .link {
          color: #60a5fa;
          text-decoration: underline;
          cursor: pointer;
          transition: color 0.2s;
        }

        .link:hover {
          color: #93c5fd;
        }

        .btn-select {
          padding: 6px 14px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
          transition: all 0.2s;
          background: rgba(59, 130, 246, 0.2);
          border: 1px solid rgba(59, 130, 246, 0.4);
          color: #60a5fa;
        }

        .btn-select:hover {
          background: rgba(59, 130, 246, 0.3);
        }

        .btn-select.selected {
          background: rgba(34, 197, 94, 0.3);
          border-color: rgba(34, 197, 94, 0.5);
          color: #22c55e;
        }

        .empty-state {
          text-align: center;
          padding: 80px 20px;
        }

        .empty-icon {
          font-size: 72px;
          margin-bottom: 20px;
          opacity: 0.4;
        }

        .empty-hint {
          color: rgba(255, 255, 255, 0.5);
          font-size: 14px;
          margin-top: 8px;
        }

        @media (max-width: 1024px) {
          .scoring-header {
            flex-direction: column;
            gap: 16px;
            align-items: flex-start;
          }

          .actions {
            width: 100%;
            flex-direction: column;
          }

          .btn-portfolio,
          .btn-refresh {
            width: 100%;
          }

          .table-container {
            overflow-x: scroll;
          }

          .score-table {
            min-width: 1000px;
          }
        }
      `}</style>
    </div>
  );
}

// ============= 辅助组件 =============
function Th({
  onClick,
  label,
  active,
  asc,
}: {
  onClick: () => void;
  label: string;
  active?: boolean;
  asc?: boolean;
}) {
  return (
    <th
      onClick={onClick}
      className="th"
      style={{
        color: active ? "#60a5fa" : undefined,
      }}
      title="点击排序"
    >
      {label} {active ? (asc ? "↑" : "↓") : ""}
    </th>
  );
}

function fmtNum(v?: number, d = 1, fallback = "--") {
  if (v === undefined || v === null || Number.isNaN(v)) return fallback;
  return Number(v).toFixed(d);
}
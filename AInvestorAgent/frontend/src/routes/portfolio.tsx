// frontend/src/routes/portfolio.tsx
import { useEffect, useMemo, useState } from "react";
import WeightsPie from "../components/charts/WeightsPie";
import SectorBars from "../components/charts/SectorBars";
import HoldingsTable from "../components/tables/HoldingsTable";
import { API_BASE } from "../services/endpoints";

type Holding = {
  symbol: string;
  weight: number;
  score: number;
  sector?: string;
  reasons?: string[]
};

type Metrics = {
  ann_return?: number;
  mdd?: number;
  sharpe?: number;
  winrate?: number;
};

type Resp = {
  holdings: Holding[];
  sector_concentration: [string, number][];
  as_of: string;
  version_tag: string;
  snapshot_id: string;
  metrics?: Metrics;
};

const PROPOSE_URL = (API_BASE ? `${API_BASE}` : "") + "/api/portfolio/propose";
const SNAPSHOT_URL = (API_BASE ? `${API_BASE}` : "") + "/api/portfolio/snapshots";

export default function PortfolioPage() {
  // 默认股票池
  const DEFAULT_POOL = "AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AVGO, COST, LLY";

  const [pool, setPool] = useState(DEFAULT_POOL);
  const [resp, setResp] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<'create' | 'view'>('create');

  // 数据派生
  const pieData = useMemo(
    () => (resp?.holdings || []).map(h => ({ symbol: h.symbol, weight: h.weight })),
    [resp]
  );

  const sectorDist = useMemo(() => {
    const obj: Record<string, number> = {};
    (resp?.sector_concentration || []).forEach(([s, w]) => { obj[s] = w; });
    return obj;
  }, [resp]);

  const holdingsCount = resp?.holdings?.length || 0;

  // 🔧 修复：在组件挂载后立即检查 URL 参数
  useEffect(() => {
    console.log("🔍 Portfolio 页面加载，检查 URL...");

    // 读取 URL 参数
    const hash = window.location.hash || "";
    const i = hash.indexOf("?");

    if (i < 0) {
      console.log("📌 无 URL 参数，等待用户输入");
      return;
    }

    const sp = new URLSearchParams(hash.slice(i + 1));
    const symbols = sp.get("symbols") || "";
    const sid = sp.get("sid") || "";

    console.log("📋 URL 参数:", { symbols, sid });

    if (sid) {
      // 从快照加载
      console.log("📂 从快照加载:", sid);
      setMode('view');
      loadSnapshot(sid);
    } else if (symbols) {
      // 从 symbols 生成
      console.log("🎯 从股票列表生成组合:", symbols);
      setPool(symbols); // 更新输入框
      const list = symbols.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
      if (list.length > 0) {
        onPropose(list);
      }
    } else {
      console.log("⚠️ URL 参数不完整");
    }
  }, [window.location.hash]); // 依赖 hash 变化

  // 加载已有快照
  async function loadSnapshot(sid: string) {
    setLoading(true);
    setErr(null);

    try {
      console.log("📡 加载快照:", `${SNAPSHOT_URL}/${sid}`);
      const r = await fetch(`${SNAPSHOT_URL}/${sid}`);
      if (!r.ok) throw new Error(`加载快照失败: HTTP ${r.status}`);
      const data: Resp = await r.json();
      console.log("✅ 快照数据:", data);
      setResp(data);
    } catch (e: any) {
      console.error("❌ 加载快照失败:", e);
      setErr(e?.message || "加载快照失败");
    } finally {
      setLoading(false);
    }
  }

  // 智能决策：生成新组合
  async function onPropose(list?: string[]) {
    const symbols = (list && list.length)
      ? list
      : pool.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);

    console.log("🎯 开始智能决策，股票列表:", symbols);

    if (!symbols.length) {
      setErr("请输入至少一只股票");
      return;
    }

    setLoading(true);
    setErr(null);
    setMode('create');

    try {
      console.log("📡 调用 API:", PROPOSE_URL);
      console.log("📦 请求数据:", { symbols });

      const r = await fetch(PROPOSE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols }),
      });

      console.log("📨 响应状态:", r.status, r.statusText);

      if (!r.ok) {
        const errorText = await r.text();
        console.error("❌ API 错误响应:", errorText);
        throw new Error(`HTTP ${r.status}: ${errorText}`);
      }

      const data: Resp = await r.json();
      console.log("✅ 获取到数据:", data);

      setResp(data);

      if (!data.holdings || data.holdings.length === 0) {
        setErr("⚠️ API 返回成功但没有持仓数据");
      }
    } catch (e: any) {
      console.error("❌ 智能决策失败:", e);
      setErr(e?.message || "生成失败");
    } finally {
      setLoading(false);
    }
  }

  // 导出 CSV
  function exportCSV() {
    if (!resp?.holdings?.length) return;

    const rows = [
      ["Symbol", "Sector", "Score", "Weight", "Reasons"],
      ...resp.holdings.map(h => [
        h.symbol,
        h.sector || "",
        (h.score ?? "").toString(),
        (h.weight * 100).toFixed(4) + "%",
        (h.reasons || []).join("|")
      ])
    ];

    const csv = rows
      .map(r => r.map(x => `"${String(x).replace(/"/g, '""')}"`).join(","))
      .join("\r\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `portfolio_${new Date().toISOString().replace(/[:T]/g, "-").slice(0, 16)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  // 跳转回测
  function goToBacktest() {
    if (!resp?.holdings?.length) {
      alert("当前无有效持仓，请先生成组合。");
      return;
    }

    console.log("🔄 跳转回测，持仓数量:", resp.holdings.length);
    console.log("📦 持仓详情:", resp.holdings);

    // 把 holdings 数据存到 sessionStorage
    sessionStorage.setItem('backtestHoldings', JSON.stringify({
      holdings: resp.holdings.map(h => ({
        symbol: h.symbol,
        weight: h.weight
      })),
      snapshot_id: resp.snapshot_id,
      as_of: resp.as_of
    }));

    // 跳转到 simulator 页面
    window.location.hash = `#/simulator?sid=${encodeURIComponent(resp.snapshot_id)}`;
  }

  // 切换模式
  function switchToCreateMode() {
    setMode('create');
    setResp(null);
    setPool(DEFAULT_POOL);
    window.location.hash = '#/portfolio';
  }

  return (
    <div className="page">
      {/* 页面头部 */}
      <div className="page-header" style={{ gap: 8, alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ marginBottom: 8 }}>
            💼 投资组合
            {mode === 'view' && (
              <span style={{ fontSize: 14, color: '#888', marginLeft: 12 }}>
                (查看快照)
              </span>
            )}
          </h2>

          {mode === 'create' && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                value={pool}
                onChange={e => setPool(e.currentTarget.value)}
                style={{ minWidth: 420, flex: 1 }}
                placeholder="用逗号或空格分隔股票，如：AAPL, MSFT, TSLA"
              />
              <button
                className="btn btn-primary"
                onClick={() => onPropose()}
                disabled={loading}
              >
                {loading ? "🤖 AI决策中…" : "🎯 智能决策"}
              </button>
            </div>
          )}

          {mode === 'view' && (
            <button
              className="btn btn-secondary"
              onClick={switchToCreateMode}
            >
              ➕ 创建新组合
            </button>
          )}
        </div>

        {/* 右侧操作按钮 */}
        {resp && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn"
              onClick={exportCSV}
              disabled={!resp?.holdings?.length}
              title="导出为 CSV 文件"
            >
              📥 导出
            </button>
            <button
              className="btn btn-primary"
              onClick={goToBacktest}
              disabled={!resp?.snapshot_id}
              title="用此组合进行回测"
            >
              📊 回测
            </button>
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b", backgroundColor: "#fff5f5" }}>
          <div className="card-body" style={{ color: "#c92a2a" }}>
            ⚠️ {err}
          </div>
        </div>
      )}

      {/* 加载状态 */}
      {loading && !resp && (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 40 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
            <div style={{ color: '#888' }}>AI 正在分析市场数据，生成最优组合...</div>
          </div>
        </div>
      )}

      {/* 主要内容 */}
      {resp && (
        <>
          {/* 组合概览卡片 */}
          <div className="card" style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            marginBottom: 16,
            border: 'none',
            boxShadow: '0 10px 30px rgba(102, 126, 234, 0.3)'
          }}>
            <div className="card-body" style={{ padding: '24px' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: 20
              }}>
                <div style={{
                  padding: '12px',
                  background: 'rgba(255, 255, 255, 0.15)',
                  borderRadius: '8px',
                  backdropFilter: 'blur(10px)'
                }}>
                  <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 8 }}>📊 持仓数量</div>
                  <div style={{ fontSize: 32, fontWeight: 'bold' }}>{holdingsCount}</div>
                  <div style={{ fontSize: 11, opacity: 0.8, marginTop: 4 }}>
                    {holdingsCount >= 5 && holdingsCount <= 15 ? '✓ 适度分散' : '⚠️ 注意分散度'}
                  </div>
                </div>

                {resp.metrics?.ann_return != null && (
                  <div style={{
                    padding: '12px',
                    background: 'rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    backdropFilter: 'blur(10px)'
                  }}>
                    <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 8 }}>📈 年化收益</div>
                    <div style={{ fontSize: 32, fontWeight: 'bold' }}>
                      {(resp.metrics.ann_return * 100).toFixed(2)}%
                    </div>
                    <div style={{ fontSize: 11, opacity: 0.8, marginTop: 4 }}>
                      {resp.metrics.ann_return > 0.15 ? '🔥 优秀' :
                       resp.metrics.ann_return > 0.08 ? '✓ 良好' : '⚠️ 需改进'}
                    </div>
                  </div>
                )}

                {resp.metrics?.sharpe != null && (
                  <div style={{
                    padding: '12px',
                    background: 'rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    backdropFilter: 'blur(10px)'
                  }}>
                    <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 8 }}>⚖️ 夏普比率</div>
                    <div style={{ fontSize: 32, fontWeight: 'bold' }}>
                      {resp.metrics.sharpe.toFixed(2)}
                    </div>
                    <div style={{ fontSize: 11, opacity: 0.8, marginTop: 4 }}>
                      {resp.metrics.sharpe > 1.5 ? '🔥 卓越' :
                       resp.metrics.sharpe > 1.0 ? '✓ 优秀' :
                       resp.metrics.sharpe > 0.5 ? '✓ 合格' : '⚠️ 需优化'}
                    </div>
                  </div>
                )}

                {resp.metrics?.mdd != null && (
                  <div style={{
                    padding: '12px',
                    background: 'rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    backdropFilter: 'blur(10px)'
                  }}>
                    <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 8 }}>📉 最大回撤</div>
                    <div style={{ fontSize: 32, fontWeight: 'bold' }}>
                      {(resp.metrics.mdd * 100).toFixed(2)}%
                    </div>
                    <div style={{ fontSize: 11, opacity: 0.8, marginTop: 4 }}>
                      {Math.abs(resp.metrics.mdd) < 0.10 ? '✓ 风险低' :
                       Math.abs(resp.metrics.mdd) < 0.20 ? '✓ 可接受' : '⚠️ 高风险'}
                    </div>
                  </div>
                )}

                <div style={{
                  padding: '12px',
                  background: 'rgba(255, 255, 255, 0.15)',
                  borderRadius: '8px',
                  backdropFilter: 'blur(10px)'
                }}>
                  <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 8 }}>🏷️ 版本</div>
                  <div style={{ fontSize: 24, fontWeight: 'bold', fontFamily: 'monospace' }}>
                    {resp.version_tag || 'v1.0'}
                  </div>
                  <div style={{ fontSize: 11, opacity: 0.8, marginTop: 4 }}>
                    {resp.as_of ? new Date(resp.as_of).toLocaleDateString() : '今天'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 图表区域：权重饼图 + 行业集中度 */}
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="card">
              <div className="card-header">
                <h3>📊 权重分布</h3>
              </div>
              <div className="card-body">
                <WeightsPie data={pieData} />
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3>🏢 行业集中度</h3>
              </div>
              <div className="card-body">
                <SectorBars sectorDist={sectorDist} />
              </div>
            </div>
          </div>

          {/* 持仓明细表 */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <h3>📋 持仓明细</h3>
              <span style={{ fontSize: 14, color: '#888' }}>
                共 {holdingsCount} 只股票
              </span>
            </div>
            <div className="card-body">
              <HoldingsTable
                rows={(resp.holdings || []).map(h => ({
                  symbol: h.symbol,
                  sector: h.sector,
                  score: h.score,
                  weight: h.weight,
                  reasons: h.reasons || []
                }))}
              />
            </div>
          </div>

          {/* 页面底部元信息 */}
          <div style={{
            fontSize: 12,
            color: '#888',
            textAlign: 'center',
            padding: '16px 0',
            borderTop: '1px solid #e5e7eb'
          }}>
            <div>数据更新时间: {resp.as_of || new Date().toLocaleString()}</div>
            <div style={{ marginTop: 4 }}>
              快照ID: <code style={{
                background: '#f3f4f6',
                padding: '2px 6px',
                borderRadius: '4px',
                fontFamily: 'monospace'
              }}>
                {resp.snapshot_id || '—'}
              </code>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
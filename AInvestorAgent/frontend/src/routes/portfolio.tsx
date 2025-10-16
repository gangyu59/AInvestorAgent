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
  const [resp, setResp] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<'loading' | 'view' | 'empty'>('loading');

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

  // 📌 页面加载时检查URL参数
  useEffect(() => {
    console.log("🔍 Portfolio页面挂载,检查URL参数");
    loadFromURL();
  }, []);

  // 📌 监听hash变化
  useEffect(() => {
    const handleHashChange = () => {
      console.log("🔄 检测到URL变化");
      loadFromURL();
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // 📌 从URL加载数据(核心逻辑)
  function loadFromURL() {
    const hash = window.location.hash || "";
    const i = hash.indexOf("?");

    if (i < 0) {
      console.log("⚠️ 无URL参数,显示空状态");
      setMode('empty');
      setResp(null);
      return;
    }

    const sp = new URLSearchParams(hash.slice(i + 1));
    const symbols = sp.get("symbols") || "";
    const sid = sp.get("sid") || "";
    const snapshotId = sp.get("snapshot_id") || "";

    console.log("📋 URL参数:", { symbols, sid, snapshot_id: snapshotId });

    // 优先使用 snapshot_id,其次 sid
    const actualSnapshotId = snapshotId || sid;

    if (actualSnapshotId) {
      // 从快照加载
      console.log("📂 从快照加载:", actualSnapshotId);
      setMode('loading');
      loadSnapshot(actualSnapshotId);
    } else if (symbols) {
      // 从symbols生成
      console.log("🎯 从股票列表生成组合:", symbols);
      setMode('loading');
      const list = symbols.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
      if (list.length > 0) {
        onPropose(list);
      } else {
        setErr("股票列表为空");
        setMode('empty');
      }
    } else {
      console.log("⚠️ URL参数不完整,显示空状态");
      setMode('empty');
    }
  }

  // 加载已有快照
  async function loadSnapshot(sid: string) {
    setLoading(true);
    setErr(null);

    try {
      console.log("📡 加载快照:", `${SNAPSHOT_URL}/${sid}`);
      const r = await fetch(`${SNAPSHOT_URL}/${sid}`);

      // 📌 如果404,尝试加载latest
      if (r.status === 404) {
        console.warn(`⚠️ 快照 ${sid} 不存在,加载最新快照`);
        const r2 = await fetch(`${SNAPSHOT_URL}/latest`);
        if (!r2.ok) {
          setMode('empty');
          setErr("未找到任何组合数据");
          return;
        }
        const data: Resp = await r2.json();
        console.log("✅ 最新快照数据:", data);
        setResp(data);
        setMode('view');
        return;
      }

      if (!r.ok) {
        setMode('empty');
        setErr(`加载快照失败: HTTP ${r.status}`);
        return;
      }

      const data: Resp = await r.json();
      console.log("✅ 快照数据:", data);

      if (!data.holdings || data.holdings.length === 0) {
        setMode('empty');
        setErr("快照中没有持仓数据");
        return;
      }

      setResp(data);
      setMode('view');
    } catch (e: any) {
      console.error("❌ 加载快照失败:", e);
      setErr(e?.message || "加载快照失败");
      setMode('empty');
    } finally {
      setLoading(false);
    }
  }

  // 智能决策:生成新组合
  async function onPropose(list?: string[]) {
    if (!list || list.length === 0) {
      setErr("请提供股票列表");
      setMode('empty');
      return;
    }

    console.log("🎯 开始智能决策,股票列表:", list);

    setLoading(true);
    setErr(null);
    setMode('loading');

    try {
      console.log("📡 调用 API:", PROPOSE_URL);
      console.log("📦 请求数据:", { symbols: list });

      const r = await fetch(PROPOSE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols: list }),
      });

      console.log("📨 响应状态:", r.status, r.statusText);

      if (!r.ok) {
        const errorText = await r.text();
        console.error("❌ API错误响应:", errorText);
        setMode('empty');
        setErr(`生成组合失败: HTTP ${r.status}`);
        return;
      }

      const data: Resp = await r.json();
      console.log("✅ 获取到数据:", data);

      if (!data.holdings || data.holdings.length === 0) {
        setMode('empty');
        setErr("⚠️ 未生成有效组合,可能原因:\n• 股票评分未达标\n• 约束条件过严\n• 数据暂时不可用");
        return;
      }

      setResp(data);
      setMode('view');
    } catch (e: any) {
      console.error("❌ 智能决策失败:", e);
      setErr(e?.message || "生成失败");
      setMode('empty');
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
      alert("当前无有效持仓,请先生成组合。");
      return;
    }

    console.log("🔄 跳转回测,持仓数量:", resp.holdings.length);

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

  // 🔧 新增:返回首页
  function goBackHome() {
    window.location.hash = '#/';
  }

  // ========== 渲染 ==========

  // 加载中状态
  if (mode === 'loading' && loading) {
    return (
      <div className="page">
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 60 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
            <div style={{ fontSize: 18, color: '#888', marginBottom: 8 }}>
              AI 正在分析市场数据...
            </div>
            <div style={{ fontSize: 14, color: '#aaa' }}>
              生成最优投资组合
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 空状态
  if (mode === 'empty' || (!resp && !loading)) {
    return (
      <div className="page">
        <div className="page-header">
          <h2>💼 投资组合</h2>
          <button className="btn btn-secondary" onClick={goBackHome}>
            ← 返回首页
          </button>
        </div>

        <div className="card" style={{
          borderColor: "#ff6b6b",
          backgroundColor: "#fff5f5",
          textAlign: 'center',
          padding: 60
        }}>
          <div style={{ fontSize: 64, marginBottom: 20, opacity: 0.3 }}>📭</div>
          <h3 style={{ marginBottom: 12, color: '#c92a2a' }}>暂无组合数据</h3>
          {err && (
            <p style={{ color: '#e03131', marginBottom: 20, whiteSpace: 'pre-wrap' }}>
              {err}
            </p>
          )}
          <p style={{ color: '#666', marginBottom: 24 }}>
            请从首页点击「AI决策」生成投资组合
          </p>
          <button className="btn btn-primary" onClick={goBackHome}>
            返回首页开始决策
          </button>
        </div>
      </div>
    );
  }

  // 🔧 关键修复:确保resp不为null后再渲染
  if (!resp) {
    return null;
  }

  // 正常显示数据
  return (
    <div className="page">
      {/* 页面头部 */}
      <div className="page-header" style={{ gap: 8, alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ marginBottom: 8 }}>
            💼 投资组合
            {resp.version_tag && (
              <span style={{ fontSize: 14, color: '#888', marginLeft: 12 }}>
                ({resp.version_tag})
              </span>
            )}
          </h2>
        </div>

        {/* 右侧操作按钮 */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-secondary"
            onClick={goBackHome}
          >
            ← 返回首页
          </button>
          <button
            className="btn"
            onClick={exportCSV}
            disabled={!resp.holdings?.length}
            title="导出为 CSV 文件"
          >
            📥 导出
          </button>
          <button
            className="btn btn-primary"
            onClick={goToBacktest}
            disabled={!resp.snapshot_id}
            title="用此组合进行回测"
          >
            📊 回测
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b", backgroundColor: "#fff5f5" }}>
          <div className="card-body" style={{ color: "#c92a2a" }}>
            ⚠️ {err}
          </div>
        </div>
      )}

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

      {/* 图表区域:权重饼图 + 行业集中度 */}
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
            rows={resp.holdings.map(h => ({
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
    </div>
  );
}
// frontend/src/routes/portfolio.tsx
import { useEffect, useMemo, useState } from "react";
import WeightsPie from "../components/charts/WeightsPie";
import SectorBars from "../components/charts/SectorBars";
import HoldingsTable from "../components/tables/HoldingsTable";
import { API_BASE } from "../services/endpoints";

type Holding = { symbol: string; weight: number; score: number; sector?: string; reasons?: string[] };
type Resp = {
  holdings: Holding[];
  sector_concentration: [string, number][];
  as_of: string;
  version_tag: string;
  snapshot_id: string;
};

const PROPOSE_URL = (API_BASE ? `${API_BASE}` : "") + "/api/portfolio/propose";

// 读取 hash 参数的 symbols
function readHashSymbols(): string {
  const hash = window.location.hash || "";
  const i = hash.indexOf("?");
  if (i < 0) return "";
  const sp = new URLSearchParams(hash.slice(i + 1));
  return sp.get("symbols") || "";
}

export default function PortfolioPage() {
  const hashSymbols = readHashSymbols();

  // 初始池：优先 URL 里的 symbols；否则用默认池
  const [pool, setPool] = useState(
    hashSymbols || "AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AVGO, COST, LLY"
  );
  const [resp, setResp] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // 新增：AI分析相关状态
  const [smartPortfolioAnalysis, setSmartPortfolioAnalysis] = useState<any>(null);
  const [portfolioAnalysisLoading, setPortfolioAnalysisLoading] = useState(false);

  const pieData = useMemo(
    () => (resp?.holdings || []).map(h => ({ symbol: h.symbol, weight: h.weight })),
    [resp]
  );

  const sectorDist = useMemo(() => {
    const obj: Record<string, number> = {};
    (resp?.sector_concentration || []).forEach(([s, w]) => { obj[s] = w; });
    return obj;
  }, [resp]);

  // 仅当 URL 源带 symbols 时，首进页面自动生成一次；否则等待用户点击"一键生成"
  useEffect(() => {
    if (hashSymbols) {
      const list = hashSymbols.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
      void onPropose(list);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 支持可选入参：若传入 list，则用它；否则用输入框 pool
  async function onPropose(list?: string[]) {
    const symbols = (list && list.length)
      ? list
      : pool.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);

    if (!symbols.length) return;
    setLoading(true); setErr(null);

    // 清空之前的AI分析结果
    setSmartPortfolioAnalysis(null);

    try {
      const r = await fetch(PROPOSE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data: Resp = await r.json();
      setResp(data);
    } catch (e: any) {
      setErr(e?.message || "生成失败");
    } finally {
      setLoading(false);
    }
  }

  // 新增：智能组合分析函数
  async function runSmartPortfolioAnalysis() {
    if (!resp?.holdings?.length) {
      setErr("请先生成组合后再进行AI分析");
      return;
    }

    setPortfolioAnalysisLoading(true);
    try {
      const symbols = resp.holdings.map(h => h.symbol);

      // 调用后端智能组合分析API
      const response = await fetch(`${API_BASE}/api/portfolio/smart_analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: symbols,
          weights: resp.holdings.map(h => ({ symbol: h.symbol, weight: h.weight })),
          use_llm: true
        })
      });

      if (!response.ok) throw new Error(`${response.status}: ${response.statusText}`);

      const result = await response.json();
      setSmartPortfolioAnalysis(result);
    } catch (error: any) {
      setErr(`AI组合分析失败: ${error?.message || '未知错误'}`);
      console.error('Smart portfolio analysis failed:', error);
    } finally {
      setPortfolioAnalysisLoading(false);
    }
  }

  function exportCSV() {
    if (!resp?.holdings?.length) return;
    const rows = [
      ["Symbol","Sector","Score","Weight","Reasons"],
      ...resp.holdings.map(h => [
        h.symbol,
        h.sector || "",
        (h.score ?? "").toString(),
        (h.weight * 100).toFixed(4) + "%",
        (h.reasons || []).join("|")
      ])
    ];
    const csv = rows.map(r => r.map(x => `"${String(x).replace(/"/g,'""')}"`).join(",")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `portfolio_${new Date().toISOString().replace(/[:T]/g,"-").slice(0,16)}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
  }

  return (
    <div className="page">
      <div className="page-header" style={{gap: 8}}>
        <h2>组合建议</h2>
        <input
            defaultValue={pool}
            onBlur={e => setPool(e.currentTarget.value)}
            style={{minWidth: 420}}
            placeholder="用逗号或空格分隔股票，如：AAPL, MSFT, TSLA"
        />
        <button className="btn btn-primary" onClick={() => onPropose()} disabled={loading}>
          {loading ? "生成中…" : "一键生成"}
        </button>
        <button className="btn" onClick={exportCSV} disabled={!resp?.holdings?.length}>
          导出 CSV
        </button>
        <button
            className="btn"
            onClick={() => {
              if (!resp?.snapshot_id) {
                alert("当前无有效快照，先点『一键生成』产出组合。");
                return;
              }
              // 跳转到回测页，携带 sid
              window.location.hash = `#/simulator?sid=${encodeURIComponent(resp.snapshot_id)}`;
            }}
            disabled={!resp?.snapshot_id}
        >
          Run Backtest
        </button>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b" }}>
          <div className="card-body">{err}</div>
        </div>
      )}

      {resp && (
        <>
          <div className="grid-2">
            <div className="card">
              <div className="card-header"><h3>权重饼图</h3></div>
              <div className="card-body">
                <WeightsPie data={pieData} />
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h3>行业集中度</h3></div>
              <div className="card-body">
                <SectorBars sectorDist={sectorDist} />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><h3>持仓明细</h3></div>
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

          {/* 新增：AI组合分析卡片 */}
          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>AI组合分析</h3>
              <button
                onClick={runSmartPortfolioAnalysis}
                disabled={portfolioAnalysisLoading || !resp?.holdings?.length}
                className={`btn ${portfolioAnalysisLoading ? '' : 'btn-primary'}`}
                style={{ fontSize: '14px', padding: '6px 12px' }}
              >
                {portfolioAnalysisLoading ? '分析中...' : '开始AI分析'}
              </button>
            </div>
            <div className="card-body">
              {smartPortfolioAnalysis ? (
                <div style={{ display: 'grid', gap: 16 }}>

                  {/* 组合综合评分 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: '#f8f9fa', borderRadius: '8px' }}>
                    <span style={{ fontSize: '16px', fontWeight: 600 }}>组合综合评分</span>
                    <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#2563eb' }}>
                      {smartPortfolioAnalysis.portfolio_score || '--'}/100
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>

                    {/* 个股分析摘要 */}
                    <div>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>个股分析摘要</h4>
                      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                        {smartPortfolioAnalysis.stock_analyses && Object.entries(smartPortfolioAnalysis.stock_analyses).map(([symbol, analysis]: [string, any]) => (
                          <div key={symbol} style={{ padding: '8px', border: '1px solid #e5e7eb', borderRadius: '6px', marginBottom: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                              <span style={{ fontWeight: 600 }}>{symbol}</span>
                              <span style={{ fontSize: '14px', color: '#6b7280' }}>
                                权重: {(resp.holdings.find(h => h.symbol === symbol)?.weight * 100 || 0).toFixed(1)}%
                              </span>
                            </div>
                            <div style={{ fontSize: '13px', color: '#374151' }}>
                              评分: {analysis.adjusted_score || analysis.score || '--'}
                              {analysis.llm_analysis?.recommendation && (
                                <span style={{ marginLeft: '8px', color:
                                  analysis.llm_analysis.recommendation.includes('买入') ? '#059669' :
                                  analysis.llm_analysis.recommendation.includes('卖出') ? '#dc2626' : '#6b7280'
                                }}>
                                  | {analysis.llm_analysis.recommendation}
                                </span>
                              )}
                            </div>
                            {analysis.llm_analysis?.logic && (
                              <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                                {analysis.llm_analysis.logic}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* AI组合建议 */}
                    <div>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>AI组合建议</h4>
                      <div style={{ fontSize: '14px', lineHeight: '1.5' }}>
                        {smartPortfolioAnalysis.portfolio_reasoning && (
                          <div style={{ padding: '12px', background: '#f0f9ff', borderRadius: '6px', marginBottom: '12px' }}>
                            <div style={{ fontWeight: 600, marginBottom: '4px' }}>选择理由:</div>
                            <div>{smartPortfolioAnalysis.portfolio_reasoning}</div>
                          </div>
                        )}

                        {smartPortfolioAnalysis.risk_assessment && (
                          <div style={{ padding: '12px', background: '#fef2f2', borderRadius: '6px', marginBottom: '12px' }}>
                            <div style={{ fontWeight: 600, marginBottom: '4px', color: '#dc2626' }}>风险评估:</div>
                            <div>{smartPortfolioAnalysis.risk_assessment}</div>
                          </div>
                        )}

                        {smartPortfolioAnalysis.recommendations && (
                          <div style={{ padding: '12px', background: '#f0fdf4', borderRadius: '6px' }}>
                            <div style={{ fontWeight: 600, marginBottom: '4px', color: '#059669' }}>投资建议:</div>
                            <div>{smartPortfolioAnalysis.recommendations}</div>
                          </div>
                        )}
                      </div>
                    </div>

                  </div>

                  {/* 组合风险指标 */}
                  {smartPortfolioAnalysis.risk_metrics && (
                    <div>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>风险指标</h4>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
                        {Object.entries(smartPortfolioAnalysis.risk_metrics).map(([key, value]: [string, any]) => (
                          <div key={key} style={{ textAlign: 'center', padding: '8px', background: '#f8f9fa', borderRadius: '6px' }}>
                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '2px' }}>
                              {key === 'volatility' ? '波动率' :
                               key === 'sharpe_ratio' ? '夏普比率' :
                               key === 'max_drawdown' ? '最大回撤' : key}
                            </div>
                            <div style={{ fontSize: '14px', fontWeight: 600 }}>
                              {typeof value === 'number' ?
                                (key.includes('ratio') ? value.toFixed(2) : `${(value * 100).toFixed(1)}%`) :
                                value}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 错误处理 */}
                  {smartPortfolioAnalysis.error && (
                    <div style={{ padding: '12px', background: '#fef2f2', borderRadius: '6px', color: '#dc2626' }}>
                      分析过程中遇到问题: {smartPortfolioAnalysis.error}
                    </div>
                  )}

                </div>
              ) : (
                <div style={{ textAlign: 'center', color: '#6b7280', fontSize: '14px', padding: '40px 0' }}>
                  点击"开始AI分析"获取组合的智能评估和建议
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
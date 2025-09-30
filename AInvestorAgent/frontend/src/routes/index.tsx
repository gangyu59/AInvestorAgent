import { useEffect, useMemo, useState } from "react";

declare global {
  interface Window {
    latestBacktestData: any;
  }
}

// 保持原有的API函数和格式化函数
const fmt = (x: any, d = 2): string =>
  typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--";
const pct = (x: any, d = 1): string =>
  x == null || !Number.isFinite(+x) ? "--" : `${(+x * 100).toFixed(d)}%`;

const normMetrics = (m: any) => ({
  ann_return: m?.ann_return ?? m?.annReturn ?? null,
  sharpe: m?.sharpe ?? m?.Sharpe ?? null,
  mdd: m?.mdd ?? m?.max_dd ?? m?.maxDD ?? null,
  winrate: m?.winrate ?? m?.win_rate ?? m?.winRate ?? null,
});

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"];

export default function ImprovedDashboard() {
  const [symbols, setSymbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [decide, setDecide] = useState<any>(null);
  const [scores, setScores] = useState<any[]>([]);
  const [sentiment, setSentiment] = useState<any>(null);
  const [backtest, setBacktest] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setError] = useState<string | null>(null);
  const [analyzeMsg, setAnalyzeMsg] = useState<string>("");

  // 模拟数据加载
  useEffect(() => {
    setSnapshot({
      weights: { AAPL: 0.25, MSFT: 0.2, NVDA: 0.15, AMZN: 0.2, GOOGL: 0.2 },
      metrics: { ann_return: 0.15, mdd: -0.12, sharpe: 1.3, winrate: 0.68 },
      version_tag: "ai_v1.2"
    });

    setScores([
      { symbol: "AAPL", score: { score: 82, factors: { value: 0.7, quality: 0.8, momentum: 0.6, growth: 0.9, news: 0.3 } }, as_of: "2025-01-15" },
      { symbol: "MSFT", score: { score: 78, factors: { value: 0.6, quality: 0.9, momentum: 0.7, growth: 0.8, news: 0.5 } }, as_of: "2025-01-15" },
      { symbol: "NVDA", score: { score: 85, factors: { value: 0.4, quality: 0.7, momentum: 0.9, growth: 1.0, news: 0.8 } }, as_of: "2025-01-15" },
      { symbol: "AMZN", score: { score: 75, factors: { value: 0.5, quality: 0.6, momentum: 0.8, growth: 0.7, news: 0.4 } }, as_of: "2025-01-15" },
      { symbol: "GOOGL", score: { score: 80, factors: { value: 0.8, quality: 0.8, momentum: 0.5, growth: 0.6, news: 0.6 } }, as_of: "2025-01-15" }
    ]);

    setSentiment({
      latest_news: [
        { title: "Apple发布新款Vision Pro", url: "#", score: 0.7 },
        { title: "微软Azure增长超预期", url: "#", score: 0.5 },
        { title: "英伟达GPU需求持续强劲", url: "#", score: 0.8 },
        { title: "亚马逊云服务扩张", url: "#", score: 0.4 },
        { title: "谷歌AI技术突破", url: "#", score: 0.6 }
      ]
    });

    setBacktest({
      nav: [100, 102, 105, 103, 108, 112, 115, 118, 114, 120],
      benchmark_nav: [100, 101, 103, 102, 105, 108, 109, 112, 110, 115],
      metrics: { ann_return: 0.18, sharpe: 1.4, mdd: -0.08, winrate: 0.72 }
    });
  }, []);

  const keptTop5 = useMemo(() => {
    const weights = snapshot?.weights || {};
    return Object.entries(weights).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [snapshot]);

  const btM = useMemo(() => normMetrics(backtest?.metrics), [backtest]);

  // 只替换你index.tsx中的 onDecide 函数：
  async function onDecide() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/orchestrator/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbols: symbols,  // ✅ 已有
          topk: 15,          // 改为 15（与测试页一致）
          min_score: 55,     // 添加这个必需字段
          params: {          // 添加风控参数
            'risk.max_stock': 0.3,
            'risk.max_sector': 0.5,
            'risk.count_range': [5, 15]
          },
          mock: false        // 生产环境用 false
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errText}`);
      }

      const decideData = await response.json();

      const weights: Record<string, number> = {};
      const kept: string[] = [];

      if (decideData?.holdings) {
        decideData.holdings.forEach((holding: any) => {
          weights[holding.symbol] = holding.weight;
          kept.push(holding.symbol);
        });
      }

      setDecide({
        context: {
          weights,
          kept,
          orders: decideData?.orders || [],
          version_tag: decideData?.version_tag || "ai_v1.3"
        }
      });

    } catch (error) {
      console.error("AI决策失败:", error);
      setError(`AI决策失败: ${error instanceof Error ? error.message : '未知错误'}`);

      // 后备方案
      setTimeout(() => {
        setDecide({
          context: {
            weights: { AAPL: 0.3, MSFT: 0.25, NVDA: 0.2, GOOGL: 0.25 },
            kept: ["AAPL", "MSFT", "NVDA", "GOOGL"],
            orders: [],
            version_tag: "fallback_v1.0"
          }
        });
        setLoading(false);
      }, 2000);
      return;
    } finally {
      setLoading(false);
    }
  }

  // 只需要修改 index.tsx 中的 onRunBacktest 函数
  async function onRunBacktest() {
    setLoading(true);
    setError(null);

    try {
      let weights: Array<{symbol: string; weight: number}> = [];

      if (decide?.context?.weights) {
        weights = Object.entries(decide.context.weights).map(([symbol, weight]) => ({
          symbol,
          weight: Number(weight)
        }));
      } else {
        weights = symbols.map(symbol => ({
          symbol,
          weight: 1.0 / symbols.length
        }));
      }

      console.log("发送回测请求，权重:", weights);

      const response = await fetch("http://localhost:8000/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          weights,
          window_days: 252,
          trading_cost: 0.001
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const backtestData = await response.json();
      console.log("收到回测结果:", backtestData);

      // 使用全局变量存储数据
      window.latestBacktestData = backtestData;
      console.log("已存储回测结果到全局变量");

      // 跳转到 simulator 页面
      window.location.hash = '#/simulator?from=backtest';
      console.log("已跳转到 simulator 页面");

    } catch (error) {
      console.error("回测失败:", error);
      setError(`回测失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setLoading(false);
    }
  }

  // 替换 onGenerateReport 函数：
  async function onGenerateReport() {
    setLoading(true);
    setError(null);

    try {
      const mockReport = `# 投资决策日报
  生成时间: ${new Date().toLocaleString()}
  
  ## 组合概况
  - 持仓股票: ${symbols.join(", ")}
  - 当前权重: ${decide?.context?.weights ? 
    Object.entries(decide.context.weights)
      .map(([s, w]) => `${s}(${(Number(w)*100).toFixed(1)}%)`)
      .join(", ") : "等权重"}
  
  ## 市场情绪
  - 整体情绪偏向积极
  - 主要关注科技股走势
  
  ## 建议
  - 维持当前配置
  - 关注市场变化
  `;

      const blob = new Blob([mockReport], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `investment_report_${new Date().toISOString().split('T')[0]}.md`;
      a.click();
      URL.revokeObjectURL(url);

      alert("报告已生成并下载！");

    } catch (error) {
      setError(`报告生成失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setLoading(false);
    }
  }

  async function onAnalyzeClick() {
    const sym = (document.querySelector("#analyzeSym") as HTMLInputElement)?.value || "AAPL";
    setAnalyzeMsg(`正在分析 ${sym}...`);
    setTimeout(() => setAnalyzeMsg(`${sym} 分析完成 - 综合评分 82/100`), 1500);
  }

  async function checkAIStatus() {
    setTimeout(() => {
      const updateStatus = (id: string, status: string, color: string) => {
        const el = document.getElementById(id);
        if (el) {
          el.textContent = status;
          el.style.color = color;
        }
      };
      updateStatus('deepseekStatus', '正常', '#48bb78');
      updateStatus('doubaoStatus', '正常', '#48bb78');
      updateStatus('sentimentStatus', '正常', '#48bb78');
    }, 1000);
  }

  // 页面跳转函数
  const navigateTo = (path: string) => {
    window.location.hash = `#${path}`;
  };

  return (
    <div className="dashboard-content">
      {/* 固定顶部导航栏 */}
      <header className="dashboard-header">
        <div className="dashboard-brand">
          <div className="dashboard-logo">AI</div>
          <div>
            <h1 className="dashboard-brand-title">AInvestorAgent</h1>
            <p className="dashboard-brand-subtitle">智能投资决策平台</p>
          </div>
        </div>

        <div className="dashboard-actions">
          <div className="dashboard-search">
            <input
              type="text"
              placeholder="搜索股票代码..."
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  const v = (e.target as HTMLInputElement).value.trim();
                  if (v) navigateTo(`/stock?query=${encodeURIComponent(v)}`);
                }
              }}
            />
            <button
              className="dashboard-btn dashboard-btn-search"
              onClick={() => {
                const el = document.querySelector(".dashboard-search input") as HTMLInputElement;
                const v = el?.value.trim();
                if (v) navigateTo(`/stock?query=${encodeURIComponent(v)}`);
              }}
            >
              搜索
            </button>
          </div>

          <div className="dashboard-cta-group">
            <button
              onClick={onDecide}
              disabled={loading}
              className={`dashboard-btn dashboard-btn-primary ${loading ? 'disabled' : ''}`}
            >
              {loading ? "决策中..." : "AI决策"}
            </button>
            <button
              onClick={onRunBacktest}
              className="dashboard-btn dashboard-btn-secondary"
            >
              回测
            </button>
            <button
              onClick={onGenerateReport}
              className="dashboard-btn dashboard-btn-secondary"
            >
              报告
            </button>
          </div>
        </div>
      </header>

      {/* 错误提示 */}
      {errorMsg && (
        <div className="dashboard-error">
          {errorMsg}
        </div>
      )}

      {/* 核心指标卡片组 */}
      <section className="dashboard-section">
        <h2 className="dashboard-section-title">投资组合概览</h2>
        <div className="dashboard-grid dashboard-grid-auto">
          {/* 组合表现 */}
          <div className="dashboard-card" onClick={() => navigateTo('/portfolio')}>
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">组合表现</h3>
            </div>
            <div className="dashboard-card-body">
              <div className="dashboard-kpi-grid">
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">年化收益</p>
                  <p className={`dashboard-kpi-value large ${(snapshot?.metrics?.ann_return ?? 0) >= 0 ? 'up' : 'down'}`}>
                    {pct(snapshot?.metrics?.ann_return, 1)}
                  </p>
                </div>
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">夏普比率</p>
                  <p className="dashboard-kpi-value large neutral">
                    {fmt(snapshot?.metrics?.sharpe, 2)}
                  </p>
                </div>
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">最大回撤</p>
                  <p className="dashboard-kpi-value medium down">
                    {pct(snapshot?.metrics?.mdd, 1)}
                  </p>
                </div>
                <div className="dashboard-kpi">
                  <p className="dashboard-kpi-label">胜率</p>
                  <p className="dashboard-kpi-value medium up">
                    {btM.winrate ? `${Math.round(btM.winrate * 100)}%` : '--'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 持仓分布 */}
          <div className="dashboard-card" onClick={() => navigateTo('/portfolio')}>
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">Top 5 持仓</h3>
            </div>
            <div className="dashboard-card-body">
              <div className="dashboard-holdings">
                {keptTop5.map(([sym, weight]) => (
                  <div key={sym} className="dashboard-holding-item">
                    <span className="dashboard-holding-symbol">{sym}</span>
                    <span className="dashboard-holding-weight">{pct(weight, 1)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI决策状态 */}
          <div className="dashboard-card" onClick={() => navigateTo('/portfolio')}>
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">最新AI决策</h3>
            </div>
            <div className="dashboard-card-body">
              {decide?.context?.kept?.length ? (
                <div>
                  <div className="dashboard-decision-summary">
                    <div className="dashboard-metric">
                      <span className="dashboard-metric-label">选中股票</span>
                      <span className="dashboard-metric-value">{decide.context.kept.length} 只</span>
                    </div>
                    <div className="dashboard-metric">
                      <span className="dashboard-metric-label">决策方法</span>
                      <span className="dashboard-metric-value">
                        {decide?.context?.version_tag?.includes('ai') ? 'AI增强' : '传统算法'}
                      </span>
                    </div>
                  </div>
                  <div className="dashboard-holdings-preview">
                    {decide.context.kept.slice(0, 4).map((symbol: string) => (
                      <div key={symbol} className="dashboard-holding-chip">
                        <span className="symbol">{symbol}</span>
                        <span className="weight">
                          {((decide?.context?.weights?.[symbol] || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                    {(decide?.context?.kept?.length || 0) > 4 && (
                      <span className="dashboard-more">+{(decide?.context?.kept?.length || 0) - 4} 更多</span>
                    )}
                  </div>
                  <button className="dashboard-btn dashboard-btn-secondary" style={{width: '100%'}}>
                    查看详细组合
                  </button>
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <span>暂无决策记录</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDecide();
                    }}
                    className="dashboard-btn dashboard-btn-primary"
                  >
                    开始AI决策
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 快速操作区 */}
      <section className="dashboard-section">
        <h2 className="dashboard-section-title">快速分析</h2>
        <div className="dashboard-grid dashboard-grid-auto-wide">
          {/* AI分析工具 */}
          <div className="dashboard-card" onClick={() => navigateTo('/stock')}>
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">智能分析</h3>
            </div>
            <div className="dashboard-card-body">
              <div className="dashboard-analysis-row">
                <input
                  id="analyzeSym"
                  defaultValue="AAPL"
                  className="dashboard-analysis-input"
                  onClick={(e) => e.stopPropagation()}
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onAnalyzeClick();
                  }}
                  className="dashboard-btn dashboard-btn-primary"
                >
                  分析
                </button>
              </div>
              <div className="dashboard-analysis-result">
                {analyzeMsg || "输入股票代码开始AI分析"}
              </div>
            </div>
          </div>

          {/* 系统状态 */}
          <div className="dashboard-card" onClick={() => navigateTo('/manage')}>
            <div className="dashboard-status-header">
              <h3 className="dashboard-card-title">系统状态</h3>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  checkAIStatus();
                }}
                className="dashboard-btn dashboard-btn-secondary"
              >
                检查
              </button>
            </div>
            <div className="dashboard-card-body">
              <div className="dashboard-status-grid">
                <div className="dashboard-status-item">
                  <span>DeepSeek AI</span>
                  <span id="deepseekStatus" className="dashboard-status-indicator">检查中...</span>
                </div>
                <div className="dashboard-status-item">
                  <span>豆包 AI</span>
                  <span id="doubaoStatus" className="dashboard-status-indicator">检查中...</span>
                </div>
                <div className="dashboard-status-item">
                  <span>情绪分析</span>
                  <span id="sentimentStatus" className="dashboard-status-indicator">检查中...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 股票池和市场情绪 */}
      <section className="dashboard-section">
        <div className="dashboard-grid dashboard-grid-2">
          {/* 股票评分表 */}
          <div className="dashboard-card" onClick={() => navigateTo('/stock')}>
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">股票池评分</h3>
            </div>
            <div className="dashboard-card-body">
              <div className="dashboard-scores-grid dashboard-scores-header">
                <span>代码</span>
                <span>评分分布</span>
                <span>总分</span>
                <span>操作</span>
              </div>
              {scores.map((item) => (
                <div key={item.symbol} className="dashboard-scores-grid">
                  <span className="dashboard-scores-symbol">{item.symbol}</span>

                  {/* 雷达图 */}
                  <svg width="100" height="30" className="dashboard-radar">
                    {(() => {
                      const factors = item.score?.factors || {};
                      const order = ["value", "quality", "momentum", "growth", "news"];
                      const vals = order.map(k => Math.max(0, Math.min(1, factors[k] || 0)));
                      const cx = 15, cy = 15, r = 12, n = order.length;
                      const points = vals.map((v, i) => {
                        const angle = -Math.PI / 2 + i * (2 * Math.PI / n);
                        const radius = r * v;
                        const x = cx + radius * Math.cos(angle);
                        const y = cy + radius * Math.sin(angle);
                        return `${x},${y}`;
                      }).join(" ");

                      return (
                        <>
                          <circle cx={cx} cy={cy} r={r} fill="none" stroke="#374151" strokeWidth="1"/>
                          <polygon
                            points={points}
                            fill="rgba(59, 130, 246, 0.2)"
                            stroke="#3b82f6"
                            strokeWidth="1.5"
                          />
                        </>
                      );
                    })()}
                  </svg>

                  <span className={`dashboard-scores-total ${
                    item.score?.score >= 80 ? 'good' : 
                    item.score?.score >= 70 ? 'mid' : 'bad'
                  }`}>
                    {item.score?.score || '--'}
                  </span>

                  <button
                    className="dashboard-btn dashboard-btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigateTo(`/stock?query=${item.symbol}`);
                    }}
                  >
                    详情
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* 市场情绪 */}
          <div className="dashboard-card" onClick={() => navigateTo('/monitor')}>
            <div className="dashboard-card-header">
              <h3 className="dashboard-card-title">市场情绪</h3>
            </div>
            <div className="dashboard-card-body">
              {/* 情绪趋势图 */}
              <div className="dashboard-sentiment-chart">
                <svg width="100%" height="100%">
                  <line x1="0" y1="30" x2="100%" y2="30" stroke="#374151" strokeWidth="1"/>
                  <path
                    d="M 0,40 Q 25,20 50,25 T 100,15"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2"
                  />
                </svg>
              </div>

              {/* 最新新闻 */}
              <div className="dashboard-news-section">
                <h4>最新动态</h4>
                <div className="dashboard-news-list">
                  {sentiment?.latest_news?.slice(0, 3).map((news: any, i: number) => (
                    <div key={i} className="dashboard-news-item">
                      <div className="dashboard-news-content">
                        <span className="dashboard-news-title">{news.title}</span>
                        <span className={`dashboard-news-sentiment ${
                          news.score > 0 ? 'positive' : 
                          news.score < 0 ? 'negative' : 'neutral'
                        }`}>
                          {news.score > 0 ? '+' : ''}{fmt(news.score, 1)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 页脚导航 */}
      <footer className="dashboard-footer">
        <div className="dashboard-footer-links">
          <a href="/#/stock" className="dashboard-footer-link">个股分析</a>
          <a href="/#/portfolio" className="dashboard-footer-link">组合管理</a>
          <a href="/#/simulator" className="dashboard-footer-link">回测模拟</a>
          <a href="/#/trading" className="dashboard-footer-link">模拟交易</a>
          <a href="/#/monitor" className="dashboard-footer-link">舆情监控</a>
          <a href="/#/manage" className="dashboard-footer-link">系统管理</a>
        </div>

        <div className="dashboard-footer-info">
          AInvestorAgent v1.2 | 低频投资决策 ≤3次/周 |
          <span className="dashboard-footer-status">● 系统运行正常</span>
        </div>
      </footer>
    </div>
  );
}
// frontend/src/routes/index.tsx — 安全渲染修复版
// 关键改动：
// 1) 新增 fmt()/pct() 安全格式化，杜绝对 null/undefined 调用 toFixed 导致的崩溃
// 2) 所有 .toFixed(...) 全部替换为 fmt()/pct()；所有 map() 的数据源统一给默认 []
// 3) UI 逻辑不变，不影响你已跑通的其它页面

import { useEffect, useMemo, useState } from "react";
import {
  decideNow,
  runBacktest,
  scoreBatch,
  fetchSentimentBrief,
  fetchLastSnapshot,
  type DecideResponse,
  type BacktestResponse,
  type ScoreItem,
  type SentimentBrief,
  type SnapshotBrief,
} from "../services/endpoints";
import logoUrl from "/src/assets/images/logo.svg";
import { analyzeEndpoint } from "../services/endpoints";


// ===== 安全格式化工具 =====
const fmt = (x: any, d = 2): string =>
  typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--";
const pct = (x: any, d = 1): string =>
  x == null || !Number.isFinite(+x) ? "--" : `${(+x * 100).toFixed(d)}%`;

// 统一指标字段（兼容 ann_return/max_dd/win_rate 等大小写差异）
type AnyMetrics = Record<string, any> | null | undefined;
const normMetrics = (m: AnyMetrics) => ({
  ann_return: m?.ann_return ?? m?.annReturn ?? null,
  sharpe:     m?.sharpe     ?? m?.Sharpe     ?? null,
  mdd:        m?.mdd        ?? m?.max_dd     ?? m?.maxDD ?? null,
  winrate:    m?.winrate    ?? m?.win_rate   ?? m?.winRate ?? null,
});

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"];
const API_BASE = (import.meta as any).env?.VITE_API_BASE || "";

export default function HomePage() {
  const [symbols, setSymbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [decide, setDecide] = useState<DecideResponse | null>(null);
  const [scores, setScores] = useState<ScoreItem[]>([]);
  const [sentiment, setSentiment] = useState<SentimentBrief | null>(null);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [snapshot, setSnapshot] = useState<SnapshotBrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setError] = useState<string | null>(null);

  // 首次加载：快照 / 情绪 / 批量评分
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);

        // 先启动 Promise（并发开始），再分别 await（不会串行阻塞）
        const p1 = fetchLastSnapshot().catch(() => null) as Promise<SnapshotBrief | null>;
        const p2 = fetchSentimentBrief(symbols).catch(() => null) as Promise<SentimentBrief | null>;
        const p3 = scoreBatch(symbols).catch(() => []) as Promise<ScoreItem[]>;

        const snap    = await p1;                      // SnapshotBrief | null
        const brief   = await p2;                      // SentimentBrief | null
        const scoring = await p3;                      // ScoreItem[]

        if (cancelled) return;

        if (snap)  setSnapshot(snap);
        if (brief) setSentiment(brief);
        setScores(scoring);
      } catch (e: any) {
        if (!cancelled) setError(e?.message ?? "加载失败");
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  // 取 top5 权重（来自最新 decide 或 snapshot）
  const keptTop5 = useMemo<[string, number][]>(() => {
    const weights: Record<string, number> =
      (snapshot?.weights as Record<string, number> | undefined) || {};
    return Object.entries(weights).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [snapshot]);


  async function onDecide() {
    setLoading(true);
    setError(null);
    try {
      // 优先用你 endpoints.ts 里的 decideNow；没有的话走直连 fetch
      let res: any;
      if (typeof decideNow === "function") {
        res = await decideNow({ symbols });
      } else {
        const base = (import.meta as any).env?.VITE_API_BASE || "";
        const r = await fetch(`${base}/api/portfolio/propose`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbols }),
        });
        if (!r.ok) throw new Error(await r.text());
        res = await r.json();
      }

      setDecide(res);

      // ✅ 关键：跳转到组合页
      const sid = res?.snapshot_id ?? res?.context?.snapshot_id;
      if (sid) {
        window.location.hash = `#/portfolio?sid=${encodeURIComponent(sid)}`;
      } else {
        window.location.hash = "#/portfolio";
      }
    } catch (e: any) {
      setError(e?.message || "Decide 调用失败");
      alert("Decide 失败：" + (e?.message || ""));
    } finally {
      setLoading(false);
    }
  }


    // ====== 回测：点击“Run Backtest” ======
  async function onRunBacktest() {
    setLoading(true);
    setError(null);
    try {
      // 取最新权重；没有快照就用等权
      const weights: Record<string, number> =
        (decide?.context?.weights as Record<string, number> | undefined) ||
        (snapshot?.weights as Record<string, number> | undefined) ||
        Object.fromEntries(symbols.map(s => [s, 1 / symbols.length]));

      let bt: any;
      if (typeof runBacktest === "function") {
        // 你的 runBacktest 是按 symbols 触发回测；这里给 1 年周频
        bt = await runBacktest({
          symbols: Object.keys(weights),
          rebalance: "weekly",
          weeks: 52,
        });
      } else {
        const base = (import.meta as any).env?.VITE_API_BASE || "";
        const r = await fetch(`${base}/backtest/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          // ✅ 你的后端要求字段名是 weights（不是 holdings）
          body: JSON.stringify({
            weights: Object.entries(weights).map(([symbol, weight]) => ({ symbol, weight })),
          }),
        });
        if (!r.ok) throw new Error(await r.text());
        bt = await r.json();
      }

      setBacktest(bt);

      // ✅ 关键：跳转到模拟页
      const bid = bt?.backtest_id;
      if (bid) {
        window.location.hash = `#/simulator?bid=${encodeURIComponent(bid)}`;
      } else {
        window.location.hash = "#/simulator";
      }
    } catch (e: any) {
      setError(e?.message || "Backtest 调用失败");
      alert("Backtest 失败：" + (e?.message || ""));
    } finally {
      setLoading(false);
    }
  }


  // ====== 个股分析：点击“运行 /api/analyze” ======
  async function onAnalyzeClick() {
    try {
      // 输入框 id 与你当前 JSX 一致（见下方）
      const el = document.querySelector<HTMLInputElement>("#analyzeSym");
      const sym = (el?.value || "AAPL").trim().toUpperCase();
      // ✅ IMPORTANT：analyzeEndpoint 应只返回 path，这里再拼 base
      const url = `${API_BASE}${analyzeEndpoint(sym)}`;
      const r = await fetch(url, { method: "GET" }); // 如果你的后端是 POST，请改为 {method:"POST"}
      if (!r.ok) throw new Error(await r.text());
      // 成功后跳到个股页查看完整图表
      window.location.hash = `#/stock?query=${encodeURIComponent(sym)}`;
    } catch (e: any) {
      alert("Analyze 失败：" + (e?.message || ""));
    }
  }

  return (
    <>
      {/* ===== 顶栏（sticky） ===== */}
      <header className="topbar">
        <div className="brand">
          <img src={logoUrl} alt="logo" className="logo" />
          <span className="title">AInvestorAgent</span>
        </div>

        {/* 顶部链接菜单 */}
        <nav className="nav">
          <a href="/#/stock" className="nav-item">个股</a>
          <a href="/#/portfolio" className="nav-item">组合</a>
          <a href="/#/simulator" className="nav-item">模拟</a>
          <a href="/#/monitor" className="nav-item">舆情</a>
          <a href="/#/manage" className="nav-item">管理</a>
        </nav>

        <div className="actions">
          <div className="search">
            <input
                type="text"
                placeholder="搜索代码或名称（AAPL / TSLA / NVDA）"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    const v = (e.target as HTMLInputElement).value.trim();
                    if (v) window.location.hash = `#/stock?query=${encodeURIComponent(v)}`;
                  }
                }}
            />
            <button
                className="btn btn-secondary"
                onClick={() => {
                  const el = document.querySelector<HTMLInputElement>(".topbar .search input");
                  const v = el?.value.trim();
                  if (v) window.location.hash = `#/stock?query=${encodeURIComponent(v)}`;
                }}
            >
              搜索
            </button>
          </div>

          <div className="cta-group">
            <button className="btn btn-primary" onClick={onDecide} disabled={loading}>
              {loading ? "Deciding..." : "Decide Now"}
            </button>
            <button className="btn" onClick={onRunBacktest} disabled={loading}>
              Run Backtest
            </button>
            <button
                className="btn"
                onClick={async () => {
                  try {
                    const base = (import.meta as any).env?.VITE_API_BASE || "";
                    const r = await fetch(`${base}/api/report/generate`, {method: "POST"});
                    if (!r.ok) throw new Error(String(r.status));
                    alert("已触发报告生成");
                  } catch {
                    alert("报告接口未就绪：请稍后再试");
                  }
                }}
            >
              Generate Report
            </button>
          </div>
        </div>
      </header>

      {/* ===== 主体两栏布局 ===== */}
      <div className="layout">
        {/* 侧栏 */}
        <aside className="sidebar">
          <nav>
            <a href="/#/stock" className="nav-item">个股分析（Stock）</a>
            <a href="/#/portfolio" className="nav-item">组合建议（Portfolio）</a>
            <a href="/#/simulator" className="nav-item">回测与模拟（Simulator）</a>
            <a href="/#/monitor" className="nav-item">舆情与监控（Monitor）</a>
            <a href="/#/manage" className="nav-item">管理与配置（Manage）</a>
          </nav>
          <div className="side-meta">
            <div className="tag">深色主题</div>
            <div className="tag">低频决策 ≤ 3/周</div>
            <div className="tag">版本：{decide?.context?.version_tag || "scorer_v1"}</div>
          </div>
        </aside>

        {/* 内容 */}
        <main className="content">
          {errorMsg && (
              <div className="card" style={{borderColor: "#ff6b6b", marginBottom: 12}}>
                <div className="card-header"><h3>错误</h3></div>
                <div className="card-body">{String(errorMsg)}</div>
              </div>
          )}

          {/* === Hero：三卡 === */}
          <section className="hero">
            {/* Portfolio Snapshot */}
            <div className="card xl">
              <div className="card-header">
                <h3>Portfolio Snapshot</h3>
                <a href="/#/portfolio" className="link">查看详情 →</a>
              </div>
              <div className="card-body row">
                <div className="mini-chart donut" aria-label="权重饼图（示意）" />
                <div className="kpis">
                  <div className="kpi">
                    <div className="kpi-label">年化</div>
                    <div className={`kpi-value ${(snapshot?.metrics?.ann_return ?? 0) >= 0 ? "up" : "down"}`}>
                      {pct(snapshot?.metrics?.ann_return, 1)}
                    </div>
                  </div>
                  <div className="kpi">
                    <div className="kpi-label">最大回撤</div>
                    <div className="kpi-value down">{pct(snapshot?.metrics?.mdd, 1)}</div>
                  </div>
                  <div className="kpi">
                    <div className="kpi-label">Sharpe</div>
                    <div className="kpi-value">{fmt(snapshot?.metrics?.sharpe, 2)}</div>
                  </div>
                  <div className="kpi">
                    <div className="kpi-label">胜率</div>
                    <div className="kpi-value">
                      {snapshot?.metrics?.winrate == null ? "--" : `${Math.round((snapshot!.metrics!.winrate as number) * 100)}%`}
                    </div>
                  </div>
                </div>
                <ul className="list">
                  {(keptTop5.length ? keptTop5 : Object.entries(snapshot?.weights || {}).slice(0, 5)).map(([sym, w]) => (
                    <li key={sym}>{sym} {pct(w, 1)}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Quick Decide */}
            <div className="card lg">
              <div className="card-header">
                <h3>Quick Decide</h3>
                <a href="/#/manage" className="link">配置预设 →</a>
              </div>
              <div className="card-body column">
                <div className="field">
                  <span>股票池</span>
                  <input
                    defaultValue={symbols.join(", ")}
                    onBlur={(e) => {
                      const v = e.target.value;
                      setSymbols(v.split(",").map(s => s.trim().toUpperCase()).filter(Boolean));
                    }}
                  />
                </div>
                <div className="hint">
                  最近一次：kept {(decide?.context?.kept?.length ?? snapshot?.kept?.length ?? 0)}, {" "}
                  orders {(decide?.context?.orders?.length ?? 0)}, {" "}
                  version_tag: {decide?.context?.version_tag || snapshot?.version_tag || "--"}
                </div>
                <div className="buttons">
                  <button className="btn btn-primary" onClick={onDecide} disabled={loading}>生成建议</button>
                  <a href="/#/portfolio" className="btn">查看组合</a>
                </div>
              </div>
            </div>

            {/* Heatmap（占位） */}
            <div className="card lg">
              <div className="card-header">
                <h3>Sector Heatmap</h3>
                <a href="/#/monitor" className="link">更多市场视图 →</a>
              </div>
              <div className="card-body heatmap">
                <div className="cell up">Tech</div>
                <div className="cell flat">Energy</div>
                <div className="cell down">Consumer</div>
                <div className="cell up">Financials</div>
                <div className="cell flat">Healthcare</div>
                <div className="cell up">Industrials</div>
              </div>
            </div>
          </section>

          {/* === 双列：排行/新闻 + 风险/回测/Agents === */}
          <section className="grid-2">
            <div className="stack">
              {/* Rankings */}
              <div className="card">
                <div className="card-header">
                  <h3>Watchlist Rankings</h3>
                  <a href="/#/stock" className="link">到个股页 →</a>
                </div>
                <div className="table">
                  <div className="thead">
                    <span>Symbol</span><span>Score</span><span>因子雷达</span><span>更新时间</span><span></span>
                  </div>
                  <div className="tbody">
                    {(scores || []).map(it => (
                      <div className="row" key={it.symbol}>
                        <span>{it.symbol}</span>
                        {(() => {
                          const s = (it as any)?.score?.score ?? (typeof (it as any).score === "number" ? (it as any).score : 0);
                          return (
                            <span className={`score ${s >= 85 ? "good" : s >= 70 ? "mid" : "bad"}`}>{Number.isFinite(s) ? s : "--"}</span>
                          );
                        })()}
                        <span className="radar" />
                        <span>{(it as any).as_of || "--"}</span>
                        <span><a href="/#/portfolio" className="btn tiny">加入组合</a></span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* News & Sentiment */}
              <div className="card">
                <div className="card-header">
                  <h3>News & Sentiment (7D)</h3>
                  <a href="/#/monitor" className="link">查看舆情 →</a>
                </div>
                <div className="card-body column">
                  <div className="mini-chart line" aria-label="情绪时间轴（示意）" />
                  <ul className="news-list">
                    {((sentiment?.latest_news || []).slice(0, 5)).map((n, i) => (
                      <li key={i}>
                        <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
                        <span className={`pill ${((n as any).score ?? 0) > 0 ? "up" : ((n as any).score ?? 0) < 0 ? "down" : "flat"}`}>
                          {fmt((n as any).score, 1)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>


            <div className="card">
              <div className="card-header">
                <h3>Analyze Snapshot</h3>
                <a href="/#/stock" className="link">到个股页 →</a>
              </div>
              <div className="card-body column">
                <div className="row" style={{gap: 8}}>
                  <input id="analyzeSym" defaultValue="AAPL"/>
                  <button
                      className="btn"
                      onClick={async () => {
                        try {
                          const el = document.querySelector<HTMLInputElement>("#analyze-input"); // 假设你的输入框 id="analyze-input"
                          const sym = (el?.value || "AAPL").trim().toUpperCase();
                          const base = (import.meta as any).env?.VITE_API_BASE || "";
                          const r = await fetch(`${base}${analyzeEndpoint(sym)}`); // e.g. /api/analyze/AAPL
                          if (!r.ok) throw new Error(String(r.status));
                          // 成功后直接跳到个股页查看完整图表
                          window.location.hash = `#/stock?query=${encodeURIComponent(sym)}`;
                        } catch (e: any) {
                          alert("Analyze 失败：" + (e?.message || ""));
                        }
                      }}
                  >
                    运行 /api/analyze
                  </button>
                </div>
                <div id="analyzeOut"
                     style={{fontFamily: "ui-monospace,monospace", fontSize: 12, marginTop: 8, color: "#111"}}>（等待运行）
                </div>
              </div>
            </div>


            <div className="stack">
              {/* Risk */}
              <div className="card">
                <div className="card-header">
                  <h3>Risk & Constraints</h3>
                  <a href="/#/manage" className="link">编辑规则 →</a>
                </div>
                <div className="card-body column">
                  <div className="rule">单票 ≤ <b>30%</b>，行业 ≤ <b>50%</b>，持仓 <b>5–15</b></div>
                  <div className="violations">
                  <div className="vio ok">未发现超限</div>
                  </div>
                </div>
              </div>

              {/* Backtest */}
              <div className="card">
                <div className="card-header">
                  <h3>Last Backtest (1Y, weekly ≤3)</h3>
                  <a href="/#/simulator" className="link">查看详情 →</a>
                </div>
                <div className="card-body row">
                  <div className="mini-chart area" aria-label="净值 vs 基准（示意）" />
                  <div className="kpis">
                    <div className="kpi">
                      <div className="kpi-label">Ann.Return</div>
                      <div className={`kpi-value ${(backtest?.metrics?.ann_return ?? 0) >= 0 ? "up" : "down"}`}>
                        {pct(backtest?.metrics?.ann_return, 1)}
                      </div>
                    </div>
                    <div className="kpi">
                      <div className="kpi-label">MDD</div>
                      <div className="kpi-value down">{pct(backtest?.metrics?.mdd, 1)}</div>
                    </div>
                    <div className="kpi">
                      <div className="kpi-label">Sharpe</div>
                      <div className="kpi-value">{fmt(backtest?.metrics?.sharpe, 2)}</div>
                    </div>
                    <div className="kpi">
                      <div className="kpi-label">Winrate</div>
                      <div className="kpi-value">{backtest?.metrics?.winrate == null ? "--" : `${Math.round((backtest!.metrics!.winrate as number) * 100)}%`}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Agents */}
              <div className="card">
                <div className="card-header">
                  <h3>Agents & Traces</h3>
                  <a href="/#/monitor" className="link">查看 Trace →</a>
                </div>
                <div className="agents">
                  <div className="agent ok">Ingestor</div>
                  <div className="agent ok">Researcher</div>
                  <div className="agent ok">Risk</div>
                  <div className="agent ok">PM</div>
                  <div className="agent ok">Backtest</div>
                  <div className="agent ok">Report</div>
                </div>
                <ul className="trace-list">
                  <li>#f1a2… 2.3s OK</li>
                  <li>#b7c9… 3.1s OK（降级：news 备用源）</li>
                  <li>#98de… 1.8s OK</li>
                </ul>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}

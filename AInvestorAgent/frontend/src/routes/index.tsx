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
  const [analyzeMsg, setAnalyzeMsg] = useState<string>("");

  // ===== 工具：统一向后端发起回测（/backtest/run），并缓存“最近一次回测” =====
  async function postBacktest(weightsObj: Record<string, number>) {
    const base = (import.meta as any).env?.VITE_API_BASE || "";
    const weights = Object.entries(weightsObj).map(([symbol, weight]) => ({
      symbol,
      weight: Number(weight),
    }));
    if (weights.length === 0) throw new Error("没有可用权重，无法回测");

    const payload = {
      weights,            // ✅ 后端要求：[{symbol, weight}]
      window_days: 180,   // 轻量回测窗口
      trading_cost: 0,
      mock: true,         // 保证演示稳定；要真实回测可去掉
    };

    const r = await fetch(`${base}/backtest/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) throw new Error(await r.text());
    const bt = await r.json();

    setBacktest(bt);
    try { localStorage.setItem("lastBacktest", JSON.stringify(bt)); } catch {}
    return bt;
  }

  // ===== 首次加载：快照 / 情绪 / 批量评分 =====
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);

        // 并发请求
        const p1 = fetchLastSnapshot().catch(() => null) as Promise<SnapshotBrief | null>;
        const p2 = fetchSentimentBrief(symbols).catch(() => null) as Promise<SentimentBrief | null>;
        const p3 = scoreBatch(symbols).catch(() => []) as Promise<ScoreItem[]>;

        const snap    = await p1;
        const brief   = await p2;
        const scoring = await p3;

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

  // ===== 首屏回读“最近一次回测”缓存（来自任意页面的回测）=====
  useEffect(() => {
    try {
      const s = localStorage.getItem("lastBacktest");
      if (s && !backtest) setBacktest(JSON.parse(s));
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ===== 有快照且本页还没有回测结果时，触发一次轻量回测（可见即可用）=====
  useEffect(() => {
    if (!snapshot || backtest) return;
    const weights = snapshot.weights || {};
    if (Object.keys(weights).length === 0) return;

    (async () => {
      try {
        await postBacktest(weights);
      } catch {
        // 静默失败，保持空态
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot]);

  // 取 top5 权重（来自最新 decide 或 snapshot）
  const keptTop5 = useMemo<[string, number][]>(() => {
    const weights: Record<string, number> =
      (snapshot?.weights as Record<string, number> | undefined) || {};
    return Object.entries(weights).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [snapshot]);

  const btM = useMemo(() => {
    const m = backtest?.metrics ?? (backtest as any)?.result?.metrics ?? null;
    return normMetrics(m);
  }, [backtest]);

  // ====== 一键组合：Decide Now ======
  async function onDecide() {
    setLoading(true);
    setError(null);
    try {
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

      // 跳组合页
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
      // 取最新权重；没有快照/结果就用等权（不发 symbols/weeks 了）
      const weightsObj: Record<string, number> =
        (decide?.context?.weights as Record<string, number> | undefined) ||
        (snapshot?.weights as Record<string, number> | undefined) ||
        Object.fromEntries(symbols.map(s => [s, 1 / Math.max(symbols.length, 1)]));

      const bt = await postBacktest(weightsObj);

      // 跳模拟页
      const bid = (bt as any)?.backtest_id;
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

  // ====== 报告：Generate Report ======
  async function onGenerateReport() {
    try {
      const base = (import.meta as any).env?.VITE_API_BASE || "";
      const r = await fetch(`${base}/api/report/generate`, { method: "POST" });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      const md = data?.content || "";
      if (!md) {
        alert("报告为空（可能尚未有组合快照）");
        return;
      }
      const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const d = new Date().toISOString().slice(0, 10);
      a.download = `report_${d}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert("Generate Report 失败：" + (e?.message || ""));
    }
  }

  // ====== 个股分析：点击“运行 /api/analyze” ======
  async function onAnalyzeClick() {
    try {
      const el = document.querySelector<HTMLInputElement>("#analyzeSym");
      const sym = (el?.value || "AAPL").trim().toUpperCase();
      setAnalyzeMsg(`正在分析 ${sym} …`);
      const url = `${API_BASE}${analyzeEndpoint(sym)}`;
      const r = await fetch(url, { method: "GET" });
      if (!r.ok) throw new Error(await r.text());
      setAnalyzeMsg(`已触发 /api/analyze/${sym} 成功`); // ✅ 不跳页，只提示
    } catch (e: any) {
      setAnalyzeMsg(`Analyze 失败：${e?.message || ""}`);
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
            <button className="btn" onClick={onGenerateReport}>
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
                      {btM.winrate == null ? "--" : `${Math.round((btM.winrate as number) * 100)}%`}
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
                <a href="/#/monitor" className="link">查看舆情 →</a>
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
                                <span
                                    className={`score ${s >= 85 ? "good" : s >= 70 ? "mid" : "bad"}`}>{Number.isFinite(s) ? s : "--"}</span>
                            );
                          })()}


                          {(() => {
                            const f = ((it as any)?.score?.factors) || {};                  // 因子值 0..1
                            const order = ["value", "quality", "momentum", "growth", "news"];   // 固定顺序
                            const vals = order.map(k => {
                              const v = Number(f[k] ?? 0);
                              return v < 0 ? 0 : v > 1 ? 1 : v;                              // clamp
                            });
                            const cx = 10, cy = 10, r = 8, n = order.length;
                            const pts = vals.map((v, i) => {
                              const a = -Math.PI / 2 + i * (2 * Math.PI / n);                     // 从正上开始
                              const rr = r * v;
                              const x = cx + rr * Math.cos(a);
                              const y = cy + rr * Math.sin(a);
                              return `${x},${y}`;
                            }).join(" ");
                            return (
                                <svg width="20" height="20" className="mini-radar" aria-label="因子雷达">
                                  <circle cx={cx} cy={cy} r={r} fill="none" stroke="#eee"/>
                                  <polygon points={pts} fill="rgba(100,149,237,0.35)" stroke="#6495ED"
                                           strokeWidth="0.8"/>
                                </svg>
                            );
                          })()}

                          <span>{(it as any).as_of || (it as any).updated_at || (it as any).version_tag || (it as any)?.score?.as_of || "--"}</span>
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

                  {(() => {
                    const list = (sentiment?.latest_news ?? []);
                    const avg = Math.round((list.reduce((s, n) => s + ((n as any)?.score ?? 0), 0) / Math.max(list.length, 1)) * 100) / 100;
                    const barPct = (avg + 1) * 50;
                    return (
                        <div
                            style={{
                              display: 'inline-block', marginLeft: 8, verticalAlign: 'middle',
                              width: 80, height: 6, borderRadius: 4, background: '#eee'
                            }}
                            title={`近${list.length}条，均值=${avg}`}
                        >
                          <div
                              style={{
                                height: '100%', width: `${barPct}%`, borderRadius: 4,
                                background: avg >= 0 ? '#3CB371' : '#DC143C'
                              }}/>
                        </div>
                    );
                  })()}

                  <a href="/#/monitor" className="link">查看舆情 →</a>

                </div>
                <div className="card-body column">
                  {(() => {
                    const list = (sentiment?.latest_news ?? []).slice(0, 30); // 取最近30条足够画迷你图
                    if (list.length === 0) return <div className="mini-chart line" aria-label="情绪时间轴（空）"/>;

                    const w = 180, h = 40, pad = 4;
                    const xs = list.map((_, i) => pad + (w - 2 * pad) * (i / Math.max(list.length - 1, 1)));
                    const ys = list.map(n => {
                      const s = Math.max(-1, Math.min(1, (n as any)?.score ?? 0)); // clamp -1..1
                      // 将 -1..+1 映射到 SVG 的 h-2*pad 高度，+1 在上、-1 在下
                      return pad + (h - 2 * pad) * (1 - (s + 1) / 2);
                    });
                    const d = xs.map((x, i) => `${i ? 'L' : 'M'}${x},${ys[i]}`).join(' ');
                    const last = (list[list.length - 1] as any)?.score ?? 0;
                    const color = last >= 0 ? '#3CB371' : '#DC143C';

                    return (
                        <svg width={w} height={h} className="mini-chart" role="img" aria-label="情绪时间轴">
                          <rect x="0" y="0" width={w} height={h} fill="none" stroke="#eee"/>
                          <line x1="0" y1={h / 2} x2={w} y2={h / 2} stroke="#ddd"/>
                          <path d={d} fill="none" stroke={color} strokeWidth="1.5"/>
                          <circle cx={xs[xs.length - 1]} cy={ys[ys.length - 1]} r="2" fill={color}/>
                        </svg>
                    );
                  })()}

                  <ul className="news-list">
                    {((sentiment?.latest_news || []).slice(0, 5)).map((n, i) => (
                        <li key={i}>
                          <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
                          <span
                              className={`pill ${((n as any).score ?? 0) > 0 ? "up" : ((n as any).score ?? 0) < 0 ? "down" : "flat"}`}>
                          {fmt((n as any).score, 1)}
                        </span>
                        </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            <div className="stack">
              <div className="card">
                <div className="card-header">
                  <h3>Analyze Snapshot</h3>
                  <a href="/#/stock" className="link">到个股页 →</a>
                </div>
                <div className="card-body column">
                  <div className="row" style={{gap: 8}}>
                    <input id="analyzeSym" defaultValue="AAPL"/>
                    <button className="btn" onClick={onAnalyzeClick}>运行 /api/analyze</button>
                    <div id="analyzeOut" className="muted small">{analyzeMsg}</div>
                  </div>
                </div>
              </div>

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
                  {(() => {
                    const navArr =
                        (Array.isArray(backtest?.nav) ? backtest!.nav : undefined) ??
                        (Array.isArray((backtest as any)?.equity_nav) ? (backtest as any).equity_nav : undefined) ??
                        (Array.isArray((backtest as any)?.equity) ? (backtest as any).equity : undefined) ??
                        (Array.isArray((backtest as any)?.result?.nav) ? (backtest as any).result.nav : undefined) ??
                        [];

                    const benchArr =
                        (Array.isArray(backtest?.benchmark_nav) ? backtest!.benchmark_nav : undefined) ??
                        (Array.isArray((backtest as any)?.benchmark) ? (backtest as any).benchmark : undefined) ??
                        (Array.isArray((backtest as any)?.result?.benchmark_nav) ? (backtest as any).result.benchmark_nav : undefined) ??
                        [];

                    if (navArr.length < 2) {
                      return (
                          <div style={{display: 'flex', alignItems: 'center', gap: 8}}>
                            <span style={{color: '#666'}}>暂无回测结果</span>
                            <a href="/#/simulator" className="btn tiny">去运行回测</a>
                          </div>
                      );
                    }
                    const w = 180, h = 40, pad = 4;
                    const max = Math.max(...navArr), min = Math.min(...navArr);
                    const y = (v: number) => {
                      const t = (v - min) / Math.max(max - min, 1e-6);
                      return pad + (h - 2 * pad) * (1 - t);
                    };
                    const xs = navArr.map((_, i) => pad + (w - 2 * pad) * (i / (navArr.length - 1)));
                    const d1 = xs.map((x, i) => `${i ? 'L' : 'M'}${x},${y(navArr[i])}`).join(' ');
                    const d2 = benchArr.length === navArr.length ? xs.map((x, i) => `${i ? 'L' : 'M'}${x},${y(benchArr[i])}`).join(' ') : '';
                    return (
                        <svg width={w} height={h} className="mini-chart" role="img" aria-label="净值与基准">
                          <rect x="0" y="0" width={w} height={h} fill="none" stroke="#eee"/>
                          <path d={d1} fill="none" stroke="#1f77b4" strokeWidth="1.5"/>
                          {d2 && <path d={d2} fill="none" stroke="#999" strokeWidth="1" strokeDasharray="3,2"/>}
                        </svg>
                    );
                  })()}

                  <div className="kpis">
                    <div className="kpi">
                      <div className="kpi-label">Ann.Return</div>
                      <div className={`kpi-value ${(btM.ann_return ?? 0) >= 0 ? "up" : "down"}`}>
                        {pct(btM.ann_return, 1)}
                      </div>
                    </div>
                    <div className="kpi">
                      <div className="kpi-label">MDD</div>
                      <div className="kpi-value down">{pct(btM.mdd, 1)}</div>
                    </div>
                    <div className="kpi">
                      <div className="kpi-label">Sharpe</div>
                      <div className="kpi-value">{fmt(btM.sharpe, 2)}</div>
                    </div>
                    <div className="kpi">
                      <div className="kpi-label">Winrate</div>
                      <div className="kpi-value">
                        {btM.winrate == null ? "--" : `${Math.round((btM.winrate as number) * 100)}%`}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Agents */}
              <div className="card">
                <div className="card-header">
                  <h3>Agents & Traces</h3>
                  <a href="/#/simulator" className="link">查看详情 →</a>
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
                  <li>
                    Snapshot：{snapshot?.version_tag || "--"}
                    <span
                        className="muted"> @ {(snapshot as any)?.["as_of"] ?? (snapshot as any)?.["updated_at"] ?? snapshot?.version_tag ?? "--"}</span>
                  </li>
                  <li>
                    Backtest：
                    {backtest
                        ? `${pct(btM.ann_return, 1)} ann / ${fmt(btM.sharpe, 2)} Sharpe / ${pct(btM.mdd, 1)} MDD`
                        : "--"}
                  </li>
                  <li>
                    Trace：{(decide as any)?.trace_id || (backtest as any)?.trace_id || "--"}
                  </li>
                </ul>

              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}

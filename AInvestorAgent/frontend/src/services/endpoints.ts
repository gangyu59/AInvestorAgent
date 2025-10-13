// ========================= endpoints.ts (精简去重 · 单一真源) =========================
// 说明：
// 1) 这是一个可直接覆盖旧文件的“整洁版”实现：统一 HTTP 工具 + 统一类型 + 统一导出。
// 2) 不使用默认导出；不依赖第三方库；已处理 fetch 的 RequestInit 类型兼容问题。
// 3) 兼容后端两种返回风格：{ data: ... } 或 直接返回对象/数组。

// ------------------------- 基础配置 -------------------------
export const API_BASE: string = (import.meta as any).env?.VITE_API_BASE || "";

// ------------------------- HTTP 工具 -------------------------
function ensureOk(r: Response): Response {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r;
}

export async function httpGet<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init as RequestInit).then(ensureOk);
  return (await res.json()) as T;
}

export async function httpPost<T>(url: string, body?: unknown, init?: RequestInit): Promise<T> {
  // 合并 headers（兼容 Headers/数组/字典）
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers as any || {}),
  };

  // 不在变量初始化处声明 RequestInit，避免 TS 严格模式报错
  const options = {
    ...(init || {}),
    method: "POST",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  };

  const res = await fetch(url, options as RequestInit).then(ensureOk);
  return (await res.json()) as T;
}

export async function httpPut<T>(url: string, body?: unknown, init?: RequestInit): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers as any || {}),
  };
  const options = {
    ...(init || {}),
    method: "PUT",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  };
  const res = await fetch(url, options as RequestInit).then(ensureOk);
  return (await res.json()) as T;
}

// ------------------------- 通用类型 -------------------------
export type FactorBreakdown = {
  value?: number;
  quality?: number;
  momentum?: number;
  sentiment?: number;
};

export type ScoreItem = {
  symbol: string;
  score: number;
  factors?: FactorBreakdown;
  as_of?: string;
  version_tag?: string;
};

export type Holding = {
  symbol: string;
  weight: number;
  score?: number;
  sector?: string;
  reasons?: string[];
};

// ------------------------- 健康检查 / 基础 -------------------------
export async function ping(): Promise<{ status: string }> {
  return httpGet<{ status: string }>(`${API_BASE}/health`);
}

export const analyzeEndpoint = (symbol: string) =>
  `${API_BASE}/api/analyze/${encodeURIComponent(symbol)}`;

// ------------------------- 评分 / 因子 -------------------------
export async function scoreBatch(symbols: string[]): Promise<ScoreItem[]> {
  const j = await httpPost<any>(`${API_BASE}/api/scores/batch`, { symbols });
  return Array.isArray(j?.items) ? j.items : (Array.isArray(j) ? j : []);
}

// ------------------------- 舆情 / 新闻 -------------------------
export type SentimentPoint = { date: string; score: number };
export type NewsItem = {
  title: string;
  url: string;
  score?: number;
  source?: string;
  published_at?: string;
};
export type SentimentBrief = { series: SentimentPoint[]; latest_news: NewsItem[] };

export async function fetchSentimentBrief(symbols: string[], days = 14): Promise<SentimentBrief | null> {
  try {
    const q = encodeURIComponent(symbols.join(","));
    const j = await httpGet<any>(`${API_BASE}/api/sentiment/brief?symbols=${q}&days=${days}`);
    return j?.data || j || null;
  } catch {
    return null;
  }
}

export async function fetchNews(symbol: string, days = 7, limit = 20): Promise<NewsItem[]> {
  try {
    const j = await httpGet<any>(
      `${API_BASE}/api/news/list?symbol=${encodeURIComponent(symbol)}&days=${days}&limit=${limit}`
    );
    return j?.items || j?.data || j || [];
  } catch {
    return [];
  }
}

// ------------------------- Watchlist -------------------------
export async function getWatchlist(): Promise<string[]> {
  try {
    const j = await httpGet<any>(`${API_BASE}/api/watchlist`);
    const arr = j?.items || j?.data || j;
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

export async function saveWatchlist(symbols: string[]): Promise<{ ok: boolean }> {
  try {
    const j = await httpPut<any>(`${API_BASE}/api/watchlist`, { symbols });
    return { ok: !!(j?.ok ?? true) };
  } catch {
    return { ok: false };
  }
}

// ------------------------- 组合 / 决策 / 回测 -------------------------
// 1) 多智能体/LLM 决策（/orchestrator/decide）
export type AIDecideRequest = {
  symbols: string[];
  topk?: number;
  min_score?: number;
  use_llm?: boolean;
  refresh_prices?: boolean;
  params?: Record<string, unknown>; // 例如 "risk.max_stock": 0.3
};
export type AIDecideResponse = {
  ok?: boolean;
  method?: string;                 // "llm_enhanced" | "rules" ...
  holdings: Holding[];
  snapshot_id?: string | null;
  version_tag?: string;
  reasoning?: string;
  backtest?: {
    dates: string[];
    nav: number[];
    benchmark_nav?: number[];
    drawdown?: number[];
    metrics?: Record<string, number>;
  };
};

export async function aiSmartDecide(req: AIDecideRequest): Promise<AIDecideResponse> {
  return httpPost<AIDecideResponse>(`${API_BASE}/orchestrator/decide`, req);
}

// 2) 组合建议（非 LLM，仍有风控，/api/portfolio/propose）
export type ProposePortfolioResponse = {
  snapshot_id?: string | null;
  as_of?: string;
  version_tag?: string;
  holdings: Holding[];
  sector_concentration?: Array<{ sector: string; weight: number }>;
};

export async function proposePortfolio(symbols: string[]): Promise<ProposePortfolioResponse> {
  return httpPost<ProposePortfolioResponse>(`${API_BASE}/api/portfolio/propose`, { symbols });
}

// 3) 回测（/api/backtest/run）
// ================= 修正后的 runBacktest（双路径回退 + 结果规范化） =================
export type BacktestRunRequest = {
  holdings?: Array<{ symbol: string; weight: number }>;
  snapshot_id?: string;
  window_days?: number;
  trading_cost?: number;
  rebalance?: "weekly" | "monthly";
};
export type BacktestRunResponse = {
  dates: string[];
  nav: number[];
  benchmark_nav?: number[];
  drawdown?: number[];
  metrics?: Record<string, number>;
  version_tag?: string;
};

export async function runBacktest(req: BacktestRunRequest): Promise<BacktestRunResponse> {
  const payload: any = {
    // 两种都带上，后端有哪个吃哪个；防 422
    holdings: req.holdings,
    weights: req.holdings?.map(h => ({ symbol: h.symbol, weight: h.weight })),
    snapshot_id: req.snapshot_id,
    window_days: req.window_days ?? 252,
    trading_cost: req.trading_cost ?? 0,
    rebalance: req.rebalance ?? "weekly",
  };

  const normalize = (j: any): BacktestRunResponse => {
    const d = j?.data || j || {};
    return {
      dates: d.dates || [],
      nav: d.nav || d.equity || [],
      benchmark_nav: d.benchmark_nav || d.benchmark || [],
      drawdown: d.drawdown || [],
      metrics: d.metrics || {},
      version_tag: d.version_tag,
    };
  };

  // 优先 /api/backtest/run ，失败回退到 /backtest/run
  const url1 = `${API_BASE}/api/backtest/run`;
  const url2 = `${API_BASE}/backtest/run`;
  try {
    const j1 = await httpPost<any>(url1, payload);
    return normalize(j1);
  } catch (e1) {
    const j2 = await httpPost<any>(url2, payload);
    return normalize(j2);
  }
}


// ------------------------- 旧名别名（可选；减少改动面） -------------------------
// 如果你的页面里引用了这些常量名，也可以继续工作：
export const DECIDE_API = `${API_BASE}/orchestrator/decide`;
export const PROPOSE_API = `${API_BASE}/api/portfolio/propose`;
export const RUN_BACKTEST_API = `${API_BASE}/api/backtest/run`;

// ==============================================================================

// frontend/src/services/endpoints.ts - 修复版

// ===== 统一API配置 =====
export const API_BASE: string = (import.meta as any).env?.VITE_API_BASE || "";
const JSON_HEADERS = { "Content-Type": "application/json" };
const ok = (r: Response) => {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r;
};

// ===== 类型定义 =====
export type ScoreItem = {
  symbol: string;
  score: number | { score: number; value?: number; quality?: number; momentum?: number; sentiment?: number; version_tag?: string };
  factors?: { value?: number; quality?: number; momentum?: number; sentiment?: number };
  as_of?: string;
  updated_at?: string;
  version_tag?: string;
};

export type BacktestMetrics = {
  ann_return?: number;
  mdd?: number;
  sharpe?: number;
  winrate?: number;
  max_dd?: number;
  win_rate?: number;
  annReturn?: number;
  maxDD?: number;
};

export type BacktestResponse = {
  nav?: number[];
  benchmark_nav?: number[];
  dates?: string[];
  metrics: BacktestMetrics;
  equity_nav?: number[];
  benchmark?: number[];
};

export type DecideContext = {
  weights: Record<string, number>;
  kept?: string[];
  orders?: Array<{symbol: string; action: "BUY"|"SELL"; weight?: number}>;
  backtest?: BacktestResponse;
  version_tag?: string;
};

export type DecideResponse = { context: DecideContext };

export type SnapshotBrief = {
  weights: Record<string, number>;
  metrics?: BacktestMetrics;
  version_tag?: string;
  kept?: string[];
};

export type SentimentBrief = {
  series?: Array<{ date: string; score: number }>;
  latest_news?: Array<{ title: string; url: string; score: number }>;
};

// ===== 核心功能API =====

// 批量评分 - 修复路径
export async function scoreBatch(symbols: string[]): Promise<ScoreItem[]> {
  const r = await fetch(`${API_BASE}/api/scores/batch`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ symbols }),
  }).then(ok);
  const j = await r.json();
  return Array.isArray(j?.items) ? j.items : Array.isArray(j) ? j : [];
}

// 组合建议 - 直接调用你已测试通过的接口
export async function proposePortfolio(symbols: string[]): Promise<any> {
  const r = await fetch(`${API_BASE}/api/portfolio/propose`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ symbols }),
  }).then(ok);
  return r.json();
}

// 回测 - 修复为正确的API路径
export async function runBacktest(payload: {
  weights?: Array<{symbol: string; weight: number}>;
  symbols?: string[];
  window_days?: number;
  trading_cost?: number;
  mock?: boolean;
}): Promise<BacktestResponse> {
  const r = await fetch(`${API_BASE}/api/backtest/run`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({
      weights: payload.weights || (payload.symbols || []).map(s => ({symbol: s, weight: 1.0/Math.max(payload.symbols?.length || 1, 1)})),
      window_days: payload.window_days || 180,
      trading_cost: payload.trading_cost || 0,
      mock: payload.mock !== false, // 默认true确保演示稳定
    }),
  }).then(ok);
  const j = await r.json();

  // 规范化返回结果
  const data = j?.data || j;
  return {
    nav: data?.nav || data?.equity_nav || data?.equity || [],
    benchmark_nav: data?.benchmark_nav || data?.benchmark || [],
    dates: data?.dates || [],
    metrics: data?.metrics || {},
  };
}

// 一键决策 - 调用orchestrator/decide
export async function decideNow(body: { symbols: string[]; params?: any }): Promise<DecideResponse> {
  const r = await fetch(`${API_BASE}/orchestrator/decide`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ topk: body.symbols.length, params: body.params }),
  }).then(ok);
  const j = await r.json();

  // 规范化返回格式
  return {
    context: {
      weights: {},
      kept: j?.context?.kept || [],
      orders: j?.context?.orders || [],
      version_tag: j?.context?.version_tag || "v1.0.0"
    }
  };
}

// 快照获取
export async function fetchLastSnapshot(): Promise<SnapshotBrief|null> {
  try {
    const r = await fetch(`${API_BASE}/api/portfolio/snapshot?latest=1`);
    if (!r.ok) return null;
    const j = await r.json();
    return j?.data || j || null;
  } catch {
    return null;
  }
}

// 情绪简报
export async function fetchSentimentBrief(
  symbols: string[],
  days = 14
): Promise<SentimentBrief | null> {
  const q = encodeURIComponent(symbols.join(","));
  try {
    const r = await fetch(`${API_BASE}/api/sentiment/brief?symbols=${q}&days=${days}`);
    if (!r.ok) return null;
    const j = await r.json();
    return j?.data || j || null;
  } catch {
    return null;
  }
}

// ===== 工具函数 =====
export const analyzeEndpoint = (symbol: string) => `/api/analyze/${encodeURIComponent(symbol)}`;

// 报告生成
export async function generateReport(): Promise<{content: string}> {
  const r = await fetch(`${API_BASE}/api/report/generate`, {
    method: "POST",
    headers: JSON_HEADERS,
  }).then(ok);
  return r.json();
}

// ===== 兼容性导出（为旧文件提供支持） =====
export const BACKTEST_RUN = `${API_BASE}/api/backtest/run`;

// 修复PRICES函数 - 使用存在的接口
export const PRICES = (symbol: string, days = 180) => {
  // 先尝试你现有的daily接口
  return `${API_BASE}/api/prices/daily?symbol=${encodeURIComponent(symbol)}&limit=${days}`;
};

// 修复价格系列获取函数
export type PricePoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export async function fetchPriceSeries(
  symbol: string,
  opts?: { range?: string; limit?: number; adjusted?: boolean }
): Promise<PricePoint[]> {
  const limit = opts?.limit ?? 180;
  const s = encodeURIComponent(symbol);

  // 1) 直接查 daily - 使用正确的返回格式解析
  try {
    const raw = await fetch(`${API_BASE}/api/prices/daily?symbol=${s}&limit=${limit}`);
    if (!raw.ok) throw new Error("");
    const j = await raw.json();

    // 解析你的API返回格式：{"symbol":"AAPL","items":[...]}
    const arr = j?.items || [];
    const norm = arr.map((d: any) => ({
      date: d.date,
      close: +(d.close || 0),
      open: +(d.open || d.close || 0),
      high: +(d.high || d.close || 0),
      low: +(d.low || d.close || 0),
      volume: d.volume || 0,
    }))
    .filter((x: any) => x.date && Number.isFinite(x.close))
    .sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime());

    if (norm.length) return norm.slice(-limit);
  } catch (e) {
    console.warn(`获取 ${symbol} 价格数据失败:`, e);
  }

  // 2) 兜底：返回空数组而不是抛错
  console.warn(`无法获取 ${symbol} 的价格数据`);
  return [];
}
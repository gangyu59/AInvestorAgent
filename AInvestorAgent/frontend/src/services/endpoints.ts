// frontend/src/services/endpoints.ts

// --------- 配置 ---------
const API = import.meta.env.VITE_API_BASE || ""; // 你 .env 里用的变量名 VITE_API_BASE

const JSON_HEADERS = { "Content-Type": "application/json" };
const ok = (r: Response) => {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r;
};

// --------- 类型 ---------
export type ScoreItem = {
  symbol: string;
  score: number;
  factors?: { value?: number; quality?: number; momentum?: number; sentiment?: number };
  as_of?: string;
  version_tag?: string;
};

export type BacktestMetrics = {
  ann_return?: number;
  sharpe?: number;
  mdd?: number;
  winrate?: number;
  turnover?: number;
};

export type BacktestResponse = {
  nav?: number[];
  benchmark_nav?: number[];
  metrics?: BacktestMetrics;
};

export type DecideContext = {
  kept?: string[];
  orders?: any[];
  weights?: Record<string, number>;
  explain?: Record<string, string[]>;
  backtest?: BacktestResponse;
  version_tag?: string;
};

export type DecideResponse = {
  ok?: boolean;
  success?: boolean;
  context: DecideContext;
};

export type SentimentBrief = {
  latest_news: { title: string; url: string; score: number; published_at?: string }[];
};

export type SnapshotBrief = {
  weights: Record<string, number>;
  metrics?: BacktestMetrics;
  kept?: string[];
  version_tag?: string;
};

// --------- 实现 ---------

// 决策（兼容端点，无 /api 前缀；由 backend/app.py 直挂）
export async function decideNow(payload: { symbols: string[] }): Promise<DecideResponse> {
  const r = await fetch(`${API}/orchestrator/decide`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({
      symbols: payload.symbols,
      topk: 10,
      min_score: 50,
      params: { "risk.max_stock": 0.3 },
    }),
  }).then(ok);
  return (await r.json()) as DecideResponse;
}

// 回测（大多数项目是 /api/backtest/run；若 404，请打开 /docs 看实际前缀后替换）
export async function runBacktest(payload: {
  symbols: string[];
  weeks: number;
  rebalance: "weekly" | "monthly";
}): Promise<BacktestResponse> {
  const r = await fetch(`${API}/api/backtest/run`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  }).then(ok);
  return (await r.json()) as BacktestResponse;
}

// 批量评分（常见是 /api/scores/batch；若你的路由是 /api/score/batch 就把下面这行改掉）
export async function scoreBatch(symbols: string[]): Promise<ScoreItem[]> {
  const r = await fetch(`${API}/api/scores/batch`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ symbols }),
  }).then(ok);
  const j = await r.json();
  return Array.isArray(j) ? (j as ScoreItem[]) : (j.items || []);
}

// 新闻情绪简表（如果后端无该端点，返回空态即可）
export async function fetchSentimentBrief(symbols: string[]): Promise<SentimentBrief | null> {
  try {
    const q = symbols.slice(0, 5).join(",");
    const r = await fetch(`${API}/api/news/brief?symbols=${encodeURIComponent(q)}&days=7`);
    if (!r.ok) return { latest_news: [] };
    return (await r.json()) as SentimentBrief;
  } catch {
    return { latest_news: [] };
  }
}

// 最近一次组合快照（若后端实际为 /api/portfolio/last，请替换为真实路径）
export async function fetchLastSnapshot(): Promise<SnapshotBrief | null> {
  try {
    const r = await fetch(`${API}/api/portfolio/last`);
    if (!r.ok) return null;
    return (await r.json()) as SnapshotBrief;
  } catch {
    return null;
  }
}


// ====== Price Series ======
export type PricePoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "";

async function _json<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} @ ${url}`);
  return r.json();
}

/**
 * 优先调用你已有的价格接口；按候选列表逐个尝试，拿到就规范化返回。
 * 你之前后端有 /api/prices/fetch /daily /query 等接口；这里都做了兼容。
 */
export async function fetchPriceSeries(
  symbol: string,
  opts?: { range?: string; limit?: number; adjusted?: boolean }
): Promise<PricePoint[]> {
  const range = opts?.range ?? "6mo";
  const limit = opts?.limit ?? 200;
  const adjusted = opts?.adjusted ?? false;

  const s = encodeURIComponent(symbol);
  const cand = [
    `${API_BASE}/api/prices/series?symbol=${s}&range=${range}&adjusted=${adjusted}`,
    `${API_BASE}/api/prices/line?symbol=${s}&range=${range}&adjusted=${adjusted}`,
    `${API_BASE}/api/prices/query?symbol=${s}&limit=${limit}&adjusted=${adjusted}`,
    `${API_BASE}/api/prices/daily?symbol=${s}&limit=${limit}&adjusted=${adjusted}`,
    `${API_BASE}/api/prices?symbol=${s}&limit=${limit}&adjusted=${adjusted}`,
  ];

  let lastErr: any = null;
  for (const url of cand) {
    try {
      const raw = await _json<any>(url);
      const arr: any[] =
        Array.isArray(raw) ? raw
        : Array.isArray(raw?.data) ? raw.data
        : Array.isArray(raw?.prices) ? raw.prices
        : Array.isArray(raw?.rows) ? raw.rows
        : [];

      if (arr.length) {
        const norm: PricePoint[] = arr.map((d: any) => ({
          date: d.date ?? d.ts ?? d.t ?? d[0],
          open: +(d.open ?? d.o ?? d[1]),
          high: +(d.high ?? d.h ?? d[2]),
          low:  +(d.low  ?? d.l ?? d[3]),
          close:+(d.close?? d.c ?? d[4]),
          volume: d.volume ?? d.v ?? d[5],
        }))
        .filter(x => x.date && Number.isFinite(x.close))
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        if (norm.length) return norm;
      }
    } catch (e) {
      lastErr = e;
    }
  }
  throw new Error(`无法获取 ${symbol} 的价格数据${lastErr ? `：${String(lastErr)}` : ""}`);
}

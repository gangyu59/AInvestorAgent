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

async function _json<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`HTTP ${r.status} @ ${url}`);
  return r.json();
}

function _limitForRange(r?: string) {
  const key = (r || "6mo").toLowerCase();
  const map: Record<string, number> = {
    "1mo": 24, "3mo": 75, "6mo": 150, "1y": 260, "ytd": 200, "max": 1000,
  };
  return map[key] ?? 150;
}

function _normDailyPayload(raw: any): PricePoint[] {
  const arr: any[] =
    Array.isArray(raw?.items) ? raw.items : // 你测试页就是这个结构
    Array.isArray(raw?.data) ? raw.data :
    Array.isArray(raw) ? raw : [];
  const norm = arr.map((d: any) => ({
    date: d.date ?? d.ts ?? d.t ?? d[0],
    // 有些 daily 只返回 close/volume，这里容错：open/high/low=close
    close: +(d.close ?? d.c ?? d[4]),
    open: +(d.open ?? d.o ?? d.close ?? d.c ?? d[1] ?? d[4]),
    high: +(d.high ?? d.h ?? d.close ?? d.c ?? d[2] ?? d[4]),
    low:  +(d.low  ?? d.l ?? d.close ?? d.c ?? d[3] ?? d[4]),
    volume: d.volume ?? d.v ?? d[5],
  }))
  .filter(x => x.date && Number.isFinite(x.close))
  .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  return norm;
}

/** 从 orchestrator/dispatch 的 trace 中提取 Ingestor 输出的 prices（兜底） */
function _extractPricesFromTrace(raw: any): PricePoint[] | null {
  const steps: any[] =
    Array.isArray(raw?.trace) ? raw.trace :
    Array.isArray(raw?.data?.trace) ? raw.data.trace : [];
  for (const s of steps) {
    const name = String(s?.name || s?.agent || s?.step || s?.step_name || "");
    if (name.toLowerCase().includes("ingest")) {
      const arr: any[] = s?.data?.prices || s?.result?.data?.prices || [];
      if (Array.isArray(arr) && arr.length) {
        const norm = arr.map(d => ({
          date: d.date ?? d.ts ?? d.t,
          close: +(d.close ?? d.c),
          open: +(d.open ?? d.o ?? d.close ?? d.c),
          high: +(d.high ?? d.h ?? d.close ?? d.c),
          low:  +(d.low  ?? d.l ?? d.close ?? d.c),
          volume: d.volume ?? d.v,
        }))
        .filter(x => x.date && Number.isFinite(x.close))
        .sort((a,b)=> new Date(a.date).getTime() - new Date(b.date).getTime());
        if (norm.length) return norm;
      }
    }
  }
  return null;
}

/**
 * 获取价格序列 —— 与你的测试页一致：
 * 1) 直接查 /api/prices/daily；2) 若空则先 POST /api/prices/fetch 再查 daily；
 * 3) 仍无则兜底 orchestrator（可 mock）保证能画图。
 */
export async function fetchPriceSeries(
  symbol: string,
  opts?: { range?: string; limit?: number; adjusted?: boolean }
): Promise<PricePoint[]> {
  const limit = opts?.limit ?? _limitForRange(opts?.range);
  const s = encodeURIComponent(symbol);

  // 1) 直接查 daily
  try {
    const raw = await _json<any>(`${API_BASE}/api/prices/daily?symbol=${s}&limit=${limit}`);
    const norm = _normDailyPayload(raw);
    if (norm.length) return norm.slice(-limit);
  } catch { /* 继续 */ }

  // 2) 拉取并入库，然后再查 daily（严格复刻你的测试页做法） :contentReference[oaicite:1]{index=1}
  try {
    const fetchUrl = `${API_BASE}/api/prices/fetch?symbol=${s}&adjusted=${opts?.adjusted ?? true}&outputsize=compact`;
    await _json<any>(fetchUrl, { method: "POST" });                                    // fetch 并入库  :contentReference[oaicite:2]{index=2}
    const raw2 = await _json<any>(`${API_BASE}/api/prices/daily?symbol=${s}&limit=${limit}`); // 再查 daily  :contentReference[oaicite:3]{index=3}
    const norm2 = _normDailyPayload(raw2);
    if (norm2.length) return norm2.slice(-limit);
  } catch { /* 继续 */ }

  // 3) 兜底：orchestrator（真实→mock）
  for (const payload of [
    { symbol, params: { news_days: 7 } },
    { symbol, params: { news_days: 7, mock: true } },
  ]) {
    try {
      const raw = await _json<any>(`${API_BASE}/orchestrator/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const norm = _extractPricesFromTrace(raw);
      if (norm && norm.length) return norm.slice(-limit);
    } catch { /* ignore and keep trying */ }
  }

  throw new Error(`无法获取 ${symbol} 的价格数据（daily / fetch / orchestrator 均无返回）`);
}

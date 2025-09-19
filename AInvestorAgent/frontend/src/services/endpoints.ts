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


// ========== Backtest ==========
function _decodeBacktest(j: any): BacktestResponse | null {
  // 直接 backtest 接口返回
  const direct = j?.data ?? j;
  if (Array.isArray(direct?.nav) || Array.isArray(direct?.benchmark_nav)) {
    return {
      nav: direct.nav || [],
      benchmark_nav: direct.benchmark_nav || [],
      dates: direct.dates || [],
      metrics: direct.metrics || {},
    };
  }
  return null;
}
function _decodeFromContext(j: any): BacktestResponse | null {
  const ctx = j?.context ?? j?.data?.context ?? null;
  if (!ctx) return null;
  const nav = ctx.nav || ctx.backtest?.nav || [];
  const bn  = ctx.benchmark_nav || ctx.backtest?.benchmark_nav || [];
  const dates = ctx.dates || ctx.backtest?.dates || [];
  const metrics = ctx.metrics || ctx.backtest?.metrics || {};
  if (nav?.length || bn?.length) return { nav, benchmark_nav: bn, dates, metrics };
  return null;
}

export async function runBacktest(payload: {
  symbols: string[];
  weeks?: number;
  rebalance?: "weekly" | "monthly";
}): Promise<BacktestResponse> {
  const headers = { "Content-Type": "application/json" };

  // 先试稳定接口
  try {
    const r = await fetch(`${API_BASE}/backtest/run`, { method: "POST", headers, body: JSON.stringify(payload) });
    if (r.ok) {
      const j = await r.json();
      const d = j?.data ?? j;
      if (Array.isArray(d?.nav) || Array.isArray(d?.benchmark_nav)) {
        return { nav: d.nav || [], benchmark_nav: d.benchmark_nav || [], dates: d.dates || [], metrics: d.metrics || {} };
      }
    }
  } catch {}

  // 再试 orchestrator（拍平在 context 或 trace）
  try {
    const r = await fetch(`${API_BASE}/orchestrator/propose_backtest`, {
      method: "POST", headers,
      body: JSON.stringify({ symbols: payload.symbols, params: { weeks: payload.weeks ?? 52, rebalance: payload.rebalance ?? "weekly" } })
    });
    if (r.ok) {
      const j = await r.json();
      const ctx = j?.context ?? j?.data?.context ?? {};
      const direct = ctx?.backtest ? ctx.backtest :
        (ctx?.nav || ctx?.benchmark_nav ? { nav: ctx.nav, benchmark_nav: ctx.benchmark_nav, dates: ctx.dates, metrics: ctx.metrics } : null);
      if (direct) return { nav: direct.nav || [], benchmark_nav: direct.benchmark_nav || [], dates: direct.dates || [], metrics: direct.metrics || {} };

      const t = extractFromTrace(j);
      if (t?.backtest) return t.backtest;
    }
  } catch {}

  // 兜底：返回空，不抛错
  return { nav: [], benchmark_nav: [], dates: [], metrics: {} };
}



// ========== Snapshot ==========
export type SnapshotBrief = {
  weights: Record<string, number>;
  metrics?: BacktestMetrics;
  version_tag?: string;
  kept?: string[];
};
export async function fetchLastSnapshot(): Promise<SnapshotBrief|null> {
  const cands = [
    `${API_BASE}/api/portfolio/snapshot?latest=1`,
    `${API_BASE}/portfolio/snapshot?latest=1`,
  ];
  for (const u of cands) {
    try {
      const r = await fetch(u);
      if (!r.ok) throw new Error(String(r.status));
      const j = await r.json();
      const data = j?.data || j || null;
      if (data && data.weights) return data;
    } catch {}
  }
  return null;
}

// ========== Sentiment / News ==========
export type SentimentBrief = {
  series?: Array<{ date: string; score: number }>;
  latest_news?: Array<{ title: string; url: string; score: number }>;
};
export async function fetchSentimentBrief(symbols: string[], days = 7): Promise<SentimentBrief|null> {
  const q = encodeURIComponent(symbols.join(","));
  const cands = [
    `${API_BASE}/api/sentiment/brief?symbols=${q}&days=${days}`,
    `${API_BASE}/news/sentiment?symbols=${q}&days=${days}`,
  ];
  for (const u of cands) {
    try {
      const r = await fetch(u);
      if (!r.ok) throw new Error(String(r.status));
      const j = await r.json();
      return j?.data || j || null;
    } catch {}
  }
  // orchestrator 兜底（从 trace 的 research/news 步骤拿）
  try {
    const r = await fetch(`${API_BASE}/orchestrator/dispatch`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ symbol: symbols[0], params: { news_days: days } })
    });
    if (r.ok) {
      const j = await r.json();
      const steps = j?.trace || j?.data?.trace || [];
      for (const s of steps) {
        const data = s?.data || s?.result?.data;
        if (data?.sentiment || data?.latest_news) {
          return { series: data.series || data.sentiment, latest_news: data.latest_news };
        }
      }
    }
  } catch {}
  return null;
}

// ========== Rules ==========
export type Rules = {
  "risk.max_stock"?: number;
  "risk.max_sector"?: number;
  "risk.min_positions"?: number;
  "risk.max_positions"?: number;
  [k: string]: any;
};
export async function getRules(): Promise<Rules> {
  for (const u of [`${API_BASE}/api/rules`, `${API_BASE}/rules`]) {
    try { const r = await fetch(u); if (!r.ok) throw new Error(""); return await r.json(); } catch {}
  }
  return {};
}
export async function updateRules(body: Rules): Promise<void> {
  for (const u of [`${API_BASE}/api/rules`, `${API_BASE}/rules`]) {
    try {
      const r = await fetch(u, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
      if (!r.ok) throw new Error("");
      return;
    } catch {}
  }
  throw new Error("保存失败");
}

// ========== Reports ==========
export type ReportInfo = { id?: string; name?: string; created_at?: string; url?: string };
export async function triggerReport(): Promise<void> {
  for (const u of [`${API_BASE}/api/report/generate`, `${API_BASE}/reports/generate`]) {
    try { const r = await fetch(u, { method: "POST" }); if (!r.ok) throw new Error(""); return; } catch {}
  }
  throw new Error("触发报告失败");
}
export async function listReports(): Promise<ReportInfo[]> {
  for (const u of [`${API_BASE}/api/reports`, `${API_BASE}/api/report/list`, `${API_BASE}/reports`]) {
    try { const r = await fetch(u); if (!r.ok) throw new Error(""); const j = await r.json(); return j?.data || j || []; } catch {}
  }
  return [];
}


// 类型同你现有定义即可
export type BacktestMetrics = { ann_return?: number; mdd?: number; sharpe?: number; winrate?: number };
export type BacktestResponse = { nav?: number[]; benchmark_nav?: number[]; dates?: string[]; metrics: BacktestMetrics };
export type DecideContext = {
  weights: Record<string, number>;
  kept?: string[];
  orders?: Array<{symbol: string; action: "BUY"|"SELL"; weight?: number}>;
  backtest?: BacktestResponse;
  version_tag?: string;
};
export type DecideResponse = { context: DecideContext };

function decodeBacktestFromContext(ctx: any): BacktestResponse | undefined {
  if (!ctx) return undefined;
  const nav = ctx.nav || ctx.backtest?.nav;
  const bn  = ctx.benchmark_nav || ctx.backtest?.benchmark_nav;
  const dates = ctx.dates || ctx.backtest?.dates;
  const metrics = ctx.metrics || ctx.backtest?.metrics;
  if (nav || bn || metrics) return { nav, benchmark_nav: bn, dates, metrics: metrics || {} };
  return undefined;
}


// ---- helpers ----
function toWeightObj(w: any): Record<string, number> {
  const out: Record<string, number> = {};
  if (!w) return out;
  if (Array.isArray(w)) {
    for (const it of w) {
      const sym = it?.["symbol"] ?? it?.["ticker"] ?? it?.["code"] ?? it?.["id"];
      const wt  = it?.["weight"] ?? it?.["w"] ?? it?.["target"] ?? it?.["ratio"];
      if (sym && wt != null && isFinite(+wt)) out[sym] = +wt;
    }
    return out;
  }
  if (typeof w === "object") {
    for (const k of Object.keys(w)) {
      const v = (w as any)[k];
      if (v != null && isFinite(+v)) out[k] = +v;
    }
  }
  return out;
}

function extractFromTrace(raw: any) {
  const steps: any[] = Array.isArray(raw?.trace) ? raw.trace :
                       Array.isArray(raw?.data?.trace) ? raw.data.trace : [];
  const ctx: any = {};
  for (const s of steps) {
    const name = String(s?.name || s?.step_name || s?.agent || "");
    const data = s?.data ?? s?.result?.data ?? {};
    // 有些实现把组合放在 portfolio / decide / weights 字段里
    const w = data?.weights ?? data?.portfolio?.weights ?? data?.result?.weights;
    if (!ctx.weights && w) ctx.weights = toWeightObj(w);
    if (!ctx.orders && data?.orders) ctx.orders = data?.orders;
    if (!ctx.kept && data?.kept) ctx.kept = data?.kept;
    // 回测可能拍平在 data 顶层
    if (!ctx.backtest && (data?.nav || data?.benchmark_nav || data?.metrics)) {
      ctx.backtest = { nav: data.nav, benchmark_nav: data.benchmark_nav, dates: data.dates, metrics: data.metrics ?? {} };
    }
  }
  return ctx;
}

function normalizeDecide(payload: any): DecideResponse {
  const base = payload?.context ?? payload?.data?.context ?? payload?.data ?? {};
  const traceCtx = extractFromTrace(payload);
  const weights = toWeightObj(base?.weights) || traceCtx.weights || {};
  const kept    = base?.kept ?? traceCtx.kept ?? [];
  const orders  = base?.orders ?? traceCtx.orders ?? [];
  const version_tag = base?.version_tag ?? base?.version ?? base?.tag;
  const backtest = (base?.backtest
    || (base?.nav || base?.benchmark_nav || base?.metrics ? {
         nav: base.nav, benchmark_nav: base.benchmark_nav, dates: base.dates, metrics: base.metrics ?? {}
       } : undefined)
    || traceCtx.backtest) as BacktestResponse | undefined;
  return { context: { weights, kept, orders, version_tag, backtest } };
}

// ---- decideNow：只打 /orchestrator/decide ----
export async function decideNow(body: { symbols: string[]; params?: any }): Promise<DecideResponse> {
  const headers = { "Content-Type": "application/json" };
  const payload = { symbols: body.symbols, params: body.params };
  const r = await fetch(`${API_BASE}/orchestrator/decide`, {
    method: "POST", headers, body: JSON.stringify(payload)
  });
  if (!r.ok) throw new Error(`decide ${r.status}`);
  const j = await r.json();
  return normalizeDecide(j);
}


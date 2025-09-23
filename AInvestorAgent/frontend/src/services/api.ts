// frontend/src/services/api.ts
import {
  PRICES,
  FUNDAMENTALS,
  METRICS,
  ANALYZE,
  SCORE_BATCH,
  PORTFOLIO_PROPOSE,
  BACKTEST_RUN,
} from "./endpoints";

// -------- 基础类型 --------
export type PricePoint = [string, number];

export type PriceSeriesResp = {
  symbol: string;
  series: PricePoint[];
  ma?: Record<string, number[]>; // { "5":[], "20":[], ... }
};

export type FundamentalsResp = {
  symbol: string;
  pe: number; pb: number; roe: number; net_margin: number;
  market_cap: number; sector: string; industry?: string;
};

export type MetricsResp = {
  symbol: string;
  one_m: number; three_m: number; twelve_m: number;
};

export type AnalyzeResp = {
  symbol: string;
  as_of: string;
  price: { series: PricePoint[]; ma?: Record<string, number[]> };
  fundamentals: FundamentalsResp;
  factors: { value: number; quality: number; momentum: number; risk?: number; sentiment: number };
  score: { value: number; quality: number; momentum: number; sentiment: number; score: number; version_tag: string };
  sentiment_timeline: Array<{ date: string; score: number; n?: number }>;
};

// 批量评分（B）
export type FactorBreakdown = {
  f_value?: number; f_quality?: number; f_momentum?: number; f_sentiment?: number; f_risk?: number;
};
export type ScoreDetail = {
  value: number; quality: number; momentum: number; sentiment: number; score: number; version_tag: string;
};
export type BatchScoreItem = {
  symbol: string;
  factors: FactorBreakdown;
  score: ScoreDetail;
  updated_at: string;
};
export type BatchScoreResponse = {
  items: BatchScoreItem[];
  as_of: string;
  version_tag: string;
};

// 组合 & 回测
export type Holding = { symbol: string; weight: number; score?: number; sector?: string; reasons?: string[] };
export type ProposeResp = {
  holdings: Holding[];
  sector_concentration: [string, number][];
  as_of: string;
  version_tag: string;
  snapshot_id?: string;
};

export type BacktestRunReq =
  | { holdings: Holding[]; window?: string; cost?: number; rebalance?: string; max_trades_per_week?: number }
  | { snapshot_id: string; window?: string; cost?: number; rebalance?: string; max_trades_per_week?: number };

export type BacktestResp = {
  dates: string[];
  nav: number[];
  benchmark_nav: number[];
  drawdown: number[];
  metrics: { ann_return: number; max_dd: number; sharpe: number; win_rate: number };
  params: { window: string; cost: number; rebalance?: string; max_trades_per_week?: number };
  version_tag: string;
};

// -------- 通用 fetch --------
async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.json() as Promise<T>;
}

async function postJson<T>(url: string, body: any): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.json() as Promise<T>;
}

// -------- 具体 API --------
export async function fetchPrices(symbol: string, days = 180) {
  return getJson<PriceSeriesResp>(PRICES(symbol, days));
}

export async function fetchFundamentals(symbol: string) {
  return getJson<FundamentalsResp>(FUNDAMENTALS(symbol));
}

export async function fetchMetrics(symbol: string) {
  return getJson<MetricsResp>(METRICS(symbol));
}

export async function analyze(symbol: string) {
  return getJson<AnalyzeResp>(ANALYZE(symbol));
}

// 冲刺B：批量评分（默认真实数据）
export async function scoreBatch(symbols: string[], mock = false) {
  const data = await postJson<BatchScoreResponse>(SCORE_BATCH, { symbols, mock });
  return data.items; // 页面通常只关心 items
}

// 组合建议
export async function portfolioPropose(symbols: string[], constraints?: Record<string, any>) {
  const body = { symbols, ...(constraints ? { constraints } : {}) };
  return postJson<ProposeResp>(PORTFOLIO_PROPOSE, body);
}

// 回测
export async function backtestRun(payload: BacktestRunReq) {
  return postJson<BacktestResp>(BACKTEST_RUN, payload);
}

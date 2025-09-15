// frontend/src/services/api.ts
import { PRICES } from "./endpoints";

export async function fetchPrices(symbol: string, range = "3M", refresh = false) {
  const resp = await fetch(PRICES(symbol, range, refresh));
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}


// frontend/src/services/api.ts
import { FUNDAMENTALS, METRICS } from "./endpoints";

export type FundamentalsResp = {
  symbol: string;
  pe: number; pb: number; roe: number; net_margin: number;
  market_cap: number; sector: string; industry: string; as_of: string;
};

export async function fetchFundamentals(symbol: string): Promise<FundamentalsResp> {
  const r = await fetch(FUNDAMENTALS(symbol));
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type MetricsResp = {
  symbol: string;
  one_month_change: number;
  three_months_change: number;
  twelve_months_change: number;
  volatility: number;
  as_of: string;
};

export async function fetchMetrics(symbol: string): Promise<MetricsResp> {
  const r = await fetch(METRICS(symbol));
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

import { ORCH_PROPOSE, ORCH_PROPOSE_BACKTEST, BACKTEST_RUN } from './endpoints';

type Candidate = {
  symbol: string; sector?: string; score: number;
  factors?: Record<string, number>;
};

export async function proposePortfolio(candidates: Candidate[], params?: Record<string, any>) {
  const r = await fetch(ORCH_PROPOSE, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ candidates, params })
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json(); // { success, context:{ proposal, kept, concentration, actions }, trace:[...] }
}

export async function proposeAndBacktest(candidates: Candidate[], params?: Record<string, any>) {
  const r = await fetch(ORCH_PROPOSE_BACKTEST, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ candidates, params })
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json(); // { success, context:{ kept, dates, nav, benchmark_nav, metrics, ... }, trace:[...] }
}

type WeightItem = { symbol: string; weight: number };
export async function runBacktest(payload: {
  kept?: any[]; weights?: WeightItem[];
  start?: string; end?: string; window_days?: number;
  trading_cost?: number; benchmark_symbol?: string; mock?: boolean;
}) {
  const r = await fetch(BACKTEST_RUN, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json(); // { success, data:{ dates, nav, drawdown, benchmark_nav, metrics{...} } }
}

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

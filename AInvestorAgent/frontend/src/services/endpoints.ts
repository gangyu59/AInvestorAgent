// frontend/src/services/endpoints.ts
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const PRICES = (symbol: string, range = "3M") =>
  `${API_BASE}/prices/${symbol}?range=${range}`;

export const FUNDAMENTALS = (symbol: string) =>
  `${API_BASE}/fundamentals/${symbol}`;

export const METRICS = (symbol: string) =>
  `${API_BASE}/metrics/${symbol}`;

// 新增三个端点（保持已有常量风格）
export const ORCH_PROPOSE = '/orchestrator/propose';
export const ORCH_PROPOSE_BACKTEST = '/orchestrator/propose_backtest';
export const BACKTEST_RUN = '/backtest/run';

export type TestRun = {
  timestamp: string;
  duration_sec: number;
  target: string;
  pass_rate: number;
  return_code: number;
  stats: {
    total: number; passed: number; failed: number; skipped: number;
    xfailed: number; xpassed: number; errors: number;
  };
  junit_xml?: string | null;
  html_report?: string | null;
};

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function fetchRuns(limit = 50): Promise<TestRun[]> {
  const r = await fetch(`${API_BASE}/qa/test_runs?limit=${limit}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function fetchLatest(): Promise<TestRun> {
  const r = await fetch(`${API_BASE}/qa/latest`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function fetchLastReport(): Promise<{exists: boolean; path: string}> {
  const r = await fetch(`${API_BASE}/qa/last_report`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

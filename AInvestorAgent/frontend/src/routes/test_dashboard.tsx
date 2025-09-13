import React from "react";
import PassRateChart from "../components/qa/PassRateChart";
import SuiteBar from "../components/qa/SuiteBar";
import RecentRunsTable from "../components/qa/RecentRunsTable";
import { fetchRuns, fetchLatest, fetchLastReport, TestRun } from "../services/qa";

export default function TestDashboard() {
  const [runs, setRuns] = React.useState<TestRun[]>([]);
  const [latest, setLatest] = React.useState<TestRun | null>(null);
  const [auto, setAuto] = React.useState(true);
  const [intervalMs, setIntervalMs] = React.useState(10000);

  const load = React.useCallback(async () => {
    try {
      const [rs, lt] = await Promise.all([fetchRuns(50), fetchLatest().catch(() => null)]);
      setRuns(rs);
      setLatest(lt || (rs.length ? rs[0] : null));
    } catch (e) {
      console.error(e);
    }
  }, []);

  React.useEffect(() => {
    load();
    if (!auto) return;
    const id = setInterval(load, intervalMs);
    return () => clearInterval(id);
  }, [auto, intervalMs, load]);

  return (
    <div className="p-4 text-white space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">测试仪表盘</h1>
        <label className="text-sm opacity-80 flex items-center gap-2">
          <input type="checkbox" checked={auto} onChange={e => setAuto(e.target.checked)} />
          自动刷新
        </label>
        <select
          className="bg-[#0f1115] border border-gray-700 rounded px-2 py-1 text-sm"
          value={intervalMs}
          onChange={e => setIntervalMs(Number(e.target.value))}
        >
          <option value={5000}>5s</option>
          <option value={10000}>10s</option>
          <option value={30000}>30s</option>
          <option value={60000}>60s</option>
        </select>
        <button
          className="ml-auto border border-gray-700 rounded px-3 py-1 text-sm hover:bg-[#141820]"
          onClick={load}
        >手动刷新</button>
        <a
          className="border border-gray-700 rounded px-3 py-1 text-sm hover:bg-[#141820]"
          href="/reports/last_report.html" target="_blank" rel="noreferrer"
        >打开最新HTML报告</a>
      </div>

      <PassRateChart runs={runs} />
      <SuiteBar latest={latest} />
      <RecentRunsTable runs={runs} />
    </div>
  );
}

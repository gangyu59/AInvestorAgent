import React, { useEffect, useMemo, useState } from "react";
import KPIGrid from "../components/cards/KPIGrid";
import RequestsChart from "../components/charts/RequestsChart";
import EventsTable from "../components/tables/EventsTable";

type KPIData = {
  fetchStatus: string;
  updatedAt: string;
  reqToday: number;
  rateRemaining: string;
  queueSize: number;
  queueRunning: number;
  alertCount: number;
  alertLatest: string;
};

type MetricPoint = { label: string; value: number };
type EventRow = { time: string; level: "INFO" | "WARN" | "ERROR"; module: string; msg: string };

const MonitorPage: React.FC = () => {
  const [kpi, setKpi] = useState<KPIData | null>(null);
  const [metric, setMetric] = useState<"requests" | "latency" | "errors">("requests");
  const [series, setSeries] = useState<MetricPoint[]>([]);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [level, setLevel] = useState<"" | "info" | "warn" | "error">("");
  const [keyword, setKeyword] = useState("");

  // TODO: 与后端对接时，替换为真实接口（请在 frontend/src/services/endpoints.ts 里补常量，不改命名）
  async function loadKPIs() {
    // const res = await fetch(ENDPOINTS.MONITOR.KPIS).then(r => r.json());
    const mock: KPIData = {
      fetchStatus: "正常",
      updatedAt: new Date().toLocaleString(),
      reqToday: 128,
      rateRemaining: "4/5 rpm",
      queueSize: 2,
      queueRunning: 1,
      alertCount: 0,
      alertLatest: "—",
    };
    setKpi(mock);
  }

  async function loadSeries(m: typeof metric) {
    // const res = await fetch(`${ENDPOINTS.MONITOR.METRICS}?metric=${m}`).then(r=>r.json());
    const pts = Array.from({ length: 24 }, (_, i) => ({
      label: `${i}:00`,
      value: Math.round(Math.random() * (m === "latency" ? 300 : m === "errors" ? 10 : 120)),
    }));
    setSeries(pts);
  }

  async function loadEvents() {
    // const res = await fetch(`${ENDPOINTS.MONITOR.EVENTS}?level=${level}&q=${encodeURIComponent(keyword)}`).then(r=>r.json());
    const rows: EventRow[] = [
      { time: new Date().toLocaleString(), level: "INFO", module: "fetcher", msg: "抓取 AAPL 成功" },
      { time: new Date().toLocaleString(), level: "WARN", module: "rate", msg: "接近速率限制" },
    ];
    setEvents(rows);
  }

  useEffect(() => {
    loadKPIs();
    loadSeries(metric);
    loadEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadSeries(metric);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metric]);

  const filteredEvents = useMemo(() => {
    return events.filter((r) => {
      const okLevel = !level || r.level.toLowerCase() === level;
      const okKeyword = !keyword || r.msg.includes(keyword) || r.module.includes(keyword);
      return okLevel && okKeyword;
    });
  }, [events, level, keyword]);

  return (
    <div className="container app-content">
      <KPIGrid data={kpi || undefined} />
      <div className="card">
        <div className="card-header row between center">
          <h2 className="card-title">近24小时趋势</h2>
          <div className="row gap-8">
            <select
              className="select"
              value={metric}
              onChange={(e) => setMetric(e.target.value as typeof metric)}
            >
              <option value="requests">请求数</option>
              <option value="latency">平均延迟(ms)</option>
              <option value="errors">错误数</option>
            </select>
            <button className="btn primary" onClick={() => { loadKPIs(); loadSeries(metric); loadEvents(); }}>
              刷新
            </button>
          </div>
        </div>
        <div className="card-body">
          <RequestsChart points={series} />
        </div>
      </div>

      <div className="card">
        <div className="card-header row between center">
          <h2 className="card-title">事件流</h2>
          <div className="row gap-8">
            <input
              className="input"
              placeholder="关键字过滤…"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <select
              className="select"
              value={level}
              onChange={(e) => setLevel(e.target.value as typeof level)}
            >
              <option value="">级别：全部</option>
              <option value="info">INFO</option>
              <option value="warn">WARN</option>
              <option value="error">ERROR</option>
            </select>
          </div>
        </div>
        <div className="card-body">
          <EventsTable rows={filteredEvents} />
        </div>
      </div>
    </div>
  );
};

export default MonitorPage;

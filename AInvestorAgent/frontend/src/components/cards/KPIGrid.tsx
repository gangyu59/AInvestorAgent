import React from "react";

type KPI = {
  fetchStatus: string;
  updatedAt: string;
  reqToday: number;
  rateRemaining: string;
  queueSize: number;
  queueRunning: number;
  alertCount: number;
  alertLatest: string;
};

const KPIGrid: React.FC<{ data?: KPI | null }> = ({ data }) => {
  const k = data || {
    fetchStatus: "—",
    updatedAt: "—",
    reqToday: 0,
    rateRemaining: "—",
    queueSize: 0,
    queueRunning: 0,
    alertCount: 0,
    alertLatest: "—",
  };

  return (
    <section className="grid kpi-grid">
      <div className="card kpi-card">
        <div className="kpi-title">数据抓取状态</div>
        <div className="kpi-value">{k.fetchStatus}</div>
        <div className="kpi-sub">{k.updatedAt}</div>
      </div>
      <div className="card kpi-card">
        <div className="kpi-title">今日请求数</div>
        <div className="kpi-value">{k.reqToday}</div>
        <div className="kpi-sub">速率限制：{k.rateRemaining}</div>
      </div>
      <div className="card kpi-card">
        <div className="kpi-title">任务队列</div>
        <div className="kpi-value">{k.queueSize}</div>
        <div className="kpi-sub">进行中：{k.queueRunning}</div>
      </div>
      <div className="card kpi-card">
        <div className="kpi-title">告警</div>
        <div className="kpi-value kpi-danger">{k.alertCount}</div>
        <div className="kpi-sub">最近：{k.alertLatest}</div>
      </div>
    </section>
  );
};

export default KPIGrid;

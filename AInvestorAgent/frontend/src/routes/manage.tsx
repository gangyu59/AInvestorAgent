import React, { useEffect, useState } from "react";

type TaskRow = { id: string; type: string; status: string; createdAt: string; duration: number };
type AgentRow = { id: string; name: string; desc: string; status: "active" | "paused" };

const ManagePage: React.FC = () => {
  const [defaultSymbol, setDefaultSymbol] = useState("AAPL");
  const [fetchInterval, setFetchInterval] = useState<number>(5);
  const [avKeySet, setAvKeySet] = useState<boolean>(true);
  const [newsKeySet, setNewsKeySet] = useState<boolean>(true);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);

  async function loadConfig() {
    // TODO: 接后端配置接口；不要在前端暴露明文 Key
    setDefaultSymbol("AAPL");
    setFetchInterval(5);
    setAvKeySet(true);
    setNewsKeySet(true);
  }

  async function saveConfig() {
    const body = { defaultSymbol, fetchInterval };
    // TODO: fetch(ENDPOINTS.MANAGE.SAVE_CONFIG, {method:'POST', body: JSON.stringify(body), headers:{'Content-Type':'application/json'}})
    console.log("保存配置", body);
  }

  async function loadTasks() {
    // TODO: 接你的 /api/tasks
    setTasks([
      { id: "T-001", type: "fetch-daily", status: "queued", createdAt: new Date().toLocaleString(), duration: 0 },
      { id: "T-002", type: "fetch-quote", status: "running", createdAt: new Date().toLocaleString(), duration: 1200 },
    ]);
  }

  async function loadAgents() {
    // TODO: 接你的 /api/agents
    setAgents([
      { id: "A-001", name: "NewsSentinel", desc: "新闻监控与情绪分析", status: "active" },
      { id: "A-002", name: "AlphaFetcher", desc: "AlphaVantage 日线/报价抓取", status: "paused" },
    ]);
  }

  useEffect(() => {
    loadConfig();
    loadTasks();
    loadAgents();
  }, []);

  return (
    <div className="container app-content">
      {/* 数据源配置 */}
      <div className="card">
        <div className="card-header row between center">
          <h2 className="card-title">数据源配置</h2>
          <button className="btn primary" onClick={saveConfig}>保存</button>
        </div>
        <div className="card-body grid form-grid">
          <label className="form-field">
            <span className="label">AlphaVantage Key（只读占位）</span>
            <input className="input" type="password" value={avKeySet ? "****** 已配置（受保护）" : ""} disabled />
          </label>
          <label className="form-field">
            <span className="label">News API Key（只读占位）</span>
            <input className="input" type="password" value={newsKeySet ? "****** 已配置（受保护）" : ""} disabled />
          </label>
          <label className="form-field">
            <span className="label">默认股票代码</span>
            <input className="input" value={defaultSymbol} onChange={(e) => setDefaultSymbol(e.target.value)} />
          </label>
          <label className="form-field">
            <span className="label">抓取周期（分钟）</span>
            <input className="input" type="number" min={1} value={fetchInterval} onChange={(e) => setFetchInterval(parseInt(e.target.value || "1", 10))} />
          </label>
        </div>
      </div>

      {/* 任务队列 */}
      <div className="card">
        <div className="card-header row between center">
          <h2 className="card-title">任务队列</h2>
          <div className="row gap-8">
            <button className="btn" onClick={() => console.log("立即运行")}>立即运行</button>
            <button className="btn" onClick={() => console.log("重试失败")}>重试失败</button>
            <button className="btn danger" onClick={() => console.log("清空队列")}>清空队列</button>
          </div>
        </div>
        <div className="card-body">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th><th>类型</th><th>状态</th><th>创建时间</th><th>耗时(ms)</th><th>操作</th>
              </tr>
            </thead>
            <tbody>
            {tasks.map(r => (
              <tr key={r.id}>
                <td>{r.id}</td><td>{r.type}</td><td>{r.status}</td><td>{r.createdAt}</td><td>{r.duration}</td>
                <td>
                  <button className="btn btn-sm" onClick={() => console.log("retry", r.id)}>重试</button>
                  <button className="btn btn-sm danger" onClick={() => console.log("cancel", r.id)}>取消</button>
                </td>
              </tr>
            ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Agent 管理 */}
      <div className="card">
        <div className="card-header row between center">
          <h2 className="card-title">Agent 列表</h2>
          <button className="btn primary" onClick={() => console.log("新建 Agent")}>新建 Agent</button>
        </div>
        <div className="card-body grid cards-grid">
          {agents.map(a => (
            <div key={a.id} className={`agent-card card ${a.status === "active" ? "success" : "muted"}`}>
              <div className="card-body">
                <div className="row between center">
                  <div>
                    <div className="h3">{a.name}</div>
                    <div className="muted">{a.desc}</div>
                  </div>
                  <div className="row gap-8">
                    <span className={`badge ${a.status === "active" ? "badge-success" : "badge-muted"}`}>{a.status}</span>
                    <button className="btn btn-sm" onClick={() => console.log("toggle", a.id)}>
                      {a.status === "active" ? "暂停" : "启用"}
                    </button>
                    <button className="btn btn-sm" onClick={() => console.log("edit", a.id)}>编辑</button>
                    <button className="btn btn-sm danger" onClick={() => console.log("delete", a.id)}>删除</button>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {!agents.length && <div className="empty">暂无 Agent</div>}
        </div>
      </div>
    </div>
  );
};

export default ManagePage;

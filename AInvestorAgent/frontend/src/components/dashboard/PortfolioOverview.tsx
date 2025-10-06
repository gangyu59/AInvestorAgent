const fmt = (x: any, d = 2) => (typeof x === "number" && Number.isFinite(x) ? x.toFixed(d) : "--");
const pct = (x: any, d = 1) => (x == null || !Number.isFinite(+x) ? "--" : `${(+x * 100).toFixed(d)}%`);

type Props = {
  snapshot?: any;
  keptTop5?: Array<[string, number]>;
  onDecide?: () => void;
};

export function PortfolioOverview({ snapshot, keptTop5 = [], onDecide }: Props) {
  return (
    <div className="dashboard-card po-card">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">投资组合概览</h3>
        <button className="dashboard-btn dashboard-btn-secondary" onClick={() => (window.location.hash = "#/portfolio")}>
          查看详情 →
        </button>
      </div>

      <div className="dashboard-card-body po-body">
        {/* 左：组合KPI */}
        <section className="po-panel">
          <h4 className="po-subtitle">组合KPI</h4>
          <div className="po-kpi-grid">
            <div className="kpi">
              <div className="label">年化收益</div>
              <div className="value">{fmt(snapshot?.metrics?.ann_return, 2)}</div>
            </div>
            <div className="kpi">
              <div className="label">最大回撤</div>
              <div className="value">{pct(snapshot?.metrics?.mdd, 1)}</div>
            </div>
            <div className="kpi">
              <div className="label">Sharpe</div>
              <div className="value">{fmt(snapshot?.metrics?.sharpe, 2)}</div>
            </div>
            <div className="kpi">
              <div className="label">胜率</div>
              <div className="value">{pct(snapshot?.metrics?.winrate, 1)}</div>
            </div>
          </div>

          <div className="po-top5">
            <div className="text-sm text-gray-400 mb-1">Top 5 持仓权重</div>
            <div className="weights-list">
              {keptTop5.map(([sym, w]) => (
                <div key={sym} className="weights-row">
                  <span className="weights-sym">{sym}</span>
                  <div className="weights-bar">
                    <div className="weights-fill" style={{ width: `${Math.min(100, w * 100)}%` }} />
                  </div>
                  <span className="weights-val">{pct(w, 1)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 右：AI 建议 */}
        <section className="po-panel">
          <h4 className="po-subtitle">AI 建议</h4>
          <p className="po-paragraph">
            基于最新评分与风控，建议维持当前配置，并关注高波动标的的仓位变化。
          </p>
          <div className="po-actions">
            <button className="dashboard-btn dashboard-btn-primary" onClick={onDecide}>
              立即决策
            </button>
            <button
              className="dashboard-btn dashboard-btn-secondary ml-2"
              onClick={() => (window.location.hash = "#/portfolio")}
            >
              查看组合
            </button>
          </div>
        </section>
      </div>

      {/* 底部：版本与备注（仍在同一卡片内，保持等高） */}
      {/*<div className="po-footer">*/}
      {/*  <div className="text-sm text-gray-400">*/}
      {/*    <span>版本：{snapshot?.version_tag || "—"}</span>*/}
      {/*    <span className="ml-4">说明：评分每周滚动更新；新闻情绪按 7 天窗口刷新。</span>*/}
      {/*  </div>*/}
      {/*</div>*/}
    </div>
  );
}

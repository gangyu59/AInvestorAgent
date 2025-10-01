import { SearchBox } from '../common/SearchBox';

export function DashboardHeader({
  watchlist,
  onDecide,
  onBacktest,
  onReport,
  onUpdate
}: {
  watchlist: string[];
  onDecide: () => void;
  onBacktest: () => void;
  onReport: () => void;
  onUpdate: () => void;
}) {
  return (
    <header className="dashboard-header">
      <div className="dashboard-brand">
        <div className="dashboard-logo">AI</div>
        <div>
          <h1 className="dashboard-brand-title">AInvestorAgent</h1>
          <p className="dashboard-brand-subtitle">智能投资决策平台</p>
        </div>
      </div>
      <div className="dashboard-actions">
        <div className="dashboard-search">
          <SearchBox watchlist={watchlist} />
        </div>
        <div className="dashboard-cta-group">
          <button onClick={onDecide} className="dashboard-btn dashboard-btn-primary">AI决策</button>
          <button onClick={onBacktest} className="dashboard-btn dashboard-btn-secondary">回测</button>
          <button onClick={onReport} className="dashboard-btn dashboard-btn-secondary">报告</button>
          <button onClick={onUpdate} className="dashboard-btn dashboard-btn-secondary">🔄 更新</button>
        </div>
      </div>
    </header>
  );
}
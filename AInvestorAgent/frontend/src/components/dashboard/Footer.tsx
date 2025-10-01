export function DashboardFooter() {
  return (
    <footer className="dashboard-footer">
      <div className="dashboard-footer-links">
        <a href="/#/stock" className="dashboard-footer-link">个股分析</a>
        <a href="/#/portfolio" className="dashboard-footer-link">组合管理</a>
        <a href="/#/simulator" className="dashboard-footer-link">回测模拟</a>
        <a href="/#/trading" className="dashboard-footer-link">模拟交易</a>
        <a href="/#/monitor" className="dashboard-footer-link">舆情监控</a>
        <a href="/#/manage" className="dashboard-footer-link">系统管理</a>
      </div>
      <div className="dashboard-footer-info">AInvestorAgent v1.3 | 低频投资决策 ≤3次/周 | <span className="dashboard-footer-status">● 系统运行正常</span></div>
    </footer>
  );
}
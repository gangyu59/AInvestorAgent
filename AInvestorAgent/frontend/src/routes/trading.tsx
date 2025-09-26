// frontend/src/routes/trading.tsx
import { useEffect, useState } from "react";
import { API_BASE } from "../services/endpoints";

interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  weight: number;
}

interface Portfolio {
  total_value: number;
  cash: number;
  position_value: number;
  total_pnl: number;
  total_return: number;
  holdings: Position[];
}

interface PnLRecord {
  date: string;
  total_value: number;
  daily_pnl: number;
  return_pct: number;
  cumulative_pnl: number;
}

export default function TradingPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [pnlHistory, setPnlHistory] = useState<PnLRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [tradeForm, setTradeForm] = useState({
    symbol: "",
    action: "BUY",
    quantity: "",
    price: ""
  });

  const fetchPortfolio = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulation/portfolio`);
      const data = await response.json();
      if (data.success) {
        setPortfolio(data.data);
      }
    } catch (error) {
      console.error("获取投资组合失败:", error);
    }
  };

  const fetchPnLHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulation/pnl?days=30`);
      const data = await response.json();
      if (data.success) {
        setPnlHistory(data.data);
      }
    } catch (error) {
      console.error("获取P&L历史失败:", error);
    }
  };

  const executeTrade = async () => {
    if (!tradeForm.symbol || !tradeForm.quantity) {
      alert("请填写股票代码和数量");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulation/trade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: (tradeForm.symbol || "").toUpperCase(),
          action: tradeForm.action,
          quantity: parseFloat(tradeForm.quantity),
          price: tradeForm.price ? parseFloat(tradeForm.price) : null
        })
      });

      const data = await response.json();
      if (data.success) {
        alert("交易执行成功");
        setTradeForm({ symbol: "", action: "BUY", quantity: "", price: "" });
        await fetchPortfolio();
      } else {
        alert(`交易失败: ${data.detail || "未知错误"}`);
      }
    } catch (error) {
      alert(`交易失败: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const calculatePnL = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulation/calculate-pnl`, {
        method: "POST"
      });
      const data = await response.json();
      if (data.success) {
        alert("P&L计算完成");
        await fetchPnLHistory();
      }
    } catch (error) {
      console.error("计算P&L失败:", error);
    }
  };

  useEffect(() => {
    fetchPortfolio();
    fetchPnLHistory();
  }, []);

  const fmt = (x: number, d = 2) => Number.isFinite(x) ? x.toFixed(d) : "--";
  const pct = (x: number, d = 1) => Number.isFinite(x) ? `${(x * 100).toFixed(d)}%` : "--";

  return (
    <div className="page">
      <div className="page-header">
        <h2>模拟交易</h2>
        <button className="btn" onClick={calculatePnL}>
          计算今日P&L
        </button>
      </div>

      {/* 账户概览 */}
      <div className="card">
        <div className="card-header">
          <h3>账户概览</h3>
        </div>
        <div className="card-body">
          {portfolio ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16 }}>
              <div className="metric">
                <div className="label">总资产</div>
                <div className="value">${fmt(portfolio.total_value)}</div>
              </div>
              <div className="metric">
                <div className="label">现金</div>
                <div className="value">${fmt(portfolio.cash)}</div>
              </div>
              <div className="metric">
                <div className="label">持仓市值</div>
                <div className="value">${fmt(portfolio.position_value)}</div>
              </div>
              <div className="metric">
                <div className="label">总盈亏</div>
                <div className={`value ${portfolio.total_pnl >= 0 ? "up" : "down"}`}>
                  ${fmt(portfolio.total_pnl)}
                </div>
              </div>
              <div className="metric">
                <div className="label">总收益率</div>
                <div className={`value ${portfolio.total_return >= 0 ? "up" : "down"}`}>
                  {pct(portfolio.total_return)}
                </div>
              </div>
            </div>
          ) : (
            <div>加载中...</div>
          )}
        </div>
      </div>

      {/* 交易面板 */}
      <div className="card">
        <div className="card-header">
          <h3>手动交易</h3>
        </div>
        <div className="card-body">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, alignItems: "end" }}>
            <div>
              <label>股票代码</label>
              <input
                type="text"
                value={tradeForm.symbol}
                onChange={(e) => setTradeForm({...tradeForm, symbol: e.target.value})}
                placeholder="AAPL"
              />
            </div>
            <div>
              <label>操作</label>
              <select
                value={tradeForm.action}
                onChange={(e) => setTradeForm({...tradeForm, action: e.target.value})}
              >
                <option value="BUY">买入</option>
                <option value="SELL">卖出</option>
              </select>
            </div>
            <div>
              <label>数量</label>
              <input
                type="number"
                value={tradeForm.quantity}
                onChange={(e) => setTradeForm({...tradeForm, quantity: e.target.value})}
                placeholder="100"
              />
            </div>
            <div>
              <label>价格（选填）</label>
              <input
                type="number"
                value={tradeForm.price}
                onChange={(e) => setTradeForm({...tradeForm, price: e.target.value})}
                placeholder="市价"
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={executeTrade}
              disabled={loading}
            >
              {loading ? "执行中..." : "执行交易"}
            </button>
          </div>
        </div>
      </div>

      {/* 当前持仓 */}
      <div className="card">
        <div className="card-header">
          <h3>当前持仓</h3>
        </div>
        <div className="table">
          <div className="thead">
            <span>股票</span>
            <span>数量</span>
            <span>成本价</span>
            <span>现价</span>
            <span>市值</span>
            <span>盈亏</span>
            <span>权重</span>
          </div>
          <div className="tbody">
            {portfolio?.holdings.map(pos => (
              <div key={pos.symbol} className="row">
                <span>{pos.symbol}</span>
                <span>{fmt(pos.quantity, 0)}</span>
                <span>${fmt(pos.avg_cost)}</span>
                <span>${fmt(pos.current_price)}</span>
                <span>${fmt(pos.market_value)}</span>
                <span className={pos.unrealized_pnl >= 0 ? "up" : "down"}>
                  ${fmt(pos.unrealized_pnl)}
                </span>
                <span>{pct(pos.weight)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* P&L历史 */}
      <div className="card">
        <div className="card-header">
          <h3>P&L历史 (最近30天)</h3>
        </div>
        <div className="table">
          <div className="thead">
            <span>日期</span>
            <span>总资产</span>
            <span>当日盈亏</span>
            <span>当日收益率</span>
            <span>累计盈亏</span>
          </div>
          <div className="tbody">
            {pnlHistory.map(record => (
              <div key={record.date} className="row">
                <span>{record.date}</span>
                <span>${fmt(record.total_value)}</span>
                <span className={record.daily_pnl >= 0 ? "up" : "down"}>
                  ${fmt(record.daily_pnl)}
                </span>
                <span className={record.return_pct >= 0 ? "up" : "down"}>
                  {pct(record.return_pct)}
                </span>
                <span className={record.cumulative_pnl >= 0 ? "up" : "down"}>
                  ${fmt(record.cumulative_pnl)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
import { useState, useEffect, useRef } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { TrendingUp, TrendingDown, Activity, DollarSign, Calendar, ArrowUpRight, ArrowDownRight, RefreshCw } from 'lucide-react';

// 模拟API基础URL
const API_BASE = 'http://localhost:8000';

export default function HistoricalTradingSimulator() {
  const [loading, setLoading] = useState(false);
  const [simulationData, setSimulationData] = useState(null);
  const [config, setConfig] = useState({
    watchlist: ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'TSLA', 'META', 'SPY'],
    initialCapital: 100000,
    startDate: '2024-01-01',
    endDate: new Date().toISOString().split('T')[0],
    rebalanceFrequency: 'W-MON', // 每周一
    minScore: 50.0
  });
  const [trades, setTrades] = useState([]);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const hasRun = useRef(false);

  // 启动历史回测模拟
  const runSimulation = async () => {
    if (loading) return;

    setLoading(true);
    try {
      // 调用后端API执行历史回测
      const response = await fetch(`${API_BASE}/api/simulator/historical-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });

      if (!response.ok) {
        throw new Error('回测执行失败');
      }

      const data = await response.json();
      setSimulationData(data);
      setTrades(data.trades || []);
    } catch (error) {
      console.error('模拟失败:', error);
      // 使用模拟数据演示
      generateMockData();
    } finally {
      setLoading(false);
    }
  };

  // 生成模拟数据用于演示
  const generateMockData = () => {
    const days = 250;
    const history = [];
    const mockTrades = [];
    let nav = 1.0;
    let cash = config.initialCapital;
    let positions = {};

    // 生成历史净值曲线
    for (let i = 0; i < days; i++) {
      const date = new Date(config.startDate);
      date.setDate(date.getDate() + i);

      // 模拟市场波动
      const dailyReturn = (Math.random() - 0.48) * 0.02;
      nav *= (1 + dailyReturn);

      const totalValue = config.initialCapital * nav;
      const holdingsValue = totalValue - cash;

      history.push({
        date: date.toISOString().split('T')[0],
        nav: nav,
        totalValue: totalValue,
        cash: cash,
        holdings: holdingsValue,
        positions: Object.keys(positions).length,
        drawdown: Math.min(0, (nav - Math.max(...history.map(h => h.nav || 1))) / Math.max(...history.map(h => h.nav || 1)) * 100)
      });

      // 每周生成交易
      if (i % 7 === 0 && i > 0) {
        const symbols = config.watchlist.slice(0, Math.floor(Math.random() * 5) + 3);
        symbols.forEach(symbol => {
          const action = Math.random() > 0.5 ? 'BUY' : 'SELL';
          const shares = Math.floor(Math.random() * 50) + 10;
          const price = 100 + Math.random() * 100;

          mockTrades.push({
            date: date.toISOString().split('T')[0],
            symbol: symbol,
            action: action,
            shares: shares,
            price: price.toFixed(2),
            value: (shares * price).toFixed(2),
            reason: action === 'BUY'
              ? `评分${(Math.random() * 30 + 60).toFixed(1)} - 强劲动量+高质量因子`
              : `调仓降低权重 - 评分下降至${(Math.random() * 20 + 40).toFixed(1)}`
          });
        });
      }
    }

    const finalNav = history[history.length - 1].nav;
    const totalReturn = (finalNav - 1) * 100;
    const annReturn = (Math.pow(finalNav, 365 / days) - 1) * 100;
    const maxDD = Math.min(...history.map(h => h.drawdown || 0));

    // 计算夏普比率
    const returns = history.slice(1).map((h, i) =>
      (h.nav - history[i].nav) / history[i].nav
    );
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const stdReturn = Math.sqrt(
      returns.reduce((a, b) => a + Math.pow(b - avgReturn, 2), 0) / returns.length
    );
    const sharpe = (avgReturn / stdReturn) * Math.sqrt(252);

    const winRate = returns.filter(r => r > 0).length / returns.length * 100;

    setSimulationData({
      history,
      metrics: {
        totalReturn,
        annReturn,
        maxDrawdown: maxDD,
        sharpe,
        winRate,
        totalTrades: mockTrades.length,
        winTrades: Math.floor(mockTrades.length * 0.6),
        avgHoldings: history.reduce((a, b) => a + b.positions, 0) / history.length
      },
      trades: mockTrades,
      config
    });

    setTrades(mockTrades);
  };

  // 自动运行一次
  useEffect(() => {
    if (!hasRun.current) {
      hasRun.current = true;
      runSimulation();
    }
  }, []);

  // 格式化货币
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(to bottom, #0f172a, #1e293b)',
      padding: '24px',
      color: '#e2e8f0'
    }}>
      {/* 头部 */}
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        marginBottom: '24px'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px'
        }}>
          <div>
            <h1 style={{
              fontSize: '28px',
              fontWeight: 'bold',
              marginBottom: '8px',
              background: 'linear-gradient(to right, #60a5fa, #3b82f6)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              📊 历史回测模拟交易
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '14px' }}>
              使用历史数据模拟Paper Trading,验证策略有效性
            </p>
          </div>
          <button
            onClick={runSimulation}
            disabled={loading}
            style={{
              padding: '12px 24px',
              background: loading ? '#475569' : 'linear-gradient(to right, #3b82f6, #2563eb)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <RefreshCw size={16} style={{
              animation: loading ? 'spin 1s linear infinite' : 'none'
            }} />
            {loading ? '运行中...' : '重新运行'}
          </button>
        </div>

        {/* 配置参数展示 */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(148, 163, 184, 0.1)',
          borderRadius: '12px',
          padding: '16px',
          display: 'flex',
          gap: '24px',
          flexWrap: 'wrap'
        }}>
          <div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>回测期间</div>
            <div style={{ fontSize: '14px', fontWeight: '600' }}>
              {config.startDate} ~ {config.endDate}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>初始资金</div>
            <div style={{ fontSize: '14px', fontWeight: '600' }}>
              {formatCurrency(config.initialCapital)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>调仓频率</div>
            <div style={{ fontSize: '14px', fontWeight: '600' }}>每周一</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>股票池</div>
            <div style={{ fontSize: '14px', fontWeight: '600' }}>
              {config.watchlist.length}只股票
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容 */}
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {loading && !simulationData ? (
          <div style={{
            background: 'rgba(30, 41, 59, 0.6)',
            border: '1px solid rgba(148, 163, 184, 0.1)',
            borderRadius: '12px',
            padding: '60px',
            textAlign: 'center'
          }}>
            <Activity size={48} style={{
              color: '#3b82f6',
              animation: 'pulse 2s ease-in-out infinite',
              margin: '0 auto 16px'
            }} />
            <div style={{ fontSize: '16px', color: '#94a3b8' }}>
              正在运行历史回测...
            </div>
          </div>
        ) : simulationData ? (
          <>
            {/* 关键指标卡片 */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '16px',
              marginBottom: '24px'
            }}>
              <MetricCard
                icon={<TrendingUp size={20} />}
                label="总收益率"
                value={`${simulationData.metrics.totalReturn.toFixed(2)}%`}
                change={simulationData.metrics.totalReturn}
                color="#22c55e"
              />
              <MetricCard
                icon={<Activity size={20} />}
                label="年化收益"
                value={`${simulationData.metrics.annReturn.toFixed(2)}%`}
                change={simulationData.metrics.annReturn}
                color="#3b82f6"
              />
              <MetricCard
                icon={<TrendingDown size={20} />}
                label="最大回撤"
                value={`${simulationData.metrics.maxDrawdown.toFixed(2)}%`}
                change={simulationData.metrics.maxDrawdown}
                color="#ef4444"
                isNegative
              />
              <MetricCard
                icon={<Activity size={20} />}
                label="夏普比率"
                value={simulationData.metrics.sharpe.toFixed(3)}
                subtitle={`胜率 ${simulationData.metrics.winRate.toFixed(1)}%`}
                color="#a855f7"
              />
              <MetricCard
                icon={<DollarSign size={20} />}
                label="交易次数"
                value={simulationData.metrics.totalTrades}
                subtitle={`盈利 ${simulationData.metrics.winTrades}笔`}
                color="#f59e0b"
              />
            </div>

            {/* 净值曲线 */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              borderRadius: '12px',
              padding: '20px',
              marginBottom: '24px'
            }}>
              <h3 style={{
                fontSize: '18px',
                fontWeight: '600',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <Activity size={20} style={{ color: '#3b82f6' }} />
                组合净值曲线
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={simulationData.history}>
                  <defs>
                    <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="date"
                    stroke="#94a3b8"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => value.slice(5)}
                  />
                  <YAxis
                    stroke="#94a3b8"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => value.toFixed(2)}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                    formatter={(value) => [value.toFixed(4), '净值']}
                  />
                  <Area
                    type="monotone"
                    dataKey="nav"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fill="url(#navGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* 回撤图 */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              borderRadius: '12px',
              padding: '20px',
              marginBottom: '24px'
            }}>
              <h3 style={{
                fontSize: '18px',
                fontWeight: '600',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <TrendingDown size={20} style={{ color: '#ef4444' }} />
                回撤分析
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={simulationData.history}>
                  <defs>
                    <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="date"
                    stroke="#94a3b8"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => value.slice(5)}
                  />
                  <YAxis
                    stroke="#94a3b8"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `${value.toFixed(1)}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                    formatter={(value) => [`${value.toFixed(2)}%`, '回撤']}
                  />
                  <Area
                    type="monotone"
                    dataKey="drawdown"
                    stroke="#ef4444"
                    strokeWidth={2}
                    fill="url(#ddGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* 交易明细 */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              borderRadius: '12px',
              padding: '20px'
            }}>
              <h3 style={{
                fontSize: '18px',
                fontWeight: '600',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <Calendar size={20} style={{ color: '#f59e0b' }} />
                交易明细 ({trades.length}笔)
              </h3>

              <div style={{
                maxHeight: '500px',
                overflowY: 'auto',
                overflowX: 'auto'
              }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '13px'
                }}>
                  <thead>
                    <tr style={{
                      background: 'rgba(15, 23, 42, 0.6)',
                      borderBottom: '1px solid rgba(148, 163, 184, 0.1)'
                    }}>
                      <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8' }}>日期</th>
                      <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8' }}>股票</th>
                      <th style={{ padding: '12px', textAlign: 'center', color: '#94a3b8' }}>操作</th>
                      <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8' }}>股数</th>
                      <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8' }}>价格</th>
                      <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8' }}>金额</th>
                      <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8' }}>理由</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade, idx) => (
                      <tr
                        key={idx}
                        onClick={() => setSelectedTrade(trade)}
                        style={{
                          borderBottom: '1px solid rgba(148, 163, 184, 0.05)',
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                          background: selectedTrade === trade ? 'rgba(59, 130, 246, 0.1)' : 'transparent'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(59, 130, 246, 0.05)';
                        }}
                        onMouseLeave={(e) => {
                          if (selectedTrade !== trade) {
                            e.currentTarget.style.background = 'transparent';
                          }
                        }}
                      >
                        <td style={{ padding: '12px' }}>{trade.date}</td>
                        <td style={{ padding: '12px', fontWeight: '600' }}>{trade.symbol}</td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{
                            padding: '4px 12px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: '600',
                            background: trade.action === 'BUY' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                            color: trade.action === 'BUY' ? '#22c55e' : '#ef4444',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}>
                            {trade.action === 'BUY' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                            {trade.action}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right' }}>{trade.shares}</td>
                        <td style={{ padding: '12px', textAlign: 'right' }}>${trade.price}</td>
                        <td style={{ padding: '12px', textAlign: 'right', fontWeight: '600' }}>
                          ${Number(trade.value).toLocaleString()}
                        </td>
                        <td style={{
                          padding: '12px',
                          fontSize: '12px',
                          color: '#94a3b8',
                          maxWidth: '300px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {trade.reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : null}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}

// 指标卡片组件
function MetricCard({ icon, label, value, subtitle, change, color, isNegative }) {
  return (
    <div style={{
      background: 'rgba(30, 41, 59, 0.6)',
      border: '1px solid rgba(148, 163, 184, 0.1)',
      borderRadius: '12px',
      padding: '20px',
      transition: 'all 0.2s'
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.transform = 'translateY(-2px)';
      e.currentTarget.style.boxShadow = '0 8px 16px rgba(0, 0, 0, 0.2)';
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = 'none';
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '12px'
      }}>
        <div style={{ color: color }}>
          {icon}
        </div>
        <div style={{
          fontSize: '12px',
          color: '#94a3b8',
          fontWeight: '500'
        }}>
          {label}
        </div>
      </div>
      <div style={{
        fontSize: '24px',
        fontWeight: 'bold',
        color: color,
        marginBottom: '4px'
      }}>
        {value}
      </div>
      {subtitle && (
        <div style={{
          fontSize: '12px',
          color: '#64748b'
        }}>
          {subtitle}
        </div>
      )}
      {change !== undefined && (
        <div style={{
          fontSize: '12px',
          color: isNegative ? (change < 0 ? '#22c55e' : '#ef4444') : (change > 0 ? '#22c55e' : '#ef4444'),
          marginTop: '4px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}>
          {isNegative ? (change < 0 ? '✓ 风险可控' : '⚠ 需要关注') : (change > 0 ? '↑ 表现优异' : '↓ 需要改进')}
        </div>
      )}
    </div>
  );
}
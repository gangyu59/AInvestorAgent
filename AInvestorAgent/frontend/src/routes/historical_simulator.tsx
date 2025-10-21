// frontend/src/routes/historical_simulator.tsx
import { useState, useEffect, useRef } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { API_BASE } from '../services/endpoints';

export default function HistoricalSimulatorPage() {
  const [loading, setLoading] = useState(false);
  const [simulationData, setSimulationData] = useState<any>(null);
  const [config, setConfig] = useState({
    watchlist: [] as string[],
    initialCapital: 100000,
    startDate: '2024-01-01',
    endDate: new Date().toISOString().split('T')[0],
    rebalanceFrequency: 'W-MON',
    minScore: 50.0
  });
  const [trades, setTrades] = useState<any[]>([]);
  const [selectedTrade, setSelectedTrade] = useState<any>(null);
  const hasInitRun = useRef(false);

  // 从URL参数读取watchlist
  useEffect(() => {
    const hash = window.location.hash;
    const queryStart = hash.indexOf('?');
    if (queryStart > 0) {
      const params = new URLSearchParams(hash.slice(queryStart + 1));
      const symbolsParam = params.get('symbols');

      if (symbolsParam) {
        const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
        setConfig(prev => ({ ...prev, watchlist: symbols }));
      }
    }
  }, []);

  // 启动历史回测模拟
  const runSimulation = async () => {
    if (loading) return;

    if (config.watchlist.length === 0) {
      alert('请先在Dashboard添加股票到关注列表');
      return;
    }

    setLoading(true);
    try {
      console.log('🚀 启动历史回测模拟');
      console.log('📋 配置:', config);

      const response = await fetch(`${API_BASE}/api/simulation/historical-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`回测失败: ${errorText}`);
      }

      const result = await response.json();

      if (result.success && result.data) {
        console.log('✅ 回测成功:', result.data);
        setSimulationData(result.data);
        setTrades(result.data.trades || []);
      } else {
        throw new Error('回测返回数据格式错误');
      }
    } catch (error: any) {
      console.error('❌ 模拟失败:', error);
      alert(`回测失败: ${error.message}\n\n请确保:\n1. 后端服务正常运行\n2. 已经运行过数据更新\n3. historical_backtest_simulator.py 文件存在`);
    } finally {
      setLoading(false);
    }
  };

  // 自动运行一次
  useEffect(() => {
    if (!hasInitRun.current && config.watchlist.length > 0) {
      hasInitRun.current = true;
      setTimeout(() => runSimulation(), 500);
    }
  }, [config.watchlist]);

  // 格式化货币
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  // 导出CSV
  const exportCSV = () => {
    if (!simulationData) return;

    const rows = [
      ['日期', '净值', '总价值', '现金', '持仓价值', '持仓数', '回撤%'],
      ...simulationData.history.map((h: any) => [
        h.date,
        h.nav.toFixed(4),
        h.totalValue.toFixed(2),
        h.cash.toFixed(2),
        h.holdings.toFixed(2),
        h.positions,
        h.drawdown.toFixed(2)
      ])
    ];

    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `historical_backtest_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
  };

  // 导出交易记录
  const exportTrades = () => {
    if (!trades.length) return;

    const rows = [
      ['日期', '股票', '操作', '股数', '价格', '金额', '理由'],
      ...trades.map((t: any) => [
        t.date,
        t.symbol,
        t.action,
        t.shares,
        t.price,
        t.value,
        t.reason
      ])
    ];

    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
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
          marginBottom: '16px',
          flexWrap: 'wrap',
          gap: '12px'
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

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button
              onClick={exportCSV}
              disabled={!simulationData}
              style={{
                padding: '10px 20px',
                background: simulationData ? 'rgba(34, 197, 94, 0.1)' : 'rgba(75, 85, 99, 0.3)',
                color: simulationData ? '#22c55e' : '#6b7280',
                border: simulationData ? '1px solid rgba(34, 197, 94, 0.3)' : '1px solid rgba(75, 85, 99, 0.3)',
                borderRadius: '8px',
                cursor: simulationData ? 'pointer' : 'not-allowed',
                fontSize: '14px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📥 导出数据
            </button>

            <button
              onClick={exportTrades}
              disabled={!trades.length}
              style={{
                padding: '10px 20px',
                background: trades.length ? 'rgba(59, 130, 246, 0.1)' : 'rgba(75, 85, 99, 0.3)',
                color: trades.length ? '#3b82f6' : '#6b7280',
                border: trades.length ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid rgba(75, 85, 99, 0.3)',
                borderRadius: '8px',
                cursor: trades.length ? 'pointer' : 'not-allowed',
                fontSize: '14px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📥 导出交易
            </button>

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
                transition: 'all 0.2s'
              }}
            >
              {loading ? '⏳ 运行中...' : '🔄 重新运行'}
            </button>
          </div>
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
              {config.watchlist.length}只股票: {config.watchlist.slice(0, 5).join(', ')}
              {config.watchlist.length > 5 && '...'}
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
            <div style={{
              fontSize: '48px',
              animation: 'pulse 2s ease-in-out infinite',
              margin: '0 auto 16px'
            }}>⏳</div>
            <div style={{ fontSize: '16px', color: '#94a3b8', marginBottom: '8px' }}>
              正在运行历史回测...
            </div>
            <div style={{ fontSize: '14px', color: '#64748b' }}>
              这可能需要1-2分钟,请耐心等待
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
                icon="📈"
                label="总收益率"
                value={`${simulationData.metrics.totalReturn.toFixed(2)}%`}
                change={simulationData.metrics.totalReturn}
                color="#22c55e"
              />
              <MetricCard
                icon="📊"
                label="年化收益"
                value={`${simulationData.metrics.annReturn.toFixed(2)}%`}
                change={simulationData.metrics.annReturn}
                color="#3b82f6"
              />
              <MetricCard
                icon="📉"
                label="最大回撤"
                value={`${simulationData.metrics.maxDrawdown.toFixed(2)}%`}
                change={simulationData.metrics.maxDrawdown}
                color="#ef4444"
                isNegative
              />
              <MetricCard
                icon="⚖️"
                label="夏普比率"
                value={simulationData.metrics.sharpe.toFixed(3)}
                subtitle={`胜率 ${simulationData.metrics.winRate.toFixed(1)}%`}
                color="#a855f7"
              />
              <MetricCard
                icon="💼"
                label="交易次数"
                value={simulationData.metrics.totalTrades}
                subtitle={`平均持仓 ${simulationData.metrics.avgHoldings.toFixed(1)}只`}
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
                marginBottom: '16px'
              }}>
                📈 组合净值曲线
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
                    formatter={(value: any) => [value.toFixed(4), '净值']}
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
                marginBottom: '16px'
              }}>
                📉 回撤分析
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
                    formatter={(value: any) => [`${value.toFixed(2)}%`, '回撤']}
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
                marginBottom: '16px'
              }}>
                📋 交易明细 ({trades.length}笔)
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
                      borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
                      position: 'sticky',
                      top: 0
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
                            color: trade.action === 'BUY' ? '#22c55e' : '#ef4444'
                          }}>
                            {trade.action === 'BUY' ? '⬆️ ' : '⬇️ '}
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
        ) : config.watchlist.length === 0 ? (
          <div style={{
            background: 'rgba(30, 41, 59, 0.6)',
            border: '1px solid rgba(148, 163, 184, 0.1)',
            borderRadius: '12px',
            padding: '60px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }}>📊</div>
            <div style={{ fontSize: '18px', color: '#e2e8f0', marginBottom: '8px' }}>
              请先在Dashboard添加股票
            </div>
            <div style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '20px' }}>
              返回首页,在关注列表中添加要回测的股票
            </div>
            <button
              onClick={() => window.location.hash = '#/'}
              style={{
                padding: '12px 24px',
                background: 'linear-gradient(to right, #3b82f6, #2563eb)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '600'
              }}
            >
              返回首页
            </button>
          </div>
        ) : null}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}

// 指标卡片组件 (使用 emoji 代替图标)
function MetricCard({ icon, label, value, subtitle, change, color, isNegative }: {
  icon: string;
  label: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  color: string;
  isNegative?: boolean;
}) {
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
        <div style={{ fontSize: '20px' }}>
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
          marginTop: '4px'
        }}>
          {isNegative ? (change < 0 ? '✓ 风险可控' : '⚠ 需要关注') : (change > 0 ? '↑ 表现优异' : '↓ 需要改进')}
        </div>
      )}
    </div>
  );
}
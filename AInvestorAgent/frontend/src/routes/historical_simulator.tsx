// frontend/src/routes/historical_simulator.tsx - 修复 saveConfig 版本
import { useState, useEffect, useRef } from 'react';
import { ResponsiveContainer, Area, AreaChart, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { API_BASE } from '../services/endpoints';

export default function HistoricalSimulatorPage() {
  const [loading, setLoading] = useState(false);
  const [simulationData, setSimulationData] = useState<any>(null);
  const [showConfig, setShowConfig] = useState(true);

  // 从 localStorage 加载保存的配置
  const loadSavedConfig = () => {
    const saved = localStorage.getItem('backtest_config');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    return null;
  };

  const [config, setConfig] = useState(loadSavedConfig() || {
    watchlist: [] as string[],
    initialCapital: 100000,
    startDate: '2024-01-01',
    endDate: new Date().toISOString().split('T')[0],
    rebalanceFrequency: 'W-MON',
    minScore: 70,
    maxSingle: 0.25,
    maxSector: 0.40,
    minPositions: 5,
    maxPositions: 8,
    tradingCost: 0.001,
    minTradeThreshold: 0.05,
    maxAdjustmentsPerRebalance: 5,
    shortTermTaxRate: 0.37,
    longTermTaxRate: 0.20,
    enableTaxOptimization: true,
    optimizeFactorWeights: true,
    optimizationObjective: 'sharpe',
  });

  const [trades, setTrades] = useState<any[]>([]);

  // 保存配置到 localStorage (关键函数!)
  const saveConfig = (newConfig: any) => {
    setConfig(newConfig);
    localStorage.setItem('backtest_config', JSON.stringify(newConfig));
    console.log('✅ 配置已保存到 localStorage:', newConfig);
  };

  // 从 URL 参数加载股票列表
  useEffect(() => {
    const hash = window.location.hash;
    const queryStart = hash.indexOf('?');
    if (queryStart > 0) {
      const params = new URLSearchParams(hash.slice(queryStart + 1));
      const symbolsParam = params.get('symbols');
      if (symbolsParam) {
        const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
        // 使用 saveConfig 而不是直接 setConfig
        saveConfig({ ...config, watchlist: symbols });
      }
    }
  }, []);

  const runSimulation = async (customConfig?: any) => {
    const finalConfig = customConfig || config;
    if (loading) return;
    if (finalConfig.watchlist.length === 0) {
      alert('请先在Dashboard添加股票到关注列表');
      return;
    }
    setLoading(true);
    setShowConfig(false);
    try {
      const response = await fetch(`${API_BASE}/api/simulation/historical-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(finalConfig)
      });
      if (!response.ok) throw new Error(`回测失败: ${await response.text()}`);
      const result = await response.json();
      if (result.success && result.data) {
        setSimulationData(result.data);
        setTrades(result.data.trades || []);
      } else {
        throw new Error('回测返回数据格式错误');
      }
    } catch (error: any) {
      alert(`回测失败: ${error.message}`);
      setShowConfig(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{minHeight:'100vh',background:'linear-gradient(to bottom,#0f172a,#1e293b)',padding:'24px',color:'#e2e8f0'}}>
      <div style={{maxWidth:'1400px',margin:'0 auto',marginBottom:'24px'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <div>
            <h1 style={{fontSize:'28px',fontWeight:'bold',marginBottom:'8px',background:'linear-gradient(to right,#60a5fa,#3b82f6)',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent'}}>📊 历史回测模拟交易</h1>
            <p style={{color:'#94a3b8',fontSize:'14px'}}>使用历史数据模拟Paper Trading · 支持税务优化和因子权重优化</p>
          </div>
          {simulationData && (
            <button onClick={() => setShowConfig(!showConfig)} style={{padding:'10px 20px',background:'rgba(59,130,246,0.1)',border:'1px solid rgba(59,130,246,0.3)',borderRadius:'8px',color:'#60a5fa',fontSize:'14px',fontWeight:'600',cursor:'pointer'}}>
              {showConfig ? '📊 查看结果' : '⚙️ 调整参数'}
            </button>
          )}
        </div>
      </div>
      <div style={{maxWidth:'1400px',margin:'0 auto'}}>
        {/* 🔥 关键修改:传递 saveConfig 而不是 setConfig */}
        {showConfig && <ConfigPanel config={config} onConfigChange={saveConfig} onRun={runSimulation} loading={loading}/>}
        {loading && (
          <div style={{background:'rgba(30,41,59,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'12px',padding:'60px',textAlign:'center'}}>
            <div style={{fontSize:'48px',marginBottom:'16px'}}>⏳</div>
            <div style={{fontSize:'16px',color:'#94a3b8'}}>正在运行历史回测...预计需要 1-2 分钟</div>
          </div>
        )}
        {simulationData && !showConfig && <ResultsDisplay data={simulationData} trades={trades} config={config}/>}
      </div>
    </div>
  );
}

function ConfigPanel({config,onConfigChange,onRun,loading}:any) {
  const [showTaxSettings,setShowTaxSettings] = useState(false);
  const [showOptimization,setShowOptimization] = useState(false);

  // handleChange 现在会调用 onConfigChange (即 saveConfig)
  const handleChange = (key:string,value:any) => {
    const newConfig = {...config,[key]:value};
    onConfigChange(newConfig);  // 这里会触发 saveConfig
    console.log(`✅ 配置项 ${key} 已更新并保存:`, value);
  };

  const presets:any = {
    conservative:{name:'保守型',maxSingle:0.20,maxSector:0.35,minPositions:6,maxPositions:10,minScore:75,minTradeThreshold:0.08,shortTermTaxRate:0.37,longTermTaxRate:0.20,optimizeFactorWeights:true,optimizationObjective:'sharpe'},
    balanced:{name:'平衡型',maxSingle:0.25,maxSector:0.40,minPositions:5,maxPositions:8,minScore:70,minTradeThreshold:0.05,shortTermTaxRate:0.37,longTermTaxRate:0.20,optimizeFactorWeights:true,optimizationObjective:'sharpe'},
    aggressive:{name:'进取型',maxSingle:0.30,maxSector:0.50,minPositions:4,maxPositions:6,minScore:65,minTradeThreshold:0.03,shortTermTaxRate:0.37,longTermTaxRate:0.20,optimizeFactorWeights:true,optimizationObjective:'return'}
  };

  const taxPresets:any = {
    us_federal:{name:'美国联邦税率',shortTermTaxRate:0.37,longTermTaxRate:0.20},
    california:{name:'加州(含州税)',shortTermTaxRate:0.50,longTermTaxRate:0.33},
    new_york:{name:'纽约(含州税)',shortTermTaxRate:0.49,longTermTaxRate:0.31},
    no_tax:{name:'免税账户',shortTermTaxRate:0.0,longTermTaxRate:0.0}
  };

  return (
    <div style={{background:'rgba(30,41,59,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'12px',padding:'24px',marginBottom:'24px'}}>
      <h3 style={{fontSize:'18px',fontWeight:'600',marginBottom:'20px'}}>⚙️ 回测参数配置</h3>

      {/* 快速预设 */}
      <div style={{marginBottom:'24px'}}>
        <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'12px'}}>🎯 快速预设</label>
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:'12px'}}>
          {Object.entries(presets).map(([key,preset]:any)=>(
            <button key={key} onClick={()=>onConfigChange({...config,...preset})} style={{padding:'12px',background:'rgba(59,130,246,0.1)',border:'1px solid rgba(59,130,246,0.3)',borderRadius:'8px',color:'#60a5fa',fontSize:'14px',fontWeight:'600',cursor:'pointer',textAlign:'left'}}>
              <div style={{marginBottom:'4px'}}>{preset.name}</div>
              <div style={{fontSize:'11px',color:'#94a3b8',fontWeight:'normal'}}>
                {preset.minPositions}-{preset.maxPositions}只 · 分数≥{preset.minScore} · {(preset.maxSingle*100).toFixed(0)}%上限
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 股票池 */}
      <div style={{marginBottom:'20px'}}>
        <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>📋 股票池 ({config.watchlist.length}只)</label>
        <div style={{padding:'12px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',minHeight:'40px',fontSize:'14px'}}>
          {config.watchlist.length>0?config.watchlist.join(', '):'请从Dashboard添加股票'}
        </div>
      </div>

      {/* 基础参数 */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:'16px',marginBottom:'20px'}}>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>💰 初始资金</label>
          <input type="number" value={config.initialCapital} onChange={e=>handleChange('initialCapital',Number(e.target.value))} style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>📅 回测周期</label>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'8px'}}>
            <input type="date" value={config.startDate} onChange={e=>handleChange('startDate',e.target.value)} style={{padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
            <input type="date" value={config.endDate} onChange={e=>handleChange('endDate',e.target.value)} style={{padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
          </div>
        </div>
      </div>

      {/* 调仓策略 */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:'16px',marginBottom:'20px'}}>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>🔄 调仓频率</label>
          <select value={config.rebalanceFrequency} onChange={e=>handleChange('rebalanceFrequency',e.target.value)} style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}>
            <option value="W-MON">每周一</option>
            <option value="MS">每月初</option>
            <option value="QS">每季度初</option>
            <option value="D">每天</option>
          </select>
        </div>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>📊 最低评分</label>
          <input type="number" value={config.minScore} onChange={e=>handleChange('minScore',Number(e.target.value))} min="0" max="100" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
      </div>

      {/* 仓位限制 */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:'16px',marginBottom:'20px'}}>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>📈 单股上限</label>
          <input type="number" value={config.maxSingle} onChange={e=>handleChange('maxSingle',Number(e.target.value))} min="0" max="1" step="0.05" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>🏢 板块上限</label>
          <input type="number" value={config.maxSector} onChange={e=>handleChange('maxSector',Number(e.target.value))} min="0" max="1" step="0.05" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>🎯 持仓下限</label>
          <input type="number" value={config.minPositions} onChange={e=>handleChange('minPositions',Number(e.target.value))} min="1" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>🎯 持仓上限</label>
          <input type="number" value={config.maxPositions} onChange={e=>handleChange('maxPositions',Number(e.target.value))} min="1" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
      </div>

      {/* 交易成本 */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:'16px',marginBottom:'20px'}}>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>💸 交易成本</label>
          <input type="number" value={config.tradingCost} onChange={e=>handleChange('tradingCost',Number(e.target.value))} min="0" max="0.01" step="0.0001" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>⚖️ 交易阈值</label>
          <input type="number" value={config.minTradeThreshold} onChange={e=>handleChange('minTradeThreshold',Number(e.target.value))} min="0" max="0.5" step="0.01" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
        <div>
          <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>🔢 调仓次数上限</label>
          <input type="number" value={config.maxAdjustmentsPerRebalance} onChange={e=>handleChange('maxAdjustmentsPerRebalance',Number(e.target.value))} min="1" max="20" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
        </div>
      </div>

      {/* 税务设置折叠面板 */}
      <div style={{border:'1px solid rgba(239,68,68,0.3)',borderRadius:'8px',marginBottom:'20px',overflow:'hidden'}}>
        <button onClick={()=>setShowTaxSettings(!showTaxSettings)} style={{width:'100%',padding:'12px 16px',background:'rgba(239,68,68,0.1)',border:'none',display:'flex',justifyContent:'space-between',alignItems:'center',cursor:'pointer',color:'#e2e8f0',fontSize:'14px',fontWeight:'600'}}>
          <span>💸 税务优化设置</span>
          <span style={{fontSize:'12px'}}>{showTaxSettings?'▼':'▶'}</span>
        </button>
        {showTaxSettings && (
          <div style={{padding:'16px',background:'rgba(30,41,59,0.4)'}}>
            <div style={{marginBottom:'16px'}}>
              <label style={{display:'flex',alignItems:'center',fontSize:'14px',color:'#e2e8f0',cursor:'pointer'}}>
                <input type="checkbox" checked={config.enableTaxOptimization} onChange={e=>handleChange('enableTaxOptimization',e.target.checked)} style={{marginRight:'8px',width:'16px',height:'16px'}}/>
                启用税务优化 (优先卖出短期亏损/长期盈利)
              </label>
            </div>
            <div style={{marginBottom:'16px'}}>
              <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>🎯 税率预设</label>
              <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:'8px'}}>
                {Object.entries(taxPresets).map(([key,preset]:any)=>(
                  <button key={key} onClick={()=>onConfigChange({...config,shortTermTaxRate:preset.shortTermTaxRate,longTermTaxRate:preset.longTermTaxRate})} style={{padding:'8px',background:'rgba(239,68,68,0.1)',border:'1px solid rgba(239,68,68,0.3)',borderRadius:'6px',color:'#ef4444',fontSize:'12px',cursor:'pointer',textAlign:'left'}}>
                    {preset.name}
                  </button>
                ))}
              </div>
            </div>
            <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:'16px'}}>
              <div>
                <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>📉 短期资本利得税率</label>
                <input type="number" value={config.shortTermTaxRate} onChange={e=>handleChange('shortTermTaxRate',Number(e.target.value))} min="0" max="1" step="0.01" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
                <div style={{fontSize:'11px',color:'#64748b',marginTop:'4px'}}>持有期≤1年</div>
              </div>
              <div>
                <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>📈 长期资本利得税率</label>
                <input type="number" value={config.longTermTaxRate} onChange={e=>handleChange('longTermTaxRate',Number(e.target.value))} min="0" max="1" step="0.01" style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}/>
                <div style={{fontSize:'11px',color:'#64748b',marginTop:'4px'}}>持有期大于1年</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 因子权重优化折叠面板 */}
      <div style={{border:'1px solid rgba(59,130,246,0.3)',borderRadius:'8px',marginBottom:'20px',overflow:'hidden'}}>
        <button onClick={()=>setShowOptimization(!showOptimization)} style={{width:'100%',padding:'12px 16px',background:'rgba(59,130,246,0.1)',border:'none',display:'flex',justifyContent:'space-between',alignItems:'center',cursor:'pointer',color:'#e2e8f0',fontSize:'14px',fontWeight:'600'}}>
          <span>🎯 因子权重优化</span>
          <span style={{fontSize:'12px'}}>{showOptimization?'▼':'▶'}</span>
        </button>
        {showOptimization && (
          <div style={{padding:'16px',background:'rgba(30,41,59,0.4)'}}>
            <div style={{marginBottom:'16px'}}>
              <label style={{display:'flex',alignItems:'center',fontSize:'14px',color:'#e2e8f0',cursor:'pointer'}}>
                <input type="checkbox" checked={config.optimizeFactorWeights} onChange={e=>handleChange('optimizeFactorWeights',e.target.checked)} style={{marginRight:'8px',width:'16px',height:'16px'}}/>
                启用因子权重优化 (自动寻找最优权重)
              </label>
            </div>
            {config.optimizeFactorWeights && (
              <div>
                <label style={{display:'block',fontSize:'14px',fontWeight:'500',color:'#94a3b8',marginBottom:'8px'}}>🎯 优化目标</label>
                <select value={config.optimizationObjective} onChange={e=>handleChange('optimizationObjective',e.target.value)} style={{width:'100%',padding:'10px',background:'rgba(15,23,42,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'8px',color:'#e2e8f0',fontSize:'14px'}}>
                  <option value="sharpe">夏普比率 (风险调整后收益)</option>
                  <option value="return">总收益率 (最大化收益)</option>
                  <option value="sortino">索提诺比率 (下行风险)</option>
                  <option value="calmar">卡玛比率 (最大回撤)</option>
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      <button onClick={()=>onRun()} disabled={loading||config.watchlist.length===0} style={{width:'100%',padding:'14px',background:loading||config.watchlist.length===0?'rgba(100,116,139,0.3)':'linear-gradient(to right,#3b82f6,#2563eb)',border:'none',borderRadius:'8px',color:'#fff',fontSize:'16px',fontWeight:'bold',cursor:loading||config.watchlist.length===0?'not-allowed':'pointer'}}>
        {loading?'⏳ 回测中...':'🚀 开始回测'}
      </button>
    </div>
  );
}

function ResultsDisplay({data,trades,config}:any) {
  const [showTaxDetails,setShowTaxDetails]=useState(false);
  return (
    <>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:'16px',marginBottom:'24px'}}>
        <MetricCard icon="📈" label="税前总收益率" value={`${(data.metrics.totalReturnGross||data.metrics.totalReturn||0).toFixed(2)}%`} color="#22c55e"/>
        <MetricCard icon="💵" label="税后总收益率" value={`${(data.metrics.totalReturnNet||data.metrics.totalReturn||0).toFixed(2)}%`} color="#10b981" subtitle={`税务影响 -${(data.metrics.taxImpact||0).toFixed(2)}%`}/>
        <MetricCard icon="📊" label="年化收益(税后)" value={`${(data.metrics.annReturnNet||data.metrics.annReturn||0).toFixed(2)}%`} color="#3b82f6"/>
        <MetricCard icon="📉" label="最大回撤" value={`${(data.metrics.maxDrawdown||0).toFixed(2)}%`} color="#ef4444"/>
        <MetricCard icon="⚖️" label="夏普比率" value={(data.metrics.sharpe||0).toFixed(3)} color="#a855f7" subtitle={`胜率 ${(data.metrics.winRate||0).toFixed(1)}%`}/>
        <MetricCard icon="💼" label="交易次数" value={data.metrics.totalTrades||0} color="#f59e0b" subtitle={`平均 ${(data.metrics.avgHoldings||0).toFixed(1)}只`}/>
      </div>
      {data.taxSummary && (
        <div style={{background:'rgba(30,41,59,0.6)',border:'1px solid rgba(239,68,68,0.3)',borderRadius:'12px',padding:'20px',marginBottom:'24px'}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'16px'}}>
            <h3 style={{fontSize:'18px',fontWeight:'600',margin:0}}>💸 税务影响分析</h3>
            <button onClick={()=>setShowTaxDetails(!showTaxDetails)} style={{padding:'6px 12px',background:'rgba(239,68,68,0.1)',border:'1px solid rgba(239,68,68,0.3)',borderRadius:'6px',color:'#ef4444',fontSize:'12px',cursor:'pointer'}}>{showTaxDetails?'收起详情':'展开详情'}</button>
          </div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(150px,1fr))',gap:'16px'}}>
            <div><div style={{fontSize:'12px',color:'#94a3b8',marginBottom:'4px'}}>总缴税金</div><div style={{fontSize:'20px',fontWeight:'bold',color:'#ef4444'}}>${(data.taxSummary.totalTaxPaid||0).toLocaleString()}</div></div>
            <div><div style={{fontSize:'12px',color:'#94a3b8',marginBottom:'4px'}}>税务影响</div><div style={{fontSize:'20px',fontWeight:'bold',color:'#f97316'}}>-{(data.taxSummary.taxImpactPercent||0).toFixed(2)}%</div></div>
            <div><div style={{fontSize:'12px',color:'#94a3b8',marginBottom:'4px'}}>短期税率</div><div style={{fontSize:'20px',fontWeight:'bold',color:'#64748b'}}>{(config.shortTermTaxRate*100).toFixed(0)}%</div></div>
            <div><div style={{fontSize:'12px',color:'#94a3b8',marginBottom:'4px'}}>长期税率</div><div style={{fontSize:'20px',fontWeight:'bold',color:'#64748b'}}>{(config.longTermTaxRate*100).toFixed(0)}%</div></div>
          </div>
          {showTaxDetails && (
            <div style={{marginTop:'16px',paddingTop:'16px',borderTop:'1px solid rgba(148,163,184,0.1)',fontSize:'13px',color:'#94a3b8',lineHeight:'1.6'}}>
              <p style={{margin:'0 0 8px 0'}}>💡 <strong>税务优化建议:</strong></p>
              <ul style={{marginLeft:'20px',marginTop:'8px',marginBottom:0}}>
                {config.shortTermTaxRate>config.longTermTaxRate&&<li>持有期超过1年可节省{((config.shortTermTaxRate-config.longTermTaxRate)*100).toFixed(0)}%税率</li>}
                <li>本次回测共缴纳 ${(data.taxSummary.totalTaxPaid||0).toLocaleString()} 税金</li>
                <li>税务影响导致收益率降低 {(data.taxSummary.taxImpactPercent||0).toFixed(2)} 个百分点</li>
                {(data.metrics.taxImpact||0)>5&&<li style={{color:'#f59e0b'}}>⚠️ 税务影响较大,建议启用税务优化或降低交易频率</li>}
              </ul>
            </div>
          )}
        </div>
      )}
      {data.optimizedWeights && config.optimizeFactorWeights && (
        <div style={{background:'rgba(30,41,59,0.6)',border:'1px solid rgba(59,130,246,0.3)',borderRadius:'12px',padding:'20px',marginBottom:'24px'}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'16px'}}>
            <h3 style={{fontSize:'18px',fontWeight:'600',margin:0}}>🎯 优化后的因子权重</h3>
            <div style={{padding:'4px 12px',background:'rgba(34,197,94,0.1)',border:'1px solid rgba(34,197,94,0.3)',borderRadius:'6px',fontSize:'12px',color:'#22c55e'}}>
              优化目标: {config.optimizationObjective==='sharpe'?'夏普比率':config.optimizationObjective==='return'?'最大化收益':config.optimizationObjective==='sortino'?'索提诺比率':'卡玛比率'}
            </div>
          </div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(120px,1fr))',gap:'16px'}}>
            <WeightBar label="价值因子" value={data.optimizedWeights.value} color="#3b82f6"/>
            <WeightBar label="质量因子" value={data.optimizedWeights.quality} color="#10b981"/>
            <WeightBar label="动量因子" value={data.optimizedWeights.momentum} color="#f59e0b"/>
            <WeightBar label="情绪因子" value={data.optimizedWeights.sentiment} color="#a855f7"/>
          </div>
          <div style={{marginTop:'12px',fontSize:'12px',color:'#94a3b8'}}>💡 系统已根据历史数据自动优化因子权重</div>
        </div>
      )}
      <div style={{background:'rgba(30,41,59,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'12px',padding:'20px',marginBottom:'24px'}}>
        <h3 style={{fontSize:'18px',fontWeight:'600',marginBottom:'16px'}}>📈 组合净值曲线</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data.history}>
            <defs><linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155"/>
            <XAxis dataKey="date" stroke="#94a3b8" tick={{fontSize:12}} tickFormatter={v=>v.slice(5)}/>
            <YAxis stroke="#94a3b8" tick={{fontSize:12}}/>
            <Tooltip contentStyle={{background:'#1e293b',border:'1px solid #334155',borderRadius:'8px'}}/>
            <Area type="monotone" dataKey="nav" stroke="#3b82f6" strokeWidth={2} fill="url(#navGradient)"/>
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div style={{background:'rgba(30,41,59,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'12px',padding:'20px'}}>
        <h3 style={{fontSize:'18px',fontWeight:'600',marginBottom:'16px'}}>📋 交易明细 ({trades.length}笔)</h3>
        <div style={{maxHeight:'400px',overflowY:'auto'}}>
          <table style={{width:'100%',borderCollapse:'collapse',fontSize:'13px'}}>
            <thead>
              <tr style={{background:'rgba(15,23,42,0.6)',position:'sticky',top:0}}>
                <th style={{padding:'12px',textAlign:'left',color:'#94a3b8'}}>日期</th>
                <th style={{padding:'12px',textAlign:'left',color:'#94a3b8'}}>股票</th>
                <th style={{padding:'12px',textAlign:'center',color:'#94a3b8'}}>操作</th>
                <th style={{padding:'12px',textAlign:'right',color:'#94a3b8'}}>股数</th>
                <th style={{padding:'12px',textAlign:'right',color:'#94a3b8'}}>价格</th>
                <th style={{padding:'12px',textAlign:'right',color:'#94a3b8'}}>金额</th>
                <th style={{padding:'12px',textAlign:'right',color:'#94a3b8'}}>税金</th>
                <th style={{padding:'12px',textAlign:'right',color:'#94a3b8'}}>净额</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t:any,i:number)=>(
                <tr key={i} style={{borderBottom:'1px solid rgba(148,163,184,0.05)'}}>
                  <td style={{padding:'12px'}}>{t.date}</td>
                  <td style={{padding:'12px',fontWeight:'600'}}>{t.symbol}</td>
                  <td style={{padding:'12px',textAlign:'center'}}>
                    <span style={{padding:'4px 12px',borderRadius:'6px',fontSize:'12px',fontWeight:'600',background:t.action==='BUY'?'rgba(34,197,94,0.2)':'rgba(239,68,68,0.2)',color:t.action==='BUY'?'#22c55e':'#ef4444'}}>{t.action}</span>
                  </td>
                  <td style={{padding:'12px',textAlign:'right'}}>{t.shares}</td>
                  <td style={{padding:'12px',textAlign:'right'}}>${t.price}</td>
                  <td style={{padding:'12px',textAlign:'right',fontWeight:'600'}}>${Number(t.value).toLocaleString()}</td>
                  <td style={{padding:'12px',textAlign:'right',color:t.tax&&Number(t.tax)>0?'#ef4444':'#64748b'}}>${t.tax||'0.00'}</td>
                  <td style={{padding:'12px',textAlign:'right',fontWeight:'600',color:'#10b981'}}>${t.netValue||t.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function MetricCard({icon,label,value,color,subtitle}:any) {
  return (
    <div style={{background:'rgba(30,41,59,0.6)',border:'1px solid rgba(148,163,184,0.1)',borderRadius:'12px',padding:'20px'}}>
      <div style={{display:'flex',alignItems:'center',gap:'8px',marginBottom:'12px'}}>
        <span style={{fontSize:'20px'}}>{icon}</span>
        <span style={{fontSize:'12px',color:'#94a3b8',fontWeight:'500'}}>{label}</span>
      </div>
      <div style={{fontSize:'24px',fontWeight:'bold',color,marginBottom:'4px'}}>{value}</div>
      {subtitle&&<div style={{fontSize:'12px',color:'#64748b'}}>{subtitle}</div>}
    </div>
  );
}

function WeightBar({label,value,color}:{label:string;value:number;color:string}) {
  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',marginBottom:'6px'}}>
        <span style={{fontSize:'12px',color:'#94a3b8'}}>{label}</span>
        <span style={{fontSize:'12px',fontWeight:'600',color}}>{(value*100).toFixed(1)}%</span>
      </div>
      <div style={{width:'100%',height:'8px',background:'rgba(0,0,0,0.3)',borderRadius:'4px',overflow:'hidden'}}>
        <div style={{width:`${value*100}%`,height:'100%',background:color,borderRadius:'4px',transition:'width 0.3s ease'}}/>
      </div>
    </div>
  );
}
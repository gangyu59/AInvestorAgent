import React, { useState } from 'react';
import EquityCurve from '../components/charts/EquityCurve';
import { proposeAndBacktest, runBacktest } from '../services/api';

export default function SimulatorPage() {
  const [loading, setLoading] = useState(false);
  const [ctx, setCtx] = useState<any>(null);
  const [days, setDays] = useState(180);
  const [mock, setMock] = useState(true);

  const defaultCands = [
    { symbol:'AAPL', sector:'Technology', score:86 },
    { symbol:'MSFT', sector:'Technology', score:88 },
    { symbol:'NVDA', sector:'Technology', score:92 },
    { symbol:'AMZN', sector:'Consumer Discretionary', score:79 },
    { symbol:'META', sector:'Communication Services', score:83 },
    { symbol:'JPM', sector:'Financials', score:68 },
    { symbol:'XOM', sector:'Energy', score:65 }
  ];

  const onRun = async () => {
    setLoading(true);
    try {
      const res = await proposeAndBacktest(defaultCands, {
        'risk.max_stock':0.30, 'risk.max_sector':0.50, 'risk.count_range':[5,15],
        window_days: days, mock
      });
      setCtx(res.context);
    } catch (e) {
      console.error(e); alert('run failed');
    } finally {
      setLoading(false);
    }
  };

  const dates = ctx?.dates || ctx?.data?.dates || [];
  const nav = ctx?.nav || ctx?.data?.nav || [];
  const bench = ctx?.benchmark_nav || ctx?.data?.benchmark_nav || [];
  const drawdown = ctx?.drawdown || ctx?.data?.drawdown || [];
  const m = ctx?.metrics || ctx?.data?.metrics;

  return (
    <div className="page simulator" style={{padding:20}}>
      <h2>Simulator — Propose & Backtest</h2>
      <div style={{display:'flex', gap:16, alignItems:'center'}}>
        <label>Window (days)
          <input type="number" value={days} onChange={e=>setDays(parseInt(e.target.value||'180'))}/>
        </label>
        <label><input type="checkbox" checked={mock} onChange={()=>setMock(x=>!x)}/> Mock Data</label>
        <button disabled={loading} onClick={onRun} className="btn-primary">
          {loading ? 'Running...' : 'Propose & Backtest'}
        </button>
      </div>

      {nav.length ? (
        <>
          <div className="card" style={{marginTop:20}}>
            <h3>Equity Curve</h3>
            <EquityCurve dates={dates} nav={nav} benchmarkNav={bench} drawdown={drawdown}/>
          </div>
          {m && (
            <div className="card" style={{marginTop:20}}>
              <h3>Performance</h3>
              <ul style={{display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:8}}>
                <li>Annualized: {(m.annualized_return*100).toFixed(2)}%</li>
                <li>Sharpe: {m.sharpe}</li>
                <li>Max DD: {(m.max_drawdown*100).toFixed(2)}%</li>
                <li>Win Rate: {(m.win_rate*100).toFixed(1)}%</li>
                <li>Turnover: {m.turnover.toFixed(2)}</li>
              </ul>
            </div>
          )}
        </>
      ) : (
        <div style={{marginTop:20}}>点击“Propose & Backtest”查看净值/回撤与指标</div>
      )}
    </div>
  );
}

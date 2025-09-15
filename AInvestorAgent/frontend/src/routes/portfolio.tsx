import React, { useMemo, useState } from 'react';
import WeightsPie from '../components/charts/WeightsPie';
import SectorBars from '../components/charts/SectorBars';
import HoldingsTable from '../components/tables/HoldingsTable';
import { proposePortfolio } from '../services/api';

type Candidate = { symbol: string; sector?: string; score: number; factors?: Record<string, number> };

const DEFAULT_CANDS: Candidate[] = [
  { symbol:'AAPL', sector:'Technology', score:86, factors:{ momentum:0.72, quality:0.61, sentiment:0.58 } },
  { symbol:'MSFT', sector:'Technology', score:88, factors:{ quality:0.75, momentum:0.65, sentiment:0.56 } },
  { symbol:'NVDA', sector:'Technology', score:92, factors:{ momentum:0.82, sentiment:0.60, value:0.41 } },
  { symbol:'AMZN', sector:'Consumer Discretionary', score:79, factors:{ quality:0.62, momentum:0.57 } },
  { symbol:'META', sector:'Communication Services', score:83, factors:{ momentum:0.66, quality:0.60 } },
  { symbol:'JPM', sector:'Financials', score:68, factors:{ quality:0.58, value:0.52 } },
  { symbol:'XOM', sector:'Energy', score:65, factors:{ value:0.60, quality:0.50 } }
];

export default function PortfolioPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [params, setParams] = useState({ 'risk.max_stock':0.30, 'risk.max_sector':0.50, 'risk.count_range':[5,15] });
  const candidates = DEFAULT_CANDS; // 也可以从 Watchlist 状态读取

  const kept = result?.context?.kept || [];
  const sectorDist = result?.context?.concentration?.sector_dist || {};
  const pieData = useMemo(() => kept.map((k:any)=>({symbol:k.symbol, weight:k.weight})), [kept]);

  const onPropose = async () => {
    setLoading(true);
    try {
      const res = await proposePortfolio(candidates, params);
      setResult(res);
    } catch (e) {
      console.error(e);
      alert('propose failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page portfolio" style={{padding:20}}>
      <h2>Portfolio — Propose with Risk Constraints</h2>
      <div style={{display:'flex', gap:20, alignItems:'center'}}>
        <button disabled={loading} onClick={onPropose} className="btn-primary">
          {loading ? 'Proposing...' : 'Generate Proposal'}
        </button>
        <label>Max per stock
          <input type="number" step="0.05" value={params['risk.max_stock']}
            onChange={e=>setParams({...params, 'risk.max_stock':parseFloat(e.target.value)})}/>
        </label>
        <label>Max per sector
          <input type="number" step="0.05" value={params['risk.max_sector']}
            onChange={e=>setParams({...params, 'risk.max_sector':parseFloat(e.target.value)})}/>
        </label>
      </div>

      {kept.length ? (
        <>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginTop:20}}>
            <div className="card">
              <h3>Weights</h3>
              <WeightsPie data={pieData}/>
            </div>
            <div className="card">
              <h3>Sector Concentration</h3>
              <SectorBars sectorDist={sectorDist}/>
            </div>
          </div>
          <div className="card" style={{marginTop:20}}>
            <h3>Holdings</h3>
            <HoldingsTable rows={kept}/>
          </div>
        </>
      ) : (
        <div style={{marginTop:20}}>点击“Generate Proposal”生成组合建议</div>
      )}
    </div>
  );
}

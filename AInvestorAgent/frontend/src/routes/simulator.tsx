import { useEffect, useState } from "react";
import { runBacktest, type BacktestResponse } from "../services/endpoints";

export default function SimulatorPage() {
  const [pool, setPool] = useState("AAPL, MSFT, NVDA");
  const [bt, setBt] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string|null>(null);

  async function run() {
    setLoading(true); setErr(null);
    try {
      const symbols = pool.split(",").map(s=>s.trim().toUpperCase()).filter(Boolean);
      const r = await runBacktest({ symbols, weeks: 52, rebalance: "weekly" });
      setBt(r);
    } catch (e:any) { setErr(e?.message || "回测失败"); }
    finally { setLoading(false); }
  }

  useEffect(()=>{ run(); }, []);

  return (
    <div className="page">
      <div className="page-header" style={{gap:8}}>
        <h2>回测与模拟</h2>
        <input defaultValue={pool} onBlur={e=>setPool(e.currentTarget.value)} style={{minWidth:340}} />
        <button className="btn btn-primary" onClick={run} disabled={loading}>{loading?"回测中…":"重新回测"}</button>
      </div>

      {err && <div className="card" style={{borderColor:"#ff6b6b"}}><div className="card-body">{err}</div></div>}
      <div className="card">
        <div className="card-header"><h3>NAV vs Benchmark</h3></div>
        {bt ? <NavChart bt={bt}/> : <div className="card-body">无数据</div>}
      </div>
    </div>
  );
}

function NavChart({ bt }: { bt: BacktestResponse }) {
  const W=940,H=260,P=24;
  const nav = bt.nav || []; const bn = bt.benchmark_nav || []; const n = Math.max(nav.length, bn.length);
  if (!n) return <div className="card-body">无数据</div>;
  const all = [...nav, ...bn].filter(v=>typeof v==="number");
  const min = Math.min(...all), max = Math.max(...all), rng = (max-min)||1;
  const x = (i:number)=> P + (W-2*P) * (i/(n-1||1));
  const y = (v:number)=> P + (H-2*P) * (1 - (v-min)/rng);
  function path(arr:number[]){ let p=""; for(let i=0;i<arr.length;i++){ const v=arr[i]; if(v==null) continue; p+=`${p?"L":"M"} ${x(i)} ${y(v)} `;} return p.trim(); }
  return (
    <svg width={W} height={H} style={{display:"block"}}>
      <path d={path(nav)} fill="none" strokeWidth={2}/>
      {bn.length>0 && <path d={path(bn)} fill="none" strokeWidth={1.5} strokeOpacity={0.6}/>}
      <text x={W-90} y={18} fontSize="12">Ann: {fmtPct(bt.metrics?.ann_return)}</text>
      <text x={W-90} y={36} fontSize="12">MDD: {fmtPct(bt.metrics?.mdd)}</text>
      <text x={W-90} y={54} fontSize="12">Sharpe: {bt.metrics?.sharpe?.toFixed(2) ?? "-"}</text>
    </svg>
  );
}
function fmtPct(p?: number){ return p==null? "-" : (p*100).toFixed(1)+"%"; }

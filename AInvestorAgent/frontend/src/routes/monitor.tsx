import { useEffect, useMemo, useState } from "react";
import { fetchSentimentBrief, type SentimentBrief } from "../services/endpoints";

export default function MonitorPage() {
  const [q, setQ] = useState("AAPL, MSFT, NVDA, AMZN, GOOGL");
  const [brief, setBrief] = useState<SentimentBrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string|null>(null);

  async function load() {
    setLoading(true); setErr(null);
    try {
      const symbols = q.split(",").map(s=>s.trim().toUpperCase()).filter(Boolean);
      const b = await fetchSentimentBrief(symbols, 14);
      setBrief(b);
    } catch (e:any) { setErr(e?.message || "获取失败"); }
    finally { setLoading(false); }
  }
  useEffect(()=>{ load(); }, []);

  const chart = useMemo(()=>{
    const s = brief?.series || [];
    const W=940,H=220,P=24;
    if (!s.length) return null;
    const xs = s.map((_,i)=>i); const ys = s.map(p=>p.score);
    const min = Math.min(0, ...ys), max = Math.max(0, ...ys), rng=(max-min)||1;
    const x=(i:number)=> P + (W-2*P)*(i/(xs.length-1||1));
    const y=(v:number)=> P + (H-2*P)*(1-(v-min)/rng);
    let path=""; for(let i=0;i<s.length;i++){ const v=s[i].score; path+=`${path?"L":"M"} ${x(i)} ${y(v)} `; }
    const area = `M ${x(0)} ${y(0)} L ${path.slice(2)} L ${x(s.length-1)} ${y(0)} Z`;
    return { W,H,P,x,y,path,area };
  }, [brief]);

  return (
    <div className="page">
      <div className="page-header" style={{gap:8}}>
        <h2>舆情与监控</h2>
        <input defaultValue={q} onBlur={e=>setQ(e.currentTarget.value)} style={{minWidth:360}} />
        <button className="btn btn-primary" onClick={load} disabled={loading}>{loading?"加载中…":"刷新"}</button>
      </div>

      {err && <div className="card" style={{borderColor:"#ff6b6b"}}><div className="card-body">{err}</div></div>}

      <div className="card">
        <div className="card-header"><h3>情绪时间轴（14日）</h3></div>
        <div className="card-body">
          {chart ? (
            <svg width={chart.W} height={chart.H}>
              <path d={chart.area} fillOpacity={0.15}/>
              <path d={chart.path} fill="none" strokeWidth={2}/>
              <line x1={chart.P} y1={chart.y(0)} x2={chart.W-chart.P} y2={chart.y(0)} stroke="#2b3444" strokeDasharray="4 4"/>
            </svg>
          ) : <div>暂无数据</div>}
        </div>
      </div>

      <div className="card">
        <div className="card-header"><h3>最新新闻</h3></div>
        <ul className="news-list" style={{padding:12}}>
          {(brief?.latest_news || []).slice(0,20).map((n,i)=>(
            <li key={i} style={{margin:"6px 0"}}>
              <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
              <span className={`pill`} style={{marginLeft:6}}>{n.score?.toFixed(1)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

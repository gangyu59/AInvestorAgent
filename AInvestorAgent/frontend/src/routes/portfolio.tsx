import { useEffect, useState } from "react";
import { decideNow, type DecideResponse } from "../services/endpoints";

export default function PortfolioPage() {
  const [res, setRes] = useState<DecideResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let dead = false;
    (async () => {
      setLoading(true);
      try {
        const r = await decideNow({ symbols: ["AAPL","MSFT","NVDA","AMZN","GOOGL"] });
        if (!dead) setRes(r);
      } finally { if (!dead) setLoading(false); }
    })();
    return () => { dead = true; };
  }, []);

  const weights = Object.entries(res?.context?.weights || {}).sort((a,b)=>b[1]-a[1]);

  return (
    <div className="page">
      <h2>组合建议</h2>
      {loading ? <div>生成中…</div> : (
        <>
          <div className="hint">kept: {res?.context?.kept?.length ?? 0}，orders: {res?.context?.orders?.length ?? 0}</div>
          <ul className="list">
            {weights.map(([sym, w]) => <li key={sym}>{sym} {(w*100).toFixed(1)}%</li>)}
          </ul>
        </>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { runBacktest, type BacktestResponse } from "../services/endpoints";

export default function SimulatorPage() {
  const [bt, setBt] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let dead = false;
    (async () => {
      setLoading(true);
      try {
        const r = await runBacktest({ symbols: ["AAPL","MSFT","NVDA"], weeks: 52, rebalance: "weekly" });
        if (!dead) setBt(r);
      } finally { if (!dead) setLoading(false); }
    })();
    return () => { dead = true; };
  }, []);

  return (
    <div className="page">
      <h2>回测与模拟</h2>
      {loading ? <div>回测中…</div> : (
        <div className="kpis">
          <div>Ann.Return: {bt?.metrics?.ann_return != null ? (bt.metrics.ann_return*100).toFixed(1)+'%' : '-'}</div>
          <div>MDD: {bt?.metrics?.mdd != null ? (bt.metrics.mdd*100).toFixed(1)+'%' : '-'}</div>
          <div>Sharpe: {bt?.metrics?.sharpe?.toFixed(2) ?? '-'}</div>
          <div>Winrate: {bt?.metrics?.winrate != null ? Math.round(bt.metrics.winrate*100)+'%' : '-'}</div>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { fetchSentimentBrief, type SentimentBrief } from "../services/endpoints";

export default function MonitorPage() {
  const [brief, setBrief] = useState<SentimentBrief | null>(null);

  useEffect(() => {
    let dead = false;
    (async () => {
      const b = await fetchSentimentBrief(["AAPL","MSFT","NVDA","AMZN","GOOGL"]);
      if (!dead) setBrief(b);
    })();
    return () => { dead = true; };
  }, []);

  return (
    <div className="page">
      <h2>舆情与监控</h2>
      <ul className="news-list">
        {(brief?.latest_news || []).slice(0, 10).map((n,i)=>(
          <li key={i}><a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> <span className={`pill ${n.score>0?'up':'flat'}`}>{n.score.toFixed(1)}</span></li>
        ))}
      </ul>
    </div>
  );
}

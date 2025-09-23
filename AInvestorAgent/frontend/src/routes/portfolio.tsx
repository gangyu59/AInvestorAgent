// frontend/src/routes/portfolio.tsx
import { useEffect, useMemo, useState } from "react";
import WeightsPie from "../components/charts/WeightsPie";
import SectorBars from "../components/charts/SectorBars";
import HoldingsTable from "../components/tables/HoldingsTable";
import { API_BASE } from "../services/endpoints"; // 继续沿用你现有 endpoints.ts 的导出

type Holding = { symbol: string; weight: number; score: number; sector?: string; reasons?: string[] };
type Resp = {
  holdings: Holding[];
  sector_concentration: [string, number][];
  as_of: string;
  version_tag: string;
  snapshot_id: string;
};

const PROPOSE_URL = (API_BASE ? `${API_BASE}` : "") + "/api/portfolio/propose";

export default function PortfolioPage() {
  const [pool, setPool] = useState("AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AVGO, COST, LLY");
  const [resp, setResp] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const pieData = useMemo(() => (resp?.holdings || []).map(h => ({ symbol: h.symbol, weight: h.weight })), [resp]);
  const sectorDist = useMemo(() => {
    const obj: Record<string, number> = {};
    (resp?.sector_concentration || []).forEach(([s, w]) => { obj[s] = w; });
    return obj;
  }, [resp]);

  useEffect(() => { void onPropose(); /* eslint-disable-next-line */ }, []);

  async function onPropose() {
    const symbols = pool.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
    if (!symbols.length) return;
    setLoading(true); setErr(null);
    try {
      const r = await fetch(PROPOSE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data: Resp = await r.json();
      setResp(data);
    } catch (e: any) {
      setErr(e?.message || "生成失败");
    } finally {
      setLoading(false);
    }
  }

  function exportCSV() {
    if (!resp?.holdings?.length) return;
    const rows = [
      ["Symbol","Sector","Score","Weight","Reasons"],
      ...resp.holdings.map(h => [
        h.symbol, h.sector || "",
        (h.score ?? "").toString(),
        (h.weight * 100).toFixed(4) + "%", (h.reasons || []).join("|")
      ])
    ];
    const csv = rows.map(r => r.map(x => `"${String(x).replace(/"/g,'""')}"`).join(",")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `portfolio_${new Date().toISOString().replace(/[:T]/g,"-").slice(0,16)}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
  }

  return (
    <div className="page">
      <div className="page-header" style={{ gap: 8 }}>
        <h2>组合建议</h2>
        <input defaultValue={pool} onBlur={e => setPool(e.currentTarget.value)} style={{ minWidth: 420 }} />
        <button className="btn btn-primary" onClick={onPropose} disabled={loading}>
          {loading ? "生成中…" : "一键生成"}
        </button>
        <button className="btn" onClick={exportCSV} disabled={!resp?.holdings?.length}>
          导出 CSV
        </button>
      </div>

      {err && <div className="card" style={{ borderColor: "#ff6b6b" }}><div className="card-body">{err}</div></div>}

      {resp && (
        <>
          <div className="grid-2">
            <div className="card">
              <div className="card-header"><h3>权重饼图</h3></div>
              <div className="card-body">
                <WeightsPie data={pieData} />
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h3>行业集中度</h3></div>
              <div className="card-body">
                <SectorBars sectorDist={sectorDist} />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><h3>持仓明细</h3></div>
            <div className="card-body">
              <HoldingsTable rows={(resp.holdings || []).map(h => ({
                symbol: h.symbol, sector: h.sector, score: h.score, weight: h.weight, reason: h.reasons || []
              }))} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

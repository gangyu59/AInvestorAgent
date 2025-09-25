// frontend/src/routes/portfolio.tsx
import { useEffect, useMemo, useState } from "react";
import WeightsPie from "../components/charts/WeightsPie";
import SectorBars from "../components/charts/SectorBars";
import HoldingsTable from "../components/tables/HoldingsTable";
import { API_BASE } from "../services/endpoints"; // 沿用你现有 endpoints.ts 的导出

type Holding = { symbol: string; weight: number; score: number; sector?: string; reasons?: string[] };
type Resp = {
  holdings: Holding[];
  sector_concentration: [string, number][];
  as_of: string;
  version_tag: string;
  snapshot_id: string;
};

const PROPOSE_URL = (API_BASE ? `${API_BASE}` : "") + "/api/portfolio/propose";

// 读取 hash 参数的 symbols（形如 "#/portfolio?sid=xxx&symbols=AAPL,MSFT,TSLA"）
function readHashSymbols(): string {
  const hash = window.location.hash || "";
  const i = hash.indexOf("?");
  if (i < 0) return "";
  const sp = new URLSearchParams(hash.slice(i + 1));
  return sp.get("symbols") || "";
}

export default function PortfolioPage() {
  const hashSymbols = readHashSymbols();

  // 初始池：优先 URL 里的 symbols；否则用你原来的默认池
  const [pool, setPool] = useState(
    hashSymbols || "AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AVGO, COST, LLY"
  );
  const [resp, setResp] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const pieData = useMemo(
    () => (resp?.holdings || []).map(h => ({ symbol: h.symbol, weight: h.weight })),
    [resp]
  );

  // 你后端返回是 [sector, weight][]；这里仍转为 { [sector]: weight } 喂给 SectorBars（与你原实现一致）
  const sectorDist = useMemo(() => {
    const obj: Record<string, number> = {};
    (resp?.sector_concentration || []).forEach(([s, w]) => { obj[s] = w; });
    return obj;
  }, [resp]);

  // ✅ 仅当 URL 携带 symbols 时，首进页面自动生成一次；否则等待用户点击“一键生成”
  useEffect(() => {
    if (hashSymbols) {
      const list = hashSymbols.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
      void onPropose(list);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 支持可选入参：若传入 list，则用它；否则用输入框 pool
  async function onPropose(list?: string[]) {
    const symbols = (list && list.length)
      ? list
      : pool.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);

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
        h.symbol,
        h.sector || "",
        (h.score ?? "").toString(),
        (h.weight * 100).toFixed(4) + "%",
        (h.reasons || []).join("|")
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
      <div className="page-header" style={{gap: 8}}>
        <h2>组合建议</h2>
        <input
            defaultValue={pool}
            onBlur={e => setPool(e.currentTarget.value)}
            style={{minWidth: 420}}
            placeholder="用逗号或空格分隔股票，如：AAPL, MSFT, TSLA"
        />
        <button className="btn btn-primary" onClick={() => onPropose()} disabled={loading}>
          {loading ? "生成中…" : "一键生成"}
        </button>
        <button className="btn" onClick={exportCSV} disabled={!resp?.holdings?.length}>
          导出 CSV
        </button>
        <button
            className="btn"
            onClick={() => {
              if (!resp?.snapshot_id) {
                alert("当前无有效快照，先点『一键生成』产出组合。");
                return;
              }
              // 跳转到回测页，携带 sid
              window.location.hash = `#/simulator?sid=${encodeURIComponent(resp.snapshot_id)}`;
            }}
            disabled={!resp?.snapshot_id}
        >
          Run Backtest
        </button>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#ff6b6b" }}>
          <div className="card-body">{err}</div>
        </div>
      )}

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
              <HoldingsTable
                rows={(resp.holdings || []).map(h => ({
                  symbol: h.symbol,
                  sector: h.sector,
                  score: h.score,
                  weight: h.weight,
                  // ✅ 对齐后端：reasons（复数）
                  reasons: h.reasons || []
                }))}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

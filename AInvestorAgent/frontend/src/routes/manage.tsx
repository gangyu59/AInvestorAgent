// frontend/src/routes/manage.tsx
import { useEffect, useMemo, useState } from "react";

// 兼容两种导出方式：default 或 命名导出 RadarFactors
import * as RadarModule from "../components/charts/RadarFactors";
const RadarFactors: any =
  (RadarModule as any).default ??
  (RadarModule as any).RadarFactors ??
  (RadarModule as any);

// ============= 仅用于“批量评分 Watchlist”的最小 API 封装 =============
async function scoreBatch(symbols: string[], mock = false) {
  const resp = await fetch("/api/scores/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols, mock }),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`HTTP ${resp.status} /api/scores/batch ${text}`);
  }
  const data = (await resp.json()) as {
    as_of: string;
    version_tag: string;
    items: {
      symbol: string;
      factors?: {
        f_value?: number;
        f_quality?: number;
        f_momentum?: number;
        f_sentiment?: number;
        f_risk?: number;
      };
      score?: {
        value?: number;
        quality?: number;
        momentum?: number;
        sentiment?: number;
        score?: number;
        version_tag?: string;
      };
      updated_at?: string;
    }[];
  };
  return data;
}

type BatchItem = {
  symbol: string;
  factors?: {
    f_value?: number;
    f_quality?: number;
    f_momentum?: number;
    f_sentiment?: number;
    f_risk?: number;
  };
  score?: {
    value?: number;
    quality?: number;
    momentum?: number;
    sentiment?: number;
    score?: number;
    version_tag?: string;
  };
  updated_at?: string;
};

type SortKey =
  | "symbol"
  | "score"
  | "value"
  | "quality"
  | "momentum"
  | "sentiment"
  | "updated_at";

const DEFAULT_LIST = [
  "AAPL",
  "MSFT",
  "NVDA",
  "AMZN",
  "GOOGL",
  "META",
  "TSLA",
  "AMD",
  "AVGO",
  "ADBE",
];

export default function ManagePage() {
  const [symbolsText, setSymbolsText] = useState<string>(DEFAULT_LIST.join(","));
  const [rows, setRows] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<{ as_of?: string; version?: string } | null>(null);

  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [asc, setAsc] = useState(false);

  const symbols = useMemo(
    () =>
      symbolsText
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean),
    [symbolsText]
  );

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const data = await scoreBatch(symbols, false);
      const items = (data.items || []).filter(Boolean);
      items.sort((a, b) => (b.score?.score || 0) - (a.score?.score || 0)); // 默认总分降序
      setRows(items);
      setInfo({ as_of: data.as_of, version: data.version_tag });
    } catch (e: any) {
      setErr(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(); // 初次加载（void 去除“Missing await”告警）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sorted = useMemo(() => {
    const arr = [...rows];
    const getVal = (x: BatchItem) => {
      switch (sortKey) {
        case "symbol":
          return x.symbol;
        case "updated_at":
          return x.updated_at || "";
        case "score":
          return x.score?.score ?? -Infinity;
        case "value":
          return x.score?.value ?? -Infinity;
        case "quality":
          return x.score?.quality ?? -Infinity;
        case "momentum":
          return x.score?.momentum ?? -Infinity;
        case "sentiment":
          return x.score?.sentiment ?? -Infinity;
      }
    };
    arr.sort((a, b) => {
      const va = getVal(a) as any;
      const vb = getVal(b) as any;
      if (va === vb) return 0;
      return (va > vb ? 1 : -1) * (asc ? 1 : -1);
    });
    return arr;
  }, [rows, sortKey, asc]);

  const onSort = (k: SortKey) => {
    if (sortKey === k) setAsc(!asc);
    else {
      setSortKey(k);
      setAsc(false);
    }
  };

  return (
    <div className="page" style={{ padding: 16 }}>
      <div className="page-header" style={{ marginBottom: 12 }}>
        <h2>Watchlist 批量评分</h2>
        {info && (
          <div style={{ color: "#6b7280", fontSize: 12 }}>
            as_of: {info.as_of} · version: {info.version}
          </div>
        )}
      </div>

      <div
        className="toolbar"
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          flexWrap: "wrap",
          marginBottom: 12,
        }}
      >
        <input
          className="input"
          placeholder="逗号分隔：AAPL,MSFT,NVDA,…"
          value={symbolsText}
          onChange={(e) => setSymbolsText(e.target.value)}
          style={{ minWidth: 520, height: 36, padding: "0 10px" }}
        />
        <button
          className="btn"
          onClick={() => void load()}
          disabled={loading}
          style={{ height: 36 }}
        >
          {loading ? "加载中…" : "刷新评分"}
        </button>
      </div>

      {err && (
        <div
          className="card"
          style={{
            border: "1px solid #fecaca",
            background: "#fff1f2",
            color: "#b91c1c",
            padding: 12,
            borderRadius: 8,
            marginBottom: 12,
          }}
        >
          {err}
        </div>
      )}

      <div className="table-wrap" style={{ overflowX: "auto" }}>
        <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <Th onClick={() => onSort("symbol")} label="代码" active={sortKey === "symbol"} asc={asc} />
              <Th onClick={() => onSort("score")} label="分数" active={sortKey === "score"} asc={asc} />
              <th style={thStyle}>迷你雷达</th>
              <Th onClick={() => onSort("value")} label="价值" active={sortKey === "value"} asc={asc} />
              <Th onClick={() => onSort("quality")} label="质量" active={sortKey === "quality"} asc={asc} />
              <Th onClick={() => onSort("momentum")} label="动量" active={sortKey === "momentum"} asc={asc} />
              <Th onClick={() => onSort("sentiment")} label="情绪" active={sortKey === "sentiment"} asc={asc} />
              <Th onClick={() => onSort("updated_at")} label="更新时间" active={sortKey === "updated_at"} asc={asc} />
              <th style={thStyle}>版本</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const f = r.factors || {};
              const s = r.score || {};
              return (
                <tr key={r.symbol}>
                  <Td>{r.symbol}</Td>
                  <Td bold>{fmtNum(s.score, 1, "--")}</Td>
                  <td style={tdStyle}>
                    <div style={{ width: 140, height: 90 }}>
                      <RadarFactors
                        data={{
                          value: f.f_value ?? 0,
                          quality: f.f_quality ?? 0,
                          momentum: f.f_momentum ?? 0,
                          sentiment: f.f_sentiment ?? 0,
                          risk: f.f_risk ?? 0,
                        }}
                        factors={{
                          value: f.f_value ?? 0,
                          quality: f.f_quality ?? 0,
                          momentum: f.f_momentum ?? 0,
                          sentiment: f.f_sentiment ?? 0,
                          risk: f.f_risk ?? 0,
                        }}
                        compact
                        mini
                        size="sm"
                      />
                    </div>
                  </td>
                  <Td>{fmtNum(s.value, 0, "-")}</Td>
                  <Td>{fmtNum(s.quality, 0, "-")}</Td>
                  <Td>{fmtNum(s.momentum, 0, "-")}</Td>
                  <Td>{fmtNum(s.sentiment, 0, "-")}</Td>
                  <Td>{r.updated_at ? new Date(r.updated_at).toLocaleString() : "-"}</Td>
                  <Td>{s.version_tag || info?.version || "-"}</Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ===== 轻量 UI 组件 =====
const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 8px",
  borderBottom: "1px solid #e5e7eb",
  whiteSpace: "nowrap",
  cursor: "pointer",
  userSelect: "none",
  fontWeight: 600,
};
const tdStyle: React.CSSProperties = {
  padding: "10px 8px",
  borderBottom: "1px solid #f3f4f6",
  whiteSpace: "nowrap",
  verticalAlign: "middle",
};

function Th({
  label,
  onClick,
  active,
  asc,
}: {
  label: string;
  onClick: () => void;
  active?: boolean;
  asc?: boolean;
}) {
  return (
    <th onClick={onClick} style={{ ...thStyle, color: active ? "#111827" : "#374151" }}>
      {label}
      {active && <span style={{ marginLeft: 4, opacity: 0.7 }}>{asc ? "▲" : "▼"}</span>}
    </th>
  );
}

function Td({ children, bold }: { children: React.ReactNode; bold?: boolean }) {
  return <td style={{ ...tdStyle, fontWeight: bold ? 700 : 400 }}>{children}</td>;
}

function fmtNum(v: any, fixed = 2, dash = "") {
  if (v === null || v === undefined || Number.isNaN(v)) return dash;
  const n = Number(v);
  if (!Number.isFinite(n)) return dash;
  return n.toFixed(fixed);
}

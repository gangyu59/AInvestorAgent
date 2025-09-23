// frontend/src/routes/manage.tsx
import { useEffect, useMemo, useState } from "react";

// 兼容两种导出方式：default 或 命名导出 RadarFactors
// （不要改路径：按你的文件树在 components/charts/ 下）
import * as RadarModule from "../components/charts/RadarFactors";
const RadarFactors: any =
  (RadarModule as any).default ??
  (RadarModule as any).RadarFactors ??
  (RadarModule as any);

// ============= 仅用于“批量评分 Watchlist”的局部 API 封装 =============
// 不依赖 endpoints.ts；也不导出任何全局常量，避免重复定义冲突
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
  return (await resp.json()) as {
    as_of?: string;
    version_tag?: string;
    items: BatchItem[];
  };
}

// ============= 类型（宽松即可跑通） =============
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

const DEFAULT_LIST = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "ADBE"];

// ============= 页面组件 =============
export default function ManagePage() {
  const [symbolsText, setSymbolsText] = useState(DEFAULT_LIST.join(","));
  const [rows, setRows] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<{ as_of?: string; version?: string } | null>(null);

  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [asc, setAsc] = useState(false);
  const [picked, setPicked] = useState<string[]>([]); // “加入组合”临时选择

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
      // 默认按总分降序
      items.sort((a, b) => (b.score?.score || 0) - (a.score?.score || 0));
      setRows(items);
      setInfo({ as_of: data.as_of, version: data.version_tag });
    } catch (e: any) {
      setErr(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
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

  const togglePick = (sym: string) => {
    setPicked((prev) => (prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]));
  };

  return (
    <div className="page" style={{ padding: 16 }}>
      <div className="page-header" style={{ marginBottom: 12 }}>
        <h2>Watchlist 批量评分</h2>
        {info && (
          <div style={{ color: "#6b7280", fontSize: 12 }}>
            as_of: {info.as_of || "--"} · version: {info.version || "--"}
          </div>
        )}
      </div>

      <div
        className="toolbar"
        style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}
      >
        <input
          className="input"
          placeholder="逗号分隔：AAPL,MSFT,NVDA,…"
          value={symbolsText}
          onChange={(e) => setSymbolsText(e.target.value)}
          style={{ minWidth: 520, height: 36, padding: "0 10px" }}
        />
        <button className="btn" onClick={() => void load()} disabled={loading} style={{ height: 36 }}>
          {loading ? "加载中…" : "刷新评分"}
        </button>
        {picked.length > 0 && (
          <span style={{ marginLeft: 8, fontSize: 12, color: "#10b981" }}>
            已选 {picked.length} 只（用于组合）
          </span>
        )}
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
              <th style={thStyle}>到个股页</th>
              <th style={thStyle}>加入组合</th>
            </tr>
          </thead>

          <tbody>
            {sorted.map((r) => {
              const s = r.score || {};
              const radar = {
                value: (r.factors?.f_value ?? s.value ?? 0) / 100,
                quality: (r.factors?.f_quality ?? s.quality ?? 0) / 100,
                momentum: (r.factors?.f_momentum ?? s.momentum ?? 0) / 100,
                sentiment: (r.factors?.f_sentiment ?? s.sentiment ?? 0) / 100,
                risk: (r.factors?.f_risk ?? 0) / 100,
              };
              const updated = r.updated_at || info?.as_of || "--";
              const version = s.version_tag || info?.version || "--";
              const href = `/#/stock?symbol=${encodeURIComponent(r.symbol)}`;

              return (
                <tr key={r.symbol}>
                  <Td>{r.symbol}</Td>
                  <Td bold>{fmtNum(s.score, 1, "--")}</Td>

                  <td style={tdStyle}>
                    <div style={{ width: 84, height: 72 }}>
                      {/* RadarFactors 已存在于你的组件库，这里按“迷你”形态使用 */}
                      <RadarFactors data={radar} mini />
                    </div>
                  </td>

                  <Td>{fmtNum(s.value, 1, "--")}</Td>
                  <Td>{fmtNum(s.quality, 1, "--")}</Td>
                  <Td>{fmtNum(s.momentum, 1, "--")}</Td>
                  <Td>{fmtNum(s.sentiment, 1, "--")}</Td>
                  <Td>{updated}</Td>
                  <Td>{version}</Td>

                  <td style={tdStyle}>
                    <a href={href} style={{ textDecoration: "underline" }}>
                      查看
                    </a>
                  </td>
                  <td style={tdStyle}>
                    <button
                      className="btn"
                      onClick={() => togglePick(r.symbol)}
                      style={{ height: 28, padding: "0 10px" }}
                    >
                      {picked.includes(r.symbol) ? "移除" : "加入"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============= 小工具 =============
function fmtNum(v?: number, d = 1, fallback = "--") {
  if (v === undefined || v === null || Number.isNaN(v)) return fallback;
  return Number(v).toFixed(d);
}

function Th({
  onClick,
  label,
  active,
  asc,
}: {
  onClick: () => void;
  label: string;
  active?: boolean;
  asc?: boolean;
}) {
  return (
    <th
      onClick={onClick}
      style={{
        ...thStyle,
        cursor: "pointer",
        color: active ? "#60a5fa" : undefined,
        whiteSpace: "nowrap",
      }}
      title="点击切换排序"
    >
      {label} {active ? (asc ? "↑" : "↓") : ""}
    </th>
  );
}

function Td({
  children,
  bold,
}: {
  children: any;
  bold?: boolean;
}) {
  return (
    <td style={{ ...tdStyle, fontWeight: bold ? 700 : 400 }}>
      <span>{children}</span>
    </td>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 8px",
  borderBottom: "1px solid #e5e7eb",
  fontWeight: 600,
  fontSize: 13,
};

const tdStyle: React.CSSProperties = {
  padding: "10px 8px",
  borderBottom: "1px solid #f1f5f9",
  fontSize: 13,
};

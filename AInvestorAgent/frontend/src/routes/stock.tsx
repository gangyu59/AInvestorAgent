// frontend/src/routes/stock.tsx
import React from "react";
import { useSearchParams } from "react-router-dom";
import { fetchFundamentals, fetchMetrics, FundamentalsResp, MetricsResp } from "../services/api";
import FactorCard from "../components/cards/FactorCard";
import MomentumBars from "../components/charts/MomentumBars";
// 假设你已有价格图组件
import PriceChart from "../components/charts/PriceChart";

function normalizeTo01(v: number, min: number, max: number) {
  if (!isFinite(v) || max === min) return 0;
  const x = (v - min) / (max - min);
  return Math.min(1, Math.max(0, x));
}

export default function Stock() {
  const [sp] = useSearchParams();
  const [symbol, setSymbol] = React.useState(sp.get("symbol") || "AAPL");

  const [fund, setFund] = React.useState<FundamentalsResp | null>(null);
  const [metr, setMetr] = React.useState<MetricsResp | null>(null);

  const [loadingF, setLoadingF] = React.useState(false);
  const [loadingM, setLoadingM] = React.useState(false);
  const [errF, setErrF] = React.useState<string | null>(null);
  const [errM, setErrM] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoadingF(true); setErrF(null);
    fetchFundamentals(symbol)
      .then(setFund)
      .catch(e => setErrF(String(e)))
      .finally(() => setLoadingF(false));
  }, [symbol]);

  React.useEffect(() => {
    setLoadingM(true); setErrM(null);
    fetchMetrics(symbol)
      .then(setMetr)
      .catch(e => setErrM(String(e)))
      .finally(() => setLoadingM(false));
  }, [symbol]);

  // ---- 基本面 → 四象限标准化（示例口径，与文档一致）
  // 估值：PB、PE 反向 ⇒ 值越低越好
  // 质量：ROE、净利率 越高越好
  // 成长：先与质量同源（若你有TTM增长率后续替换）
  // 风险：波动率反向（依赖 metrics.volatility）
  const factors = React.useMemo(() => {
    if (!fund || !metr) return null;

    const pe = fund.pe; const pb = fund.pb;
    const roe = fund.roe; const nm = fund.net_margin;

    // 简单分位/缩放（可替换为你 factors/transforms 的统一口径）
    const invPB = 1 - normalizeTo01(pb, 0, 20);
    const invPE = 1 - normalizeTo01(pe, 0, 60);
    const value = Math.max(0, Math.min(1, 0.5 * invPB + 0.5 * invPE));

    const qRoe = normalizeTo01(roe, 0, 40);
    const qNm  = normalizeTo01(nm, 0, 40);
    const quality = Math.max(0, Math.min(1, 0.5 * qRoe + 0.5 * qNm));

    const growth = quality; // 占位：后续用营收/净利增长替代

    const vol = metr.volatility ?? 0;
    const risk = 1 - normalizeTo01(vol, 0, 0.1); // 假设 10% 为高波动上限

    return { value, quality, growth, risk };
  }, [fund, metr]);

  const bars = React.useMemo(() => {
    if (!metr) return null;
    return {
      "1M": Number(metr.one_month_change.toFixed(2)),
      "3M": Number(metr.three_months_change.toFixed(2)),
      "12M": Number(metr.twelve_months_change.toFixed(2)),
    };
  }, [metr]);

  return (
    <div className="p-4 space-y-4 text-white">
      <div className="flex items-center gap-2">
        <input
          className="bg-[#0f1115] border border-gray-700 rounded-xl px-3 py-2"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.trim().toUpperCase())}
          placeholder="输入股票代码，如 AAPL"
        />
        <div className="text-sm opacity-60">个股：行情 + 基本面 + 动量</div>
      </div>

      {/* 价格折线（你已有组件） */}
      <PriceChart symbol={symbol} range="3M" />

      {/* 上：基本面雷达 */}
      <FactorCard
        loading={loadingF || loadingM}
        error={errF || errM}
        factors={factors}
        updatedAt={fund?.as_of || metr?.as_of}
      />

      {/* 下：动量条形 */}
      <MomentumBars
        loading={loadingM}
        error={errM}
        bars={bars}
        updatedAt={metr?.as_of}
      />
    </div>
  );
}

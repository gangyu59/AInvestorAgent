// frontend/src/components/cards/FactorCard.tsx
import React from "react";
import * as echarts from "echarts";

type Props = {
  loading?: boolean;
  error?: string | null;
  // 0~1 范围的四象限：估值/质量/成长/风险（风险越低得分越高）
  factors: { value: number; quality: number; growth: number; risk: number } | null;
  updatedAt?: string;
};

export default function FactorCard({ loading, error, factors, updatedAt }: Props) {
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const data = factors
      ? [factors.value, factors.quality, factors.growth, factors.risk]
      : [0, 0, 0, 0];

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      title: { text: "因子雷达", left: 10, top: 8, textStyle: { fontSize: 14 } },
      tooltip: {},
      radar: {
        indicator: [
          { name: "估值", max: 1 },
        { name: "质量", max: 1 },
        { name: "成长", max: 1 },
        { name: "风险", max: 1 },
        ],
        splitNumber: 4,
        axisName: { color: "#aaa" },
      },
      series: [
        {
          type: "radar",
          data: [{ value: data, name: "标准化因子" }],
          areaStyle: { opacity: 0.15 },
          lineStyle: { width: 2 },
          symbol: "none",
        },
      ],
    };

    chart.setOption(option);
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [factors]);

  return (
    <div className="rounded-2xl shadow p-4 bg-[#0f1115] text-white">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm opacity-70">
          {updatedAt ? `数据时间戳：${updatedAt}` : "数据时间戳：--"}
        </div>
        {loading && <div className="text-xs">加载中…</div>}
        {error && <div className="text-xs text-red-400">错误：{error}</div>}
      </div>
      <div className="grid grid-cols-4 gap-3 text-xs mb-3">
        <div>估值：{factors ? factors.value.toFixed(2) : "--"}</div>
        <div>质量：{factors ? factors.quality.toFixed(2) : "--"}</div>
        <div>成长：{factors ? factors.growth.toFixed(2) : "--"}</div>
        <div>风险：{factors ? factors.risk.toFixed(2) : "--"}</div>
      </div>
      <div ref={ref} style={{ width: "100%", height: 260 }} />
    </div>
  );
}

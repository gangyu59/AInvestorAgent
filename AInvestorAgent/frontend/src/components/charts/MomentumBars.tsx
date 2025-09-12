// frontend/src/components/charts/MomentumBars.tsx
import React from "react";
import * as echarts from "echarts";

type Props = {
  loading?: boolean;
  error?: string | null;
  bars: { "1M": number; "3M": number; "12M": number } | null; // 百分比
  updatedAt?: string;
};

export default function MomentumBars({ loading, error, bars, updatedAt }: Props) {
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const cats = ["1M", "3M", "12M"];
    const vals = bars ? [bars["1M"], bars["3M"], bars["12M"]] : [0, 0, 0];

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      title: { text: "动量条形（涨跌%）", left: 10, top: 8, textStyle: { fontSize: 14 } },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => `${v}%` },
      xAxis: { type: "category", data: cats, axisTick: { alignWithLabel: true } },
      yAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
      series: [{
        type: "bar",
        data: vals,
        label: { show: true, position: "top", formatter: ({ value }) => `${value}%` },
        itemStyle: {
          color: (params: any) => (params.value >= 0 ? "#16a34a" : "#dc2626"), // 绿涨红跌
        },
      }],
      grid: { left: 40, right: 16, top: 48, bottom: 24 },
    };

    chart.setOption(option);
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [bars]);

  return (
    <div className="rounded-2xl shadow p-4 bg-[#0f1115] text-white">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm opacity-70">
          {updatedAt ? `数据时间戳：${updatedAt}` : "数据时间戳：--"}
        </div>
        {loading && <div className="text-xs">加载中…</div>}
        {error && <div className="text-xs text-red-400">错误：{error}</div>}
      </div>
      <div ref={ref} style={{ width: "100%", height: 260 }} />
    </div>
  );
}

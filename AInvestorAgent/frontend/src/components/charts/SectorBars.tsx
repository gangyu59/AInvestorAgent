// frontend/src/components/SectorBars.tsx
import * as React from "react";
import ReactECharts from "echarts-for-react";

// 支持两种输入：对象 {sector: weight} 或 二元组数组 [sector, weight][]
type SectorPair = [string, number];
type SectorInput = Record<string, number> | SectorPair[];

export default function SectorBars({ sectorDist }: { sectorDist: SectorInput }) {
  // 统一收敛到可变数组 Array<[string, number]>
  const pairs: SectorPair[] = Array.isArray(sectorDist)
    ? (sectorDist as SectorPair[]).map((p) => [p[0], p[1]] as SectorPair) // 明确复制，去掉只读推断
    : (Object.entries(sectorDist) as SectorPair[]);

  // 避免 “readonly tuple” 的参数解构：改用 p[0]/p[1] 访问
  const names = pairs.map((p) => p[0]);
  const vals  = pairs.map((p) => +(p[1] * 100).toFixed(2));

  // 空数据兜底
  if (pairs.length === 0) {
    return <div style={{ height: 280, display: "flex", alignItems: "center", color: "#aaa" }}>暂无行业数据</div>;
  }

  const option = {
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: "category", data: names, axisLabel: { color: "#ddd" } },
    yAxis: { type: "value", axisLabel: { color: "#ddd", formatter: "{value}%"} },
    series: [{ type: "bar", data: vals }],
    tooltip: { trigger: "axis", valueFormatter: (v: any) => v + "%" },
    darkMode: true,
  };

  return <ReactECharts style={{ height: 280 }} option={option} />;
}

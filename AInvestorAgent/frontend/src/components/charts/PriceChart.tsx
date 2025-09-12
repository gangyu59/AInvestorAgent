// frontend/src/components/charts/PriceChart.tsx
import * as React from "react";
import * as echarts from "echarts";

type Point = { date: string; close: number | null };

function calcMA(series: Point[], window: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0, q: number[] = [];
  for (let i = 0; i < series.length; i++) {
    const v = series[i].close ?? 0;
    q.push(v); sum += v;
    if (q.length > window) sum -= q.shift()!;
    out.push(q.length === window ? +(sum / window).toFixed(2) : null);
  }
  return out;
}

export default function PriceChart({ data }: { data: Point[] }) {
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current as HTMLDivElement);
    const dates = data.map(d => d.date);
    const closes = data.map(d => d.close ?? null);
    chart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 20, top: 30, bottom: 30 },
      xAxis: { type: "category", data: dates },
      yAxis: { type: "value", scale: true },
      series: [
        { type: "line", name: "Close", data: closes, showSymbol: false },
        { type: "line", name: "MA20", data: calcMA(data, 20), showSymbol: false, smooth: true },
        { type: "line", name: "MA60", data: calcMA(data, 60), showSymbol: false, smooth: true },
      ],
      legend: { top: 0 }
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); chart.dispose(); };
  }, [data]);
  return <div ref={ref} style={{ width: "100%", height: 400 }} />;
}

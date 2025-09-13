import React from "react";
import * as echarts from "echarts";
import type { TestRun } from "../../services/qa";

export default function PassRateChart({ runs }: { runs: TestRun[] }) {
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const x = runs.map(r => r.timestamp).reverse();
    const y = runs.map(r => r.pass_rate).reverse();

    chart.setOption({
      title: { text: "通过率曲线（%）", left: 10, top: 8, textStyle: { fontSize: 14 } },
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: x },
      yAxis: { type: "value", min: 0, max: 100, axisLabel: { formatter: "{value}%" } },
      series: [{ type: "line", data: y, smooth: true, showSymbol: false }],
      grid: { left: 48, right: 16, top: 48, bottom: 40 },
      dataZoom: [{ type: "inside" }, { type: "slider" }],
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); chart.dispose(); };
  }, [runs]);

  return <div ref={ref} style={{ width: "100%", height: 320 }} />;
}

import React from "react";
import * as echarts from "echarts";
import type { TestRun } from "../../services/qa";

export default function SuiteBar({ latest }: { latest: TestRun | null }) {
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!ref.current || !latest) return;
    const c = echarts.init(ref.current);
    const s = latest.stats;
    c.setOption({
      title: { text: `最近一次用例分布（${latest.timestamp}）`, left: 10, top: 8, textStyle: { fontSize: 14 } },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "category", data: ["用例数"] },
      yAxis: { type: "value" },
      series: [
        { name: "通过", type: "bar", stack: "total", data: [s.passed] },
        { name: "失败", type: "bar", stack: "total", data: [s.failed] },
        { name: "错误", type: "bar", stack: "total", data: [s.errors] },
        { name: "跳过", type: "bar", stack: "total", data: [s.skipped] },
      ],
      legend: { top: 28 },
      grid: { left: 48, right: 16, top: 60, bottom: 24 },
    });
    const onResize = () => c.resize();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); c.dispose(); };
  }, [latest]);

  return <div ref={ref} style={{ width: "100%", height: 240 }} />;
}

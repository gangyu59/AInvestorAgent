import React, { useEffect, useRef } from "react";

type Point = { label: string; value: number };

const RequestsChart: React.FC<{ points: Point[] }> = ({ points }) => {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current!;
    el.innerHTML = "";
    el.classList.add("chart-area");
    // 原生 SVG 占位，便于后续替换 ECharts/Chart.js（不改组件接口）
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "240");
    svg.style.display = "block";

    const w = el.clientWidth || 800;
    const h = 240;
    const pad = 24;
    const max = Math.max(1, ...points.map((p) => p.value));
    const stepX = points.length > 1 ? (w - pad * 2) / (points.length - 1) : 0;

    const pathD = points
      .map((p, i) => {
        const x = pad + i * stepX;
        const y = h - pad - (p.value / max) * (h - pad * 2);
        return `${i === 0 ? "M" : "L"}${x},${y}`;
      })
      .join(" ");

    const path = document.createElementNS(svgNS, "path");
    path.setAttribute("d", pathD);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "2");
    svg.appendChild(path);
    el.appendChild(svg);
  }, [points]);

  return <div ref={ref} aria-label="请求趋势图" />;
};

export default RequestsChart;

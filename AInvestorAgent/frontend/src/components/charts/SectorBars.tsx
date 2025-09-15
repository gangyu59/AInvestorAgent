import React from 'react';
import ReactECharts from 'echarts-for-react';

export default function SectorBars({ sectorDist }: { sectorDist: Record<string, number> }) {
  const names = Object.keys(sectorDist);
  const vals = names.map(k => +(sectorDist[k]*100).toFixed(2));
  const option = {
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: names, axisLabel: { color: '#ddd' } },
    yAxis: { type: 'value', axisLabel: { color: '#ddd', formatter: '{value}%'} },
    series: [{ type: 'bar', data: vals }],
    tooltip: { trigger: 'axis', valueFormatter: (v:any)=> v+'%' },
    darkMode: true
  };
  return <ReactECharts style={{height: 280}} option={option} />;
}

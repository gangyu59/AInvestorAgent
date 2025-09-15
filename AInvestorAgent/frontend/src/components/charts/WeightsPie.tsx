import React from 'react';
import ReactECharts from 'echarts-for-react';

export type Weight = { symbol: string; weight: number };
export default function WeightsPie({ data }: { data: Weight[] }) {
  const option = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { left: 'left', textStyle: { color: '#ddd' } },
    series: [{
      type: 'pie', radius: '65%', center: ['50%','55%'],
      data: data.map(d => ({ name: d.symbol, value: +(d.weight*100).toFixed(2) })),
      label: { color: '#ddd', formatter: '{b}: {c}%' }
    }],
    darkMode: true
  };
  return <ReactECharts style={{height: 320}} option={option} />;
}

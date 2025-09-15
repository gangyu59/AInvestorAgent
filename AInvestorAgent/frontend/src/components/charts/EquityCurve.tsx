import React from 'react';
import ReactECharts from 'echarts-for-react';

export default function EquityCurve({
  dates, nav, benchmarkNav, drawdown
}: { dates: string[]; nav: number[]; benchmarkNav?: number[]; drawdown?: number[] }) {
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Portfolio','Benchmark','Drawdown'], textStyle:{color:'#ddd'} },
    grid: [{ left: 50, right: 20, height: '60%' }, { left: 50, right: 20, top: '70%', height: '20%' }],
    xAxis: [{ type: 'category', data: dates, axisLabel:{color:'#aaa'} }, { type: 'category', data: dates, gridIndex:1, axisLabel:{color:'#aaa'} }],
    yAxis: [{ type:'value', axisLabel:{color:'#aaa'} }, { type:'value', gridIndex:1, axisLabel:{color:'#aaa', formatter:'{value}%'} }],
    series: [
      { name:'Portfolio', type:'line', data: nav },
      ...(benchmarkNav && benchmarkNav.length ? [{ name:'Benchmark', type:'line', data: benchmarkNav }] : []),
      ...(drawdown && drawdown.length ? [{ name:'Drawdown', type:'line', xAxisIndex:1, yAxisIndex:1, data: drawdown.map(x=>(x*100)) }] : [])
    ],
    darkMode: true
  };
  return <ReactECharts style={{height: 420}} option={option} />;
}

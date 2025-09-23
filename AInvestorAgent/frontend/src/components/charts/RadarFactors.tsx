// frontend/src/components/charts/RadarFactors.tsx
import ReactECharts from 'echarts-for-react';

interface FactorRadarProps {
  factors: {
    value: number;
    quality: number;
    momentum: number;
    sentiment: number;
  };
}

/** 输入可为 0..1 或 0..100，统一按 0..100 显示 */
export default function RadarFactors({ factors }: FactorRadarProps) {
  if (!factors) return <div>无因子数据</div>;

  const to100 = (x: number) => (x <= 1 ? x * 100 : x);
  const vals = [
    to100(factors.value),
    to100(factors.quality),
    to100(factors.momentum),
    to100(factors.sentiment),
  ];

  const option = {
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '价值', max: 100 },
        { name: '质量', max: 100 },
        { name: '动量', max: 100 },
        { name: '情绪', max: 100 },
      ],
      axisName: { color: '#ddd' },
      splitLine: { lineStyle: { opacity: 0.4 } },
      splitArea: { areaStyle: { opacity: 0.04 } },
    },
    series: [
      { type: 'radar', data: [{ value: vals }], areaStyle: { opacity: 0.3 } }
    ],
    darkMode: true,
  };

  return <ReactECharts style={{ height: 250 }} option={option} />;
}

// frontend/src/components/charts/RadarFactors.tsx
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";

interface FactorRadarProps {
  factors: {
    value: number;
    quality: number;
    momentum: number;
    sentiment: number;
  };
}

export default function RadarFactors({ factors }: FactorRadarProps) {
  if (!factors) return <div>无因子数据</div>;

  const data = [
    { name: "价值", score: factors.value },
    { name: "质量", score: factors.quality },
    { name: "动量", score: factors.momentum },
    { name: "情绪", score: factors.sentiment },
  ];

  return (
    <ResponsiveContainer width="100%" height={250}>
      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="name" />
        <PolarRadiusAxis domain={[0, 100]} />
        <Radar
          name="因子得分"
          dataKey="score"
          stroke="#8884d8"
          fill="#8884d8"
          fillOpacity={0.6}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
